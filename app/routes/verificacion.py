# app/routes/verificacion.py
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from app.models import User, EmailVerificationToken, WhatsAppVerification
from app.utils.verificacion import generar_codigo_whatsapp, obtener_link_whatsapp

verificacion_bp = Blueprint("verificacion", __name__)


@verificacion_bp.route("/verificar-email/<token>")
def verificar_email(token):
    """Endpoint para verificar email con token."""
    vt = EmailVerificationToken.query.filter_by(token=token, usado=False).first()
    
    if not vt:
        flash("Link de verificación inválido o expirado", "error")
        return redirect(url_for("auth.login"))
    
    user = User.query.get(vt.user_id)
    if not user:
        flash("Usuario no encontrado", "error")
        return redirect(url_for("auth.login"))
    
    # Marcar como verificado
    user.email_verificado = True
    vt.usado = True
    db.session.commit()
    
    flash("¡Email verificado exitosamente! Ya podés usar todas las funciones.", "success")
    return redirect(url_for("auth.login"))


@verificacion_bp.route("/verificar-whatsapp", methods=["GET", "POST"])
@login_required
def verificar_whatsapp():
    """Página para verificar WhatsApp."""
    if current_user.telefono_verificado:
        flash("Tu WhatsApp ya está verificado", "success")
        return redirect(url_for("dashboard.dashboard_user"))
    
    # Buscar código activo
    wv = WhatsAppVerification.query.filter_by(
        user_id=current_user.id, 
        usado=False
    ).order_by(WhatsAppVerification.creado.desc()).first()
    
    if request.method == "POST":
        codigo_ingresado = request.form.get("codigo", "").strip()
        
        if wv and wv.codigo == codigo_ingresado:
            current_user.telefono_verificado = True
            wv.usado = True
            db.session.commit()
            
            flash("¡WhatsApp verificado exitosamente!", "success")
            return redirect(url_for("dashboard.dashboard_user"))
        else:
            flash("Código incorrecto. Verificá que sea el mismo que enviaste por WhatsApp.", "error")
    
    # Si no hay código activo, generar uno nuevo
    if not wv:
        codigo = generar_codigo_whatsapp(current_user)
        wv = WhatsAppVerification.query.filter_by(
            user_id=current_user.id, 
            usado=False
        ).order_by(WhatsAppVerification.creado.desc()).first()
    
    link_whatsapp = obtener_link_whatsapp(current_user, wv.codigo)
    
    return render_template(
        "verificar_whatsapp.html",
        codigo=wv.codigo,
        link_whatsapp=link_whatsapp,
        telefono=current_user.telefono
    )


@verificacion_bp.route("/reenviar-codigo-whatsapp")
@login_required
def reenviar_codigo_whatsapp():
    """Genera un nuevo código de WhatsApp."""
    if current_user.telefono_verificado:
        flash("Tu WhatsApp ya está verificado", "success")
        return redirect(url_for("dashboard.dashboard_user"))
    
    codigo = generar_codigo_whatsapp(current_user)
    flash(f"Nuevo código generado: {codigo}", "success")
    return redirect(url_for("verificacion.verificar_whatsapp"))