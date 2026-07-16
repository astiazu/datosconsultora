# app/services/transcription/openai_backend.py
import os
from openai import OpenAI
from .base import TranscriptionBackend


class OpenAIBackend(TranscriptionBackend):
    """Backend de transcripción usando OpenAI Whisper API (pago)."""
    
    def __init__(self):
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY no configurada en variables de entorno")
        self.client = OpenAI(api_key=api_key)
    
    def transcribe(self, file_path: str, language: str = "es") -> str:
        """Transcribe archivo usando OpenAI Whisper API."""
        try:
            with open(file_path, "rb") as audio_file:
                transcription = self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language=language,
                    response_format="text"
                )
            return transcription.text
        except Exception as e:
            raise Exception(f"Error transcribiendo con OpenAI: {str(e)}")
    
    def get_name(self) -> str:
        return "OpenAI Whisper API"