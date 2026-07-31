# app/mic/providers/base.py
"""
Interfaz abstracta para proveedores LLM.

Cualquier proveedor (Groq, OpenAI, modelo local) debe implementar
esta interfaz para ser usado por el MIC.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class LLMProvider(ABC):
    """
    Contrato que debe cumplir cualquier proveedor LLM.
    
    El MIC no conoce los detalles de cada proveedor.
    Solo interactúa con esta interfaz.
    """
    
    @abstractmethod
    def analyze_semantic(
        self,
        comentarios: list[str],
        contexto: str = "",
    ) -> dict[str, Any]:
        """
        Análisis semántico de comentarios.
        
        Retorna:
            dict con estructura:
            {
                "analyses": [
                    {
                        "message_id": "1",
                        "sentiment": "positive|negative|neutral",
                        "tone": "...",
                        "irony": bool,
                        "sarcasm": bool,
                        "irony_polarity": "...",
                        "confidence": float,
                        "literal_meaning": str,
                        "inferred_meaning": str,
                        "evidence": list
                    }
                ]
            }
        """
        raise NotImplementedError
    
    @abstractmethod
    def analyze_sentiment(
        self,
        comentarios: list[str],
        contexto: str = "",
    ) -> dict[str, Any]:
        """
        Análisis básico de sentimientos (para Free/Bronce).
        """
        raise NotImplementedError
    
    @abstractmethod
    def get_model_id(self) -> str:
        """Retorna el ID del modelo actualmente configurado."""
        raise NotImplementedError
    
    @abstractmethod
    def get_provider_name(self) -> str:
        """Retorna el nombre del proveedor (ej: 'groq', 'openai')."""
        raise NotImplementedError
    
    def get_status(self) -> dict[str, Any]:
        """
        Estado del proveedor (opcional, para monitoreo).
        Por defecto retorna info básica.
        """
        return {
            "provider": self.get_provider_name(),
            "model": self.get_model_id(),
        }