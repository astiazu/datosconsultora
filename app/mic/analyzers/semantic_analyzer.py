# app/mic/analyzers/semantic_analyzer.py
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from app.mic.domain.entities.conversation import Conversation


class SemanticAnalyzer(ABC):
    """
    Contrato que debe cumplir cualquier analizador semántico.
    """

    @abstractmethod
    def analyze(
        self,
        conversation: Conversation,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        raise NotImplementedError