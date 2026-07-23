# app/models.py
from app import db
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    telefono = db.Column(db.String(30), nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    is_active_account = db.Column(db.Boolean, default=True)
    email_verificado = db.Column(db.Boolean, default=False)
    telefono_verificado = db.Column(db.Boolean, default=False)
    creado = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, pw):
        self.password_hash = generate_password_hash(pw)

    def check_password(self, pw):
        return check_password_hash(self.password_hash, pw)


class ContactSettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email1 = db.Column(db.String(120), default="hola@datosconsultora.ar")
    email2 = db.Column(db.String(120), default="")
    email3 = db.Column(db.String(120), default="")
    whatsapp = db.Column(db.String(30), default="5491100000000")
    telefono_fijo = db.Column(db.String(30), default="")
    marca = db.Column(db.String(120), default="DatosConsultora")
    slogan = db.Column(db.String(250), default="Transformamos datos, procesos y negocios con IA")
    texto_home = db.Column(db.Text, default="")


class Role(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), unique=True, nullable=False)
    descripcion = db.Column(db.String(200))


class UserRole(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    role_id = db.Column(db.Integer, db.ForeignKey("role.id"))
    user = db.relationship("User", backref=db.backref("roles", lazy="dynamic"))
    role = db.relationship("Role")


class ActivityLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    accion = db.Column(db.String(200), nullable=False)
    detalle = db.Column(db.String(500))
    fecha = db.Column(db.DateTime, default=datetime.utcnow)
    ip = db.Column(db.String(50))
    user = db.relationship("User", backref=db.backref("activity_logs", lazy="dynamic"))


class UserProfile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    empresa = db.Column(db.String(120))
    cargo = db.Column(db.String(120))
    pais = db.Column(db.String(120))
    avatar = db.Column(db.String(200))
    user = db.relationship("User", backref=db.backref("profile", uselist=False))


class EmailVerificationToken(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    token = db.Column(db.String(200), unique=True, nullable=False)
    creado = db.Column(db.DateTime, default=datetime.utcnow)
    usado = db.Column(db.Boolean, default=False)
    user = db.relationship("User")


class PasswordResetToken(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    token = db.Column(db.String(200), unique=True, nullable=False)
    creado = db.Column(db.DateTime, default=datetime.utcnow)
    usado = db.Column(db.Boolean, default=False)
    user = db.relationship("User")


class WhatsAppVerification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    codigo = db.Column(db.String(6), nullable=False)
    creado = db.Column(db.DateTime, default=datetime.utcnow)
    usado = db.Column(db.Boolean, default=False)
    user = db.relationship("User", backref=db.backref("whatsapp_verifications", lazy="dynamic"))


class UserFile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    filename = db.Column(db.String(200))
    filepath = db.Column(db.String(300))
    tipo = db.Column(db.String(50))
    fecha = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship("User", backref=db.backref("files", lazy="dynamic"))


class Transcription(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    file_id = db.Column(db.Integer, db.ForeignKey("user_file.id"))
    texto = db.Column(db.Text)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship("User", backref=db.backref("transcriptions", lazy="dynamic"))
    file = db.relationship("UserFile")


class Assistant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    nombre = db.Column(db.String(120))
    descripcion = db.Column(db.String(300))
    creado = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship("User", backref=db.backref("assistants", lazy="dynamic"))


class UserPlan(db.Model):
    """Plan actual de un usuario."""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), unique=True)
    plan_id = db.Column(db.Integer, db.ForeignKey('plan.id'), nullable=True)
    plan = db.Column(db.String(120), default="bronce")  # Legacy, mantener por compatibilidad
    consumo_transcripciones = db.Column(db.Integer, default=0)
    consumo_analisis = db.Column(db.Integer, default=0)
    limite_transcripciones = db.Column(db.Integer, default=5)
    limite_analisis = db.Column(db.Integer, default=3)
    fecha_inicio = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_fin = db.Column(db.DateTime, nullable=True)
    es_lifetime = db.Column(db.Boolean, default=False)
    fecha_expiracion_cafecito = db.Column(db.DateTime, nullable=True)
    user = db.relationship('User', backref=db.backref('user_plan', uselist=False))
    plan_obj = db.relationship('Plan')
    
    def obtener_plan_obj(self):
        """Obtiene el objeto Plan del usuario (default: bronce)."""
        if self.plan_obj:
            return self.plan_obj
        return Plan.query.filter_by(nombre='bronce').first()
    
    def puede_usar_feature(self, feature):
        """Verifica si el usuario puede usar una feature."""
        plan = self.obtener_plan_obj()
        return plan.tiene_feature(feature) if plan else False
    
    def tiene_badge_cafecito(self):
        """Verifica si el usuario tiene el badge de cafecito activo."""
        if not self.fecha_expiracion_cafecito:
            return False
        return datetime.utcnow() < self.fecha_expiracion_cafecito
    
    def consumo_transcripciones_mes(self):
        """Cuenta transcripciones del mes actual."""
        from app.models import Transcription
        inicio_mes = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        return Transcription.query.filter(
            Transcription.user_id == self.user_id,
            Transcription.fecha >= inicio_mes
        ).count()
    
    def consumo_analisis_mes(self):
        """Cuenta análisis del mes actual (placeholder por ahora)."""
        return 0  # TODO: implementar cuando tengamos modelo de AnalysisSession
    
class Donation(db.Model):
    """Registro de donaciones 'Invitame un cafecito'."""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    monto = db.Column(db.Float, nullable=False)
    moneda = db.Column(db.String(10), default='ARS')
    mp_payment_id = db.Column(db.String(100), unique=True, nullable=True)
    mp_preference_id = db.Column(db.String(100), nullable=True)
    estado = db.Column(db.String(50), default='pending')  # pending, approved, rejected
    mensaje = db.Column(db.String(500), default='')
    fecha = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship('User', backref=db.backref('donations', lazy='dynamic'))

class Plan(db.Model):
    """Planes disponibles (editables desde el admin)."""
    __tablename__ = 'plan'
    
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), unique=True, nullable=False)  # bronce, plata, oro, lifetime
    display_name = db.Column(db.String(100), nullable=False)  # "Bronce", "Plata", etc.
    descripcion = db.Column(db.Text, default='')
    precio_mensual = db.Column(db.Float, default=0.0)
    precio_anual = db.Column(db.Float, default=0.0)
    precio_lifetime = db.Column(db.Float, nullable=True)
    es_lifetime = db.Column(db.Boolean, default=False)
    activo = db.Column(db.Boolean, default=True)
    orden = db.Column(db.Integer, default=0)
    
    # Features incluidas
    incluye_historial = db.Column(db.Boolean, default=False)
    incluye_motor_semantico = db.Column(db.Boolean, default=False)
    incluye_agentes = db.Column(db.Boolean, default=False)
    incluye_actividad_completa = db.Column(db.Boolean, default=False)
    
    # Límites de uso
    limite_transcripciones_mes = db.Column(db.Integer, default=5)
    limite_analisis_mes = db.Column(db.Integer, default=3)
    
    # Icono y color para la UI
    icono = db.Column(db.String(50), default='bi-award')
    color = db.Column(db.String(20), default='secondary')
    
    def tiene_feature(self, feature):
        """Verifica si el plan incluye una feature."""
        features_map = {
            'historial': self.incluye_historial,
            'motor_semantico': self.incluye_motor_semantico,
            'agentes': self.incluye_agentes,
            'actividad_completa': self.incluye_actividad_completa,
        }
        return features_map.get(feature, False)
