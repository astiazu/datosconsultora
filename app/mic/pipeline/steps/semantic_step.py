# app/mic/pipeline/steps/semantic_step.py
from __future__ import annotations

import logging

from app.mic.analyzers.semantic_analyzer import SemanticAnalyzer
from app.mic.pipeline.context import PipelineContext


logger = logging.getLogger(__name__)


class SemanticStep:
    """
    Paso del Pipeline responsable de ejecutar la interpretación semántica.
    """

    def __init__(self, analyzer: SemanticAnalyzer):
        self.analyzer = analyzer

    def execute(self, context: PipelineContext) -> None:
        try:
            analysis = self.analyzer.analyze(
                conversation=context.conversation,
                metadata=context.metadata,
            )

            if not isinstance(analysis, dict):
                context.error("El analizador semántico devolvió un resultado inválido.")
                return

            if "error" in analysis:
                context.error(str(analysis["error"]))
                return

            context.set("semantic_analysis", analysis)

        except Exception as exc:
            logger.exception("Error ejecutando SemanticStep.")
            context.error(f"Error en análisis semántico: {exc}")