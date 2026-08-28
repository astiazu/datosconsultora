# app/services/agentes/monitor/config/monitor_config.py
"""
Configuración del Agente de Monitoreo de Marca.

Acá viven los dataclasses puros: sin Flask, sin Playwright, sin red.
Eso deja todo el módulo testeable en cualquier máquina y con el mismo
contrato listo para reutilizar cuando el monitor se adapte al PJN.
"""
from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import List, Optional


class Platform(str, Enum):
    """Redes soportadas. Sumar una red = agregar un valor + un scraper."""

    FACEBOOK = "facebook"
    INSTAGRAM = "instagram"
    X = "x"


def slugify(texto: str) -> str:
    """'Café Aurora' -> 'cafe_aurora'. Nombres de archivo sin dolores."""
    limpio = unicodedata.normalize("NFKD", texto)
    limpio = "".join(c for c in limpio if not unicodedata.combining(c))
    limpio = re.sub(r"[^a-zA-Z0-9]+", "_", limpio).strip("_")
    return limpio.lower() or "target"


@dataclass
class MonitorTarget:
    """Una marca / candidato / producto observado en UNA red."""

    nombre: str
    platform: Platform
    url: str
    keywords: List[str] = field(default_factory=list)
    # Plan B: export "Página web, solo HTML" desde sesión logueada (Ctrl+S).
    # Es el camino confiable para Meta hoy (ago/2026): cero bloqueos.
    html_local: Optional[str] = None

    @property
    def slug(self) -> str:
        return slugify(self.nombre)

    @property
    def archivo_estado(self) -> str:
        """estado_cafe_aurora.json — como pide la especificación."""
        return f"estado_{self.slug}.json"


@dataclass
class MonitorConfig:
    """Configuración general del run + lista de targets."""

    marca: str
    targets: List[MonitorTarget] = field(default_factory=list)
    # Proporción de negativos que dispara un riesgo "ratio alto".
    umbral_negativo: float = 0.25
    carpeta_estados: str = "estados"
    carpeta_informes: str = "informes"
    carpeta_exports: str = "exports"
    # Siempre headless en el worker; jamás dentro del request de Flask.
    headless: bool = True

    @classmethod
    def desde_json(cls, ruta: str | Path) -> "MonitorConfig":
        """Levanta un config_ejemplo.json y lo hidrata a dataclasses."""
        crudo = json.loads(Path(ruta).read_text(encoding="utf-8"))
        targets = [
            MonitorTarget(
                nombre=t["nombre"],
                platform=Platform(t["platform"]),
                url=t["url"],
                keywords=t.get("keywords", []),
                html_local=t.get("html_local"),
            )
            for t in crudo.get("targets", [])
        ]
        return cls(
            marca=crudo["marca"],
            targets=targets,
            umbral_negativo=crudo.get("umbral_negativo", 0.25),
            carpeta_estados=crudo.get("carpeta_estados", "estados"),
            carpeta_informes=crudo.get("carpeta_informes", "informes"),
            carpeta_exports=crudo.get("carpeta_exports", "exports"),
            headless=crudo.get("headless", True),
        )
