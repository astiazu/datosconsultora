# app/services/agentes/monitor/__init__.py
"""
Agente de Monitoreo de Marca — paquete.

Arquitectura espejada del módulo judicial (app/services/agentes):
  · config/     → dataclasses puras (MonitorConfig, MonitorTarget, Platform)
  · scrapers/   → un archivo por familia de red, contrato ScrapedData
  · analyzers/  → comparación vs. estado_{slug}.json + detección de riesgos
  · reporters/  → consola (qué cambió) + informe .md detallado
  · run_monitor → CLI/worker para cron de Render (headless=True, fuera del request)

Se exporta lo mínimo: orquestador + configuración.
"""
from .config.monitor_config import MonitorConfig, MonitorTarget, Platform
from .monitor_agent import MonitorAgent, ResultadoTarget

__all__ = [
    "MonitorAgent",
    "MonitorConfig",
    "MonitorTarget",
    "Platform",
    "ResultadoTarget",
]
