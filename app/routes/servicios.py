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
from app.services.plan_service import (
    puede_transcribir, registrar_uso_transcripcion,
    puede_analizar, registrar_uso_analisis, limite_comentarios_para_plan
)

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
                    flash(f"❌ Has alcanzado el límite de {limite} transcripciones este mes. Mejorá tu plan para continuar.", "error")
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
    mostrar_fallback = False  # ✅ INICIALIZADO (era variable no declarada)

    # Variables para la vista premium del Plan Plata (Conversation)
    conversation_plata = None
    participants_plata = None
    record_id_plata = None

    user_plan = current_user.user_plan
    plan_obj = user_plan.obtener_plan_obj() if user_plan else None
    tiene_acceso_url = plan_obj and plan_obj.tiene_feature('motor_semantico')

    if request.method == "POST":
        action = request.form.get("action", "analizar")
        url_input = request.form.get("url_publicacion", "").strip()
        comentarios_raw = request.form.get("comentarios", "").strip()
        contexto = request.form.get("contexto", "").strip()

        # =========================================================================
        # LÓGICA 1: URL (Plan Plata+) — AUTOMÁTICO: descarga, guarda y parsea
        # =========================================================================
        if url_input and tiene_acceso_url and action == "analizar":
            try:
                puede_usar, uso_actual, limite = puede_analizar(current_user)
                if not puede_usar:
                    flash(f"❌ Has alcanzado el límite de {limite} análisis este mes.", "error")
                    return redirect(url_for("servicios.analisis_sentimientos"))

                # PASO 1: contexto opcional desde video/audio (transcripción)
                media = request.files.get("media_contexto")
                if media and media.filename:
                    ext_media = media.filename.rsplit(".", 1)[-1].lower()
                    if ext_media in ALLOWED_EXT:
                        try:
                            from app.services.transcription.audio_utils import prepare_for_transcription
                            tmp_path = os.path.join(current_app.config["UPLOAD_FOLDER"], str(current_user.id), f"{uuid4().hex}.{ext_media}")
                            os.makedirs(os.path.dirname(tmp_path), exist_ok=True)
                            media.save(tmp_path)
                            chunks = prepare_for_transcription(tmp_path)
                            backend = GroqBackend()
                            texto_media = " ".join(backend.transcribe(c).get("text", "") for c in chunks).strip()
                            if texto_media:
                                contexto = f"{contexto}\n{texto_media}".strip() if contexto else texto_media
                                flash("🎙️ Video/audio transcrito y usado como contexto.", "success")
                        except Exception as e:
                            flash(f"⚠️ No se pudo transcribir el contexto: {str(e)[:120]}", "warning")

                # PASO 2: extracción automática (descarga + guarda en origen + parsea)
                from app.services.conversation_service import ConversationService
                service = ConversationService()
                respuesta = service.extraer_conversation(url_input)

                if respuesta["success"]:
                    conversation_plata = respuesta["conversation"]
                    url_lower = url_input.lower()
                    red_social = "instagram" if "instagram" in url_lower else ("x" if ("x.com" in url_lower or "twitter" in url_lower) else "facebook")
                    participants_plata = {p.participant_id: p.display_name for p in conversation_plata.participants}
                    flash(f"✅ Página guardada en origen y {conversation_plata.total_messages} comentarios detectados ({red_social}).", "success")
                    paso = "preview_plata"
                                        # Mensaje contextual si trajo menos de los declarados
                    stats = conversation_plata.metadata.get("stats", {})
                    declarados = stats.get("comentarios")
                    if declarados:
                        try:
                            decl_num = int(str(declarados).replace(".", "").replace(",", ""))
                            if conversation_plata.total_messages < decl_num:
                                flash(
                                    f"ℹ️ Se extrajeron {conversation_plata.total_messages} de {decl_num} comentarios declarados. "
                                    f"Instagram puede limitar el acceso automático. Para recuperar todos, usá el método de página guardada.",
                                    "info"
                                )
                        except (ValueError, TypeError):
                            pass
                elif comentarios_raw:
                    # Fallback 1: el usuario pegó comentarios → los usamos
                    respuesta_manual = service.from_manual_text(comentarios_raw, contexto)
                    if respuesta_manual["success"]:
                        conversation_plata = respuesta_manual["conversation"]
                        red_social = respuesta_manual.get("red_social", "desconocido")
                        participants_plata = {p.participant_id: p.display_name for p in conversation_plata.participants}
                        flash("⚠️ La red no dejó extraer automáticamente; usamos los comentarios pegados.", "warning")
                        paso = "preview_plata"
                    else:
                        flash(f"⚠️ {respuesta_manual.get('error_msg')}", "warning")
                        paso = "input"
                        mostrar_fallback = True
                else:
                    # Fallback 2: Plan B (subir página guardada)
                    flash("⚠️ La red social bloqueó la extracción automática. Usá el Plan B de abajo: guardá la página con Ctrl+S y subila.", "warning")
                    paso = "input"
                    mostrar_fallback = True

            except Exception as e:
                error_msg = f"Error inesperado: {str(e)}"
                flash(f"❌ {error_msg}", "error")
                paso = "input"
                mostrar_fallback = True

        # =========================================================================
        # LÓGICA 1B: PLAN B — subir página guardada (Ctrl+S)
        # =========================================================================
        # =========================================================================
        # LÓGICA 1B: PLAN B — subir página guardada (Ctrl+S)
        # =========================================================================
        elif action == "subir_pagina":
            try:
                puede_usar, uso_actual, limite = puede_analizar(current_user)
                if not puede_usar:
                    flash(f"❌ Has alcanzado el límite de {limite} análisis este mes.", "error")
                    return redirect(url_for("servicios.analisis_sentimientos"))

                archivo = request.files.get("archivo_pagina")
                if not archivo or not archivo.filename or not archivo.filename.lower().endswith((".html", ".htm")):
                    flash("❌ Subí el archivo .html que guardaste con Ctrl+S.", "error")
                    paso = "input"
                    mostrar_fallback = True
                else:
                    carpeta = os.path.join(current_app.config["UPLOAD_FOLDER"], "paginas_origen")
                    os.makedirs(carpeta, exist_ok=True)
                    path_pagina = os.path.join(carpeta, f"{uuid4().hex}_{secure_filename(archivo.filename)}")
                    archivo.save(path_pagina)
                    with open(path_pagina, "r", encoding="utf-8", errors="ignore") as f:
                        html_content = f.read()

                    from app.services.conversation_service import ConversationService
                    service = ConversationService()
                    respuesta = service.from_saved_page(html_content, url_input, contexto)

                    # ✅ ÉXITO: conversación viva → preview
                    if respuesta.get("success") and respuesta.get("conversation") is not None:
                        conversation_plata = respuesta["conversation"]
                        red_social = respuesta.get("red_social", "facebook")
                        participants_plata = {
                            p.participant_id: p.display_name
                            for p in conversation_plata.participants
                        }
                        flash(f"✅ {conversation_plata.total_messages} comentarios recuperados de la página guardada.", "success")

                        # Aviso honesto si hay métricas declaradas y trajimos menos
                        stats = conversation_plata.metadata.get("stats") or {}
                        declarados = str(stats.get("comentarios") or "").strip()
                        if declarados:
                            try:
                                decl_num = int(declarados.replace(".", "").replace(",", ""))
                                if conversation_plata.total_messages < decl_num:
                                    flash(f"ℹ️ Se recuperaron {conversation_plata.total_messages} de {decl_num} comentarios declarados.", "info")
                            except (ValueError, TypeError):
                                pass
                        paso = "preview_plata"
                    # ✅ FALLO: sin conversación → volver al input
                    else:
                        flash("⚠️ " + (respuesta.get("error_msg") or "No se pudo procesar la página."), "warning")
                        paso = "input"
                        mostrar_fallback = True
            except Exception as e:
                current_app.logger.exception("Error procesando la página (Plan B)")
                flash(f"❌ Error procesando la página: {str(e)}", "error")
                paso = "input"
                mostrar_fallback = True

        # =========================================================================
        # LÓGICA 2: Limpiar y previsualizar (Plan Bronce - INTACTO)
        # =========================================================================
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

        # =========================================================================
        # LÓGICA 3: Analizar directamente (Plan Bronce - INTACTO Y BLINDADO)
        # =========================================================================
        elif action == "analizar" and not url_input:
            try:
                puede_usar, uso_actual, limite = puede_analizar(current_user)
                if not puede_usar:
                    flash(f"❌ Has alcanzado el límite de {limite} análisis este mes.", "error")
                    return redirect(url_for("servicios.analisis_sentimientos"))

                # ✅ LEER DIRECTAMENTE EL TEXTO RAW
                comentarios_raw = request.form.get("comentarios", "").strip()
                contexto = request.form.get("contexto", "").strip()

                # Regeneramos la limpieza. Es rápido, idempotente y evita cualquier error de JSON.
                comentarios_limpios, red_social = limpiar_comentarios(comentarios_raw)

                if not comentarios_limpios:
                    flash("⚠️ No hay comentarios válidos.", "warning")
                    paso = "input"
                else:
                    datos_crudos = {
                        "comments": [
                            {"text": f"[{c['usuario']}]: {c['texto']}"}
                            for c in comentarios_limpios
                        ]
                    }

                    # ✅ La LÓGICA 3 usa el flujo Bronce (sentimientos básico por lotes).
                    # Los usuarios Plata+ entran por la LÓGICA 1 (Motor Semántico con URL).
                    user_plan_name = "bronce"

                    # Normalizar origen para el MIC (evita "desconocido")
                    origen_para_mic = red_social if red_social in ["facebook", "instagram", "x"] else "facebook"

                    service = AnalysisService()
                    # ✅ CORREGIDO: eliminado `fuente=red_social` (ese parámetro no existe en el método)
                    resultado_dict = service.analizar(
                        datos_crudos=datos_crudos,
                        origen=origen_para_mic,
                        user_plan=user_plan_name,
                        contexto=contexto,
                        limite_comentarios=limite_comentarios_para_plan(current_user),
                    )

                    if resultado_dict["success"]:
                        resultado = resultado_dict
                        if contexto:
                            resultado["contexto"] = contexto
                        resultado["red_social"] = red_social
                        resultado["total_comentarios_limpios"] = len(comentarios_limpios)

                        if resultado_dict.get("advertencia"):
                            flash(f"⚠️ {resultado_dict['advertencia']}", "warning")

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

        # =========================================================================
        # LÓGICA 4: Ejecutar Motor Semántico sobre Conversation guardada (Plan Plata)
        # =========================================================================
        elif action == "analizar_plata" and request.form.get("record_id_plata"):
            try:
                puede_usar, uso_actual, limite = puede_analizar(current_user)
                if not puede_usar:
                    flash(f"❌ Has alcanzado el límite de {limite} análisis este mes.", "error")
                    return redirect(url_for("servicios.analisis_sentimientos"))

                # ✅ CORREGIDO: try/except para parseo seguro del record_id
                try:
                    record_id = int(request.form.get("record_id_plata"))
                except (TypeError, ValueError):
                    flash("❌ ID de conversación inválido.", "error")
                    paso = "input"
                else:
                    # Cargar la Conversation desde la DB
                    from app.services.plata.conversation_repository import ConversationRepository
                    repo = ConversationRepository()
                    data = repo.obtener(record_id, current_user.id)

                    if not data:
                        flash("❌ No se encontró la conversación guardada.", "error")
                        paso = "input"
                    else:
                        conversation_plata = data["conversation"]
                        record_id_plata = data["record"].id

                        # Ejecutar el Motor Semántico
                        from app.services.plata.semantic_service import SemanticService
                        semantic_service = SemanticService()
                        user_plan_name = current_user.user_plan.plan if current_user.user_plan else "free"

                        contexto_semantico = (
                            data["record"].contexto
                            or conversation_plata.metadata.get("contexto", "")
                            or ""
                        )
                        resultado_dict = semantic_service.analizar(
                            conversation=conversation_plata,
                            user_plan=user_plan_name,
                            contexto=contexto_semantico,
                        )

                        if resultado_dict["success"]:
                            # Guardar el resultado en la DB
                            repo.guardar_resultado(record_id, resultado_dict)

                            # Registrar el uso
                            registrar_uso_analisis(current_user)

                            resultado = resultado_dict
                            paso = "resultado"
                            total_analizados = resultado_dict.get("estadisticas_agregadas", {}).get("total", conversation_plata.total_messages)
                            flash(f"✅ Análisis semántico completado ({total_analizados} mensajes analizados)", "success")
                            for w in resultado_dict.get("warnings", []):
                                flash(f"⚠️ {w}", "warning")
                        else:
                            error_msg = resultado_dict.get("errors", ["Error en el análisis"])
                            if isinstance(error_msg, list):
                                error_msg = error_msg[0] if error_msg else "Error en el análisis"
                            flash(f"❌ {error_msg}", "error")
                            paso = "input"

            except Exception as e:
                error_msg = str(e)
                flash(f"❌ Error en el análisis semántico: {error_msg}", "error")
                current_app.logger.error(f"Error en análisis semántico: {str(e)}")
                paso = "input"

    # =========================================================================
    # PERSISTENCIA: si quedó una Conversation nueva sin guardar (URL o Plan B),
    # la guardamos para que "Ejecutar Motor Semántico" tenga un record_id real.
    # =========================================================================
    if conversation_plata is not None and record_id_plata is None:
        try:
            # Enriquecer contexto con caption + métricas (sin duplicar si ya están)
            if conversation_plata.metadata.get("caption") and "PUBLICACIÓN ORIGINAL:" not in contexto:
                cap = conversation_plata.metadata["caption"]
                contexto = f"PUBLICACIÓN ORIGINAL: {cap}\n{contexto}" if contexto else f"PUBLICACIÓN ORIGINAL: {cap}"

            st = conversation_plata.metadata.get("stats") or {}
            if st and "Métricas de la publicación" not in contexto:
                partes = []
                if st.get("likes"):
                    partes.append(f"{st['likes']} likes")
                if st.get("comentarios"):
                    partes.append(f"{st['comentarios']} comentarios declarados en la publicación")
                if st.get("compartidos"):
                    partes.append(f"{st['compartidos']} compartidos")
                if partes:
                    linea = "Métricas de la publicación: " + ", ".join(partes) + "."
                    contexto = f"{contexto}\n{linea}" if contexto else linea

            # El contexto COMPLETO viaja dentro del JSON de la Conversation;
            # la columna `contexto` de la DB es VARCHAR(500) → truncamos por
            # seguridad (PostgreSQL en Render sí enforcea el límite).
            conversation_plata.metadata["contexto"] = contexto

            from app.services.plata.conversation_repository import ConversationRepository
            repo = ConversationRepository()
            record = repo.guardar(current_user.id, conversation_plata, contexto[:500])
            record_id_plata = record.id
        except Exception as e:
            current_app.logger.error(f"No se pudo persistir la conversación: {e}")
            flash("⚠️ La conversación no se pudo guardar; el Motor Semántico podría no estar disponible para esta preview.", "warning")

    # =========================================================================
    # Agregar `mostrar_fallback` al contexto del template (necesario para Plan B)
    # =========================================================================
    if 'mostrar_fallback' not in locals():
        mostrar_fallback = False

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
        mostrar_fallback=mostrar_fallback,  # ✅ AGREGADO
        conversation=conversation_plata,
        participants=participants_plata,
        record_id_plata=record_id_plata,
        limite_comentarios=limite_comentarios_para_plan(current_user),
    )