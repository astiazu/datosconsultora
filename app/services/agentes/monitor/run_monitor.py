# app/services/agentes/monitor/run_monitor.py
#!/usr/bin/env python3
"""
CLI del Agente de Monitoreo de Marca.
Uso:
  # Modo seco (sin Groq, todo neutro): valida scrape + comparación
  python -m app.services.agentes.monitor.run_monitor --config CONFIG.json
  # Modo producción (sentimiento vía MIC/Groq)
  python -m app.services.agentes.monitor.run_monitor --config CONFIG.json --con-ia
"""
from __future__ import annotations

import argparse
import logging
import sys

from .config.monitor_config import MonitorConfig, Platform
from .monitor_agent import MonitorAgent
from .reporters.consola import imprimir_cambios, imprimir_sin_novedades
from .scrapers.meta_scraper import MetaScraper


def _factory(platform: Platform) -> object:
    """Un scraper por familia de red. Sumar X/TikTok = sumar una rama."""
    if platform in (Platform.FACEBOOK, Platform.INSTAGRAM):
        service = None
        try:
            # Import diferido: Playwright se toca solo en el worker.
            from app.services.scraper_service import ScraperService
            service = ScraperService()
        except ImportError:
            pass  # fuera del repo (tests sueltos) → solo Plan B
        return MetaScraper(service)
    raise NotImplementedError(f"Todavía no hay scraper para {platform.value}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Monitor de marca (worker)")
    parser.add_argument("--config", required=True, help="Path al JSON de configuración")
    parser.add_argument("--marca", help="Sobreescribe la marca de la config")
    parser.add_argument(
        "--con-ia",
        action="store_true",
        help="Activa el análisis de sentimiento con el MIC (Groq).",
    )
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(message)s",
        datefmt="%H:%M:%S",
    )

    config = MonitorConfig.desde_json(args.config)
    if args.marca:
        config.marca = args.marca

    analysis = None
    if args.con_ia:
        from .analyzers.mic_adapter import MicAdapter
        analysis = MicAdapter()

    agente = MonitorAgent(config, scraper_factory=_factory, analysis_service=analysis)

    for res in agente.correr():
        if res.comparacion.sin_novedades:
            imprimir_sin_novedades(res.target.nombre)
        else:
            imprimir_cambios(res.comparacion)
        if res.informe:
            print(f"  ✓ Informe: {res.informe}")
    return 0


if __name__ == "__main__":
    sys.exit(main())