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
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    plan = db.Column(db.String(120), default="free")
    consumo = db.Column(db.Integer, default=0)
    limite = db.Column(db.Integer, default=100)
    fecha_expiracion_cafecito = db.Column(db.DateTime, nullable=True)
    user = db.relationship("User", backref=db.backref("plan", uselist=False))
    def tiene_badge_cafecito(self):
        """Verifica si el usuario tiene el badge de cafecito activo."""
        if not self.fecha_expiracion_cafecito:
            return False
        from datetime import datetime
        return datetime.utcnow() < self.fecha_expiracion_cafecito

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
