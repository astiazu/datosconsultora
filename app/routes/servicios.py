# app/routes/servicios.py
import os
from flask import Blueprint, render_template, request, flash, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app import db
from app.models import UserFile, Transcription
from app.services.transcription import groq_backend
from app.services.analysis import GroqLLMClient
from app.services.analysis.text_cleaner import limpiar_comentarios, formatear_comentarios_para_prompt

servicios_bp = Blueprint("servicios", __name__)

ALLOWED_EXT = {"mp3", "wav", "m4a", "mp4", "mov", "avi", "mkv", "webm"}


@servicios_bp.route("/servicios/transcripcion", methods=["GET", "POST"])
@login_required
def servicio_transcripcion():
    transcript = None
    filename = None
    
    if request.method == "POST":
        f = request.files.get("media")
        if f and f.filename:
            ext = f.filename.rsplit(".", 1)[-1].lower()
            if ext in ALLOWED_EXT:
                filename = secure_filename(f.filename)
                path = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
                f.save(path)
                
                user_file = UserFile(
                    user_id=current_user.id,
                    filename=filename,
                    filepath=path,
                    tipo="audio" if ext in ["mp3", "wav", "m4a"] else "video",
                )
                db.session.add(user_file)
                db.session.commit()
                
                try:
                    backend = groq_backend()
                    transcript = backend.transcribe(path, language="es")
                    
                    transcription = Transcription(
                        user_id=current_user.id,
                        file_id=user_file.id,
                        texto=transcript,
                    )
                    db.session.add(transcription)
                    db.session.commit()
                    
                    flash(f"✅ Transcripción completada ({backend.get_name()})", "success")
                except Exception as e:
                    flash(f"❌ Error en la transcripción: {str(e)}", "error")
                    current_app.logger.error(f"Error transcribiendo: {str(e)}")
            else:
                flash("Formato no permitido", "error")
        else:
            flash("No seleccionaste ningún archivo", "error")
    
    return render_template(
        "servicio_transcripcion.html",
        transcript=transcript,
        filename=filename
    )


@servicios_bp.route("/servicios/analisis-sentimientos", methods=["GET", "POST"])
@login_required
def analisis_sentimientos():
    """Análisis de sentimientos de comentarios de redes sociales."""
    resultado = None
    comentarios_raw = ""
    comentarios_limpios = []
    red_social = "desconocido"
    error_msg = None
    paso = "input"  # input | preview | resultado
    
    if request.method == "POST":
        action = request.form.get("action", "analizar")
        comentarios_raw = request.form.get("comentarios", "").strip()
        contexto = request.form.get("contexto", "").strip()
        
        if action == "limpiar":
            # PASO 1: Solo limpiar y mostrar preview
            try:
                comentarios_limpios, red_social = limpiar_comentarios(comentarios_raw)
                
                if not comentarios_limpios:
                    flash("⚠️ No se encontraron comentarios válidos. Verificá el texto copiado.", "warning")
                    paso = "input"
                else:
                    flash(f"✅ Se detectaron {len(comentarios_limpios)} comentarios ({red_social})", "success")
                    paso = "preview"
            except Exception as e:
                flash(f"❌ Error limpiando comentarios: {str(e)}", "error")
                paso = "input"
        
        elif action == "analizar":
            # PASO 2: Analizar comentarios (ya limpios o limpiar primero)
            try:
                # Si viene del preview, los comentarios ya están limpios
                # Si viene directo del input, limpiar primero
                if request.form.get("comentarios_limpios_json"):
                    import json
                    comentarios_limpios = json.loads(request.form.get("comentarios_limpios_json"))
                else:
                    comentarios_limpios, red_social = limpiar_comentarios(comentarios_raw)
                
                if not comentarios_limpios:
                    flash("⚠️ No hay comentarios válidos para analizar", "warning")
                    paso = "input"
                elif len(comentarios_limpios) > 100:
                    flash(f"⚠️ Máximo 100 comentarios. Tenés {len(comentarios_limpios)}.", "warning")
                    paso = "input"
                else:
                    # Formatear para el prompt
                    comentarios_texto = [
                        f"[{c['usuario']}]: {c['texto']}" 
                        for c in comentarios_limpios
                    ]
                    
                    client = GroqLLMClient()
                    resultado = client.analizar_sentimientos(comentarios_texto, contexto)
                    
                    if contexto:
                        resultado["contexto"] = contexto
                    resultado["red_social"] = red_social
                    resultado["total_comentarios_limpios"] = len(comentarios_limpios)
                    
                    flash(f"✅ Análisis completado con {len(comentarios_limpios)} comentarios", "success")
                    paso = "resultado"
                    
            except Exception as e:
                error_msg = str(e)
                flash(f"❌ Error en el análisis: {error_msg}", "error")
                current_app.logger.error(f"Error en análisis: {error_msg}")
                paso = "input"
    
    return render_template(
        "analisis_sentimientos.html",
        resultado=resultado,
        comentarios_raw=comentarios_raw,
        comentarios_limpios=comentarios_limpios,
        red_social=red_social,
        paso=paso,
        error_msg=error_msg
    )