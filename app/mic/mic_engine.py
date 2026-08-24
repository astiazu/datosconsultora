# app/mic/mic_engine.py
from __future__ import annotations

import logging
from typing import Any

from app.mic.adapters.facebook.facebook_adapter import FacebookAdapter
from app.mic.analyzers.semantic_analyzer import SemanticAnalyzer
from app.mic.domain.entities.conversation import Conversation
from app.mic.models.analysis_result import AnalysisResult
from app.mic.pipeline.pipeline import Pipeline
from app.mic.pipeline.steps.clean_step import CleanStep
from app.mic.pipeline.steps.validation_step import ValidationStep
from app.mic.pipeline.steps.semantic_step import SemanticStep


logger = logging.getLogger(__name__)


class MIC:
    """
    Fachada pública del Motor de Interpretación Conversacional.

    Contrato público:
        Entrada:  datos_crudos + origen + metadata
        Salida:   AnalysisResult (objeto tipado)

    El MIC NO conoce:
        - Planes de usuario
        - Autorización de acceso
        - Lógica comercial
        - Bases de datos
        - Rutas HTTP
    """

    def __init__(
        self,
        semantic_analyzer: SemanticAnalyzer | None = None,
    ):
        self.semantic_analyzer = semantic_analyzer

    def analyze(
        self,
        conversation: Conversation,
        metadata: dict[str, Any] | None = None,
    ) -> AnalysisResult:
        """
        Analiza una conversación ya normalizada.

        Este es el método de bajo nivel para cuando ya tenés
        una Conversation armada (ej: desde tests o código interno).
        """
        conversation_id = str(
            getattr(conversation, "conversation_id", "unknown")
        )

        if conversation is None:
            return AnalysisResult(
                success=False,
                conversation_id="unknown",
                errors=["MIC recibió una conversación nula."],
            )

        try:
            pipeline = Pipeline()
            pipeline.add(CleanStep())
            pipeline.add(ValidationStep())

            if self.semantic_analyzer is not None:
                pipeline.add(
                    SemanticStep(analyzer=self.semantic_analyzer)
                )

            result = pipeline.run(
                conversation,
                metadata=metadata or {},
            )

            return AnalysisResult(
                success=result.success,
                conversation_id=conversation_id,
                statistics=result.data.get("statistics", {}),
                semantic_analysis=result.data.get("semantic_analysis", {}),
                warnings=list(result.warnings),
                errors=list(result.errors),
                evidence=result.data.get("evidence", []),
            )

        except Exception as exc:
            logger.exception("Error crítico dentro del MIC.")
            return AnalysisResult(
                success=False,
                conversation_id=conversation_id,
                errors=[f"Error interno del MIC: {exc}"],
            )

    def analizar(
        self,
        datos_crudos: dict[str, Any],
        origen: str,
        metadata: dict[str, Any] | None = None,
    ) -> AnalysisResult:
        """
        API pública de alto nivel.

        Recibe datos crudos de cualquier fuente y devuelve AnalysisResult.

        Parámetros:
            datos_crudos: dict con la data cruda (ej: de Facebook, CSV, etc.)
            origen: string identificando la fuente ("facebook", "csv", etc.)
            metadata: dict con contexto, user_plan, etc.

        Retorna:
            AnalysisResult tipado con el análisis completo.

        Este método:
            1. Selecciona el Adapter correcto según el origen
            2. Convierte datos_crudos → Conversation
            3. Ejecuta el Pipeline completo
            4. Devuelve AnalysisResult
        """
        try:
            # 1. Seleccionar Adapter
            adapter = self._get_adapter(origen)

            # 2. Convertir a Conversation
            adapter_result = adapter.convert(datos_crudos)

            if not adapter_result.success:
                return AnalysisResult(
                    success=False,
                    conversation_id="unknown",
                    errors=adapter_result.errors or [
                        "Error en la conversión de datos."
                    ],
                )

            # 3. Ejecutar análisis
            return self.analyze(
                conversation=adapter_result.conversation,
                metadata=metadata,
            )

        except ValueError as exc:
            logger.warning(f"Error de validación en MIC.analizar: {exc}")
            return AnalysisResult(
                success=False,
                conversation_id="unknown",
                errors=[str(exc)],
            )

        except Exception as exc:
            logger.exception("Error crítico en MIC.analizar.")
            return AnalysisResult(
                success=False,
                conversation_id="unknown",
                errors=[f"Error interno del MIC: {exc}"],
            )

    def _get_adapter(self, origen: str):
        """
        Factory de Adapters.
        Selecciona el adapter correcto según el origen.
        """
        from app.mic.adapters.adapter_factory import AdapterFactory
        try:
            return AdapterFactory.create(origen.lower())
        except ValueError:
            raise ValueError(
                f"Origen '{origen}' no soportado. "
                f"Orígenes disponibles: facebook, instagram, x"
            )