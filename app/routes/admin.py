# app/routes/admin.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
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
    planes_disponibles = Plan.query.order_by(Plan.orden).all()
    
    return render_template(
        "admin_usuarios.html", 
        usuarios=usuarios, 
        roles=roles, 
        filtro=filtro,
        planes_disponibles=planes_disponibles
    )

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
    
    try:
        # Importar todas las tablas relacionadas
        from app.models import (
            UserProfile, UserFile, Transcription, Assistant,
            ActivityLog, UserRole, EmailVerificationToken,
            PasswordResetToken, WhatsAppVerification, UserPlan,
            Donation, AnalysisSession, ExpedienteMonitoreado, 
            ExpedienteEstado, SesionJurisdiccion
        )
        
        # 1. Eliminar archivos subidos (y sus transcripciones)
        for user_file in UserFile.query.filter_by(user_id=user.id).all():
            Transcription.query.filter_by(file_id=user_file.id).delete()
        UserFile.query.filter_by(user_id=user.id).delete()
        
        # 2. Eliminar análisis de sentimientos (NUEVO)
        AnalysisSession.query.filter_by(user_id=user.id).delete()
        
        # 3. Eliminar expedientes monitoreados y sus estados (NUEVO)
        # Primero eliminar los estados (tienen FK a expediente_monitoreado)
        for exp in ExpedienteMonitoreado.query.filter_by(user_id=user.id).all():
            ExpedienteEstado.query.filter_by(expediente_monitoreado_id=exp.id).delete()
        ExpedienteMonitoreado.query.filter_by(user_id=user.id).delete()
        
        # 4. Eliminar sesiones de jurisdicción (NUEVO)
        SesionJurisdiccion.query.filter_by(user_id=user.id).delete()
        
        # 5. Eliminar otros registros relacionados
        UserProfile.query.filter_by(user_id=user.id).delete()
        Assistant.query.filter_by(user_id=user.id).delete()
        ActivityLog.query.filter_by(user_id=user.id).delete()
        UserRole.query.filter_by(user_id=user.id).delete()
        EmailVerificationToken.query.filter_by(user_id=user.id).delete()
        PasswordResetToken.query.filter_by(user_id=user.id).delete()
        WhatsAppVerification.query.filter_by(user_id=user.id).delete()
        
        # UserPlan (puede no existir para todos los usuarios)
        user_plan = UserPlan.query.filter_by(user_id=user.id).first()
        if user_plan:
            db.session.delete(user_plan)
        
        # Donation (del sistema de cafecito)
        Donation.query.filter_by(user_id=user.id).delete()
        
        # 6. Ahora sí eliminar el usuario
        db.session.delete(user)
        db.session.commit()
        
        # 7. Registrar el log (con user_id=None porque el usuario ya no existe)
        log = ActivityLog(
            user_id=current_user.id,
            accion="borrar_usuario",
            detalle=f"Usuario {email} eliminado con todos sus datos asociados",
            ip=request.remote_addr,
        )
        db.session.add(log)
        db.session.commit()
        
        flash(f"Usuario {email} eliminado correctamente", "success")
        
    except Exception as e:
        db.session.rollback()
        flash(f"Error al eliminar usuario: {str(e)}", "error")
        current_app.logger.error(f"Error eliminando usuario {email}: {str(e)}")
    
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
# GESTIÓN DE PLANES
# ============================================

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

# ============================================
# CAMBIO DE PLAN DE USUARIO
# ============================================

@admin_bp.route("/usuarios/<int:user_id>/plan", methods=["POST"])
def admin_usuario_plan(user_id):
    """Permite al admin cambiar el plan de un usuario y resetear su consumo."""
    from app.models import UserPlan, Plan
    
    user = User.query.get_or_404(user_id)
    nuevo_plan_nombre = request.form.get("plan_nombre")
    resetear_consumo = request.form.get("resetear_consumo") == "on"
    
    plan = Plan.query.filter_by(nombre=nuevo_plan_nombre).first()
    if not plan:
        flash("Plan inválido", "error")
        return redirect(url_for("admin.admin_usuarios"))
    
    # Buscar o crear UserPlan
    user_plan = UserPlan.query.filter_by(user_id=user.id).first()
    if not user_plan:
        user_plan = UserPlan(user_id=user.id)
        db.session.add(user_plan)
    
    # Actualizar plan
    user_plan.plan_id = plan.id
    user_plan.plan = plan.nombre  # campo legacy
    user_plan.limite_transcripciones = plan.limite_transcripciones_mes
    user_plan.limite_analisis = plan.limite_analisis_mes
    user_plan.es_lifetime = plan.es_lifetime
    
    # Resetear consumo si el admin lo pidió
    if resetear_consumo:
        user_plan.consumo_transcripciones = 0
        user_plan.consumo_analisis = 0
    
    db.session.commit()
    
    # Log de la acción
    log = ActivityLog(
        user_id=current_user.id,
        accion="cambio_plan_usuario",
        detalle=f"Plan de {user.email} cambiado a '{plan.display_name}'" + 
                (" (consumo reseteado)" if resetear_consumo else ""),
        ip=request.remote_addr,
    )
    db.session.add(log)
    db.session.commit()
    
    flash(f"✅ Plan de {user.email} cambiado a '{plan.display_name}'" + 
          (" y consumo mensual reseteado." if resetear_consumo else "."), 
          "success")
    return redirect(url_for("admin.admin_usuarios"))