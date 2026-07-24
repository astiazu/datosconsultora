# app/services/transcription/groq_backend.py
import os
from groq import Groq


class GroqBackend:
    """Backend de transcripción usando Groq Whisper API."""
    
    def __init__(self):
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY no configurada en variables de entorno")
        self.client = Groq(api_key=api_key)
    
    def transcribe(self, file_path: str, language: str = None) -> dict:
        """
        Transcribe un archivo de audio.
        
        :param file_path: Ruta al archivo de audio
        :param language: Código de idioma ('es', 'en', None para auto-detectar)
        :return: Dict con 'text', 'language', 'duration'
        """
        try:
            with open(file_path, "rb") as file:
                # Usar verbose_json para obtener idioma detectado y duración
                kwargs = {
                    "model": "whisper-large-v3",
                    "file": file,
                    "response_format": "verbose_json",
                    "temperature": 0.0,
                }
                
                if language:
                    kwargs["language"] = language
                
                transcription = self.client.audio.transcriptions.create(**kwargs)
                
                # La respuesta puede ser un objeto o dict dependiendo de la versión del SDK
                if hasattr(transcription, 'text'):
                    return {
                        "text": transcription.text or "",
                        "language": getattr(transcription, 'language', language or "es"),
                        "duration": getattr(transcription, 'duration', 0),
                    }
                else:
                    # Si es string directo (response_format="text")
                    return {
                        "text": str(transcription),
                        "language": language or "es",
                        "duration": 0,
                    }
                    
        except Exception as e:
            raise Exception(f"Error transcribiendo con Groq: {str(e)}")
    
    def get_name(self) -> str:
        return "Groq Whisper API"