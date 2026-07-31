# app/mic/domain/enums/source.py
from enum import Enum


class SourceType(str, Enum):
    """Origen de una conversación."""
    FACEBOOK = "facebook"
    INSTAGRAM = "instagram"
    WHATSAPP = "whatsapp"
    YOUTUBE = "youtube"
    X = "x"
    TIKTOK = "tiktok"
    CSV = "csv"
    EXCEL = "excel"
    TEXT = "text"
    API = "api"
    UNKNOWN = "unknown"


class EmotionType(str, Enum):
    """Emoción predominante."""
    JOY = "joy"
    SADNESS = "sadness"
    ANGER = "anger"
    FEAR = "fear"
    SURPRISE = "surprise"
    DISGUST = "disgust"
    NEUTRAL = "neutral"


class SentimentType(str, Enum):
    """Polaridad tradicional."""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    MIXED = "mixed"


class IronyType(str, Enum):
    """Clasificación de ironía."""
    NONE = "none"
    IRONY = "irony"
    SARCASM = "sarcasm"
    SATIRE = "satire"
    HUMOR = "humor"


class InsightType(str, Enum):
    """Tipos de insight generados."""
    TREND = "trend"
    ALERT = "alert"
    OPPORTUNITY = "opportunity"
    RISK = "risk"
    NARRATIVE = "narrative"
    HYPOTHESIS = "hypothesis"


class ParticipantRole(str, Enum):
    """Rol dentro de la conversación."""
    AUTHOR = "author"
    ADMIN = "admin"
    MODERATOR = "moderator"
    MEMBER = "member"
    UNKNOWN = "unknown"

