# app/mic/models/analysis_result.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class AnalysisResult:
    """
    Contrato de salida público del MIC.
    """

    success: bool
    conversation_id: str
    statistics: dict[str, Any] = field(default_factory=dict)
    semantic_analysis: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    evidence: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "conversation_id": self.conversation_id,
            "statistics": self.statistics,
            "semantic_analysis": self.semantic_analysis,
            "warnings": self.warnings,
            "errors": self.errors,
            "evidence": self.evidence,
        }


