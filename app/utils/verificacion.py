# app/utils/verificacion.py
import secrets
from flask import url_for
from flask_mail import Message
from app import mail, db
from app.models import User, EmailVerificationToken, WhatsAppVerification


def generar_token_email(user):
    """Genera y guarda un token de verificación de email."""
    # Invalidar tokens anteriores
    EmailVerificationToken.query.filter_by(user_id=user.id, usado=False).update({'usado': True})
    
    token = secrets.token_urlsafe(32)
    vt = EmailVerificationToken(user_id=user.id, token=token)
    db.session.add(vt)
    db.session.commit()
    
    return token


def enviar_email_verificacion(user, token):
    """Envía email con link de verificación."""
    verification_url = url_for('verificacion.verificar_email', token=token, _external=True)
    
    msg = Message(
        subject="Verificá tu email - DatosConsultora",
        recipients=[user.email],
        html=f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #004d5c;">¡Bienvenido/a a DatosConsultora!</h2>
            <p>Hola {user.nombre},</p>
            <p>Para activar tu cuenta, hacé click en el siguiente botón:</p>
            <p style="text-align: center; margin: 30px 0;">
                <a href="{verification_url}" 
                   style="background-color: #004d5c; color: white; padding: 12px 30px; 
                          text-decoration: none; border-radius: 8px; display: inline-block;">
                   Verificar mi email
                </a>
            </p>
            <p style="color: #666; font-size: 14px;">
                Si el botón no funciona, copiá y pegá este link en tu navegador:<br>
                <a href="{verification_url}">{verification_url}</a>
            </p>
            <p style="color: #999; font-size: 12px; margin-top: 30px;">
                Este link expira en 24 horas. Si no solicitaste este registro, ignorá este email.
            </p>
        </div>
        """
    )
    
    try:
        mail.send(msg)
        return True
    except Exception as e:
        print(f"Error enviando email: {e}")
        return False


def generar_codigo_whatsapp(user):
    """Genera y guarda un código de verificación de WhatsApp."""
    # Invalidar códigos anteriores
    WhatsAppVerification.query.filter_by(user_id=user.id, usado=False).update({'usado': True})
    
    codigo = ''.join([str(secrets.randbelow(10)) for _ in range(6)])
    wv = WhatsAppVerification(user_id=user.id, codigo=codigo)
    db.session.add(wv)
    db.session.commit()
    
    return codigo


def obtener_link_whatsapp(user, codigo):
    """Genera link de WhatsApp con mensaje prellenado."""
    from app.models import ContactSettings
    cs = ContactSettings.query.first()
    numero_empresa = cs.whatsapp if cs else "5491100000000"
    
    mensaje = f"Hola! Mi código de verificación es: {codigo}"
    mensaje_encoded = mensaje.replace(" ", "%20")
    
    return f"https://wa.me/{numero_empresa}?text={mensaje_encoded}"