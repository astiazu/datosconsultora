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


# ─── Modelos disponibles en Groq (actualizado agosto 2026) ───
AVAILABLE_MODELS: dict[str, ModelConfig] = {
    # === PRODUCCIÓN ===
    "openai/gpt-oss-120b": ModelConfig(
        id="openai/gpt-oss-120b",
        provider=ProviderType.GROQ,
        display_name="GPT OSS 120B",
        tokens_per_day=200_000,
        cost_tier="free",
        best_for=["reasoning", "semantic", "ironia", "quality"],
    ),
    "openai/gpt-oss-20b": ModelConfig(
        id="openai/gpt-oss-20b",
        provider=ProviderType.GROQ,
        display_name="GPT OSS 20B",
        tokens_per_day=200_000,
        cost_tier="free",
        best_for=["fast", "balanced", "chunks"],
    ),

    # === PREVIEW (evaluación, no producción) ===
    "qwen/qwen3.6-27b": ModelConfig(
        id="qwen/qwen3.6-27b",
        provider=ProviderType.GROQ,
        display_name="Qwen 3.6 27B",
        tokens_per_day=500_000,
        cost_tier="free",
        best_for=["balanced", "multilingual"],
    ),
    "qwen/qwen3.8-27b": ModelConfig(
        id="qwen/qwen3.8-27b",
        provider=ProviderType.GROQ,
        display_name="Qwen 3.8 27B",
        tokens_per_day=500_000,
        cost_tier="free",
        best_for=["reasoning", "multilingual"],
    ),
}

# Mapeo: plan del usuario → modelo recomendado
PLAN_MODEL_MAP: dict[str, str] = {
    "free":     "openai/gpt-oss-20b",      # Rápido, suficiente para free
    "bronce":   "openai/gpt-oss-20b",      # Rápido
    "plata":    "openai/gpt-oss-120b",      # Calidad alta
    "oro":      "openai/gpt-oss-120b",      # Mejor disponible
    "lifetime": "openai/gpt-oss-120b",      # Premium
    "premium":  "openai/gpt-oss-120b",
}

# Modelo por defecto
DEFAULT_MODEL = "openai/gpt-oss-120b"

# Fallbacks: si un modelo falla, intentar con estos
FALLBACK_CHAINS: dict[str, list[str]] = {
    "openai/gpt-oss-120b": [
        "openai/gpt-oss-20b",
        "qwen/qwen3.6-27b",
    ],
    "openai/gpt-oss-20b": [
        "openai/gpt-oss-120b",
        "qwen/qwen3.6-27b",
    ],
    "qwen/qwen3.6-27b": [
        "openai/gpt-oss-120b",
        "openai/gpt-oss-20b",
    ],
    "qwen/qwen3.8-27b": [
        "qwen/qwen3.6-27b",
        "openai/gpt-oss-120b",
    ],
}