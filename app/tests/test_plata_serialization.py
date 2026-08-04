# app/tests/test_plata_serialization.py
"""
Tests del serializador de Conversation (sin DB, sin Groq).
Valida el roundtrip: Conversation -> dict -> Conversation.
"""
from datetime import datetime
from app.mic.domain.entities.conversation import Conversation
from app.mic.domain.entities.message import Message
from app.mic.domain.entities.participant import Participant
from app.mic.domain.enums import SourceType, ParticipantRole
from app.services.plata.serialization import (
    conversation_to_dict,
    conversation_from_dict,
)


def crear_conversation():
    c = Conversation(
        conversation_id="test-001",
        source=SourceType.FACEBOOK,
        title="Prueba de serialización",
        created_at=datetime(2026, 8, 4, 12, 0, 0),
        metadata={"contexto": "prueba"},
    )
    c.add_participant(Participant(
        participant_id="u1",
        display_name="José",
        role=ParticipantRole.MEMBER,
    ))
    c.add_message(Message(
        message_id="m1",
        participant_id="u1",
        text="Hola mundo",
        created_at=datetime(2026, 8, 4, 12, 1, 0),
        reactions=3,
    ))
    return c


def test_roundtrip_conversation():
    """Conversation -> dict -> Conversation debe preservar los datos."""
    original = crear_conversation()
    data = conversation_to_dict(original)
    reconstruida = conversation_from_dict(data)

    assert reconstruida.conversation_id == original.conversation_id
    assert reconstruida.source == original.source
    assert reconstruida.title == original.title
    assert reconstruida.total_messages == original.total_messages
    assert reconstruida.total_participants == original.total_participants
    assert reconstruida.messages[0].text == "Hola mundo"
    assert reconstruida.messages[0].reactions == 3
    assert reconstruida.participants[0].display_name == "José"
    assert reconstruida.participants[0].role == ParticipantRole.MEMBER


def test_serializacion_es_json_safe():
    """El dict debe ser serializable a JSON sin errores."""
    import json
    c = crear_conversation()
    data = conversation_to_dict(c)
    json_str = json.dumps(data, ensure_ascii=False)
    assert isinstance(json_str, str)
    assert len(json_str) > 0


def test_metadata_se_preserva():
    """La metadata de la conversación debe sobrevivir al roundtrip."""
    c = crear_conversation()
    c.metadata["url"] = "https://facebook.com/post/1"
    data = conversation_to_dict(c)
    reconstruida = conversation_from_dict(data)
    assert reconstruida.metadata["url"] == "https://facebook.com/post/1"