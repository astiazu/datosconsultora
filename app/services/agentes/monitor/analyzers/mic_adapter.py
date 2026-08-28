# app/services/agentes/monitor/analyzers/mic_adapter.py
"""
Puente entre el monitor de marca y el MIC/Groq existente.
Convierte ComentarioCrudo -> ComentarioAnalizado usando el motor de
sentimientos YA VIVO del proyecto (gpt-oss-20b según model_config).

v2 (lección de la 1ª corrida --con-ia):
- Trozos propios de 15 comentarios con pacing de ~20s entre trozos,
  para entrar en los 8000 TPM del tier free SIN perder lotes por 429.
- Degradación por trozo: si un trozo falla, se marca neutro y el
  monitoreo sigue (el agente nunca debe morir).
No toca código blindado: el pacing vive solo en el worker.
"""
from __future__ import annotations

import logging
import time

from app.services.analysis.groq_llm import GroqLLMClient

from .evolucion import ComentarioAnalizado, huella
from ..scrapers.base import ComentarioCrudo

log = logging.getLogger("monitor.marca")

_MAPA = {"positivo": "positivo", "negativo": "negativo"}

# Tier free (~8000 TPM): ~3k tokens por trozo de 15 → máx ~2,5 trozos/min.
TAMANO_TROZO = 15
PACING_SEGUNDOS = 20


class MicAdapter:
    """Cumple el contrato que espera MonitorAgent: analizar_lote(lote)."""

    def __init__(self, client: GroqLLMClient | None = None) -> None:
        self._client = client or GroqLLMClient()

    def analizar_lote(self, lote: list[ComentarioCrudo]) -> list[ComentarioAnalizado]:
        out: list[ComentarioAnalizado] = []
        for i in range(0, len(lote), TAMANO_TROZO):
            trozo = lote[i:i + TAMANO_TROZO]
            items = self._analizar_trozo(trozo)
            for j, crudo in enumerate(trozo):
                item = items[j] if j < len(items) else None
                sent = (
                    _MAPA.get(str(item.get("sentimiento", "")).lower(), "neutro")
                    if item else "no_analizado"   # ✅ IA caída ≠ opinión neutra
                )
                out.append(
                    ComentarioAnalizado(
                        huella(crudo.autor, crudo.texto),
                        crudo.autor,
                        crudo.texto,
                        sent,
                        crudo.likes,
                    )
                )
            # Pacing entre trozos (no hace falta después del último)
            if i + TAMANO_TROZO < len(lote):
                time.sleep(PACING_SEGUNDOS)
        return out

    def _analizar_trozo(self, trozo: list[ComentarioCrudo]) -> list[dict]:
        try:
            resultado = self._client.analizar_sentimientos(
                [c.texto for c in trozo],
                contexto="Monitoreo de marca/candidato en redes sociales.",
            )
            return resultado.get("analisis_individual", [])
        except Exception as exc:
            log.warning(
                "⚠️ IA no disponible en trozo de %d (%s). Marco neutro.",
                len(trozo), str(exc)[:120],
            )
            return []