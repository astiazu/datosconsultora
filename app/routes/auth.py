# app/routes/auth.py
import secrets
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_user, logout_user, current_user, login_required
from app.models import User, ActivityLog
from app import db
from app.utils.verificacion import generar_token_email, enviar_email_verificacion
from app.services.google_oauth_service import oauth
from app.services.plan_service import obtener_plan_usuario

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
        email_enviado, error_msg = enviar_email_verificacion(user, token)
        if email_enviado:
            flash("Registro exitoso. Revisá tu email para verificar tu cuenta.", "success")
        else:
            flash(f"Registro exitoso, pero falló el email. Error: {error_msg}", "error")

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


@auth_bp.route("/reenviar-verificacion")
@login_required
def reenviar_verificacion():
    """Reenvía email de verificación."""
    if current_user.email_verificado:
        flash("Tu email ya está verificado", "success")
        return redirect(url_for("dashboard.dashboard_user"))

    token = generar_token_email(current_user)
    email_enviado, error_msg = enviar_email_verificacion(current_user, token)
    if email_enviado:
        flash("✅ Email de verificación reenviado. Por favor, revisá tu bandeja de entrada y también la carpeta de Spam/Correo no deseado.", "success")
    else:
        flash(f"❌ No pudimos enviar el email. Error: {error_msg}", "error")
    return redirect(url_for("dashboard.dashboard_user"))


# ============================================
# LOGIN / REGISTRO CON GOOGLE (OAuth 2.0)
# ============================================
@auth_bp.route("/auth/google")
def google_login():
    """Inicia el flujo 'Sign in with Google'."""
    if not current_app.config.get("GOOGLE_ENABLED"):
        flash("El login con Google no está configurado.", "error")
        return redirect(url_for("auth.login"))
    redirect_uri = url_for("auth.google_callback", _external=True)
    return oauth.google.authorize_redirect(redirect_uri)


@auth_bp.route("/auth/google/callback")
def google_callback():
    """Callback de Google: crea o vincula el usuario y lo loguea."""
    if not current_app.config.get("GOOGLE_ENABLED"):
        flash("El login con Google no está configurado.", "error")
        return redirect(url_for("auth.login"))

    try:
        token = oauth.google.authorize_access_token()
    except Exception as e:
        current_app.logger.error(f"Error en OAuth de Google: {e}")
        flash("No pudimos verificar tu cuenta de Google. Intentá de nuevo.", "error")
        return redirect(url_for("auth.login"))

    userinfo = token.get("userinfo")
    if not userinfo or not userinfo.get("email"):
        resp = oauth.google.get("https://www.googleapis.com/oauth2/v3/userinfo")
        userinfo = resp.json()

    email = (userinfo.get("email") or "").lower().strip()
    google_sub = userinfo.get("sub")
    nombre = userinfo.get("name") or (email.split("@")[0] if email else "Usuario Google")

    if not email or not google_sub:
        flash("Google no devolvió los datos necesarios (email).", "error")
        return redirect(url_for("auth.login"))

    user = User.query.filter_by(google_id=google_sub).first()
    if not user:
        user = User.query.filter_by(email=email).first()

    if user:
        # Cuenta existente: login (y vinculación si aún no tenía google_id)
        if not user.is_active_account:
            flash("Cuenta inactiva. Contactá al administrador.", "error")
            return redirect(url_for("auth.login"))
        accion = "login_google"
        if not user.google_id:
            user.google_id = google_sub
            accion = "vinculo_google"
        login_user(user)
    else:
        # Usuario nuevo vía Google (email verificado por Google)
        user = User(
            nombre=nombre,
            email=email,
            telefono="",
            google_id=google_sub,
            email_verificado=True,
            telefono_verificado=False,
        )
        user.set_password(secrets.token_urlsafe(24))  # contraseña aleatoria inutilizable
        db.session.add(user)
        db.session.commit()
        obtener_plan_usuario(user)  # plan free por defecto
        login_user(user)
        accion = "registro_google"

    log = ActivityLog(
        user_id=user.id,
        accion=accion,
        detalle=f"Acceso con Google: {email}",
        ip=request.remote_addr,
    )
    db.session.add(log)
    db.session.commit()

    flash(f"¡Bienvenido/a, {user.nombre}!", "success")
    if user.is_admin:
        return redirect(url_for("admin.admin_panel"))
    return redirect(url_for("dashboard.dashboard_user"))