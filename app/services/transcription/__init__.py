# app/services/transcription/__init__.py
from .base import TranscriptionBackend, get_transcription_backend

__all__ = ['TranscriptionBackend', 'get_transcription_backend']