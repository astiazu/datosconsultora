# app/routes/servicios.py
import os
import json
from uuid import uuid4
from flask import Blueprint, render_template, request, flash, current_app, redirect, url_for
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app import db
from app.models import UserFile, Transcription, AnalysisSession
from app.services.transcription.groq_backend import GroqBackend
from app.services.analysis_service import AnalysisService
from app.services.analysis.text_cleaner import limpiar_comentarios
from app.services.plan_service import puede_transcribir, registrar_uso_transcripcion, puede_analizar, registrar_uso_analisis

servicios_bp = Blueprint("servicios", __name__)

ALLOWED_EXT = {"mp3", "wav", "m4a", "mp4", "mov", "avi", "mkv", "webm", "flac", "ogg"}


@servicios_bp.route("/servicios/transcripcion", methods=["GET", "POST"])
@login_required
def servicio_transcripcion():
    transcript = None
    transcript_traducido = None
    filename = None
    idioma_detectado = "es"
    duracion_total = 0
    num_chunks = 1
    
    if request.method == "POST":
        f = request.files.get("media")
        if f and f.filename:
            ext = f.filename.rsplit(".", 1)[-1].lower()
            if ext in ALLOWED_EXT:
                puede_usar, uso_actual, limite = puede_transcribir(current_user)
                if not puede_usar:
                    flash(f" Has alcanzado el límite de {limite} transcripciones este mes. Mejorá tu plan para continuar.", "error")
                    return redirect(url_for("planes.mi_plan"))
                
                original_filename = secure_filename(f.filename)
                filename = f"{uuid4().hex}.{ext}"
                user_dir = os.path.join(current_app.config["UPLOAD_FOLDER"], str(current_user.id))
                os.makedirs(user_dir, exist_ok=True)
                path = os.path.join(user_dir, filename)
                f.save(path)
                
                tipo_archivo = "audio" if ext in ["mp3", "wav", "m4a", "flac", "ogg"] else "video"
                user_file = UserFile(user_id=current_user.id, filename=original_filename, filepath=path, tipo=tipo_archivo)
                db.session.add(user_file)
                db.session.commit()
                
                try:
                    backend = GroqBackend()
                    resultado = backend.transcribe(path)
                    transcript = resultado.get("text", "")
                    idioma_detectado = resultado.get("language", "es")
                    duracion_total = resultado.get("duration", 0)
                    
                    if idioma_detectado and idioma_detectado != "es" and transcript:
                        try:
                            from app.services.translation_service import TranslationService
                            translator = TranslationService()
                            transcript_traducido = translator.traducir(transcript, idioma_origen=idioma_detectado, idioma_destino="es")
                        except Exception as e:
                            print(f"⚠️ Error en traducción: {e}")
                            transcript_traducido = None
                    
                    transcription = Transcription(user_id=current_user.id, file_id=user_file.id, texto=transcript)
                    db.session.add(transcription)
                    db.session.commit()
                    registrar_uso_transcripcion(current_user)
                    
                    msg = f"✅ Transcripción completada ({backend.get_name()})"
                    if idioma_detectado and idioma_detectado != "es":
                        nombres = {"en": "inglés", "pt": "portugués", "fr": "francés"}
                        msg += f" - Idioma detectado: {nombres.get(idioma_detectado, idioma_detectado)}"
                    flash(msg, "success")
                    
                except Exception as e:
                    flash(f"❌ Error en la transcripción: {str(e)}", "error")
                    current_app.logger.error(f"Error transcribiendo: {str(e)}")
            else:
                flash(f"❌ Formato no permitido. Usá: {', '.join(sorted(ALLOWED_EXT))}", "error")
        else:
            flash("❌ No seleccionaste ningún archivo", "error")
    
    return render_template(
        "servicio_transcripcion.html",
        transcript=transcript,
        transcript_traducido=transcript_traducido,
        filename=filename,
        idioma_detectado=idioma_detectado,
        duracion_total=duracion_total,
        num_chunks=num_chunks
    )


@servicios_bp.route("/servicios/analisis-sentimientos", methods=["GET", "POST"])
@login_required
def analisis_sentimientos():
    resultado = None
    comentarios_raw = ""
    comentarios_limpios = []
    red_social = "desconocido"
    error_msg = None
    paso = "input"
    
    url_input = ""
    contexto = ""
    mostrar_pestaña_url = False
    
    user_plan = current_user.user_plan
    plan_obj = user_plan.obtener_plan_obj() if user_plan else None
    tiene_acceso_url = plan_obj and plan_obj.tiene_feature('motor_semantico')
    
    if request.method == "POST":
        action = request.form.get("action", "analizar")
        url_input = request.form.get("url_publicacion", "").strip()
        comentarios_raw = request.form.get("comentarios", "").strip()
        contexto = request.form.get("contexto", "").strip()
        
        if url_input:
            mostrar_pestaña_url = True
        
        # --- LÓGICA 1: URL ---
        if url_input and tiene_acceso_url and action == "analizar":
            try:
                puede_usar, uso_actual, limite = puede_analizar(current_user)
                if not puede_usar:
                    flash(f"❌ Has alcanzado el límite de {limite} análisis este mes.", "error")
                    return redirect(url_for("servicios.analisis_sentimientos"))
                
                from app.services.scraper_service import ScraperService
                scraper = ScraperService()
                extraccion = scraper.extraer_de_url(url_input)
                
                if not extraccion["success"]:
                    error_msg = extraccion['error_msg']
                    paso = "input"
                    mostrar_pestaña_url = True
                else:
                    from app.services.analysis_service import AnalysisService
                    
                    datos_crudos = extraccion["data"]
                    user_plan_name = current_user.user_plan.plan if current_user.user_plan else "free"
                    
                    service = AnalysisService()
                    resultado_dict = service.analizar(
                        datos_crudos=datos_crudos,
                        origen="facebook",
                        user_plan=user_plan_name,
                        contexto=contexto,
                    )
                    
                    if resultado_dict["success"]:
                        resultado = resultado_dict
                        resultado["red_social"] = "facebook/instagram (vía URL)"
                        resultado["total_comentarios_limpios"] = len(datos_crudos.get("comments", []))
                        
                        registrar_uso_analisis(current_user)
                        
                        analysis_session = AnalysisSession(
                            user_id=current_user.id,
                            red_social=resultado["red_social"],
                            contexto=contexto if contexto else None,
                            total_comentarios=len(datos_crudos.get("comments", [])),
                            resultado_json=json.dumps(resultado_dict, ensure_ascii=False)
                        )
                        db.session.add(analysis_session)
                        db.session.commit()
                        
                        flash(f"✅ Análisis completado con {len(datos_crudos.get('comments', []))} comentarios extraídos.", "success")
                        paso = "resultado"
                    else:
                        error_msg = resultado_dict.get("error", "Error en el análisis")
                        flash(f"❌ {error_msg}", "error")
                        paso = "input"
                        
            except Exception as e:
                error_msg = f"Error inesperado: {str(e)}"
                flash(f"❌ {error_msg}", "error")
                paso = "input"
        
        # --- LÓGICA 2: Limpiar ---
        elif action == "limpiar" and not url_input:
            try:
                comentarios_limpios, red_social = limpiar_comentarios(comentarios_raw)
                if not comentarios_limpios:
                    flash("⚠️ No se encontraron comentarios válidos.", "warning")
                    paso = "input"
                else:
                    flash(f"✅ Se detectaron {len(comentarios_limpios)} comentarios ({red_social})", "success")
                    paso = "preview"
            except Exception as e:
                flash(f"❌ Error limpiando: {str(e)}", "error")
                paso = "input"
        
        # --- LÓGICA 3: Analizar directamente ---
        elif action == "analizar" and not url_input:
            try:
                puede_usar, uso_actual, limite = puede_analizar(current_user)
                if not puede_usar:
                    flash(f"❌ Has alcanzado el límite de {limite} análisis este mes.", "error")
                    return redirect(url_for("servicios.analisis_sentimientos"))
                
                if request.form.get("comentarios_limpios_json"):
                    comentarios_limpios = json.loads(request.form.get("comentarios_limpios_json"))
                else:
                    comentarios_limpios, red_social = limpiar_comentarios(comentarios_raw)
                
                if not comentarios_limpios:
                    flash("⚠️ No hay comentarios válidos.", "warning")
                    paso = "input"
                else:
                    # ✅ USAR AnalysisService
                    from app.services.analysis_service import AnalysisService
                    
                    datos_crudos = {
                        "comments": [
                            {"text": f"[{c['usuario']}]: {c['texto']}"}
                            for c in comentarios_limpios
                        ]
                    }
                    
                    user_plan_name = current_user.user_plan.plan if current_user.user_plan else "free"
                    
                    service = AnalysisService()
                    resultado_dict = service.analizar(
                        datos_crudos=datos_crudos,
                        origen=red_social,
                        user_plan=user_plan_name,
                        contexto=contexto,
                    )
                    
                    if resultado_dict["success"]:
                        resultado = resultado_dict
                        if contexto:
                            resultado["contexto"] = contexto
                        resultado["red_social"] = red_social
                        resultado["total_comentarios_limpios"] = len(comentarios_limpios)
                        
                        registrar_uso_analisis(current_user)
                        
                        analysis_session = AnalysisSession(
                            user_id=current_user.id,
                            red_social=red_social,
                            contexto=contexto if contexto else None,
                            total_comentarios=len(comentarios_limpios),
                            resultado_json=json.dumps(resultado_dict, ensure_ascii=False)
                        )
                        db.session.add(analysis_session)
                        db.session.commit()
                        
                        flash(f"✅ Análisis completado con {len(comentarios_limpios)} comentarios", "success")
                        paso = "resultado"
                    else:
                        error_msg = resultado_dict.get("error", "Error en el análisis")
                        flash(f"❌ {error_msg}", "error")
                        paso = "input"
                        
            except Exception as e:
                error_msg = str(e)
                flash(f"❌ Error en el análisis: {error_msg}", "error")
                paso = "input"
    
    return render_template(
        "analisis_sentimientos.html",
        resultado=resultado,
        comentarios_raw=comentarios_raw,
        comentarios_limpios=comentarios_limpios,
        red_social=red_social,
        paso=paso,
        error_msg=error_msg,
        tiene_acceso_url=tiene_acceso_url,
        url_input=url_input,
        contexto=contexto,
        mostrar_pestaña_url=mostrar_pestaña_url
    )