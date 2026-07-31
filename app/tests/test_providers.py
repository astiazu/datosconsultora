# app/tests/test_providers.py
"""
Tests unitarios del sistema de providers.

NO consumen tokens de Groq.
Validan la arquitectura de selección de modelos.
"""
import os
import pytest
from unittest.mock import Mock, patch

from app.mic.providers import (
    LLMProvider,
    GroqProvider,
    ProviderRegistry,
    ModelConfig,
    ProviderType,
    AVAILABLE_MODELS,
)


class TestModelConfig:
    """Tests de configuración de modelos."""
    
    def test_modelos_disponibles_existen(self):
        """Debe haber al menos 6 modelos configurados."""
        assert len(AVAILABLE_MODELS) >= 6
    
    def test_modelo_llama_3_3_configurado(self):
        """Llama 3.3 70B debe estar disponible."""
        assert "llama-3.3-70b-versatile" in AVAILABLE_MODELS
        config = AVAILABLE_MODELS["llama-3.3-70b-versatile"]
        assert config.provider == ProviderType.GROQ
        assert config.cost_tier == "free"
    
    def test_modelo_qwen_qwq_configurado(self):
        """Qwen QwQ debe estar disponible para razonamiento."""
        assert "qwen-qwq-32b" in AVAILABLE_MODELS
        config = AVAILABLE_MODELS["qwen-qwq-32b"]
        assert "reasoning" in config.best_for
        assert "ironia" in config.best_for


class TestProviderRegistry:
    """Tests del registry de providers."""
    
    def test_select_model_default(self):
        """Sin parámetros, debe devolver el default."""
        config = ProviderRegistry.select_model()
        assert config.id == "llama-3.3-70b-versatile"
    
    def test_select_model_explicito(self):
        """Con modelo explícito, debe usar ese."""
        config = ProviderRegistry.select_model(
            explicit_model="qwen-qwq-32b"
        )
        assert config.id == "qwen-qwq-32b"
    
    def test_select_model_invalido_usa_default(self):
        """Modelo inválido debe caer al default."""
        config = ProviderRegistry.select_model(
            explicit_model="modelo-inexistente"
        )
        assert config.id == "llama-3.3-70b-versatile"
    
    def test_select_model_por_plan_free(self):
        """Plan free debe usar modelo rápido."""
        config = ProviderRegistry.select_model(user_plan="free")
        assert config.id == "llama-3.1-8b-instant"
    
    def test_select_model_por_plan_bronce(self):
        """Plan bronce debe usar modelo rápido."""
        config = ProviderRegistry.select_model(user_plan="bronce")
        assert config.id == "llama-3.1-8b-instant"
    
    def test_select_model_por_plan_plata(self):
        """Plan plata debe usar modelo balanceado."""
        config = ProviderRegistry.select_model(user_plan="plata")
        assert config.id == "llama-3.3-70b-versatile"
    
    def test_select_model_por_plan_oro(self):
        """Plan oro debe usar Qwen QwQ (razonamiento)."""
        config = ProviderRegistry.select_model(user_plan="oro")
        assert config.id == "qwen-qwq-32b"
    
    def test_select_model_por_plan_lifetime(self):
        """Plan lifetime debe usar Qwen QwQ."""
        config = ProviderRegistry.select_model(user_plan="lifetime")
        assert config.id == "qwen-qwq-32b"
    
    def test_select_model_plan_desconocido_usa_default(self):
        """Plan desconocido debe caer al default."""
        config = ProviderRegistry.select_model(user_plan="desconocido")
        assert config.id == "llama-3.3-70b-versatile"
    
    @patch.dict(os.environ, {"GROQ_MODEL": "qwen-2.5-32b"})
    def test_select_model_desde_env(self):
        """Variable de entorno debe tener prioridad sobre plan."""
        config = ProviderRegistry.select_model(user_plan="free")
        # Env tiene prioridad sobre plan
        assert config.id == "qwen-2.5-32b"
    
    def test_select_model_explicito_tiene_maxima_prioridad(self):
        """Modelo explícito tiene prioridad sobre env y plan."""
        with patch.dict(os.environ, {"GROQ_MODEL": "qwen-2.5-32b"}):
            config = ProviderRegistry.select_model(
                explicit_model="mixtral-8x7b-32768",
                user_plan="oro",
            )
            assert config.id == "mixtral-8x7b-32768"
    
    def test_list_available_models(self):
        """Debe listar todos los modelos."""
        models = ProviderRegistry.list_available_models()
        assert len(models) >= 6
        assert all(isinstance(m, ModelConfig) for m in models)
    
    def test_get_model_valido(self):
        """Debe devolver config de modelo válido."""
        config = ProviderRegistry.get_model("llama-3.3-70b-versatile")
        assert config.id == "llama-3.3-70b-versatile"
    
    def test_get_model_invalido_lanza_error(self):
        """Modelo inválido debe lanzar ValueError."""
        with pytest.raises(ValueError, match="no disponible"):
            ProviderRegistry.get_model("modelo-inexistente")


class TestGroqProvider:
    """Tests del proveedor Groq (sin llamar a la API)."""
    
    def test_provider_info(self):
        """Debe retornar info correcta del provider."""
        # ✅ CORREGIDO: ruta app.mic.providers.groq_provider
        with patch("app.mic.providers.groq_provider.GroqLLMClient"):
            provider = GroqProvider(model="llama-3.3-70b-versatile")
            assert provider.get_provider_name() == "groq"
            assert provider.get_model_id() == "llama-3.3-70b-versatile"
    
    def test_provider_es_llm_provider(self):
        """Debe implementar la interfaz LLMProvider."""
        # ✅ CORREGIDO: ruta app.mic.providers.groq_provider
        with patch("app.mic.providers.groq_provider.GroqLLMClient"):
            provider = GroqProvider()
            assert isinstance(provider, LLMProvider)
    
    def test_get_status_sin_token_monitor(self):
        """Debe funcionar aunque no haya token_monitor."""
        # ✅ CORREGIDO: ruta app.mic.providers.groq_provider
        with patch("app.mic.providers.groq_provider.GroqLLMClient"):
            provider = GroqProvider()
            status = provider.get_status()
            assert status["provider"] == "groq"
            assert "model" in status


class TestProviderRegistryIntegration:
    """Tests de integración del registry (sin llamar a la API)."""
    
    # ✅ CORREGIDO: ruta app.mic.providers.registry
    @patch("app.mic.providers.registry.GroqProvider")
    def test_get_provider_groq(self, mock_groq_class):
        """Debe crear GroqProvider para modelos Groq."""
        mock_groq_class.return_value = Mock()
        
        provider = ProviderRegistry.get_provider(
            explicit_model="llama-3.3-70b-versatile"
        )
        
        mock_groq_class.assert_called_once_with(
            model="llama-3.3-70b-versatile"
        )
    
    # ✅ CORREGIDO: ruta app.mic.providers.registry
    @patch("app.mic.providers.registry.GroqProvider")
    def test_get_provider_por_plan(self, mock_groq_class):
        """Debe crear provider correcto según plan."""
        mock_groq_class.return_value = Mock()
        
        provider = ProviderRegistry.get_provider(user_plan="oro")
        
        mock_groq_class.assert_called_once_with(
            model="qwen-qwq-32b"
        )