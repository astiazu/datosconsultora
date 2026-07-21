# app/routes/auth.py
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, current_user, login_required  
from app.models import User, ActivityLog
from app import db
from app.utils.verificacion import generar_token_email, enviar_email_verificacion  

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/registro", methods=["GET", "POST"])
def registro():
    if current_user.is_authenticated:
        if current_user.is_admin:
            return redirect(url_for("admin.admin_panel"))
        return redirect(url_for("dashboard.dashboard_user"))

    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()
        email = request.form.get("email", "").lower().strip()
        telefono = request.form.get("telefono", "").strip()
        pw = request.form.get("password", "")

        if not nombre or not email or not telefono or not pw:
            flash("Todos los campos son obligatorios", "error")
            return redirect(url_for("auth.registro"))

        if User.query.filter_by(email=email).first():
            flash("Ese email ya está registrado", "error")
            return redirect(url_for("auth.registro"))

        if len(pw) < 6:
            flash("La contraseña debe tener al menos 6 caracteres", "error")
            return redirect(url_for("auth.registro"))

        user = User(nombre=nombre, email=email, telefono=telefono)
        user.set_password(pw)
        db.session.add(user)
        db.session.commit()

        # Generar token y enviar email de verificación
        token = generar_token_email(user)
        email_enviado, error_msg = enviar_email_verificacion(user, token)  # 
        
        if email_enviado:
            flash("Registro exitoso. Revisá tu email para verificar tu cuenta.", "success")
        else:
            # ← CAMBIO: Mostramos el error real en pantalla para debuggear
            flash(f"Registro exitoso, pero falló el email. Error: {error_msg}", "error")

        # Log de registro
        log = ActivityLog(
            user_id=user.id,
            accion="registro",
            detalle=f"Nuevo usuario registrado: {email}",
            ip=request.remote_addr,
        )
        db.session.add(log)
        db.session.commit()

        return redirect(url_for("auth.login"))

    return render_template("registro.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        if current_user.is_admin:
            return redirect(url_for("admin.admin_panel"))
        return redirect(url_for("dashboard.dashboard_user"))

    if request.method == "POST":
        email = request.form.get("email", "").lower().strip()
        pw = request.form.get("password", "")

        user = User.query.filter_by(email=email).first()

        if user and user.check_password(pw):
            if not user.is_active_account:
                flash("Cuenta inactiva. Contactá al administrador.", "error")
                log = ActivityLog(
                    user_id=user.id,
                    accion="intento_fallido",
                    detalle="Intento de login con cuenta inactiva",
                    ip=request.remote_addr,
                )
                db.session.add(log)
                db.session.commit()
                return redirect(url_for("auth.login"))

            login_user(user)

            log = ActivityLog(
                user_id=user.id,
                accion="login",
                detalle="Inicio de sesión exitoso",
                ip=request.remote_addr,
            )
            db.session.add(log)
            db.session.commit()

            if user.is_admin:
                return redirect(url_for("admin.admin_panel"))
            return redirect(url_for("dashboard.dashboard_user"))

        # Login fallido
        flash("Credenciales inválidas", "error")
        user_found = User.query.filter_by(email=email).first()
        log = ActivityLog(
            user_id=user_found.id if user_found else None,
            accion="intento_fallido",
            detalle=f"Intento fallido para {email}",
            ip=request.remote_addr,
        )
        db.session.add(log)
        db.session.commit()

    return render_template("login.html")


@auth_bp.route("/logout")
def logout():
    if current_user.is_authenticated:
        log = ActivityLog(
            user_id=current_user.id,
            accion="logout",
            detalle="Cierre de sesión",
            ip=request.remote_addr,
        )
        db.session.add(log)
        db.session.commit()
    logout_user()
    return redirect(url_for("public.index"))


# app/routes/auth.py (buscá y reemplazá esta función)

@auth_bp.route("/reenviar-verificacion")
@login_required
def reenviar_verificacion():
    """Reenvía email de verificación."""
    if current_user.email_verificado:
        flash("Tu email ya está verificado", "success")
        return redirect(url_for("dashboard.dashboard_user"))
    
    from app.utils.verificacion import generar_token_email, enviar_email_verificacion
    token = generar_token_email(current_user)
    email_enviado = enviar_email_verificacion(current_user, token)
    
    if email_enviado:
        flash("✅ Email de verificación reenviado. Por favor, revisá tu bandeja de entrada y también la carpeta de Spam/Correo no deseado.", "success")
    else:
        flash("❌ No pudimos enviar el email. Contactá al administrador.", "error")
    
    return redirect(url_for("dashboard.dashboard_user"))