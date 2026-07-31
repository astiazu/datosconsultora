# app/tests/test_mic_e2e.py
from datetime import datetime

from app.mic.analyzers.semantic_analyzer import SemanticAnalyzer
from app.mic.domain.entities.conversation import Conversation
from app.mic.domain.entities.message import Message
from app.mic.domain.entities.participant import Participant
from app.mic.domain.enums import SourceType
from app.mic.mic_engine import MIC


class FakeSemanticAnalyzer(SemanticAnalyzer):
    """
    Analizador falso para pruebas.

    No llama a Groq.
    Sirve para verificar que el MIC,
    Pipeline y SemanticStep están correctamente conectados.
    """

    def analyze(
        self,
        conversation,
        metadata=None,
    ):
        metadata = metadata or {}

        return {
            "motor": "fake",
            "user_plan": metadata.get(
                "user_plan",
                "bronce",
            ),
            "contexto": metadata.get(
                "contexto",
                "",
            ),
            "mensajes_analizados": len(
                conversation.messages
            ),
            "interpretacion": {
                "sentimiento": "positivo",
                "ironia": False,
                "sarcasmo": False,
            },
        }


def crear_conversacion():

    conversation = Conversation(
        conversation_id="test-mic-001",
        source=SourceType.FACEBOOK,
        title="Prueba MIC",
        created_at=datetime.now(),
    )

    participant = Participant(
        participant_id="user-001",
        display_name="José",
    )

    conversation.add_participant(
        participant
    )

    message = Message(
        message_id="msg-001",
        participant_id="user-001",
        text="Qué buena noticia",
        created_at=datetime.now(),
    )

    conversation.add_message(
        message
    )

    return conversation


def test_mic_end_to_end():

    conversation = crear_conversacion()

    analyzer = FakeSemanticAnalyzer()

    mic = MIC(
        semantic_analyzer=analyzer
    )

    result = mic.analyze(
        conversation,
        metadata={
            "user_plan": "plata",
            "contexto": "Prueba del motor semántico",
        },
    )

    assert result.success is True

    assert result.conversation_id == "test-mic-001"

    assert result.semantic_analysis["motor"] == "fake"

    assert (
        result.semantic_analysis["user_plan"]
        == "plata"
    )

    assert (
        result.semantic_analysis[
            "mensajes_analizados"
        ]
        == 1
    )