import os
import hmac
import hashlib
from datetime import timedelta

from flask import Blueprint, current_app, jsonify, request

from app import db
from app.models import Donation
from app.services.mercadopago_service import MercadoPagoService
from app.services.plan_service import obtener_plan_usuario
from app.utils.datetime_utils import utc_now

webhook_bp = Blueprint("webhook", __name__)


def firma_valida(x_signature, x_request_id, data_id, secret):
    """Verifica HMAC SHA-256 según el manifiesto de Webhooks de Mercado Pago.

    Es compatible con el SDK 2.2.x, que no incluye ``mercadopago.webhook``.
    """
    if not x_signature or not x_request_id or not data_id:
        return False
    values = {}
    for item in x_signature.split(","):
        key, separator, value = item.strip().partition("=")
        if separator:
            values[key] = value
    timestamp, received_hash = values.get("ts"), values.get("v1")
    if not timestamp or not received_hash:
        return False
    manifest = f"id:{str(data_id).lower()};request-id:{x_request_id};ts:{timestamp};"
    expected_hash = hmac.new(secret.encode("utf-8"), manifest.encode("utf-8"), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected_hash, received_hash)


@webhook_bp.route("/webhook/mercadopago", methods=["POST"])
def mercadopago_webhook():
    """El webhook firmado, no la URL de retorno, acredita el pago."""
    payload = request.get_json(silent=True) or {}
    payment_id = request.args.get("data.id") or payload.get("data", {}).get("id")
    secret = os.environ.get("MP_WEBHOOK_SECRET")
    if not secret or not payment_id:
        return jsonify({"error": "notificación inválida"}), 401
    if not firma_valida(
        request.headers.get("x-signature"), request.headers.get("x-request-id"), payment_id, secret
    ):
        return jsonify({"error": "firma inválida"}), 401
    try:
        pago = MercadoPagoService().verificar_pago(payment_id)
        donation = Donation.query.filter_by(external_reference=pago.get("external_reference")).first()
        if not donation:
            return jsonify({"status": "ignored"}), 200
        if donation.mp_payment_id and donation.mp_payment_id != str(payment_id):
            return jsonify({"error": "pago ya asociado"}), 409
        donation.mp_payment_id = str(payment_id)
        donation.estado = pago["status"]
        if pago["status"] == "approved":
            plan = obtener_plan_usuario(donation.user)
            plan.fecha_expiracion_cafecito = utc_now() + timedelta(days=30)
        db.session.commit()
        return jsonify({"status": "ok"}), 200
    except Exception:
        db.session.rollback()
        current_app.logger.exception("Error procesando webhook Mercado Pago")
        return jsonify({"status": "error"}), 500
