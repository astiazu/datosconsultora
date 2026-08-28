# app/services/agentes/monitor/monitor_agent.py
"""
MonitorAgent: orquestador del monitoreo de marca.

Flujo por target:
    scrape (URL → Plan B) → MIC (sentimiento) → comparar vs. estado_{slug}.json
    → consola (qué cambió) → informe .md si hubo cambios → guardar estado

Acá no se importa Playwright ni Flask: los servicios llegan inyectados.
Es el mismo patrón que monitor_service.py del módulo judicial.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Callable, List, Optional

from .analyzers.evolucion import (
    ComparadorEvolucion,
    ComentarioAnalizado,
    ResultadoComparacion,
    huella,
)
from .config.monitor_config import MonitorConfig, MonitorTarget, Platform
from .scrapers.base import ComentarioCrudo, ScrapedData

log = logging.getLogger("monitor.marca")


@dataclass
class ResultadoTarget:
    """Foto final de un target: qué se extrajo, qué cambió, dónde quedó."""

    target: MonitorTarget
    scrape: ScrapedData
    comparacion: ResultadoComparacion
    informe: Optional[str] = None  # ruta del .md, solo si hubo cambios


class MonitorAgent:
    """Orquesta scrape → análisis → comparación → informe por target."""

    def __init__(
        self,
        config: MonitorConfig,
        scraper_factory: Callable[[Platform], object],
        analysis_service: object = None,
        token_monitor: object = None,
    ) -> None:
        """
        scraper_factory: callable(platform) → objeto con .extraer(target)
        analysis_service: puente al MIC (plan Bronce/Plata de la cuenta).
                          None = modo seco (tests/CI, todo neutro).
        token_monitor:    pacing extra entre lotes Groq (opcional).
        """
        self.config = config
        self._scraper_factory = scraper_factory
        self._analysis = analysis_service
        self._tokens = token_monitor
        self._comparador = ComparadorEvolucion(config.carpeta_estados)

    # ------------------------------------------------------------- público
    def correr(self) -> List[ResultadoTarget]:
        """Run completo: todos los targets, en orden, sin cascada de errores."""
        resultados: List[ResultadoTarget] = []
        for target in self.config.targets:
            try:
                resultados.append(self._monitorear(target))
            except Exception as e:  # un target roto no tumba el run entero
                log.error("Target '%s' falló: %s", target.nombre, e)
        return resultados

    # ------------------------------------------------------------- interno
    def _monitorear(self, target: MonitorTarget) -> ResultadoTarget:
        log.info("▸ %s · %s", target.nombre, target.platform.value)

        # 1) Extracción. El scraper decide solo si cae al Plan B.
        scraper = self._scraper_factory(target.platform)
        scrape = scraper.extraer(target)
        log.info("✓ %d comentarios vía %s", len(scrape.comentarios), scrape.metodo)

        # 2) Sentimiento con el MIC existente (Groq gpt-oss-20b).
        analizados = self._analizar(scrape.comentarios)

        # 3) Riesgos: ratio de negativos + clusters por keyword de la marca.
        riesgos = self._detectar_riesgos(target, analizados)

        # 4) Comparar contra estado_{slug}.json.
        comparacion = self._comparador.comparar(target, analizados, riesgos)

        # 5) Informe solo si algo cambió; si no, "sin novedades" y listo.
        informe: Optional[str] = None
        if comparacion.sin_novedades:
            log.info("■ %s: sin novedades", target.nombre)
        else:
            from .reporters.informe import escribir_informe

            informe = escribir_informe(self.config, target, comparacion, scrape)

        # 6) Guardar la foto nueva (aun sin cambios, refresca la fecha).
        self._comparador.guardar_estado(
            target, analizados, comparacion.sentimiento_actual, riesgos
        )
        return ResultadoTarget(target, scrape, comparacion, informe)

    def _analizar(self, comentarios: List[ComentarioCrudo]) -> List[ComentarioAnalizado]:
        """Pasa los crudos por el MIC en tandas de 50 (patrón del resumen)."""
        if self._analysis is None:
            # Modo seco: sin Groq, todo neutro. Para tests y CI.
            return [
                ComentarioAnalizado(huella(c.autor, c.texto), c.autor, c.texto,
                                    "neutro", c.likes)
                for c in comentarios
            ]
        resultados: List[ComentarioAnalizado] = []
        for i in range(0, len(comentarios), 50):
            lote = comentarios[i : i + 50]
            # El MIC ya absorbe el 429 (espera el reset y reintenta el lote);
            # TokenMonitor es doble seguro para el tier free (~8000 TPM).
            resultados.extend(self._analysis.analizar_lote(lote))
            if self._tokens is not None:
                self._tokens.pacing_lote()
        return resultados

    def _detectar_riesgos(
        self, target: MonitorTarget, analizados: List[ComentarioAnalizado]
    ) -> List[dict]:
        validos = [c for c in analizados if c.sentimiento in ("positivo", "neutro", "negativo")]
        if not validos:
            return []
        negativos = [c for c in validos if c.sentimiento == "negativo"]
        riesgos: List[dict] = []

        ratio = len(negativos) / len(validos)   # ✅ solo sobre analizados
        if ratio >= self.config.umbral_negativo:
            riesgos.append(
                {"titulo": "Ratio de negativos alto", "severidad": "alta",
                 "detalle": f"{ratio:.0%} de los comentarios"}
            )

        # Cluster por keyword: 3+ negativos con la misma queja = riesgo,
        # aunque el ratio global esté bien. Es la señal temprana que le
        # sirve al consultor.
        for kw in target.keywords:
            menciones = [c for c in negativos if kw.lower() in c.texto.lower()]
            if len(menciones) >= 3:
                riesgos.append(
                    {"titulo": f"Queja recurrente: {kw}", "severidad": "media",
                     "detalle": f"{len(menciones)} comentarios"}
                )
        return riesgos
