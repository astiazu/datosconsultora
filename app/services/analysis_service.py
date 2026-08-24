# app/services/analysis_service.py
"""
AnalysisService: Puente entre Flask y el MIC.
"""
from __future__ import annotations

import logging
from typing import Any

from app.mic.mic_engine import MIC
from app.mic.providers import ProviderRegistry

logger = logging.getLogger(__name__)


class AnalysisService:
    """Servicio de aplicación que orquesta el análisis de comentarios."""

    def analizar(
        self,
        datos_crudos: dict[str, Any],
        origen: str,
        user_plan: str,
        contexto: str = "",
        limite_comentarios: int | None = None,
    ) -> dict[str, Any]:
        """Analiza comentarios según el plan del usuario."""
        plan_lower = user_plan.lower()
        if limite_comentarios is None:
            from app.services.plan_service import LIMITES_COMENTARIOS_POR_PLAN
            limite_comentarios = LIMITES_COMENTARIOS_POR_PLAN.get(plan_lower, 50)

        if plan_lower in ["free", "bronce"]:
            return self._analizar_sentimientos(
                datos_crudos, origen, contexto, user_plan, limite_comentarios
            )
        elif plan_lower in ["plata", "oro", "lifetime", "premium"]:
            return self._analizar_semantica(
                datos_crudos, origen, contexto, user_plan, limite_comentarios
            )
        else:
            return {
                "success": False,
                "error": f"Plan '{user_plan}' no reconocido.",
            }

    def _analizar_sentimientos(
        self,
        datos_crudos: dict[str, Any],
        origen: str,
        contexto: str,
        user_plan: str,
        limite_comentarios: int | None = None,
    ) -> dict[str, Any]:
        """Análisis básico de sentimientos para Free/Bronce."""
        try:
            comentarios = self._extraer_comentarios(datos_crudos, origen)
            logger.info("Comentarios extraídos: %s", len(comentarios))

            if not comentarios:
                return {
                    "success": False,
                    "error": "No se encontraron comentarios válidos.",
                }

            provider = ProviderRegistry.get_provider(user_plan=user_plan)

            resultado_llm = provider.analyze_sentiment(
                comentarios=comentarios,
                contexto=contexto,
                limite_comentarios=limite_comentarios,
            )

            logger.warning("RESULTADO SENTIMIENTOS RAW: keys=%s", list(resultado_llm.keys()))

            # APLANAR: Fusionar resultado_llm en el nivel superior
            return {
                "success": True,
                "tipo_analisis": "sentimientos",
                "modelo_utilizado": getattr(provider._client, "model", provider.get_model_id()),
                "total_comentarios": len(comentarios),
                **resultado_llm,
            }
        except Exception as exc:
            logger.exception("Error en análisis de sentimientos")
            return {
                "success": False,
                "error": f"Error en análisis de sentimientos: {exc}",
            }

    def _analizar_semantica(
        self,
        datos_crudos: dict[str, Any],
        origen: str,
        contexto: str,
        user_plan: str,
        limite_comentarios: int | None = None,
    ) -> dict[str, Any]:
        """Análisis semántico avanzado para Plata+."""
        try:
            provider = ProviderRegistry.get_provider(user_plan=user_plan)
            from app.mic.analyzers.groq_semantic_analyzer import GroqSemanticAnalyzer

            analyzer = GroqSemanticAnalyzer(groq_client=provider._client)
            mic = MIC(semantic_analyzer=analyzer)

            result = mic.analizar(
                datos_crudos=datos_crudos,
                origen=origen,
                metadata={
                    "contexto": contexto,
                    "limite_comentarios": limite_comentarios,
                },
            )

            return {
                "success": result.success,
                "tipo_analisis": "semantico",
                "modelo_utilizado": getattr(provider._client, "model", provider.get_model_id()),
                "conversation_id": result.conversation_id,
                "analisis": self._serializar_semantic_analysis(result.semantic_analysis),
                "warnings": result.warnings,
                "errors": result.errors,
            }
        except Exception as exc:
            logger.exception("Error en análisis semántico")
            return {
                "success": False,
                "error": f"Error en análisis semántico: {exc}",
            }

    def _extraer_comentarios(
        self,
        datos_crudos: dict[str, Any],
        origen: str,
    ) -> list[str]:
        """Extrae lista de comentarios de los datos crudos."""
        if "comments" in datos_crudos:
            return [
                c.get("text", "") if isinstance(c, dict) else str(c)
                for c in datos_crudos["comments"]
            ]
        return []

    def _serializar_semantic_analysis(
        self,
        semantic_analysis: dict[str, Any],
    ) -> dict[str, Any]:
        """Convierte semantic_analysis a dict completamente serializable."""
        if not semantic_analysis:
            return {}
        analyses = semantic_analysis.get("analyses", [])
        serialized_analyses = []
        for analysis in analyses:
            if hasattr(analysis, "to_dict"):
                serialized_analyses.append(analysis.to_dict())
            else:
                serialized_analyses.append(analysis)
        return {
            "analyses": serialized_analyses,
            "metadata": semantic_analysis.get("metadata", {}),
        }