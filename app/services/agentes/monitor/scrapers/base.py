# app/services/agentes/monitor/scrapers/base.py
"""
Contrato base de los scrapers del monitor.

Cada familia de red implementa extraer(target) → ScrapedData y el
agente no se entera de selectores ni de bloqueos: solo consume este
contrato. Es el mismo patrón que proveedores/<jurisdiccion>.py del
módulo judicial (preparar_pagina / extraer).
"""
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class ComentarioCrudo:
    """Un comentario tal cual salió del HTML, ya limpiado de ruido de UI."""

    autor: str
    texto: str
    likes: int = 0
    fecha: Optional[str] = None  # lo que la red muestre: "2 h", "1 d"…


@dataclass
class ScrapedData:
    """Resultado de una extracción. El campo 'metodo' documenta cómo se obtuvo."""

    comentarios: List[ComentarioCrudo] = field(default_factory=list)
    metricas: dict = field(default_factory=dict)  # likes/shares del post, si vinieron
    metodo: str = "url"  # "url" | "plan_b_html"
    advertencias: List[str] = field(default_factory=list)


class BloqueoDetectado(Exception):
    """La red cortó la extracción: login wall, límites, DOM virtualizado."""
