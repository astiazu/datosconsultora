# app/__init__.py
import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_mail import Mail
from dotenv import load_dotenv

load_dotenv()

db = SQLAlchemy()
login_manager = LoginManager()
mail = Mail()

login_manager.login_view = "auth.login"
login_manager.login_message = "Iniciá sesión para acceder a las herramientas."

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "cambia-esto-en-desarrollo")
    
    # Soporte dual: PostgreSQL (Render) o SQLite (local)
    database_url = os.environ.get("DATABASE_URL")
    if database_url:
        # Render usa postgres://, SQLAlchemy necesita postgresql://
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql://", 1)
        
        # Forzar el uso del driver psycopg (versión 3) que sí funciona en Python 3.14
        if database_url.startswith("postgresql://"):
            database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)
            
        SQLALCHEMY_DATABASE_URI = database_url
    else:
        SQLALCHEMY_DATABASE_URI = "sqlite:///datosconsultora.db"
    
    UPLOAD_FOLDER = os.environ.get("UPLOAD_FOLDER", "uploads")
    MAX_CONTENT_LENGTH = 200 * 1024 * 1024
    
    MAIL_SERVER = os.environ.get("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT = int(os.environ.get("MAIL_PORT", 587))
    MAIL_USE_TLS = True
    MAIL_USE_SSL = False
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = os.environ.get(
        "MAIL_DEFAULT_SENDER", 
        "DatosConsultora <noreply@datosconsultora.ar>"
    )


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    
    db.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)
    
    from app.models import User, ContactSettings
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    @app.context_processor
    def inject_contact():
        cs = ContactSettings.query.first()
        return dict(contact=cs)
    
    from app.routes.public import public_bp
    from app.routes.auth import auth_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.admin import admin_bp
    from app.routes.servicios import servicios_bp
    from app.routes.verificacion import verificacion_bp
    
    app.register_blueprint(public_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(servicios_bp)
    app.register_blueprint(verificacion_bp)
    
    return app


def init_db(app):
    from app.models import User, ContactSettings, Role
    
    with app.app_context():
        db.create_all()
        
        if not ContactSettings.query.first():
            db.session.add(ContactSettings())
        
        if not Role.query.filter_by(nombre="admin").first():
            db.session.add(Role(nombre="admin", descripcion="Administrador del sistema"))
            db.session.add(Role(nombre="usuario", descripcion="Usuario estándar"))
        
        if not User.query.filter_by(email="admin@datosconsultora.ar").first():
            admin_pw = os.environ.get("ADMIN_PASSWORD", "admin123")
            u = User(
                nombre="Admin",
                email="admin@datosconsultora.ar",
                telefono="5491100000000",
                is_admin=True,
                is_active_account=True,
                email_verificado=True,
                telefono_verificado=True,
            )
            u.set_password(admin_pw)
            db.session.add(u)
        
        db.session.commit()


# ⭐ CLAVE: Crear la app a nivel de módulo para que gunicorn la encuentre
app = create_app()

# ⭐ Inicializar la BD automáticamente al arrancar (solo si no existe el admin)
with app.app_context():
    init_db(app)