# app/tests/test_mic_semantic_e2e.py
"""
Test End-to-End del MIC con análisis semántico real usando Groq.

Valida el flujo completo:
Conversation → MIC → Pipeline → SemanticStep → GroqSemanticAnalyzer → Groq → SemanticResult
"""
import pytest
from datetime import datetime

from app.mic.analyzers.groq_semantic_analyzer import GroqSemanticAnalyzer
from app.mic.domain.entities.conversation import Conversation
from app.mic.domain.entities.message import Message
from app.mic.domain.entities.participant import Participant
from app.mic.domain.enums import SourceType
from app.mic.mic_engine import MIC
from app.mic.models.semantic_result import SemanticResult
from app.services.analysis.groq_llm import GroqLLMClient


@pytest.fixture
def groq_client():
    """Cliente real de Groq."""
    try:
        return GroqLLMClient()
    except ValueError:
        pytest.skip("GROQ_API_KEY no configurada")


@pytest.fixture
def analyzer(groq_client):
    """Analyzer real con cliente Groq."""
    return GroqSemanticAnalyzer(groq_client=groq_client)


def crear_conversacion_pinamar():
    """
    Conversación de prueba basada en el caso real de Pinamar.
    Incluye ironía, sarcasmo, positivo literal, negativo literal y ambigüedad.
    """
    conversation = Conversation(
        conversation_id="pinamar-001",
        source=SourceType.FACEBOOK,
        title="Análisis economía Pinamar",
        created_at=datetime.now(),
    )

    # Participantes
    p1 = Participant(participant_id="user-001", display_name="maarisa.salass")
    p2 = Participant(participant_id="user-002", display_name="luis201p")
    p3 = Participant(participant_id="user-003", display_name="gabrielhoraciomariano")
    p4 = Participant(participant_id="user-004", display_name="rdlp1313")
    p5 = Participant(participant_id="user-005", display_name="charlieseasailing")

    conversation.add_participant(p1)
    conversation.add_participant(p2)
    conversation.add_participant(p3)
    conversation.add_participant(p4)
    conversation.add_participant(p5)

    # Mensajes (casos reales del proyecto)
    mensajes = [
        Message(
            message_id="msg-001",
            participant_id="user-001",
            text="Siempre el mira la necesidades de las gentes. vamos mejor pinamar ✌️💪",
            created_at=datetime.now(),
        ),
        Message(
            message_id="msg-002",
            participant_id="user-002",
            text="La mayoría de los alquileres han cambiado su modalidad, algunos las tasas municipales se pagan a media con el propietario",
            created_at=datetime.now(),
        ),
        Message(
            message_id="msg-003",
            participant_id="user-003",
            text="Otro para vivir a costa del estado",
            created_at=datetime.now(),
        ),
        Message(
            message_id="msg-004",
            participant_id="user-004",
            text="Bajen las tarifas qué son muy caras, esa es una forma de ayudar",
            created_at=datetime.now(),
        ),
        Message(
            message_id="msg-005",
            participant_id="user-005",
            text="Hace rato que Pinamar no explota en turismo. Lamentablemente nuestra ciudad está detonada. Vamos Martin 💪",
            created_at=datetime.now(),
        ),
    ]

    for msg in mensajes:
        conversation.add_message(msg)

    return conversation

@pytest.mark.integration
def test_mic_semantic_e2e_pinamar(groq_client, analyzer):
    """
    Test E2E completo con conversación real de Pinamar.
    
    Valida:
    - MIC recibe Conversation
    - Pipeline ejecuta CleanStep, ValidationStep, SemanticStep
    - GroqSemanticAnalyzer convierte a SemanticResult
    - AnalysisResult contiene semantic_analysis con SemanticResult objects
    """
    conversation = crear_conversacion_pinamar()
    
    mic = MIC(semantic_analyzer=analyzer)
    
    metadata = {
        "contexto": (
            "Martín Porretti analiza la economía de los vecinos de Pinamar, "
            "destacando el desfasaje entre las altas tasas municipales y la "
            "baja calidad de los servicios."
        ),
    }
    
    result = mic.analyze(conversation, metadata=metadata)
    
    # Validar AnalysisResult
    assert result.success is True
    assert result.conversation_id == "pinamar-001"
    assert len(result.errors) == 0
    
    # Validar semantic_analysis
    assert "analyses" in result.semantic_analysis
    analyses = result.semantic_analysis["analyses"]
    
    # Debe haber 5 SemanticResult objects
    assert len(analyses) == 5
    
    # Validar que cada análisis es un SemanticResult
    for analysis in analyses:
        assert isinstance(analysis, SemanticResult)
        assert analysis.sentiment in ["positive", "negative", "neutral"]
        assert 0.0 <= analysis.confidence <= 1.0
        assert isinstance(analysis.evidence, list)
    
    # Validar casos específicos
    # msg-001: Positivo con apoyo genuino
    assert analyses[0].sentiment == "positive"
    assert analyses[0].irony is False
    
    # msg-003: Negativo literal (crítica directa)
    assert analyses[2].sentiment == "negative"
    assert analyses[2].irony is False
    
    # msg-004: Negativo (queja por tarifas)
    assert analyses[3].sentiment == "negative"


def test_mic_semantic_e2e_ironia_con_contexto(groq_client, analyzer):
    """
    Test E2E específico para detección de ironía con contexto.
    """
    conversation = Conversation(
        conversation_id="ironia-test-001",
        source=SourceType.FACEBOOK,
        title="Test ironía",
        created_at=datetime.now(),
    )
    
    participant = Participant(
        participant_id="user-001",
        display_name="usuario_test",
    )
    conversation.add_participant(participant)
    
    message = Message(
        message_id="msg-001",
        participant_id="user-001",
        text="Qué buena gestión, cada día estamos mejor.",
        created_at=datetime.now(),
    )
    conversation.add_message(message)
    
    mic = MIC(semantic_analyzer=analyzer)
    
    metadata = {
        "contexto": "La ciudad tiene problemas de basura, calles rotas y falta de seguridad.",
    }
    
    result = mic.analyze(conversation, metadata=metadata)
    
    assert result.success is True
    analyses = result.semantic_analysis["analyses"]
    assert len(analyses) == 1
    
    analysis = analyses[0]
    
    # Debe detectar ironía
    assert analysis.irony is True
    assert analysis.sentiment == "negative"
    assert analysis.tone == "ironic_negative"
    assert len(analysis.evidence) > 0
    assert analysis.confidence >= 0.75


def test_mic_semantic_e2e_sin_analyzer():
    """
    Test que valida que MIC funciona sin analyzer (solo Clean + Validation).
    """
    conversation = Conversation(
        conversation_id="test-sin-analyzer",
        source=SourceType.FACEBOOK,
        title="Test sin analyzer",
        created_at=datetime.now(),
    )
    
    participant = Participant(
        participant_id="user-001",
        display_name="Test",
    )
    conversation.add_participant(participant)
    
    message = Message(
        message_id="msg-001",
        participant_id="user-001",
        text="Comentario de prueba",
        created_at=datetime.now(),
    )
    conversation.add_message(message)
    
    # MIC sin analyzer
    mic = MIC(semantic_analyzer=None)
    
    result = mic.analyze(conversation)
    
    # Debe funcionar sin análisis semántico
    assert result.success is True
    assert result.semantic_analysis == {}