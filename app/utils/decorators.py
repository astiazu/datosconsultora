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
                return redirect(url_for("dashboard.dashboard"))
            return f(*args, **kwargs)
        return wrapper
    return decorator