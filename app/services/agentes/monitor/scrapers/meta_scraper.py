# app/services/agentes/monitor/scrapers/meta_scraper.py
"""
Scraper de la familia Meta (Facebook e Instagram).
Estrategia en dos patas, siempre en este orden:
1. Intento por URL (Playwright headless vía ScraperService).
2. Plan B: export "Página web, solo HTML" desde sesión logueada.
INTEGRACIÓN: si hay ScraperService inyectado, el parseo y las métricas se
delegan al parser YA CALIBRADO del proyecto (_extraer_comentarios /
_extraer_stats), el mismo que usa el flujo web del Plan Plata. Así el
monitor no duplica filtros de ruido ni selectores.
"""
from __future__ import annotations

import logging
import re
from pathlib import Path

from bs4 import BeautifulSoup

from ..config.monitor_config import MonitorTarget
from .base import BloqueoDetectado, ComentarioCrudo, ScrapedData

log = logging.getLogger("monitor.marca")

# Señales de que Meta nos mandó al login wall (lección 1).
_SENALES_BLOQUEO = (
    "se limitaron los comentarios",
    "inicia sesión",
    "log in or sign up",
)

# URL ficticia por red: solo para que el parser calibrado detecte la plataforma.
_URL_FALSA = {
    "facebook": "https://facebook.com/guardada",
    "instagram": "https://instagram.com/p/guardada",
    "x": "https://x.com/guardado",
}

# Por debajo de esto, lo que vino de la URL es login wall / basura.
MIN_COMENTARIOS = 5


class MetaScraper:
    """Extrae comentarios de un post/hilo de Facebook o Instagram."""

    def __init__(self, scraper_service: object = None) -> None:
        self._scraper = scraper_service

    # ------------------------------------------------------------- público
    def extraer(self, target: MonitorTarget) -> ScrapedData:
        """URL primero; si viene pelada o falla, Plan B sin discutir."""
        if self._scraper is not None:
            try:
                datos = self._extraer_por_url(target)
                if len(datos.comentarios) >= MIN_COMENTARIOS or not target.html_local:
                    return datos
                log.info("La URL trajo solo %d comentarios (login wall). Uso Plan B.",
                         len(datos.comentarios))
            except BloqueoDetectado:
                pass  # caemos al Plan B, que es el que no falla
            except Exception as e:  # cualquier falla de red/Playwright → Plan B
                log.warning("URL falló (%s). Pruebo Plan B.", str(e)[:150])
        if target.html_local:
            return self._extraer_de_html_local(target)
        raise BloqueoDetectado(
            f"{target.platform.value}: sin scraper vivo ni export Plan B "
            f"para '{target.nombre}'. Guardá el hilo desde tu sesión "
            f"(Ctrl+S → solo HTML) y subilo en el panel."
        )

    # ----------------------------------------------------------------- URL
    def _extraer_por_url(self, target: MonitorTarget) -> ScrapedData:
        html = self._scraper.obtener_html(target.url, headless=True)
        bajo = html.lower()
        if any(senal in bajo for senal in _SENALES_BLOQUEO):
            raise BloqueoDetectado(f"Login wall / límite de comentarios en {target.url}")
        return self._parsear(html, metodo="url", platform=target.platform.value)

    # -------------------------------------------------------------- Plan B
    def _extraer_de_html_local(self, target: MonitorTarget) -> ScrapedData:
        ruta = Path(target.html_local)
        if not ruta.exists():
            raise BloqueoDetectado(f"No existe el export Plan B: {ruta}")
        html = ruta.read_text(encoding="utf-8", errors="ignore")
        # ✅ La red la manda el HTML, no lo que diga la marca (Porretti es IG, no FB)
        platform = target.platform.value
        if self._scraper is not None and hasattr(self._scraper, "detectar_red_desde_html"):
            soup = BeautifulSoup(html, "html.parser")
            platform = self._scraper.detectar_red_desde_html(soup, "") or platform
        datos = self._parsear(html, metodo="plan_b_html", platform=platform)
        datos.advertencias.append("Extracción vía export local (Plan B)")
        return datos

    # --------------------------------------------------------------- parse
    def _parsear(self, html: str, metodo: str, platform: str) -> ScrapedData:
        """Con ScraperService inyectado, usa el parser calibrado del proyecto."""
        if self._scraper is not None:
            soup = BeautifulSoup(html, "html.parser")
            crudos = self._scraper._extraer_comentarios(
                soup, _URL_FALSA.get(platform, _URL_FALSA["facebook"])
            )
            comentarios = [
                ComentarioCrudo(autor=c.get("usuario", "autor-desconocido"), texto=c["texto"])
                for c in crudos
            ]
            try:
                metricas = self._scraper._extraer_stats(soup, platform)
            except Exception:  # las métricas son opcionales
                metricas = {}
            return ScrapedData(comentarios=comentarios, metricas=metricas, metodo=metodo)

        # Fallback sin ScraperService (tests sueltos): dir="auto" + ruido básico.
        soup = BeautifulSoup(html, "lxml")
        comentarios = []
        vistos = set()
        nodos = [n for n in soup.select('[dir="auto"]') if n.get_text(strip=True)]
        for nodo in nodos:
            texto = nodo.get_text(" ", strip=True)
            if not texto or self._es_ruido(texto):
                continue
            autor = self._autor_cercano(nodo)
            clave = (autor, texto[:120])
            if clave in vistos:
                continue
            vistos.add(clave)
            comentarios.append(ComentarioCrudo(autor=autor, texto=texto))
        return ScrapedData(comentarios=comentarios, metodo=metodo)

    # ------------------------------------------------------------- helpers
    @staticmethod
    def _es_ruido(texto: str) -> bool:
        patrones = (
            r"^Puede ser una imagen de",
            r"^Les gusta a \w+",
            r"^(Me gusta|Responder|Compartir|Ver más|Editar)$",
            r"^(Todos los comentarios|Más relevantes|Filtros)$",
            r"^\d+\s*(min|h|d|sem)\b\.?$",
        )
        return any(re.match(p, texto, re.I) for p in patrones)

    @staticmethod
    def _autor_cercano(nodo) -> str:
        enlace = nodo.find_previous("a", attrs={"aria-label": True})
        if enlace:
            return enlace["aria-label"].strip()
        fuerte = nodo.find_previous(["strong", "span"], attrs={"role": "link"})
        return fuerte.get_text(strip=True) if fuerte else "autor-desconocido"