# app/routes/dashboard.py
from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import os
from app import db
from app.models import UserProfile, UserFile, Transcription

dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/dashboard")


@dashboard_bp.route("/")
@login_required
def dashboard_user():
    if not current_user.is_active_account:
        flash("Tu cuenta está inactiva. Contactá al administrador.", "error")
        return redirect(url_for("auth.logout"))

    # Asegurar que el usuario tenga perfil
    if not current_user.profile:
        profile = UserProfile(user_id=current_user.id)
        db.session.add(profile)
        db.session.commit()

    return render_template("dashboard_user.html")


@dashboard_bp.route("/perfil", methods=["POST"])
@login_required
def actualizar_perfil():
    profile = current_user.profile
    if not profile:
        profile = UserProfile(user_id=current_user.id)
        db.session.add(profile)

    profile.empresa = request.form.get("empresa", "").strip()
    profile.cargo = request.form.get("cargo", "").strip()
    profile.pais = request.form.get("pais", "").strip()
    db.session.commit()

    flash("Perfil actualizado", "success")
    return redirect(url_for("dashboard.dashboard_user"))


@dashboard_bp.route("/avatar", methods=["POST"])
@login_required
def actualizar_avatar():
    profile = current_user.profile
    if not profile:
        profile = UserProfile(user_id=current_user.id)
        db.session.add(profile)

    f = request.files.get("avatar")
    if f and f.filename:
        ext = f.filename.rsplit(".", 1)[-1].lower()
        if ext in {"png", "jpg", "jpeg", "webp"}:
            filename = secure_filename(f"avatar_{current_user.id}.{ext}")
            path = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
            f.save(path)
            profile.avatar = f"/{path}"
            db.session.commit()
            flash("Avatar actualizado", "success")
        else:
            flash("Formato de imagen no permitido", "error")
    else:
        flash("No seleccionaste ninguna imagen", "error")

    return redirect(url_for("dashboard.dashboard_user"))