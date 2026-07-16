# app/services/transcription/groq_backend.py
import os
from groq import Groq
from .base import TranscriptionBackend


class GroqBackend(TranscriptionBackend):
    """Backend de transcripción usando Groq Whisper API (gratis)."""
    
    def __init__(self):
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY no configurada en variables de entorno")
        self.client = Groq(api_key=api_key)
    
    def transcribe(self, file_path: str, language: str = "es") -> str:
        """Transcribe archivo usando Groq Whisper API."""
        try:
            with open(file_path, "rb") as file:
                transcription = self.client.audio.transcriptions.create(
                    model="whisper-large-v3",
                    file=file,
                    language=language,
                    response_format="text",
                    temperature=0.0
                )
            return transcription
        except Exception as e:
            raise Exception(f"Error transcribiendo con Groq: {str(e)}")
    
    def get_name(self) -> str:
        return "Groq Whisper API"