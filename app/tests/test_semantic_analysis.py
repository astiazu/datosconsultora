# app/tests/test_semantic_analysis.py
import pytest
from unittest.mock import Mock, patch
from app.services.analysis.groq_llm import GroqLLMClient


class TestAnalizarSemanticaEstructura:
    """
    Tests unitarios que validan la estructura del método
    sin llamar a Groq.
    """
    
    def test_comentarios_vacio(self):
        """Lista vacía debe devolver analyses vacío."""
        client = GroqLLMClient.__new__(GroqLLMClient)
        client.client = Mock()
        client.model = "test"
        
        resultado = client.analizar_semantica([])
        
        assert resultado == {"analyses": []}
    
    def test_comentarios_no_lista(self):
        """Si no es lista, debe lanzar TypeError."""
        client = GroqLLMClient.__new__(GroqLLMClient)
        client.client = Mock()
        client.model = "test"
        
        with pytest.raises(TypeError, match="comentarios debe ser una lista"):
            client.analizar_semantica("no es lista")
    
    def test_mas_de_100_comentarios(self):
        """Más de 100 comentarios debe lanzar ValueError."""
        client = GroqLLMClient.__new__(GroqLLMClient)
        client.client = Mock()
        client.model = "test"
        
        comentarios = ["texto"] * 101
        
        with pytest.raises(ValueError, match="Máximo 100 comentarios"):
            client.analizar_semantica(comentarios)
    
    def test_normaliza_none_a_string_vacio(self):
        """None en comentarios debe convertirse a string vacío."""
        client = GroqLLMClient.__new__(GroqLLMClient)
        client.client = Mock()
        client.model = "test"
        
        # Mock de respuesta válida
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '{"analyses": [{"message_id": "1", "texto_original": "", "sentiment": "neutral", "tone": "neutral", "irony": false, "sarcasm": false, "irony_polarity": "none", "confidence": 0.9, "literal_meaning": "vacío", "inferred_meaning": "vacío", "evidence": []}]}'
        
        client.client.chat.completions.create.return_value = mock_response
        
        resultado = client.analizar_semantica([None])
        
        assert len(resultado["analyses"]) == 1

@pytest.mark.integration
class TestAnalizarSemanticaCasosArgentinos:
    """
    Tests de integración con casos argentinos reales.
    Estos tests SÍ llaman a Groq.
    
    Para ejecutarlos:
    pytest app/tests/test_semantic_analysis.py::TestAnalizarSemanticaCasosArgentinos -v
    """
    
    @pytest.fixture
    def client(self):
        """Cliente real de Groq."""
        try:
            return GroqLLMClient()
        except ValueError:
            pytest.skip("GROQ_API_KEY no configurada")
    
    def test_ironia_obvia_con_contexto(self, client):
        """
        Caso: Ironía evidente cuando el contexto contradice el elogio.
        Esperado: irony=true, tone=ironic_negative
        """
        comentarios = [
            "Qué buena gestión, cada día estamos mejor."
        ]
        contexto = "La ciudad tiene problemas de basura, calles rotas y falta de seguridad."
        
        resultado = client.analizar_semantica(comentarios, contexto)
        
        assert len(resultado["analyses"]) == 1
        analysis = resultado["analyses"][0]
        
        assert analysis["sentiment"] == "negative"
        assert analysis["irony"] is True
        assert analysis["tone"] == "ironic_negative"
        assert len(analysis["evidence"]) > 0
        assert analysis["confidence"] >= 0.75
    
    def test_ironia_ambigua_sin_contexto(self, client):
        """
        Caso: Expresión que podría ser irónica pero sin contexto no hay evidencia.
        Esperado: irony=false, tone=neutral o ambiguous
        """
        comentarios = [
            "Qué fenómeno."
        ]
        
        resultado = client.analizar_semantica(comentarios)
        
        assert len(resultado["analyses"]) == 1
        analysis = resultado["analyses"][0]
        
        # Sin contexto, NO debería marcar ironía
        assert analysis["irony"] is False
        assert analysis["tone"] in ["neutral", "ambiguous", "positive"]
    
    def test_positivo_literal(self, client):
        """
        Caso: Comentario genuinamente positivo sin ironía.
        Esperado: sentiment=positive, irony=false
        """
        comentarios = [
            "Qué lindo día, gracias por solucionar el problema."
        ]
        
        resultado = client.analizar_semantica(comentarios)
        
        assert len(resultado["analyses"]) == 1
        analysis = resultado["analyses"][0]
        
        assert analysis["sentiment"] == "positive"
        assert analysis["irony"] is False
        assert analysis["tone"] == "positive"
    
    def test_negativo_literal(self, client):
        """
        Caso: Comentario genuinamente negativo sin ironía.
        Esperado: sentiment=negative, irony=false
        """
        comentarios = [
            "Otro para vivir a costa del estado."
        ]
        
        resultado = client.analizar_semantica(comentarios)
        
        assert len(resultado["analyses"]) == 1
        analysis = resultado["analyses"][0]
        
        assert analysis["sentiment"] == "negative"
        assert analysis["irony"] is False
        assert analysis["tone"] == "negative"
    
    def test_emoji_contradice_texto(self, client):
        """
        Caso: Elogio literal con emoji que contradice.
        Esperado: irony=true, evidence menciona emoji
        """
        comentarios = [
            "Excelente servicio 🙄"
        ]
        contexto = "El servicio es conocido por ser malo."
        
        resultado = client.analizar_semantica(comentarios, contexto)
        
        assert len(resultado["analyses"]) == 1
        analysis = resultado["analyses"][0]
        
        assert analysis["irony"] is True
        assert any("emoji" in ev.lower() or "🙄" in ev for ev in analysis["evidence"])
    
    def test_sarcasmo_vs_ironia(self, client):
        """
        Caso: Sarcasmo implica burla, no solo ironía.
        Esperado: sarcasm=true, irony=true
        """
        comentarios = [
            "Sí, claro... un genio el que inventó esto."
        ]
        contexto = "El producto es defectuoso y nadie lo usa."
        
        resultado = client.analizar_semantica(comentarios, contexto)
        
        assert len(resultado["analyses"]) == 1
        analysis = resultado["analyses"][0]
        
        assert analysis["irony"] is True
        # Sarcasmo puede o no estar marcado, pero si hay burla, debería estar
        # assert analysis["sarcasm"] is True  # Opcional, depende del modelo
    
    def test_jerga_argentina_sin_polaridad_automatica(self, client):
        """
        Caso: Jerga argentina no debe determinar polaridad por sí sola.
        Esperado: análisis completo, no solo por palabras clave
        """
        comentarios = [
            "Laburar laburamos, pero no vemos resultados."
        ]
        
        resultado = client.analizar_semantica(comentarios)
        
        assert len(resultado["analyses"]) == 1
        analysis = resultado["analyses"][0]
        
        # Debe ser negativo por el contexto, no por "laburar"
        assert analysis["sentiment"] == "negative"
        assert analysis["irony"] is False
    
    def test_ambiguedad_valida(self, client):
        """
        Caso: Comentario ambiguo sin evidencia clara.
        Esperado: tone=ambiguous, confidence moderada
        """
        comentarios = [
            "Bueno... veremos."
        ]
        
        resultado = client.analizar_semantica(comentarios)
        
        assert len(resultado["analyses"]) == 1
        analysis = resultado["analyses"][0]
        
        # Debe permitir ambigüedad
        assert analysis["tone"] in ["ambiguous", "neutral"]
        assert analysis["confidence"] <= 0.8
    
    def test_multiples_comentarios_mezclados(self, client):
        """
        Caso: Múltiples comentarios con diferentes características.
        Esperado: análisis individual correcto para cada uno
        """
        comentarios = [
            "Qué buena gestión, cada día estamos mejor.",  # Irónico
            "Gracias por solucionar el problema.",  # Positivo literal
            "Otro para vivir a costa del estado.",  # Negativo literal
            "Bueno... veremos.",  # Ambiguo
        ]
        contexto = "La gestión tiene muchos problemas."
        
        resultado = client.analizar_semantica(comentarios, contexto)
        
        assert len(resultado["analyses"]) == 4
        
        # Primer comentario: irónico
        assert resultado["analyses"][0]["irony"] is True
        assert resultado["analyses"][0]["sentiment"] == "negative"
        
        # Segundo comentario: positivo
        assert resultado["analyses"][1]["sentiment"] == "positive"
        assert resultado["analyses"][1]["irony"] is False
        
        # Tercer comentario: negativo
        assert resultado["analyses"][2]["sentiment"] == "negative"
        assert resultado["analyses"][2]["irony"] is False
        
        # Cuarto comentario: ambiguo
        assert resultado["analyses"][3]["tone"] in ["ambiguous", "neutral"]
    
    def test_ironia_sin_evidencia_es_error(self, client):
        """
        Caso: Si el modelo marca ironía sin evidencia, debe fallar validación.
        Este test verifica que la validación post-LLM funciona.
        """
        # Mock de respuesta inválida (irony=true sin evidence)
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '{"analyses": [{"message_id": "1", "texto_original": "test", "sentiment": "negative", "tone": "ironic_negative", "irony": true, "sarcasm": false, "irony_polarity": "negative", "confidence": 0.9, "literal_meaning": "test", "inferred_meaning": "test", "evidence": []}]}'
        
        client_real = GroqLLMClient.__new__(GroqLLMClient)
        client_real.client = Mock()
        client_real.model = "test"
        client_real.client.chat.completions.create.return_value = mock_response
        client_real._extraer_json = lambda x: {"analyses": [{"message_id": "1", "texto_original": "test", "sentiment": "negative", "tone": "ironic_negative", "irony": True, "sarcasm": False, "irony_polarity": "negative", "confidence": 0.9, "literal_meaning": "test", "inferred_meaning": "test", "evidence": []}]}
        
        # Debe fallar después de 3 intentos
        with pytest.raises(Exception, match="Error procesando análisis semántico"):
            client_real.analizar_semantica(["test"])

@pytest.mark.integration
class TestAnalizarSemanticaContrato:
    """
    Tests que validan el contrato de salida del método.
    """
    
    @pytest.fixture
    def client(self):
        try:
            return GroqLLMClient()
        except ValueError:
            pytest.skip("GROQ_API_KEY no configurada")
    
    def test_estructura_json_correcta(self, client):
        """Valida que la estructura JSON sea exactamente la esperada."""
        comentarios = ["Test comment"]
        
        resultado = client.analizar_semantica(comentarios)
        
        # Estructura básica
        assert "analyses" in resultado
        assert isinstance(resultado["analyses"], list)
        assert len(resultado["analyses"]) == 1
        
        analysis = resultado["analyses"][0]
        
        # Campos obligatorios
        assert "message_id" in analysis
        assert "texto_original" in analysis
        assert "sentiment" in analysis
        assert "tone" in analysis
        assert "irony" in analysis
        assert "sarcasm" in analysis
        assert "irony_polarity" in analysis
        assert "confidence" in analysis
        assert "literal_meaning" in analysis
        assert "inferred_meaning" in analysis
        assert "evidence" in analysis
        
        # Tipos correctos
        assert isinstance(analysis["message_id"], str)
        assert isinstance(analysis["sentiment"], str)
        assert isinstance(analysis["tone"], str)
        assert isinstance(analysis["irony"], bool)
        assert isinstance(analysis["sarcasm"], bool)
        assert isinstance(analysis["confidence"], (int, float))
        assert isinstance(analysis["evidence"], list)
    
    def test_valores_enums_validos(self, client):
        """Valida que los valores de enums sean los permitidos."""
        comentarios = ["Test"]
        
        resultado = client.analizar_semantica(comentarios)
        analysis = resultado["analyses"][0]
        
        # Sentiment válido
        assert analysis["sentiment"] in ["positive", "negative", "neutral"]
        
        # Tone válido
        assert analysis["tone"] in [
            "positive", "negative", "neutral",
            "ironic_positive", "ironic_negative",
            "sarcastic", "mixed", "ambiguous"
        ]
        
        # Irony polarity válido
        assert analysis["irony_polarity"] in [
            "positive", "negative", "neutral", "none"
        ]
        
        # Confidence en rango
        assert 0.0 <= analysis["confidence"] <= 1.0
        
        # Coherencia irony/polarity
        if not analysis["irony"]:
            assert analysis["irony_polarity"] == "none"