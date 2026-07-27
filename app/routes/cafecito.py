from uuid import uuid4

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app import db
from app.models import Donation, UserPlan
from app.services.mercadopago_service import MercadoPagoService

cafecito_bp = Blueprint("cafecito", __name__)


@cafecito_bp.route("/cafecito")
@login_required
def cafecito():
    plan = UserPlan.query.filter_by(user_id=current_user.id).first()
    return render_template(
        "cafecito.html",
        tiene_badge=bool(plan and plan.tiene_badge_cafecito()),
        donaciones_count=Donation.query.filter_by(user_id=current_user.id, estado="approved").count(),
    )


@cafecito_bp.route("/cafecito/donar", methods=["POST"])
@login_required
def donar():
    mensaje = request.form.get("mensaje", "").strip()
    donation = Donation(
        user_id=current_user.id, monto=5000.0, moneda="ARS", estado="pending",
        mensaje=mensaje, external_reference=f"donation-{uuid4().hex}",
    )
    try:
        db.session.add(donation)
        db.session.commit()
        preference = MercadoPagoService().crear_preferencia_pago(
            current_user, donation.external_reference, donation.monto, mensaje
        )
        donation.mp_preference_id = preference["preference_id"]
        db.session.commit()
        return redirect(preference["init_point"])
    except Exception:
        db.session.rollback()
        current_app.logger.exception("Error creando preferencia de Mercado Pago")
        flash("No pudimos iniciar el pago. Intentá nuevamente.", "error")
        return redirect(url_for("cafecito.cafecito"))


@cafecito_bp.route("/cafecito/exito")
@login_required
def exito():
    # Nunca acreditar desde una URL controlada por el navegador.
    flash("Recibimos tu regreso de Mercado Pago. Confirmaremos el pago automáticamente.", "info")
    return redirect(url_for("cafecito.cafecito"))


@cafecito_bp.route("/cafecito/fallo")
@login_required
def fallo():
    flash("El pago no se pudo completar. Podés intentar de nuevo.", "error")
    return redirect(url_for("cafecito.cafecito"))


@cafecito_bp.route("/cafecito/pendiente")
@login_required
def pendiente():
    flash("Tu pago está siendo procesado. Te avisaremos cuando se confirme.", "info")
    return redirect(url_for("cafecito.cafecito"))
