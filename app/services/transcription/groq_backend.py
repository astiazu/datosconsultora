# app/services/transcription/groq_backend.py
import os
from groq import Groq

class GroqBackend:
    """Backend de transcripción usando Groq Whisper API (soporta audio y video nativamente)."""
    
    def __init__(self):
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY no configurada en variables de entorno")
        self.client = Groq(api_key=api_key)
    
    def transcribe(self, file_path: str, language: str = None) -> dict:
        """
        Transcribe un archivo de audio o video.
        """
        try:
            with open(file_path, "rb") as file:
                kwargs = {
                    "model": "whisper-large-v3",
                    "file": file,
                    "response_format": "verbose_json",
                    "temperature": 0.0,
                }
                if language:
                    kwargs["language"] = language
                
                transcription = self.client.audio.transcriptions.create(**kwargs)
                
                if hasattr(transcription, 'text'):
                    return {
                        "text": transcription.text or "",
                        "language": getattr(transcription, 'language', language or "es"),
                        "duration": getattr(transcription, 'duration', 0),
                    }
                else:
                    return {
                        "text": str(transcription),
                        "language": language or "es",
                        "duration": 0,
                    }
        except Exception as e:
            raise Exception(f"Error transcribiendo con Groq: {str(e)}")
    
    def get_name(self) -> str:
        return "Groq Whisper API"