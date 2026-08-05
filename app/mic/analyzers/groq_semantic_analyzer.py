# app/mic/analyzers/groq_semantic_analyzer.py
from __future__ import annotations

import logging
from typing import Any

from app.mic.analyzers.semantic_analyzer import SemanticAnalyzer
from app.mic.domain.entities.conversation import Conversation
from app.mic.models.semantic_result import SemanticResult
from app.services.analysis.groq_llm import GroqLLMClient

logger = logging.getLogger(__name__)


class GroqSemanticAnalyzer(SemanticAnalyzer):
    """
    Implementación del análisis semántico utilizando Groq.

    Responsabilidades:
    - Extraer mensajes de la Conversation.
    - Llamar a GroqLLMClient.analizar_semantica().
    - Convertir el dict crudo de Groq a objetos SemanticResult.

    NO conoce:
    - El plan del usuario.
    - La autorización de acceso.
    - Las estadísticas agregadas.
    """

    def __init__(
        self,
        groq_client: GroqLLMClient | None = None,
    ):
        self.groq_client = groq_client

    def analyze(
        self,
        conversation: Conversation,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Analiza la conversación y devuelve SemanticResult objects.
        """
        metadata = metadata or {}

        mensajes = self._build_messages(conversation)

        if not mensajes:
            return {
                "analyses": [],
                "metadata": {
                    "warning": "No hay mensajes válidos para analizar."
                },
            }

        contexto = str(metadata.get("contexto", "")).strip()
        comentarios = [mensaje["texto"] for mensaje in mensajes]

        try:
            client = self._get_client()

            # Llamada al motor semántico (SIN plan)
            resultado_groq = client.analizar_semantica(
                comentarios=comentarios,
                contexto=contexto,
            )

            # Convertir dict crudo a SemanticResult objects
            analyses = self._convert_to_semantic_results(
                resultado_groq.get("analyses", []),
                mensajes,
            )

            metadata_salida = {
                "provider": "groq",
                "model": client.model,
                "total_analizados": len(analyses),
            }

            # ✅ NUEVO: propagar el warning del cliente
            # (ej: "se analizaron solo los primeros 100 comentarios")
            if resultado_groq.get("warning"):
                metadata_salida["warning"] = resultado_groq["warning"]

            return {
                "analyses": analyses,
                "metadata": metadata_salida,
            }

        except AttributeError:
            logger.exception(
                "GroqLLMClient no dispone de analizar_semantica()."
            )
            # ✅ NUEVO: "error" en el nivel superior para que el
            # SemanticStep lo detecte y el Pipeline marque el fallo
            # (evita informes en blanco con success=True).
            return {
                "error": (
                    "GroqLLMClient no tiene implementado "
                    "el método analizar_semantica()."
                ),
                "analyses": [],
                "metadata": {
                    "error": (
                        "GroqLLMClient no tiene implementado "
                        "el método analizar_semantica()."
                    )
                },
            }

        except Exception as exc:
            logger.exception(
                "Error ejecutando análisis semántico con Groq."
            )
            # ✅ NUEVO: "error" en el nivel superior (ver comentario arriba)
            return {
                "error": f"Fallo en el motor semántico: {exc}",
                "analyses": [],
                "metadata": {
                    "error": f"Fallo en el motor semántico: {exc}"
                },
            }

    def _get_client(self) -> GroqLLMClient:
        if self.groq_client is None:
            self.groq_client = GroqLLMClient()
        return self.groq_client

    def _build_messages(
        self,
        conversation: Conversation,
    ) -> list[dict[str, str]]:
        """
        Extrae mensajes válidos de la Conversation.
        """
        participantes = {
            participante.participant_id: participante.display_name
            for participante in conversation.participants
        }

        mensajes: list[dict[str, str]] = []

        for message in conversation.messages:
            texto = str(message.text or "").strip()
            if not texto:
                continue

            participante = participantes.get(
                message.participant_id,
                "Anónimo",
            )

            mensajes.append({
                "message_id": message.message_id,
                "participant_id": message.participant_id,
                "participante": participante,
                "texto": texto,
            })

        return mensajes

    def _convert_to_semantic_results(
        self,
        analyses_groq: list[dict],
        mensajes_originales: list[dict],
    ) -> list[SemanticResult]:
        """
        Convierte el dict crudo de Groq a objetos SemanticResult.

        Esta es la capa de adaptación:
        - Groq devuelve dicts con campos específicos.
        - El MIC trabaja con SemanticResult objects.
        """
        resultados: list[SemanticResult] = []

        for index, analysis in enumerate(analyses_groq):
            try:
                # Obtener el mensaje original para preservar metadata
                mensaje_original = (
                    mensajes_originales[index]
                    if index < len(mensajes_originales)
                    else {}
                )

                semantic_result = SemanticResult(
                    sentiment=str(analysis.get("sentiment", "neutral")),
                    tone=str(analysis.get("tone", "neutral")),
                    irony=bool(analysis.get("irony", False)),
                    sarcasm=bool(analysis.get("sarcasm", False)),
                    irony_polarity=str(
                        analysis.get("irony_polarity", "none")
                    ),
                    confidence=float(analysis.get("confidence", 0.0)),
                    literal_meaning=str(
                        analysis.get("literal_meaning", "")
                    ),
                    inferred_meaning=str(
                        analysis.get("inferred_meaning", "")
                    ),
                    evidence=list(analysis.get("evidence", [])),
                    metadata={
                        "message_id": analysis.get("message_id"),
                        "texto_original": analysis.get(
                            "texto_original",
                            mensaje_original.get("texto", ""),
                        ),
                        "participant_id": mensaje_original.get(
                            "participant_id"
                        ),
                        "participante": mensaje_original.get(
                            "participante"
                        ),
                    },
                )

                resultados.append(semantic_result)

            except (ValueError, TypeError, KeyError) as exc:
                logger.warning(
                    f"Error convirtiendo análisis {index}: {exc}"
                )
                continue

        return resultados