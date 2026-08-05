# app/services/plata/semantic_service.py
"""
Orquestador del análisis semántico del Plan Plata.
Toma una Conversation ya armada, ejecuta el MIC con GroqSemanticAnalyzer,
calcula estadísticas agregadas y genera un resumen ejecutivo.
"""
from app.mic.mic_engine import MIC
from app.mic.analyzers.groq_semantic_analyzer import GroqSemanticAnalyzer
from app.mic.providers import ProviderRegistry


class SemanticService:
    """Ejecuta el Motor Semántico sobre una Conversation del Plan Plata."""

    def analizar(self, conversation, user_plan: str, contexto: str = "") -> dict:
        """Analiza la conversación y devuelve un dict serializable."""
        provider = ProviderRegistry.get_provider(user_plan=user_plan)
        analyzer = GroqSemanticAnalyzer(groq_client=provider._client)
        mic = MIC(semantic_analyzer=analyzer)

        result = mic.analyze(
            conversation,
            metadata={"contexto": contexto},
        )

        analyses_serialized = self._serializar(result.semantic_analysis)
        analyses = analyses_serialized.get("analyses", [])

        # ✅ Estadísticas agregadas calculadas en Python (para el gráfico)
        estadisticas = self._agregar_estadisticas(analyses)

        # ✅ Resumen ejecutivo generado por el LLM (meta-análisis)
        resumen_ejecutivo = {}
        if result.success and estadisticas["total"] > 0:
            try:
                resumen_ejecutivo = provider._client.resumir_conversacion(
                    analyses=analyses,
                    contexto=contexto,
                )
            except Exception as exc:
                # El resumen es un "extra": si falla, no rompe el análisis
                resumen_ejecutivo = {"error": f"No se pudo generar el resumen ejecutivo: {exc}"}

        warnings = list(result.warnings)
        sem_warning = (result.semantic_analysis or {}).get("metadata", {}).get("warning")
        if sem_warning:
            warnings.append(sem_warning)

        return {
            "success": result.success,
            "tipo_analisis": "semantico",
            "conversation_id": result.conversation_id,
            "statistics": result.statistics,
            "estadisticas_agregadas": estadisticas,
            "resumen_ejecutivo": resumen_ejecutivo,
            "semantic_analysis": analyses_serialized,
            "warnings": warnings,
            "errors": result.errors,
            "modelo_utilizado": provider.get_model_id(),
        }

    def _agregar_estadisticas(self, analyses: list) -> dict:
        """Calcula contadores y porcentajes para el gráfico y los badges."""
        total = len(analyses)
        positivos = sum(1 for a in analyses if a.get("sentiment") == "positive")
        negativos = sum(1 for a in analyses if a.get("sentiment") == "negative")
        neutrales = total - positivos - negativos
        ironia = sum(1 for a in analyses if a.get("irony"))
        sarcasmo = sum(1 for a in analyses if a.get("sarcasm"))
        ambiguos = sum(1 for a in analyses if a.get("tone") == "ambiguous")

        def pct(n):
            return round((n / total) * 100) if total else 0

        return {
            "total": total,
            "positivos": positivos,
            "negativos": negativos,
            "neutrales": neutrales,
            "porcentaje_positivo": pct(positivos),
            "porcentaje_negativo": pct(negativos),
            "porcentaje_neutral": pct(neutrales),
            "ironia": ironia,
            "sarcasmo": sarcasmo,
            "ambiguos": ambiguos,
        }

    def _serializar(self, semantic_analysis: dict) -> dict:
        """Convierte SemanticResult objects a dicts serializables."""
        if not semantic_analysis:
            return {}
        analyses = semantic_analysis.get("analyses", [])
        serialized = []
        for a in analyses:
            serialized.append(a.to_dict() if hasattr(a, "to_dict") else a)
        return {
            "analyses": serialized,
            "metadata": semantic_analysis.get("metadata", {}),
        }