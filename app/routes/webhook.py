# app/routes/webhook.py
from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta
from app import db
from app.models import Donation, User, UserPlan
from app.services.mercadopago_service import MercadoPagoService

webhook_bp = Blueprint("webhook", __name__)


@webhook_bp.route("/webhook/mercadopago", methods=["POST"])
def mercadopago_webhook():
    """
    Webhook para recibir notificaciones de Mercado Pago.
    MP envía POST a esta URL cuando hay un cambio en el estado del pago.
    """
    try:
        # Mercado Pago envía diferentes tipos de notificaciones
        data = request.get_json()
        
        if not data:
            return jsonify({"status": "ok"}), 200
        
        # Filtrar solo notificaciones de pagos
        if data.get("type") == "payment":
            payment_id = data.get("data", {}).get("id")
            
            if payment_id:
                # Verificar el pago
                mp_service = MercadoPagoService()
                pago_info = mp_service.verificar_pago(payment_id)
                
                if pago_info["status"] == "approved":
                    # Buscar la donación por external_reference
                    external_ref = pago_info.get("external_reference", "")
                    
                    # Extraer user_id del external_reference (formato: "user-{id}-{timestamp}")
                    if external_ref.startswith("user-"):
                        parts = external_ref.split("-")
                        if len(parts) >= 2:
                            user_id = int(parts[1])
                            
                            # Actualizar donación
                            donation = Donation.query.filter_by(
                                mp_preference_id=payment_id,
                                user_id=user_id
                            ).first()
                            
                            if donation:
                                donation.estado = 'approved'
                                donation.mp_payment_id = payment_id
                                db.session.commit()
                                
                                # Activar badge de cafecito por 30 días
                                plan = UserPlan.query.filter_by(user_id=user_id).first()
                                if not plan:
                                    plan = UserPlan(user_id=user_id)
                                    db.session.add(plan)
                                
                                plan.fecha_expiracion_cafecito = datetime.utcnow() + timedelta(days=30)
                                db.session.commit()
                                
                                print(f"✅ Donación confirmada para user_id={user_id}")
        
        return jsonify({"status": "ok"}), 200
        
    except Exception as e:
        print(f"❌ Error en webhook: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500



