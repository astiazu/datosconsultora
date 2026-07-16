# app/routes/public.py
from flask import Blueprint, render_template

public_bp = Blueprint("public", __name__)


@public_bp.route("/")
def index():
    return render_template("index.html")


@public_bp.route("/servicios")
def servicios():
    return render_template("servicios.html")


@public_bp.route("/nosotros")
def nosotros():
    return render_template("nosotros.html")


@public_bp.route("/contacto")
def contacto():
    return render_template("contacto.html")