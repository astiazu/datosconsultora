# app/__init__.py
import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_mail import Mail
from flask_wtf.csrf import CSRFProtect
from dotenv import load_dotenv

load_dotenv()

db = SQLAlchemy()
login_manager = LoginManager()
mail = Mail()
csrf = CSRFProtect()

login_manager.login_view = "auth.login"
login_manager.login_message = "Iniciá sesión para acceder a las herramientas."


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY")

    # Soporte dual: PostgreSQL (Render) o SQLite (local)
    database_url = os.environ.get("DATABASE_URL")
    if database_url:
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql://", 1)
        if database_url.startswith("postgresql://"):
            database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)
        SQLALCHEMY_DATABASE_URI = database_url
    else:
        SQLALCHEMY_DATABASE_URI = "sqlite:///datosconsultora.db"

    # ✅ ANTI-SSL-ERROR: valida y recicla conexiones a PostgreSQL
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,         # valida conexión antes de cada query
        "pool_recycle": 280,           # recicla cada 280s (< 300s de Render)
        "pool_timeout": 30,
        "connect_args": {
            "connect_timeout": 10,
            "keepalives": 1,
            "keepalives_idle": 30,
            "keepalives_interval": 10,
            "keepalives_count": 5,
        } if database_url else {},
    }

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

    SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "true").lower() == "true"
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    if not app.config["SECRET_KEY"]:
        raise RuntimeError("SECRET_KEY es obligatoria; configurala en el entorno.")

    if not os.path.isabs(app.config["UPLOAD_FOLDER"]):
        app.config["UPLOAD_FOLDER"] = os.path.join(app.instance_path, app.config["UPLOAD_FOLDER"])
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)
    csrf.init_app(app)

    # OAuth de Google (opcional: si authlib no está instalado o falla el init,
    # la app arranca igual con GOOGLE_ENABLED=False)
    try:
        from app.services.google_oauth_service import init_oauth
        init_oauth(app)
    except Exception as exc:
        app.config["GOOGLE_ENABLED"] = False
        import logging
        logging.getLogger(__name__).warning(
            f"⚠️ No se pudo inicializar OAuth de Google: {exc}. "
            f"El login con Google quedará deshabilitado."
        )

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
    from app.routes.cafecito import cafecito_bp
    from app.routes.webhook import webhook_bp
    from app.routes.planes import planes_bp
    from app.routes.historial import historial_bp
    from app.routes.agentes import agentes_bp
    from app.routes.api import api_bp
    from app.routes.plata import plata_bp

    app.register_blueprint(public_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(servicios_bp)
    app.register_blueprint(verificacion_bp)
    app.register_blueprint(cafecito_bp)
    app.register_blueprint(webhook_bp)
    csrf.exempt(webhook_bp)
    app.register_blueprint(planes_bp)
    app.register_blueprint(historial_bp)
    app.register_blueprint(agentes_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(plata_bp)

    return app


def _migrar_donation():
    """
    Migración idempotente para la tabla donation.
    Agrega columnas faltantes (external_reference, mp_preference_id) si no existen.
    Se ejecuta automáticamente al arrancar la app.
    """
    from sqlalchemy import inspect, text
    
    insp = inspect(db.engine)
    
    # Verificar que la tabla existe
    if "donation" not in insp.get_table_names():
        return  # Se creará al primer arranque normal
    
    cols = [c["name"] for c in insp.get_columns("donation")]
    
    columnas_necesarias = {
        "external_reference": "VARCHAR(100)",
        "mp_preference_id": "VARCHAR(100)",
    }
    
    # Agregar columnas faltantes
    for col, tipo in columnas_necesarias.items():
        if col not in cols:
            try:
                db.session.execute(text(f'ALTER TABLE donation ADD COLUMN {col} {tipo}'))
                db.session.commit()
                print(f"✅ Columna '{col}' agregada a donation")
            except Exception as e:
                db.session.rollback()
                print(f"⚠️ Migración de '{col}' omitida: {e}")
    
    # Ajustar NOT NULL de external_reference si existen filas viejas sin valor
    try:
        insp2 = inspect(db.engine)
        cols2 = [c["name"] for c in insp2.get_columns("donation")]
        if "external_reference" in cols2:
            # Detectar dialecto: PostgreSQL vs SQLite
            dialect_name = db.engine.dialect.name
            
            if dialect_name == "postgresql":
                # PostgreSQL: usar cast nativo
                db.session.execute(text("""
                    UPDATE donation 
                    SET external_reference = 'legacy-' || id::text 
                    WHERE external_reference IS NULL
                """))
            else:
                # SQLite y otros: usar CAST estándar
                db.session.execute(text("""
                    UPDATE donation 
                    SET external_reference = 'legacy-' || CAST(id AS TEXT) 
                    WHERE external_reference IS NULL
                """))
            
            db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"⚠️ No se pudo poblar external_reference legacy: {e}")
    
    # Crear índice único para external_reference si no existe
    try:
        idx_existentes = [i["name"] for i in insp.get_indexes("donation")]
        if "uq_donation_external_reference" not in idx_existentes:
            db.session.execute(text(
                'CREATE UNIQUE INDEX uq_donation_external_reference '
                'ON donation (external_reference)'
            ))
            db.session.commit()
            print("✅ Índice único external_reference creado")
    except Exception as e:
        db.session.rollback()
        print(f"⚠️ No se pudo crear índice único: {e}")


def init_db(app):
    from app.models import User, ContactSettings, Role
    with app.app_context():
        db.create_all()
        
        # ✅ Migración automática de tabla donation
        _migrar_donation()

        if not ContactSettings.query.first():
            db.session.add(ContactSettings())

        if not Role.query.filter_by(nombre="admin").first():
            db.session.add(Role(nombre="admin", descripcion="Administrador del sistema"))
            db.session.add(Role(nombre="usuario", descripcion="Usuario estándar"))

        if not User.query.filter_by(email="admin@datosconsultora.ar").first():
            admin_pw = os.environ.get("ADMIN_PASSWORD")
            if not admin_pw:
                raise RuntimeError("ADMIN_PASSWORD es obligatoria al crear el administrador inicial.")
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