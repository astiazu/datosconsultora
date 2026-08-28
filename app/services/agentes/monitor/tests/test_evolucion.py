# app/services/agentes/monitor/tests/test_evolucion.py
"""
Tests del comparador: la parte que no puede fallar en producción.

Corren sin Playwright, sin Groq y sin red: solo dataclasses y JSON.
"""
from pathlib import Path

from app.services.agentes.monitor.analyzers.evolucion import (
    ComparadorEvolucion,
    ComentarioAnalizado,
    huella,
)
from app.services.agentes.monitor.config.monitor_config import (
    MonitorTarget,
    Platform,
)


def _target() -> MonitorTarget:
    return MonitorTarget(
        nombre="Café Aurora",
        platform=Platform.FACEBOOK,
        url="https://facebook.com/cafeaurora",
    )


def test_huella_estable_ante_ruido():
    """Mismo comentario con distinto ruido de DOM → misma huella."""
    assert huella(" Ana ", "  el café  está  bueno ") == huella(
        "ana", "el café está bueno"
    )


def test_primera_corrida_marca_todo_nuevo(tmp_path):
    comp = ComparadorEvolucion(carpeta_estados=tmp_path)
    comentarios = [
        ComentarioAnalizado(huella("ana", "buenísimo"), "ana", "buenísimo", "positivo")
    ]
    r = comp.comparar(_target(), comentarios, riesgos=[])
    assert not r.sin_novedades
    assert len(r.nuevos) == 1
    assert r.estado_anterior_fecha is None


def test_sin_novedades_cuando_no_cambia_nada(tmp_path):
    comp = ComparadorEvolucion(carpeta_estados=tmp_path)
    comentarios = [
        ComentarioAnalizado(huella("ana", "buenísimo"), "ana", "buenísimo", "positivo")
    ]
    dist = {"positivo": 100.0, "neutro": 0.0, "negativo": 0.0}
    comp.comparar(_target(), comentarios, riesgos=[])
    comp.guardar_estado(_target(), comentarios, dist, [])

    r2 = comp.comparar(_target(), comentarios, riesgos=[])
    assert r2.sin_novedades
    assert (Path(tmp_path) / "estado_cafe_aurora.json").exists()


def test_riesgo_nuevo_rompe_el_sin_novedades(tmp_path):
    comp = ComparadorEvolucion(carpeta_estados=tmp_path)
    comentarios = [
        ComentarioAnalizado(huella("ana", "buenísimo"), "ana", "buenísimo", "positivo")
    ]
    dist = {"positivo": 100.0, "neutro": 0.0, "negativo": 0.0}
    comp.guardar_estado(_target(), comentarios, dist, [])

    riesgo = {"titulo": "Queja recurrente: envío", "severidad": "media",
              "detalle": "3 comentarios"}
    r = comp.comparar(_target(), comentarios, riesgos=[riesgo])
    assert not r.sin_novedades
