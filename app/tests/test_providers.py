# app/tests/test_providers.py
"""Tests unitarios del sistema de providers. NO consumen tokens.
Agnósticos al catálogo: validan contra AVAILABLE_MODELS / PLAN_MODEL_MAP
reales, así no se rompen cada vez que Groq depreca modelos."""
import os
import pytest
from unittest.mock import Mock, patch
from app.mic.providers import (
    LLMProvider, GroqProvider, ProviderRegistry,
    ModelConfig, ProviderType, AVAILABLE_MODELS,
    DEFAULT_MODEL, PLAN_MODEL_MAP,
)


class TestModelConfig:
    def test_hay_modelos_vivos(self):
        assert len(AVAILABLE_MODELS) >= 2

    def test_default_esta_en_el_catalogo(self):
        assert DEFAULT_MODEL in AVAILABLE_MODELS

    def test_todos_los_planes_tienen_modelo(self):
        for plan, model_id in PLAN_MODEL_MAP.items():
            assert model_id in AVAILABLE_MODELS, f"plan {plan} apunta a modelo muerto"


class TestProviderRegistry:
    def test_select_model_default(self):
        assert ProviderRegistry.select_model().id == DEFAULT_MODEL

    def test_select_model_explicito(self):
        modelo = next(iter(AVAILABLE_MODELS))
        assert ProviderRegistry.select_model(explicit_model=modelo).id == modelo

    def test_select_model_invalido_usa_default(self):
        assert ProviderRegistry.select_model(explicit_model="modelo-inexistente").id == DEFAULT_MODEL

    def test_select_model_por_plan(self):
        for plan, model_id in PLAN_MODEL_MAP.items():
            assert ProviderRegistry.select_model(user_plan=plan).id == model_id

    @patch.dict(os.environ, {"GROQ_MODEL": ""})
    def test_env_vacio_no_rompe(self):
        assert ProviderRegistry.select_model(user_plan="free").id == PLAN_MODEL_MAP.get("free", DEFAULT_MODEL)

    def test_get_model_invalido_lanza_error(self):
        with pytest.raises(ValueError, match="no disponible"):
            ProviderRegistry.get_model("modelo-inexistente")

    def test_list_available_models(self):
        models = ProviderRegistry.list_available_models()
        assert all(isinstance(m, ModelConfig) for m in models)


class TestGroqProvider:
    def test_provider_info(self):
        with patch("app.mic.providers.groq_provider.GroqLLMClient"):
            provider = GroqProvider(model=DEFAULT_MODEL)
            assert provider.get_provider_name() == "groq"
            assert provider.get_model_id() == DEFAULT_MODEL

    def test_provider_es_llm_provider(self):
        with patch("app.mic.providers.groq_provider.GroqLLMClient"):
            assert isinstance(GroqProvider(), LLMProvider)

    def test_get_status_sin_token_monitor(self):
        with patch("app.mic.providers.groq_provider.GroqLLMClient"):
            status = GroqProvider().get_status()
            assert status["provider"] == "groq"
            assert "model" in status


class TestProviderRegistryIntegration:
    @patch("app.mic.providers.registry.GroqProvider")
    def test_get_provider_groq(self, mock_groq_class):
        mock_groq_class.return_value = Mock()
        ProviderRegistry.get_provider(explicit_model=DEFAULT_MODEL)
        mock_groq_class.assert_called_once_with(model=DEFAULT_MODEL)

    @patch("app.mic.providers.registry.GroqProvider")
    def test_get_provider_por_plan(self, mock_groq_class):
        mock_groq_class.return_value = Mock()
        plan = next(iter(PLAN_MODEL_MAP))
        ProviderRegistry.get_provider(user_plan=plan)
        mock_groq_class.assert_called_once_with(model=PLAN_MODEL_MAP[plan])