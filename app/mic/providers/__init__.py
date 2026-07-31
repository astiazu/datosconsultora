# app/mic/providers/__init__.py
"""
Proveedores LLM del MIC.

Permite cambiar entre Groq, OpenAI, modelos locales, etc.
sin modificar el resto del sistema.
"""
from app.mic.providers.base import LLMProvider
from app.mic.providers.groq_provider import GroqProvider
from app.mic.providers.registry import ProviderRegistry
from app.mic.providers.model_config import (
    ModelConfig,
    ProviderType,
    AVAILABLE_MODELS,
    PLAN_MODEL_MAP,
)

__all__ = [
    "LLMProvider",
    "GroqProvider",
    "ProviderRegistry",
    "ModelConfig",
    "ProviderType",
    "AVAILABLE_MODELS",
    "PLAN_MODEL_MAP",
]