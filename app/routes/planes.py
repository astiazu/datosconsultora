# app/routes/planes.py
from flask import Blueprint, render_template, flash, redirect, url_for
from flask_login import login_required, current_user
from app.services.plan_service import (
    obtener_plan_usuario,
    obtener_todos_los_planes,
    inicializar_planes_por_defecto
)

planes_bp = Blueprint("planes", __name__)


@planes_bp.route("/planes")
def lista_planes():
    """Página pública con comparativa de planes."""
    inicializar_planes_por_defecto()
    planes = obtener_todos_los_planes()
    
    plan_actual = None
    if current_user.is_authenticated:
        plan_actual = obtener_plan_usuario(current_user)
    
    return render_template(
        "planes.html",
        planes=planes,
        plan_actual=plan_actual
    )


@planes_bp.route("/planes/mi-plan")
@login_required
def mi_plan():
    """Página del plan actual del usuario."""
    inicializar_planes_por_defecto()
    user_plan = obtener_plan_usuario(current_user)
    plan_obj = user_plan.obtener_plan_obj()
    planes = obtener_todos_los_planes()
    
    return render_template(
        "mi_plan.html",
        user_plan=user_plan,
        plan_obj=plan_obj,
        planes=planes,
        consumo_transcripciones=user_plan.consumo_transcripciones_mes(),
        consumo_analisis=user_plan.consumo_analisis_mes()
    )


@planes_bp.route("/planes/elegir/<nombre_plan>")
@login_required
def elegir_plan(nombre_plan):
    """Por ahora solo muestra mensaje 'Próximamente'."""
    flash(f"🚧 La suscripción al plan {nombre_plan} estará disponible próximamente. ¡Gracias por tu interés!", "info")
    return redirect(url_for("planes.lista_planes"))