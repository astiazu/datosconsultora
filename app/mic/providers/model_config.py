# app/mic/providers/model_config.py
"""
Configuración de modelos disponibles.

Define qué modelos existen, sus características,
y cuál usar según el plan del usuario.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from enum import Enum
from typing import Optional


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
    cost_tier: str  # "free", "basic", "premium"
    best_for: list[str]  # ej: ["semantic", "fast", "ironia"]


# Registry de modelos disponibles
AVAILABLE_MODELS: dict[str, ModelConfig] = {
    # === GROQ: LLAMA ===
    "llama-3.3-70b-versatile": ModelConfig(
        id="llama-3.3-70b-versatile",
        provider=ProviderType.GROQ,
        display_name="Llama 3.3 70B",
        tokens_per_day=100_000,
        cost_tier="free",
        best_for=["semantic", "balanced"],
    ),
    "llama-3.1-8b-instant": ModelConfig(
        id="llama-3.1-8b-instant",
        provider=ProviderType.GROQ,
        display_name="Llama 3.1 8B (rápido)",
        tokens_per_day=500_000,
        cost_tier="free",
        best_for=["fast", "cheap", "sentimientos"],
    ),
    
    # === GROQ: QWEN ===
    "qwen-2.5-32b": ModelConfig(
        id="qwen-2.5-32b",
        provider=ProviderType.GROQ,
        display_name="Qwen 2.5 32B",
        tokens_per_day=100_000,
        cost_tier="free",
        best_for=["semantic", "multilingual"],
    ),
    "qwen-qwq-32b": ModelConfig(
        id="qwen-qwq-32b",
        provider=ProviderType.GROQ,
        display_name="Qwen QwQ 32B (razonamiento)",
        tokens_per_day=100_000,
        cost_tier="free",
        best_for=["semantic", "reasoning", "ironia"],
    ),
    
    # === GROQ: OTROS ===
    "mixtral-8x7b-32768": ModelConfig(
        id="mixtral-8x7b-32768",
        provider=ProviderType.GROQ,
        display_name="Mixtral 8x7B",
        tokens_per_day=500_000,
        cost_tier="free",
        best_for=["balanced", "cheap"],
    ),
    "gemma2-9b-it": ModelConfig(
        id="gemma2-9b-it",
        provider=ProviderType.GROQ,
        display_name="Gemma 2 9B",
        tokens_per_day=500_000,
        cost_tier="free",
        best_for=["fast", "cheap"],
    ),
}


# Mapeo: plan del usuario → modelo recomendado
PLAN_MODEL_MAP: dict[str, str] = {
    "free": "llama-3.3-70b-versatile",      # ✅ CAMBIADO: más capacidad (100k TPM)
    "bronce": "llama-3.3-70b-versatile",    # ✅ CAMBIADO: más capacidad (100k TPM)
    "plata": "llama-3.3-70b-versatile",     # Balance calidad/velocidad
    "oro": "qwen-qwq-32b",                  # Mejor para ironía/razonamiento
    "lifetime": "qwen-qwq-32b",             # Premium
    "premium": "qwen-qwq-32b",
}


# Modelo por defecto
DEFAULT_MODEL = "llama-3.3-70b-versatile"

# Fallbacks: si un modelo falla, intentar con estos en orden
FALLBACK_CHAINS: dict[str, list[str]] = {
    "llama-3.3-70b-versatile": [
        "llama-3.1-8b-instant",  # 500k tokens, más rápido
        "qwen-2.5-32b",          # Alternativa de calidad
        "mixtral-8x7b-32768",    # 500k tokens
        "gemma2-9b-it",          # 500k tokens
    ],
    "qwen-qwq-32b": [
        "qwen-2.5-32b",          # Mismo proveedor, diferente modelo
        "llama-3.3-70b-versatile",
        "llama-3.1-8b-instant",
    ],
    "llama-3.1-8b-instant": [
        "qwen-2.5-32b",          # ✅ Agregado: alternativa de calidad
        "mixtral-8x7b-32768",
        "gemma2-9b-it",
    ],
}