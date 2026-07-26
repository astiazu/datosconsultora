# app/routes/agentes.py
"""
Panel de usuario para el modulo de "Agentes judiciales": permite cargar
expedientes a seguir, subir la sesion (para jurisdicciones que la piden,
como MEV-SCBA) y ver el ultimo estado conocido de cada uno.

El chequeo periodico en si (scraping + mail) NO corre aca: lo hace
worker/monitor_worker.py como proceso aparte (pensado para un Render Cron
Job), porque Playwright con un Chrome real no es algo que deba correr
dentro del ciclo request/response de un servidor web.
"""

import json

from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user

from app import db
from app.models import ExpedienteMonitoreado, SesionJurisdiccion
from app.utils.decorators import feature_required
from app.services.agentes.jurisdicciones import listar_jurisdicciones, obtener_jurisdiccion

agentes_bp = Blueprint("agentes", __name__, url_prefix="/dashboard/agentes")


@agentes_bp.route("/")
@login_required
@feature_required("agentes")
def panel_agentes():
    expedientes = (
        ExpedienteMonitoreado.query.filter_by(user_id=current_user.id, activo=True)
        .order_by(ExpedienteMonitoreado.creado.desc())
        .all()
    )

    sesiones = {
        s.jurisdiccion: s
        for s in SesionJurisdiccion.query.filter_by(user_id=current_user.id).all()
    }

    return render_template(
        "agentes_dashboard.html",
        expedientes=expedientes,
        jurisdicciones=listar_jurisdicciones(),
        sesiones=sesiones,
    )


@agentes_bp.route("/nuevo", methods=["GET", "POST"])
@login_required
@feature_required("agentes")
def nuevo_expediente():
    jurisdicciones = listar_jurisdicciones()

    if request.method == "POST":
        jid = request.form.get("jurisdiccion")
        nombre = request.form.get("nombre", "").strip()
        jurisdiccion = obtener_jurisdiccion(jid)

        if not jurisdiccion:
            flash("Jurisdiccion invalida.", "error")
            return redirect(url_for("agentes.nuevo_expediente"))

        if not nombre:
            flash("Poné un nombre para identificar este expediente.", "error")
            return redirect(url_for("agentes.nuevo_expediente"))

        parametros = {}
        for campo in jurisdiccion["campos_formulario"]:
            parametros[campo["name"]] = request.form.get(campo["name"], "").strip()

        expediente = ExpedienteMonitoreado(
            user_id=current_user.id,
            jurisdiccion=jid,
            nombre=nombre,
        )
        expediente.set_parametros(parametros)
        db.session.add(expediente)
        db.session.commit()

        flash(f"'{nombre}' se agregó a tus expedientes monitoreados.", "success")
        return redirect(url_for("agentes.panel_agentes"))

    return render_template("agentes_nuevo.html", jurisdicciones=jurisdicciones)


@agentes_bp.route("/<int:expediente_id>/eliminar", methods=["POST"])
@login_required
@feature_required("agentes")
def eliminar_expediente(expediente_id):
    expediente = ExpedienteMonitoreado.query.get_or_404(expediente_id)

    if expediente.user_id != current_user.id:
        flash("No tenés permisos sobre ese expediente.", "error")
        return redirect(url_for("agentes.panel_agentes"))

    expediente.activo = False
    db.session.commit()

    flash("Expediente eliminado de tu panel.", "success")
    return redirect(url_for("agentes.panel_agentes"))


@agentes_bp.route("/sesion/<jurisdiccion_id>", methods=["POST"])
@login_required
@feature_required("agentes")
def subir_sesion(jurisdiccion_id):
    """Sube el session.json generado localmente con
    login_y_guardar_sesion.py (el script standalone), para que el worker en
    background pueda usarlo sin que el usuario tenga que resolver el login
    (con captcha) de nuevo cada vez."""
    jurisdiccion = obtener_jurisdiccion(jurisdiccion_id)
    if not jurisdiccion or not jurisdiccion["necesita_login"]:
        flash("Esta jurisdiccion no usa sesion.", "error")
        return redirect(url_for("agentes.panel_agentes"))

    archivo = request.files.get("session_file")
    if not archivo or not archivo.filename:
        flash("Seleccioná el archivo session.json.", "error")
        return redirect(url_for("agentes.panel_agentes"))

    try:
        contenido = archivo.read().decode("utf-8")
        json.loads(contenido)  # valida que sea JSON antes de guardarlo
    except (UnicodeDecodeError, ValueError):
        flash("El archivo no parece un session.json valido.", "error")
        return redirect(url_for("agentes.panel_agentes"))

    from app.utils.datetime_utils import utc_now

    sesion = SesionJurisdiccion.query.filter_by(
        user_id=current_user.id, jurisdiccion=jurisdiccion_id
    ).first()
    if sesion is None:
        sesion = SesionJurisdiccion(user_id=current_user.id, jurisdiccion=jurisdiccion_id)
        db.session.add(sesion)

    sesion.storage_state_json = contenido
    sesion.expirada = False
    sesion.actualizado = utc_now()
    db.session.commit()

    flash(f"Sesión de {jurisdiccion['nombre']} actualizada.", "success")
    return redirect(url_for("agentes.panel_agentes"))
