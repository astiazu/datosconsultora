# app/mic/providers/groq_provider.py
"""
Proveedor LLM usando Groq.
Envuelve GroqLLMClient para cumplir con la interfaz LLMProvider.
"""
from __future__ import annotations
import logging
from typing import Any

from app.mic.providers.base import LLMProvider
from app.services.analysis.groq_llm import GroqLLMClient
from app.mic.providers.model_config import DEFAULT_MODEL

logger = logging.getLogger(__name__)


class GroqProvider(LLMProvider):
    """
    Proveedor que utiliza Groq como motor LLM.
    Soporta todos los modelos disponibles en Groq:
    - Llama 3.3 70B
    - Llama 3.1 8B
    - Qwen 2.5 32B
    - Qwen QwQ 32B
    - Mixtral 8x7B
    - Gemma 2 9B
    """

    def __init__(self, model: str = DEFAULT_MODEL):
        self._client = GroqLLMClient(model=model)
        self._model = model

    def analyze_semantic(
        self,
        comentarios: list[str],
        contexto: str = "",
        limite_comentarios: int | None = None,
    ) -> dict[str, Any]:
        """Delega al GroqLLMClient.analizar_semantica() con límite por plan."""
        return self._client.analizar_semantica(
            comentarios=comentarios,
            contexto=contexto,
            limite_comentarios=limite_comentarios,
        )

    def analyze_sentiment(
        self,
        comentarios: list[str],
        contexto: str = "",
        limite_comentarios: int | None = None,
    ) -> dict[str, Any]:
        """Delega al GroqLLMClient.analizar_sentimientos() con límite por plan."""
        return self._client.analizar_sentimientos(
            comentarios=comentarios,
            contexto=contexto,
            limite_comentarios=limite_comentarios,
        )

    def get_model_id(self) -> str:
        return self._model

    def get_provider_name(self) -> str:
        return "groq"

    def get_status(self) -> dict[str, Any]:
        """Incluye info del monitor de tokens."""
        status = super().get_status()
        if hasattr(self._client, "token_monitor"):
            status["tokens"] = self._client.token_monitor.get_summary()
        return status