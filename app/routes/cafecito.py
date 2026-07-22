# app/routes/cafecito.py
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from app import db
from app.models import Donation, UserPlan
from app.services.mercadopago_service import MercadoPagoService

cafecito_bp = Blueprint("cafecito", __name__)


@cafecito_bp.route("/cafecito")
@login_required
def cafecito():
    """Página de donación 'Invitame un cafecito'."""
    # Verificar si el usuario ya tiene el badge activo
    plan = UserPlan.query.filter_by(user_id=current_user.id).first()
    tiene_badge = plan and plan.tiene_badge_cafecito()
    
    # Contar donaciones del usuario
    donaciones_count = Donation.query.filter_by(user_id=current_user.id, estado='approved').count()
    
    return render_template(
        "cafecito.html",
        tiene_badge=tiene_badge,
        donaciones_count=donaciones_count
    )


@cafecito_bp.route("/cafecito/donar", methods=["POST"])
@login_required
def donar():
    """Crea preferencia de pago y redirige a Mercado Pago."""
    mensaje = request.form.get("mensaje", "").strip()
    monto = 5000.0  # Monto fijo de $5.000 ARS
    
    try:
        mp_service = MercadoPagoService()
        preference = mp_service.crear_preferencia_pago(current_user, monto, mensaje)
        
        # Guardar donación pendiente en BD
        donation = Donation(
            user_id=current_user.id,
            monto=monto,
            moneda='ARS',
            mp_preference_id=preference["preference_id"],
            estado='pending',
            mensaje=mensaje
        )
        db.session.add(donation)
        db.session.commit()
        
        # Redirigir a Mercado Pago
        return redirect(preference["init_point"])
        
    except Exception as e:
        flash(f"Error al crear la preferencia de pago: {str(e)}", "error")
        return redirect(url_for("cafecito.cafecito"))


@cafecito_bp.route("/cafecito/exito")
@login_required
def exito():
    """Página de éxito después de pagar."""
    payment_id = request.args.get("payment_id")
    
    if payment_id:
        # Verificar el pago
        try:
            mp_service = MercadoPagoService()
            pago_info = mp_service.verificar_pago(payment_id)
            
            if pago_info["status"] == "approved":
                # Actualizar donación
                donation = Donation.query.filter_by(mp_payment_id=payment_id).first()
                if donation:
                    donation.estado = 'approved'
                    donation.mp_payment_id = payment_id
                    db.session.commit()
                
                # Activar badge de cafecito 
                plan = UserPlan.query.filter_by(user_id=current_user.id).first()
                if not plan:
                    plan = UserPlan(user_id=current_user.id)
                    db.session.add(plan)
                
                plan.fecha_expiracion_cafecito = datetime.utcnow() + timedelta(days=30)
                db.session.commit()
                
                flash("¡Gracias por tu cafecito! ❤️ Tu badge está activo.", "success")
            else:
                flash("El pago está pendiente de confirmación.", "warning")
                
        except Exception as e:
            flash(f"Error verificando el pago: {str(e)}", "error")
    
    return redirect(url_for("cafecito.cafecito"))


@cafecito_bp.route("/cafecito/fallo")
@login_required
def fallo():
    """Página de fallo después de intentar pagar."""
    flash("El pago no se pudo completar. Podés intentar de nuevo.", "error")
    return redirect(url_for("cafecito.cafecito"))


@cafecito_bp.route("/cafecito/pendiente")
@login_required
def pendiente():
    """Página de pago pendiente."""
    flash("Tu pago está siendo procesado. Te avisaremos cuando se confirme.", "info")
    return redirect(url_for("cafecito.cafecito"))