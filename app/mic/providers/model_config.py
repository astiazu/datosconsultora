# app/mic/providers/model_config.py
"""
Configuración de modelos disponibles.
⚠️ ACTUALIZADO 23/08/2026: Groq deprecó masivamente llama/qwen/mixtral/gemma.
Únicos modelos vivos verificados con diagnosticar_modelos.py:
  - openai/gpt-oss-20b   (rápido)
  - openai/gpt-oss-120b  (máxima calidad)
"""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum


class ProviderType(str, Enum):
    GROQ = "groq"
    # Futuros:
    # OPENAI = "openai"
    # LOCAL = "local"


@dataclass(frozen=True)
class ModelConfig:
    """Configuración inmutable de un modelo."""
    id: str
    provider: ProviderType
    display_name: str
    tokens_per_day: int
    cost_tier: str
    best_for: list[str]


# Registry de modelos VIVOS (verificados)
AVAILABLE_MODELS: dict[str, ModelConfig] = {
    "openai/gpt-oss-20b": ModelConfig(
        id="openai/gpt-oss-20b",
        provider=ProviderType.GROQ,
        display_name="GPT-OSS 20B (rápido)",
        tokens_per_day=500_000,
        cost_tier="free",
        best_for=["fast", "cheap", "sentimientos"],
    ),
    "openai/gpt-oss-120b": ModelConfig(
        id="openai/gpt-oss-120b",
        provider=ProviderType.GROQ,
        display_name="GPT-OSS 120B (calidad)",
        tokens_per_day=100_000,
        cost_tier="free",
        best_for=["semantic", "reasoning", "ironia"],
    ),
}

# Mapeo: plan del usuario → modelo recomendado
PLAN_MODEL_MAP: dict[str, str] = {
    "free": "openai/gpt-oss-20b",       # Rápido y barato
    "bronce": "openai/gpt-oss-20b",     # Rápido y barato
    "plata": "openai/gpt-oss-120b",     # Máxima calidad semántica
    "oro": "openai/gpt-oss-120b",       # Máxima calidad
    "lifetime": "openai/gpt-oss-120b",  # Premium
    "premium": "openai/gpt-oss-120b",
}

# Modelo por defecto
DEFAULT_MODEL = "openai/gpt-oss-20b"

# Fallbacks: si un modelo falla, intentar con el otro
FALLBACK_CHAINS: dict[str, list[str]] = {
    "openai/gpt-oss-20b": ["openai/gpt-oss-120b"],
    "openai/gpt-oss-120b": ["openai/gpt-oss-20b"],
}