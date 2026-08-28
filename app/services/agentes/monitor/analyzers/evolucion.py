# app/services/agentes/monitor/analyzers/evolucion.py
"""
Comparación contra el estado anterior + detección de evolución.

Decisión documentada: el estado vive en estado_{slug}.json (un archivo
por target). Cuando el monitor sea multiusuario migra a una tabla tipo
ExpedienteMonitoreo del módulo judicial; el contrato del comparador no
cambia, solo cambia el backend de guardar/cargar.

El comparador es puro: entra estado viejo + comentarios nuevos, sale
un ResultadoComparacion. Cero I/O salvo el JSON de estado → testeable.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


def huella(autor: str, texto: str) -> str:
    crudo = f"{autor.strip().lower()}::{' '.join(texto.split()).lower()}"
    return hashlib.sha256(crudo.encode("utf-8")).hexdigest()[:24]

@dataclass
class ComentarioAnalizado:
    """Comentario con sentimiento asignado por el MIC."""

    huella: str
    autor: str
    texto: str
    sentimiento: str  # positivo | neutro | negativo
    likes: int = 0


@dataclass
class ResultadoComparacion:
    """Todo lo que cambió (o no) respecto del estado anterior."""

    marca: str
    sin_novedades: bool
    nuevos: List[ComentarioAnalizado] = field(default_factory=list)
    eliminados: int = 0
    sentimiento_actual: Dict[str, float] = field(default_factory=dict)
    sentimiento_anterior: Dict[str, float] = field(default_factory=dict)
    cobertura: Dict[str, int] = field(default_factory=dict)
    riesgos: List[dict] = field(default_factory=list)
    estado_anterior_fecha: Optional[str] = None

    @property
    def delta_positivo(self) -> float:
        return self.sentimiento_actual.get(
            "positivo", 0.0
        ) - self.sentimiento_anterior.get("positivo", 0.0)


class ComparadorEvolucion:
    """Carga/guarda estado_{slug}.json y lo compara contra lo nuevo."""

    def __init__(self, carpeta_estados: str = "estados") -> None:
        self.carpeta = Path(carpeta_estados)
        self.carpeta.mkdir(parents=True, exist_ok=True)

    def cargar_estado(self, target) -> Optional[dict]:
        """Estado guardado anterior; None si es la primera corrida."""
        ruta = self.carpeta / target.archivo_estado
        if not ruta.exists():
            return None
        return json.loads(ruta.read_text(encoding="utf-8"))

    def comparar(
        self,
        target,
        comentarios: List[ComentarioAnalizado],
        riesgos: List[dict],
    ) -> ResultadoComparacion:
        """Núcleo del agente: qué es nuevo, qué desapareció, qué se movió."""
        anterior = self.cargar_estado(target)

        if anterior is None:
            # Primera corrida: todo es "nuevo", pero no es una alarma.
            return ResultadoComparacion(
                marca=target.nombre,
                sin_novedades=False,
                nuevos=comentarios,
                sentimiento_actual=self._distribucion(comentarios),
                riesgos=riesgos,
                cobertura=self._cobertura(comentarios),
            )

        conocidas = {c["huella"] for c in anterior.get("comentarios", [])}
        nuevos = [c for c in comentarios if c.huella not in conocidas]
        eliminados = len(conocidas - {c.huella for c in comentarios})

        dist_actual = self._distribucion(comentarios)
        dist_anterior = anterior.get("sentimiento", {})
        riesgos_previos = {r["titulo"] for r in anterior.get("riesgos", [])}

        # "Sin novedades" = nada nuevo, nada perdido, sentimiento estable
        # (±1 pt de ruido) y ningún riesgo que no estuviera ya anotado.
        sin_novedades = (
            not nuevos
            and eliminados == 0
            and not any(r["titulo"] not in riesgos_previos for r in riesgos)
            and abs(dist_actual.get("positivo", 0.0)
                    - dist_anterior.get("positivo", 0.0)) < 1.0
        )

        return ResultadoComparacion(
            marca=target.nombre,
            sin_novedades=sin_novedades,
            nuevos=nuevos,
            eliminados=eliminados,
            sentimiento_actual=dist_actual,
            sentimiento_anterior=dist_anterior,
            riesgos=riesgos,
            estado_anterior_fecha=anterior.get("fecha"),
            cobertura=self._cobertura(comentarios),
        )

    def guardar_estado(self, target, comentarios, sentimiento, riesgos) -> Path:
        """Pisa estado_{slug}.json con la foto nueva (el 'guardado' del patrón)."""
        payload = {
            "marca": target.nombre,
            "platform": target.platform.value,
            "fecha": datetime.now().isoformat(timespec="seconds"),
            "menciones": len(comentarios),
            "sentimiento": sentimiento,
            "comentarios": [
                {"huella": c.huella, "autor": c.autor, "texto": c.texto,
                 "sentimiento": c.sentimiento, "likes": c.likes}
                for c in comentarios
            ],
            "riesgos": riesgos,
            "cobertura": self._cobertura(comentarios),
        }
        ruta = self.carpeta / target.archivo_estado
        ruta.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return ruta

    @staticmethod
    def _distribucion(comentarios: List[ComentarioAnalizado]) -> Dict[str, float]:
        """Porcentajes sobre los REALMENTE analizados (excluye no_analizado)."""
        validos = [c for c in comentarios if c.sentimiento in ("positivo", "neutro", "negativo")]
        cuentas = {"positivo": 0, "neutro": 0, "negativo": 0}
        for c in validos:
            cuentas[c.sentimiento] += 1
        total = len(validos) or 1
        return {k: round(v / total * 100, 1) for k, v in cuentas.items()}

    @staticmethod
    def _cobertura(comentarios: List[ComentarioAnalizado]) -> Dict[str, int]:
        """Cuántos comentarios quedaron afuera por falla de IA."""
        return {
            "total": len(comentarios),
            "analizados": len([c for c in comentarios if c.sentimiento != "no_analizado"]),
        }
