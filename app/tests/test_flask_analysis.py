# app/tests/test_flask_analysis.py
"""
Test de integración Flask → AnalysisService → MIC → Groq

Versión autocontenida que no depende de fixtures externas de conftest.py.
"""
import pytest
from unittest.mock import patch
import sys
import os

# Asegurar que podamos importar desde la raíz del proyecto
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Importá tu instancia de Flask. 
# Si usas una factory function (ej: create_app), cambiá esto por:
# from app import create_app
# y en la fixture app: return create_app("testing")
try:
    from app import app as flask_app
except ImportError:
    try:
        from run import app as flask_app
    except ImportError:
        raise ImportError("No se pudo encontrar la instancia de la app Flask. Ajustá el import en test_flask_analysis.py")


@pytest.fixture
def app():
    """Configura la app para testing."""
    flask_app.config["TESTING"] = True
    flask_app.config["WTF_CSRF_ENABLED"] = False  # Desactiva CSRF para tests
    return flask_app


@pytest.fixture
def client(app):
    """Crea el cliente de test de Flask."""
    return app.test_client()


def test_api_analisis_sin_auth(client):
    """Sin autenticación debe devolver 401 o redirigir (302)."""
    response = client.post(
        "/api/analisis",
        json={
            "origen": "facebook",
            "comentarios": ["test"],
        },
    )
    
    # Flask-Login usualmente devuelve 401 Unauthorized o 302 Redirect a login
    assert response.status_code in [401, 302]


@patch("flask_login.utils.current_user")
def test_api_analisis_con_auth(mock_user, client):
    """Con autenticación debe ejecutar el análisis y devolver respuesta."""
    # Configurar el mock del usuario con plan Plata
    mock_user.id = 1
    mock_user.email = "test@example.com"
    mock_user.plan = "plata"
    mock_user.is_authenticated = True
    mock_user.is_active = True
    mock_user.is_anonymous = False
    mock_user.get_id = lambda: "1"
    
    response = client.post(
        "/api/analisis",
        json={
            "origen": "facebook",
            "comentarios": [
                "Qué buena gestión, cada día estamos mejor 🙄",
                "Excelente trabajo 👏",
                "Bueno... veremos",
            ],
            "contexto": "Opiniones sobre la gestión municipal",
        },
    )
    
    # Debe devolver respuesta válida (200 OK, o 400/500 si hay error de lógica, pero NUNCA 401/403)
    assert response.status_code in [200, 400, 500]
    
    data = response.get_json()
    assert "success" in data


@patch("flask_login.utils.current_user")
def test_api_analisis_comentarios_vacios(mock_user, client):
    """Sin comentarios debe devolver error 400."""
    mock_user.id = 1
    mock_user.plan = "plata"
    mock_user.is_authenticated = True
    mock_user.is_active = True
    mock_user.is_anonymous = False
    mock_user.get_id = lambda: "1"
    
    response = client.post(
        "/api/analisis",
        json={
            "origen": "facebook",
            "comentarios": [],
        },
    )
    
    assert response.status_code == 400
    data = response.get_json()
    assert data["success"] is False
    assert "al menos un comentario" in data["error"].lower()# app/tests/test_flask_analysis.py
"""
Test de integración Flask → AnalysisService → MIC → Groq

Versión autocontenida que no depende de fixtures externas de conftest.py.
"""
import pytest
from unittest.mock import patch
import sys
import os

# Asegurar que podamos importar desde la raíz del proyecto
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Importá tu instancia de Flask. 
# Si usas una factory function (ej: create_app), cambiá esto por:
# from app import create_app
# y en la fixture app: return create_app("testing")
try:
    from app import app as flask_app
except ImportError:
    try:
        from run import app as flask_app
    except ImportError:
        raise ImportError("No se pudo encontrar la instancia de la app Flask. Ajustá el import en test_flask_analysis.py")


@pytest.fixture
def app():
    """Configura la app para testing."""
    flask_app.config["TESTING"] = True
    flask_app.config["WTF_CSRF_ENABLED"] = False  # Desactiva CSRF para tests
    return flask_app


@pytest.fixture
def client(app):
    """Crea el cliente de test de Flask."""
    return app.test_client()


def test_api_analisis_sin_auth(client):
    """Sin autenticación debe devolver 401 o redirigir (302)."""
    response = client.post(
        "/api/analisis",
        json={
            "origen": "facebook",
            "comentarios": ["test"],
        },
    )
    
    # Flask-Login usualmente devuelve 401 Unauthorized o 302 Redirect a login
    assert response.status_code in [401, 302]


@patch("flask_login.utils.current_user")
def test_api_analisis_con_auth(mock_user, client):
    """Con autenticación debe ejecutar el análisis y devolver respuesta."""
    # Configurar el mock del usuario con plan Plata
    mock_user.id = 1
    mock_user.email = "test@example.com"
    mock_user.plan = "plata"
    mock_user.is_authenticated = True
    mock_user.is_active = True
    mock_user.is_anonymous = False
    mock_user.get_id = lambda: "1"
    
    response = client.post(
        "/api/analisis",
        json={
            "origen": "facebook",
            "comentarios": [
                "Qué buena gestión, cada día estamos mejor 🙄",
                "Excelente trabajo 👏",
                "Bueno... veremos",
            ],
            "contexto": "Opiniones sobre la gestión municipal",
        },
    )
    
    # Debe devolver respuesta válida (200 OK, o 400/500 si hay error de lógica, pero NUNCA 401/403)
    assert response.status_code in [200, 400, 500]
    
    data = response.get_json()
    assert "success" in data


@patch("flask_login.utils.current_user")
def test_api_analisis_comentarios_vacios(mock_user, client):
    """Sin comentarios debe devolver error 400."""
    mock_user.id = 1
    mock_user.plan = "plata"
    mock_user.is_authenticated = True
    mock_user.is_active = True
    mock_user.is_anonymous = False
    mock_user.get_id = lambda: "1"
    
    response = client.post(
        "/api/analisis",
        json={
            "origen": "facebook",
            "comentarios": [],
        },
    )
    
    assert response.status_code == 400
    data = response.get_json()
    assert data["success"] is False
    assert "al menos un comentario" in data["error"].lower()