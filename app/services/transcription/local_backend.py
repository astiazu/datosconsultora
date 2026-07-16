# app/services/transcription/local_backend.py
import os
import whisper
from .base import TranscriptionBackend


class LocalWhisperBackend(TranscriptionBackend):
    """Backend de transcripción usando Whisper local (requiere GPU para velocidad)."""
    
    def __init__(self, model_size: str = "base"):
        """
        :param model_size: tiny, base, small, medium, large-v3
        """
        print(f"Cargando modelo Whisper {model_size}... (puede tardar)")
        self.model = whisper.load_model(model_size)
        print("Modelo Whisper cargado")
    
    def transcribe(self, file_path: str, language: str = "es") -> str:
        """Transcribe archivo usando Whisper local."""
        try:
            result = self.model.transcribe(
                file_path,
                language=language,
                task="transcribe",
                verbose=False
            )
            return result["text"]
        except Exception as e:
            raise Exception(f"Error transcribiendo con Whisper local: {str(e)}")
    
    def get_name(self) -> str:
        return "Whisper Local"