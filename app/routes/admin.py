# app/routes/admin.py
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from app.models import User, ContactSettings, ActivityLog, Role, UserRole, Plan
from app.services.plan_service import inicializar_planes_por_defecto

admin_bp = Blueprint("admin", __name__)


@admin_bp.before_request
@login_required
def check_admin():
    if not current_user.is_admin:
        flash("No tenés permisos de administrador", "error")
        return redirect(url_for("dashboard.dashboard_user"))


@admin_bp.route("/")
def admin_panel():
    usuarios = User.query.all()
    usuarios_count = len(usuarios)
    activos_count = len([u for u in usuarios if u.is_active_account])
    logs_recientes = ActivityLog.query.order_by(ActivityLog.fecha.desc()).limit(10).all()
    return render_template(
        "admin_panel.html",
        usuarios_count=usuarios_count,
        activos_count=activos_count,
        logs_recientes=logs_recientes,
    )


@admin_bp.route("/usuarios")
def admin_usuarios():
    filtro = request.args.get("filtro", "todos")
    if filtro == "activos":
        usuarios = User.query.filter_by(is_active_account=True).all()
    elif filtro == "inactivos":
        usuarios = User.query.filter_by(is_active_account=False).all()
    else:
        usuarios = User.query.all()

    roles = Role.query.all()
    return render_template("admin_usuarios.html", usuarios=usuarios, roles=roles, filtro=filtro)


@admin_bp.route("/usuarios/<int:user_id>/toggle")
def admin_usuario_toggle(user_id):
    user = User.query.get_or_404(user_id)
    user.is_active_account = not user.is_active_account
    db.session.commit()

    log = ActivityLog(
        user_id=current_user.id,
        accion="cambio_estado_usuario",
        detalle=f"Usuario {user.email} {'activado' if user.is_active_account else 'desactivado'}",
        ip=request.remote_addr,
    )
    db.session.add(log)
    db.session.commit()

    flash(f"Usuario {'activado' if user.is_active_account else 'desactivado'}", "success")
    return redirect(url_for("admin.admin_usuarios"))


@admin_bp.route("/usuarios/<int:user_id>/roles", methods=["POST"])
def admin_usuario_roles(user_id):
    user = User.query.get_or_404(user_id)
    roles_ids = request.form.getlist("roles")

    UserRole.query.filter_by(user_id=user.id).delete()

    for role_id in roles_ids:
        ur = UserRole(user_id=user.id, role_id=int(role_id))
        db.session.add(ur)

    db.session.commit()

    log = ActivityLog(
        user_id=current_user.id,
        accion="cambio_roles",
        detalle=f"Roles actualizados para {user.email}",
        ip=request.remote_addr,
    )
    db.session.add(log)
    db.session.commit()

    flash("Roles actualizados", "success")
    return redirect(url_for("admin.admin_usuarios"))


@admin_bp.route("/usuarios/<int:user_id>/reset", methods=["POST"])
def admin_usuario_reset_password(user_id):
    user = User.query.get_or_404(user_id)
    nueva_pw = request.form.get("nueva_password")

    if nueva_pw:
        user.set_password(nueva_pw)
        db.session.commit()

        log = ActivityLog(
            user_id=current_user.id,
            accion="reset_password",
            detalle=f"Password reseteado para {user.email}",
            ip=request.remote_addr,
        )
        db.session.add(log)
        db.session.commit()

        flash("Contraseña actualizada", "success")
    else:
        flash("La contraseña no puede estar vacía", "error")

    return redirect(url_for("admin.admin_usuarios"))


@admin_bp.route("/usuarios/<int:user_id>/delete", methods=["POST"])
def admin_usuario_delete(user_id):
    user = User.query.get_or_404(user_id)

    if user.id == current_user.id:
        flash("No podés eliminarte a vos mismo", "error")
        return redirect(url_for("admin.admin_usuarios"))

    email = user.email
    db.session.delete(user)
    db.session.commit()

    log = ActivityLog(
        user_id=current_user.id,
        accion="borrar_usuario",
        detalle=f"Usuario {email} eliminado",
        ip=request.remote_addr,
    )
    db.session.add(log)
    db.session.commit()

    flash("Usuario eliminado", "success")
    return redirect(url_for("admin.admin_usuarios"))


@admin_bp.route("/config", methods=["GET", "POST"])
def admin_config():
    cs = ContactSettings.query.first()

    if request.method == "POST":
        cs.email1 = request.form.get("email1", "")
        cs.email2 = request.form.get("email2", "")
        cs.email3 = request.form.get("email3", "")
        cs.whatsapp = request.form.get("whatsapp", "")
        cs.telefono_fijo = request.form.get("telefono_fijo", "")
        cs.marca = request.form.get("marca", "")
        cs.slogan = request.form.get("slogan", "")
        cs.texto_home = request.form.get("texto_home", "")

        db.session.commit()

        log = ActivityLog(
            user_id=current_user.id,
            accion="config_update",
            detalle="Configuración del sitio actualizada",
            ip=request.remote_addr,
        )
        db.session.add(log)
        db.session.commit()

        flash("Configuración guardada", "success")
        return redirect(url_for("admin.admin_config"))

    return render_template("admin_config.html", cs=cs)


@admin_bp.route("/logs")
def admin_logs():
    tipo = request.args.get("tipo", "todos")

    if tipo == "todos":
        logs = ActivityLog.query.order_by(ActivityLog.fecha.desc()).limit(200).all()
    else:
        logs = (
            ActivityLog.query.filter_by(accion=tipo)
            .order_by(ActivityLog.fecha.desc())
            .limit(200)
            .all()
        )

    return render_template("admin_logs.html", logs=logs, tipo=tipo)

# ============================================
# GESTIÓN DE PLANES (agregado al final del archivo)
# ============================================
#from app.models import Plan
#from app.services.plan_service import inicializar_planes_por_defecto


@admin_bp.route("/planes")
def admin_planes():
    inicializar_planes_por_defecto()
    planes = Plan.query.order_by(Plan.orden).all()
    return render_template("admin_planes.html", planes=planes)


@admin_bp.route("/planes/<int:plan_id>/editar", methods=["POST"])
def admin_plan_editar(plan_id):
    plan = Plan.query.get_or_404(plan_id)
    
    plan.display_name = request.form.get("display_name", plan.display_name)
    plan.descripcion = request.form.get("descripcion", plan.descripcion)
    plan.precio_mensual = float(request.form.get("precio_mensual", plan.precio_mensual) or 0)
    plan.precio_anual = float(request.form.get("precio_anual", plan.precio_anual) or 0)
    plan.precio_lifetime = float(request.form.get("precio_lifetime", plan.precio_lifetime) or 0) if request.form.get("precio_lifetime") else plan.precio_lifetime
    plan.limite_transcripciones_mes = int(request.form.get("limite_transcripciones_mes", plan.limite_transcripciones_mes) or 0)
    plan.limite_analisis_mes = int(request.form.get("limite_analisis_mes", plan.limite_analisis_mes) or 0)
    plan.incluye_historial = request.form.get("incluye_historial") == "on"
    plan.incluye_motor_semantico = request.form.get("incluye_motor_semantico") == "on"
    plan.incluye_agentes = request.form.get("incluye_agentes") == "on"
    plan.incluye_actividad_completa = request.form.get("incluye_actividad_completa") == "on"
    plan.activo = request.form.get("activo") == "on"
    
    db.session.commit()
    
    log = ActivityLog(
        user_id=current_user.id,
        accion="plan_update",
        detalle=f"Plan '{plan.display_name}' actualizado",
        ip=request.remote_addr,
    )
    db.session.add(log)
    db.session.commit()
    
    flash(f"Plan '{plan.display_name}' actualizado correctamente", "success")
    return redirect(url_for("admin.admin_planes"))