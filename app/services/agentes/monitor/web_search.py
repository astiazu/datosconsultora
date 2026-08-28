# app/services/agentes/monitor/web_search.py
"""
Paneo de web abierta para la corrida inicial del monitor.
Búsqueda PROFUNDA en 3 capas:
1. Nombre exacto + keywords del operador.
2. Nombre + sufijos de escándalo/denuncia/causa.
3. MOCHILA FAMILIAR: búsquedas por APELLIDO con sufijos duros.
   Los escándalos de un padre/madre viven bajo el apellido, no bajo
   el nombre del candidato: buscar solo "Martin Porretti" NUNCA
   encuentra la nota de "Roberto Porretti".
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

log = logging.getLogger("monitor.marca")


@dataclass
class ResultadoWeb:
    titulo: str
    url: str
    snippet: str


@dataclass
class BarridoResult:
    query: str
    resultados: list[ResultadoWeb] = field(default_factory=list)
    error: str | None = None


_SUFIJOS_NOMBRE = ["escándalo", "denuncia acusación", "causa judicial procesado"]
_SUFIJOS_APELLIDO = [
    "escándalo OR denuncia OR causa OR coimas",
    "muerte OR procesado OR cámara oculta",
]
MAX_QUERIES = 10


def _apellido(nombre: str) -> str:
    partes = nombre.strip().split()
    return partes[-1] if partes else ""


def barrido_web(nombre: str, keywords=None, max_por_query=5, profundo=True):
    queries = [f'"{nombre}"']
    for kw in (keywords or [])[:2]:
        queries.append(f'"{nombre}" {kw}')
    if profundo:
        for suf in _SUFIJOS_NOMBRE:
            queries.append(f'"{nombre}" {suf}')
        ap = _apellido(nombre)
        if ap:
            for suf in _SUFIJOS_APELLIDO:
                queries.append(f'"{ap}" {suf}')
    queries = list(dict.fromkeys(queries))[:MAX_QUERIES]

    try:
        from ddgs import DDGS
    except ImportError:
        try:
            from duckduckgo_search import DDGS
        except ImportError:
            log.warning("ddgs no instalado: se omite el paneo web")
            return [BarridoResult(query=q, error="ddgs no instalado") for q in queries]

    resultados = []
    for q in queries:
        try:
            with DDGS() as ddgs:
                raw = list(ddgs.text(q, max_results=max_por_query))
            resultados.append(BarridoResult(
                query=q,
                resultados=[
                    ResultadoWeb(titulo=r.get("title", ""), url=r.get("href", ""),
                                 snippet=r.get("body", ""))
                    for r in raw
                ],
            ))
        except Exception as e:
            log.warning("Paneo web falló para '%s': %s", q, str(e)[:120])
            resultados.append(BarridoResult(query=q, error=str(e)[:200]))
    return resultados


def resumen_para_prompt(barridos, max_caracteres=3500):
    lineas = []
    for b in barridos:
        if b.error or not b.resultados:
            lineas.append(f'Consulta "{b.query}": sin resultados.')
            continue
        lineas.append(f'Consulta "{b.query}" ({len(b.resultados)} resultados):')
        for r in b.resultados:
            snippet_corto = (r.snippet[:150] + "...") if len(r.snippet) > 150 else r.snippet
            lineas.append(f"- {r.titulo} | {snippet_corto}")
    resultado = "\n".join(lineas)
    if len(resultado) > max_caracteres:
        log.warning("⚠️ Paneo web muy largo (%d chars), truncando a %d",
                    len(resultado), max_caracteres)
        resultado = resultado[:max_caracteres] + "\n[... truncado ...]"
    return resultado


# ─────────────────────────────────────────────────────────────
barrido_inicial = barrido_web
# ─────────────────────────────────────────────────────────────