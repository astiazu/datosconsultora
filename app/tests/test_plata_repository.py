# app/tests/test_plata_repository.py
"""
Tests del ConversationRepository con SQLite temporal.
Valida guardar, obtener y listar sin tocar Groq ni la DB real.

IMPORTANTE: Este fixture usa un archivo SQLite temporal para aislar
completamente los tests de la base de datos real. NUNCA toques la DB
de producción desde los tests.
"""
import os
import tempfile
import pytest

from app import create_app, db
from app.models import User, ConversationRecord
from app.services.conversation_service import ConversationService
from app.services.plata.conversation_repository import ConversationRepository


@pytest.fixture(scope="function")
def app():
    """App de prueba aislada con SQLite temporal."""
    # Crear archivo temporal para la DB de tests
    db_fd, db_path = tempfile.mkstemp(suffix=".db")

    app = create_app()
    app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_path}",
        "WTF_CSRF_ENABLED": False,
        "SECRET_KEY": "test-secret-key-for-tests",
    })

    with app.app_context():
        # ✅ CLAVE: Resetear el engine para usar la nueva URI.
        # Esto evita que el engine creado a nivel de módulo (con la DB real)
        # sea usado en los tests.
        db.engine.dispose()
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

    # Limpiar el archivo temporal
    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture(scope="function")
def user(app):
    """Usuario de prueba."""
    with app.app_context():
        u = User(
            nombre="Test",
            email="test@example.com",
            telefono="5491100000000",
        )
        u.set_password("password")
        db.session.add(u)
        db.session.commit()

        # ✅ Forzar carga de atributos y separar de la sesión
        db.session.refresh(u)
        db.session.expunge(u)

        return u


def test_guardar_y_obtener(app, user):
    """Debe guardar una Conversation y reconstruirla igual."""
    with app.app_context():
        service = ConversationService()
        respuesta = service.from_manual_text(
            "José: Hola mundo\nMaría: Qué bueno verte",
            contexto="prueba",
        )
        assert respuesta["success"]
        conversation = respuesta["conversation"]

        repo = ConversationRepository()
        record = repo.guardar(user.id, conversation, contexto="prueba")

        assert record.id is not None
        assert record.estado == "pendiente"
        assert record.total_messages == conversation.total_messages

        # Reconstruir
        data = repo.obtener(record.id, user.id)
        assert data is not None
        reconstruida = data["conversation"]
        assert reconstruida.total_messages == conversation.total_messages
        assert reconstruida.messages[0].text == conversation.messages[0].text


def test_obtener_de_otro_usuario_devuelve_none(app, user):
    """No debe poder acceder a un record de otro usuario."""
    with app.app_context():
        service = ConversationService()
        respuesta = service.from_manual_text("José: Hola mundo")
        conversation = respuesta["conversation"]

        repo = ConversationRepository()
        record = repo.guardar(user.id, conversation)

        # Otro user_id
        data = repo.obtener(record.id, user_id=9999)
        assert data is None


def test_guardar_resultado(app, user):
    """Debe actualizar el estado y guardar el resultado."""
    with app.app_context():
        service = ConversationService()
        respuesta = service.from_manual_text("José: Hola mundo")
        conversation = respuesta["conversation"]

        repo = ConversationRepository()
        record = repo.guardar(user.id, conversation)

        resultado = {"success": True, "analisis": {"prueba": 1}}
        repo.guardar_resultado(record.id, resultado)

        updated = ConversationRecord.query.get(record.id)
        assert updated.estado == "analizada"
        assert updated.obtener_resultado()["success"] is True