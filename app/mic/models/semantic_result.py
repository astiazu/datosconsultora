# app/mic/models/semantic_result.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class SemanticResult:
    """
    Resultado normalizado de la interpretación semántica
    de un mensaje o conversación.
    """

    sentiment: str = "neutral"
    tone: str = "neutral"
    irony: bool = False
    sarcasm: bool = False
    irony_polarity: str = "neutral"
    confidence: float = 0.0
    literal_meaning: str = ""
    inferred_meaning: str = ""
    evidence: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "sentiment": self.sentiment,
            "tone": self.tone,
            "irony": self.irony,
            "sarcasm": self.sarcasm,
            "irony_polarity": self.irony_polarity,
            "confidence": self.confidence,
            "literal_meaning": self.literal_meaning,
            "inferred_meaning": self.inferred_meaning,
            "evidence": self.evidence,
            "metadata": self.metadata,
        }