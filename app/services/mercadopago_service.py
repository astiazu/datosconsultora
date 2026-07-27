# app/services/mercadopago_service.py
import os
import mercadopago
from datetime import datetime, timedelta
from app.utils.datetime_utils import utc_now
from flask import url_for
from flask import current_app


class MercadoPagoService:
    """Servicio para integrar Mercado Pago."""
    
    def __init__(self):
        access_token = os.environ.get('MP_ACCESS_TOKEN')
        if not access_token:
            raise ValueError("MP_ACCESS_TOKEN no configurado en variables de entorno")
        self.sdk = mercadopago.SDK(access_token)
    
    def crear_preferencia_pago(self, user, external_reference, monto=5000.0, mensaje=""):
        """
        Crea una preferencia de pago en Mercado Pago.
        
        :param user: Usuario que dona
        :param monto: Monto en ARS (default: $5.000)
        :param mensaje: Mensaje opcional del donante
        :return: Dict con preference_id e init_point (URL de pago)
        """
        preference_data = {
            "items": [
                {
                    "id": f"cafecito-{user.id}",
                    "title": "❤️ Invitame un cafecito",
                    "description": f"Donación de {user.nombre} a DatosConsultora",
                    "quantity": 1,
                    "currency_id": "ARS",
                    "unit_price": float(monto),
                }
            ],
            "payer": {
                "name": user.nombre,
                "email": user.email,
            },
            "external_reference": external_reference,
            "back_urls": {
                "success": url_for('cafecito.exito', _external=True),
                "failure": url_for('cafecito.fallo', _external=True),
                "pending": url_for('cafecito.pendiente', _external=True),
            },
            "auto_return": "approved",
            "notification_url": url_for('webhook.mercadopago_webhook', _external=True),
            "statement_descriptor": "DATOSCONSULTORA",
        }
        
        try:
            preference_response = self.sdk.preference().create(preference_data)
            preference = preference_response.get("response", {})
            if not isinstance(preference, dict) or "id" not in preference:
                status = preference_response.get("status", "desconocido")
                detalle = preference.get("message") if isinstance(preference, dict) else None
                detalle = detalle or preference.get("error") if isinstance(preference, dict) else detalle
                current_app.logger.error(
                    "Mercado Pago rechazó la preferencia (status=%s, detalle=%s)", status, detalle or preference
                )
                raise ValueError(f"Mercado Pago rechazó la preferencia (HTTP {status}).")
            
            return {
                "preference_id": preference["id"],
                "init_point": preference["init_point"],  # URL para redirigir al usuario
            }
        except Exception as e:
            raise Exception(f"Error creando preferencia de pago: {str(e)}")
    
    def verificar_pago(self, payment_id):
        """
        Verifica el estado de un pago en Mercado Pago.
        
        :param payment_id: ID del pago de MP
        :return: Dict con estado del pago
        """
        try:
            payment_response = self.sdk.payment().get(payment_id)
            payment = payment_response["response"]
            
            return {
                "status": payment["status"],  # approved, pending, rejected
                "status_detail": payment.get("status_detail", ""),
                "external_reference": payment.get("external_reference", ""),
            }
        except Exception as e:
            raise Exception(f"Error verificando pago: {str(e)}")
