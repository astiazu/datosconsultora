# app/mic/domain/enums/semantic.py
from enum import Enum


class Sentiment(Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


class Tone(Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    IRONIC_POSITIVE = "ironic_positive"
    IRONIC_NEGATIVE = "ironic_negative"
    SARCASTIC = "sarcastic"
    MIXED = "mixed"
    AMBIGUOUS = "ambiguous"


class IronyPolarity(Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    NONE = "none"


