# app/mic/pipeline/result.py
from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class PipelineResult:
    """
    Resultado final de la ejecución del Pipeline.
    """

    success: bool

    data: dict[str, Any] = field(default_factory=dict)

    warnings: list[str] = field(default_factory=list)

    errors: list[str] = field(default_factory=list)
    def get(self, key: str, default=None):

        return self.data.get(key, default)

    def warning(self, msg: str):

        self.warnings.append(msg)

    def error(self, msg: str):

        self.errors.append(msg)