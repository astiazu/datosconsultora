# app/utils/decoratosrs.py
from functools import wraps
from flask import redirect, url_for, flash
from flask_login import current_user

def active_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not current_user.is_active_account:
            flash("Cuenta inactiva", "error")
            return redirect(url_for("auth.logout"))
        return f(*args, **kwargs)
    return wrapper

def role_required(role_name):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                flash("Iniciá sesión para acceder.", "error")
                return redirect(url_for("auth.login"))
            roles = [ur.role.nombre for ur in current_user.roles]
            if role_name not in roles and not current_user.is_admin:
                flash("No tenés permisos para acceder a esta sección.", "error")
                return redirect(url_for("dashboard.dashboard_user"))  # ✅ endpoint real
            return f(*args, **kwargs)
        return wrapper
    return decorator

def feature_required(feature_name):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            from app.services.plan_service import obtener_plan_usuario
            user_plan = obtener_plan_usuario(current_user)
            plan_obj = user_plan.obtener_plan_obj()
            if not plan_obj or not plan_obj.tiene_feature(feature_name):
                plan_minimo = {
                    "historial": "Plata",
                    "motor_semantico": "Plata",
                    "agentes": "Oro",
                    "actividad_completa": "Oro",
                }.get(feature_name, "Oro")
                flash(
                    f"Esta función está disponible a partir del plan {plan_minimo}. "
                    "Mejorá tu plan para acceder.",
                    "error",
                )
                return redirect(url_for("planes.mi_plan"))
            return f(*args, **kwargs)
        return wrapper
    return decorator
