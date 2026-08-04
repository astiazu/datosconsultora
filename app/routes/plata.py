# app/routes/plata.py

from flask import Blueprint, render_template
from flask_login import login_required

plata_bp = Blueprint(
    "plata",
    __name__,
    url_prefix="/plata"
)


@plata_bp.route("/")
@login_required
def dashboard():

    return render_template(
        "plata/dashboard.html"
    )


@plata_bp.route("/motor-semantico")
@login_required
def motor_semantico():

    return render_template(
        "plata/motor_semantico.html"
    )


@plata_bp.route("/nueva-conversacion")
@login_required
def nueva_conversacion():

    return render_template(
        "plata/nueva_conversacion.html"
    )


@plata_bp.route("/mis-archivos")
@login_required
def mis_archivos():

    return render_template(
        "plata/mis_archivos.html"
    )


@plata_bp.route("/historial")
@login_required
def historial():

    return render_template(
        "plata/historial.html"
    )


@plata_bp.route("/estadisticas")
@login_required
def estadisticas():

    return render_template(
        "plata/estadisticas.html"
    )