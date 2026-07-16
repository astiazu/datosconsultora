# app/services/transcription/base.py
from abc import ABC, abstractmethod
from typing import Optional
import os


class TranscriptionBackend(ABC):
    """Clase abstracta para backends de transcripción."""
    
    @abstractmethod
    def transcribe(self, file_path: str, language: str = "es") -> str:
        """
        Transcribe un archivo de audio/video a texto.
        
        :param file_path: Ruta al archivo de audio/video
        :param language: Código de idioma (es, en, etc.)
        :return: Texto transcrito
        """
        pass
    
    @abstractmethod
    def get_name(self) -> str:
        """Retorna el nombre del backend."""
        pass


def get_transcription_backend() -> TranscriptionBackend:
    """
    Factory para obtener el backend de transcripción configurado.
    Lee la variable de entorno TRANSCRIPTION_BACKEND.
    """
    backend_name = os.environ.get("TRANSCRIPTION_BACKEND", "groq").lower()
    
    if backend_name == "groq":
        from .groq_backend import GroqBackend
        return GroqBackend()
    elif backend_name == "openai":
        from .openai_backend import OpenAIBackend
        return OpenAIBackend()
    elif backend_name == "local":
        from .local_backend import LocalWhisperBackend
        return LocalWhisperBackend()
    else:
        raise ValueError(f"Backend de transcripción no soportado: {backend_name}")