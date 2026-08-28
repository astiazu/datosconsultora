# app/services/agentes/monitor/reporters/informe.py
"""
Informe detallado en Markdown: informes/informe_{slug}_{fecha}.md

Pensado para que lo lea un consultor apurado: resumen ejecutivo arriba,
evidencia abajo. Se regenera en cada corrida con cambios.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from ..analyzers.evolucion import ResultadoComparacion
from ..config.monitor_config import MonitorConfig, MonitorTarget
from ..scrapers.base import ScrapedData


def escribir_informe(
    config: MonitorConfig,
    target: MonitorTarget,
    r: ResultadoComparacion,
    scrape: ScrapedData,
) -> str:
    """Arma el .md y lo deja en carpeta_informes. Devuelve la ruta."""
    fecha = datetime.now().strftime("%Y-%m-%d")
    carpeta = Path(config.carpeta_informes)
    carpeta.mkdir(parents=True, exist_ok=True)
    ruta = carpeta / f"informe_{target.slug}_{fecha}.md"

    l: list[str] = [
        f"# Informe de evolución — {target.nombre}",
        "",
        f"**Marca:** {config.marca} · **Red:** {target.platform.value} · **Fecha:** {fecha}",
        f"**Método de extracción:** {scrape.metodo} · **Comentarios:** {len(scrape.comentarios)}",
        f"**Estado anterior:** {r.estado_anterior_fecha or 'primera corrida'}",
        "",
        "## Resumen ejecutivo",
        "",
        f"- Comentarios nuevos: **{len(r.nuevos)}**"
        + (f" · eliminados: {r.eliminados}" if r.eliminados else ""),
        f"- Sentimiento positivo: {r.sentimiento_anterior.get('positivo', 0):.1f}% → "
        f"**{r.sentimiento_actual.get('positivo', 0):.1f}%** "
        f"(Δ {r.delta_positivo:+.1f} pts)",
    ]

    for riesgo in r.riesgos:
        l.append(f"- **▲ Riesgo:** {riesgo['titulo']} · {riesgo['severidad']} · {riesgo['detalle']}")

    l += ["", "| Autor | Comentario | Sentimiento | Likes |", "|---|---|---|---|"]
    for c in r.nuevos:
        texto = c.texto.replace("|", "/")[:110]
        l.append(f"| {c.autor} | {texto} | {c.sentimiento} | {c.likes} |")

    l += [
        "",
        "---",
        "Generado por MonitorAgent · MIC (Groq gpt-oss-20b) · DatosConsultora",
    ]
    ruta.write_text("\n".join(l), encoding="utf-8")
    return str(ruta)
