# app/mic/pipeline/context.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.mic.domain.entities.conversation import Conversation


@dataclass(slots=True)
class PipelineContext:
    """
    Contexto compartido entre todos los pasos del Pipeline.
    """

    conversation: Conversation
    data: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def set(self, key: str, value: Any) -> None:
        self.data[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)

    def warning(self, msg: str) -> None:
        self.warnings.append(msg)

    def error(self, msg: str) -> None:
        self.errors.append(msg)