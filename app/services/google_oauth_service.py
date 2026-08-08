# app/services/google_oauth_service.py
"""
Integración OAuth 2.0 con Google ("Sign in with Google").

IMPORTANTE: authlib es una dependencia OPCIONAL. Si no está instalada,
la app arranca igual pero sin el botón de Google (GOOGLE_ENABLED=False).
Esto evita tumbar el sitio entero si la instalación falla en algún entorno.
"""
import logging
import os

logger = logging.getLogger(__name__)

# Intentamos importar authlib de forma defensiva
try:
    from authlib.integrations.flask_client import OAuth
    _AUTHLIB_AVAILABLE = True
except ImportError:
    _AUTHLIB_AVAILABLE = False
    OAuth = None
    logger.warning(
        "⚠️ authlib no está instalado. El login con Google quedará deshabilitado. "
        "Para activarlo: pip install authlib"
    )

oauth = OAuth() if _AUTHLIB_AVAILABLE else None


def init_oauth(app):
    """Registra el cliente de Google solo si authlib está instalado y hay credenciales."""
    # 1) Sin authlib → no hay OAuth posible
    if not _AUTHLIB_AVAILABLE or oauth is None:
        app.config["GOOGLE_ENABLED"] = False
        return

    # 2) Sin credenciales → OAuth existe pero Google no está configurado
    client_id = os.environ.get("GOOGLE_CLIENT_ID")
    client_secret = os.environ.get("GOOGLE_CLIENT_SECRET")
    if not client_id or not client_secret:
        app.config["GOOGLE_ENABLED"] = False
        return

    # 3) Todo listo → registrar cliente de Google
    try:
        oauth.init_app(app)
        oauth.register(
            name="google",
            client_id=client_id,
            client_secret=client_secret,
            server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
            client_kwargs={"scope": "openid email profile"},
        )
        app.config["GOOGLE_ENABLED"] = True
        logger.info("✅ OAuth de Google inicializado correctamente.")
    except Exception as exc:
        logger.exception(f"Error inicializando OAuth de Google: {exc}")
        app.config["GOOGLE_ENABLED"] = False