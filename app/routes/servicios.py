import os
import json
from flask import Blueprint, render_template, request, flash, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from app import db
from app.models import UserFile, Transcription
from app.services.analysis import GroqLLMClient
from app.services.analysis.text_cleaner import limpiar_comentarios
from app.services.transcription.groq_backend import GroqBackend

# ✅ CORREGIDO: __name__ y sin espacios en las extensiones (solo audio por ahora)
servicios_bp = Blueprint("servicios", __name__)
ALLOWED_EXT = {"mp3", "wav", "m4a"}


# app/routes/servicios.py
import os
from flask import Blueprint, render_template, request, flash, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app import db
from app.models import UserFile, Transcription
from app.services.transcription.groq_backend import GroqBackend
from app.services.transcription.audio_utils import prepare_for_transcription, is_video_file
from app.services.translation_service import TranslationService

servicios_bp = Blueprint("servicios", __name__)

ALLOWED_EXT = {"mp3", "wav", "m4a", "mp4", "mov", "avi", "mkv", "webm", "flac", "ogg"}


@servicios_bp.route("/servicios/transcripcion", methods=["GET", "POST"])
@login_required
def servicio_transcripcion():
    transcript = None
    transcript_traducido = None
    filename = None
    idioma_detectado = None
    duracion_total = 0
    num_chunks = 1
    
    if request.method == "POST":
        f = request.files.get("media")
        if f and f.filename:
            ext = f.filename.rsplit(".", 1)[-1].lower()
            if ext in ALLOWED_EXT:
                filename = secure_filename(f.filename)
                path = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
                f.save(path)
                
                tipo_archivo = "video" if is_video_file(path) else "audio"
                
                # Guardar archivo en BD
                user_file = UserFile(
                    user_id=current_user.id,
                    filename=filename,
                    filepath=path,
                    tipo=tipo_archivo,
                )
                db.session.add(user_file)
                db.session.commit()
                
                try:
                    backend = GroqBackend()
                    
                    # Preparar archivo (extraer audio si es video, dividir si es grande)
                    files_to_transcribe = prepare_for_transcription(path)
                    num_chunks = len(files_to_transcribe)
                    
                    # Transcribir cada chunk
                    transcripts = []
                    idioma = None
                    duracion = 0
                    
                    for i, chunk_path in enumerate(files_to_transcribe):
                        print(f"🎙️ Transcribiendo chunk {i+1}/{len(files_to_transcribe)}...")
                        resultado = backend.transcribe(chunk_path)
                        transcripts.append(resultado["text"])
                        
                        # Capturar idioma del primer chunk
                        if idioma is None and resultado.get("language"):
                            idioma = resultado["language"]
                        
                        # Sumar duración
                        duracion += resultado.get("duration", 0)
                    
                    # Concatenar transcripciones
                    transcript = " ".join(transcripts)
                    idioma_detectado = idioma or "es"
                    duracion_total = round(duracion, 1)
                    
                    # Si el idioma detectado NO es español, traducir
                    if idioma_detectado != "es" and transcript:
                        try:
                            translator = TranslationService()
                            transcript_traducido = translator.traducir(
                                transcript, 
                                idioma_origen=idioma_detectado, 
                                idioma_destino="es"
                            )
                        except Exception as e:
                            print(f"⚠️ Error en traducción: {e}")
                            transcript_traducido = None
                    
                    # Guardar transcripción en BD
                    transcription = Transcription(
                        user_id=current_user.id,
                        file_id=user_file.id,
                        texto=transcript,
                    )
                    db.session.add(transcription)
                    db.session.commit()
                    
                    # Mensaje de éxito
                    tipo_texto = "video" if tipo_archivo == "video" else "audio"
                    msg = f"✅ Transcripción completada ({backend.get_name()})"
                    if num_chunks > 1:
                        msg += f" - Procesado en {num_chunks} partes"
                    if idioma_detectado and idioma_detectado != "es":
                        nombres = {"en": "inglés", "pt": "portugués", "fr": "francés"}
                        nombre_idioma = nombres.get(idioma_detectado, idioma_detectado)
                        msg += f" - Idioma detectado: {nombre_idioma}"
                    
                    flash(msg, "success")
                    
                except Exception as e:
                    error_msg = str(e)
                    flash(f"❌ Error en la transcripción: {error_msg}", "error")
                    current_app.logger.error(f"Error transcribiendo: {error_msg}")
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
    paso = "input"  # input | preview | resultado
    
    if request.method == "POST":
        action = request.form.get("action", "analizar")
        comentarios_raw = request.form.get("comentarios", "").strip()
        contexto = request.form.get("contexto", "").strip()
        
        if action == "limpiar":
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
            try:
                if request.form.get("comentarios_limpios_json"):
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