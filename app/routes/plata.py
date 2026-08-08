# app/routes/plata.py
import base64

from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user

from app import db
from app.models import ExtraccionJob, SesionPlataforma
from app.utils.datetime_utils import utc_now
from app.utils.decorators import feature_required

plata_bp = Blueprint("plata", __name__, url_prefix="/plata")

MAX_JOBS_POR_DIA = 2


@plata_bp.route("/")
@login_required
def dashboard():
    return render_template("plata/dashboard.html")


@plata_bp.route("/motor-semantico")
@login_required
def motor_semantico():
    return render_template("plata/motor_semantico.html")


@plata_bp.route("/nueva-conversacion")
@login_required
def nueva_conversacion():
    return render_template("plata/nueva_conversacion.html")


@plata_bp.route("/mis-archivos")
@login_required
def mis_archivos():
    return render_template("plata/mis_archivos.html")


@plata_bp.route("/historial")
@login_required
def historial():
    return render_template("plata/historial.html")


@plata_bp.route("/estadisticas")
@login_required
def estadisticas():
    return render_template("plata/estadisticas.html")


# ============================================
# EXTRACCIÓN DE COMENTARIOS (FASE 1)
# ============================================
@plata_bp.route("/extraccion", methods=["GET", "POST"])
@login_required
@feature_required("motor_semantico")
def extraccion():
    if request.method == "POST":
        url = request.form.get("url", "").strip()
        contexto = request.form.get("contexto", "").strip()
        if not url or "instagram.com" not in url:
            flash("Pegá una URL válida de Instagram (instagram.com/p/... o /reel/...).", "error")
            return redirect(url_for("plata.extraccion"))

        hoy = utc_now().replace(hour=0, minute=0, second=0, microsecond=0)
        jobs_hoy = ExtraccionJob.query.filter(
            ExtraccionJob.user_id == current_user.id,
            ExtraccionJob.creado >= hoy,
        ).count()
        if jobs_hoy >= MAX_JOBS_POR_DIA:
            flash(f"Límite de {MAX_JOBS_POR_DIA} extracciones por día alcanzado (política anti-bloqueo).", "error")
            return redirect(url_for("plata.extraccion"))

        job = ExtraccionJob(
            user_id=current_user.id,
            plataforma="instagram",
            url=url,
            contexto=contexto,
        )
        db.session.add(job)
        db.session.commit()
        flash(f"Extracción #{job.id} en cola. El worker la procesará con ritmo humano.", "success")
        return redirect(url_for("plata.extraccion"))

    sesion = SesionPlataforma.query.filter_by(
        user_id=current_user.id, plataforma="instagram"
    ).first()
    jobs = (
        ExtraccionJob.query.filter_by(user_id=current_user.id)
        .order_by(ExtraccionJob.creado.desc())
        .limit(20)
        .all()
    )
    return render_template("plata/extraccion.html", sesion=sesion, jobs=jobs)


@plata_bp.route("/extraccion/sesion", methods=["POST"])
@login_required
@feature_required("motor_semantico")
def subir_sesion_instagram():
    archivo = request.files.get("session_file")
    if not archivo or not archivo.filename:
        print("❌ subir_sesion: no llegó ningún archivo (revisá enctype del form)")
        flash("Seleccioná el archivo sesion_instagram.b64.txt.", "error")
        return redirect(url_for("plata.extraccion"))

    # Leer y validar el base64 (tolerante a saltos de línea/espacios)
    try:
        contenido = "".join(archivo.read().decode("utf-8").split())
        base64.b64decode(contenido, validate=True)
    except Exception as e:
        print(f"❌ subir_sesion: validación base64 falló: {e}")
        flash("El archivo no parece un sesion_instagram.b64.txt válido.", "error")
        return redirect(url_for("plata.extraccion"))

    try:
        sesion = SesionPlataforma.query.filter_by(
            user_id=current_user.id, plataforma="instagram"
        ).first()
        if sesion is None:
            sesion = SesionPlataforma(user_id=current_user.id, plataforma="instagram")
            db.session.add(sesion)
        sesion.storage_state_json = contenido
        sesion.expirada = False
        sesion.actualizado = utc_now()
        db.session.commit()
        print(f"✅ subir_sesion: sesión guardada para user {current_user.id}")
        flash("✅ Sesión de Instagram conectada.", "success")
    except Exception as e:
        db.session.rollback()
        print(f"❌ subir_sesion: error de DB: {e}")
        flash(f"Error al guardar la sesión: {e}", "error")
    return redirect(url_for("plata.extraccion"))


@plata_bp.route("/extraccion/progreso")
@login_required
@feature_required("motor_semantico")
def progreso_extraccion():
    activos = ExtraccionJob.query.filter(
        ExtraccionJob.user_id == current_user.id,
        ExtraccionJob.estado.in_(["cola", "progreso", "pausa_rate_limit"]),
    ).all()
    return jsonify([
        {"id": j.id, "estado": j.estado, "total_extraido": j.total_extraido}
        for j in activos
    ])


@plata_bp.route("/extraccion/<int:job_id>")
@login_required
@feature_required("motor_semantico")
def detalle_extraccion(job_id):
    job = ExtraccionJob.query.get_or_404(job_id)
    if job.user_id != current_user.id:
        flash("No tenés permisos sobre esa extracción.", "error")
        return redirect(url_for("plata.extraccion"))

    conversation = None
    participants = {}
    if job.conversation_record_id:
        from app.services.plata.conversation_repository import ConversationRepository
        data = ConversationRepository().obtener(job.conversation_record_id, current_user.id)
        if data:
            conversation = data["conversation"]
            participants = {p.participant_id: p.display_name for p in conversation.participants}

    return render_template(
        "plata/extraccion_detalle.html",
        job=job,
        conversation=conversation,
        participants=participants,
    )