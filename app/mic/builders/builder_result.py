# app/mic/builders/builder_result.py
from dataclasses import dataclass, field
from typing import List

from app.mic.domain.entities.conversation import Conversation


@dataclass(slots=True)
class BuildStatistics:
    """
    Estadísticas generadas durante la construcción.
    """
    participants_added: int = 0
    messages_added: int = 0
    duplicate_participants: int = 0
    duplicate_messages: int = 0
    empty_messages: int = 0


@dataclass(slots=True)
class BuilderResult:
    success: bool
    conversation: Conversation | None = None
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    statistics: BuildStatistics = field(
        default_factory=BuildStatistics
    )

    def add_warning(self, message: str):
        self.warnings.append(message)

    def add_error(self, message: str):
        self.errors.append(message)
