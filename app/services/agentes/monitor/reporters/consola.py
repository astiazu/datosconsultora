# app/services/agentes/monitor/reporters/consola.py
"""
Reporter de consola: muestra QUÉ CAMBIÓ, como pide la especificación.

ANSI puro, cero dependencias. En Render/cron esto va al log del worker;
en local se ve coloreado, igual que la salida del worker judicial.
"""
from ..analyzers.evolucion import ResultadoComparacion

_V = "\033[92m"  # verde → ok / comentarios nuevos
_A = "\033[93m"  # ámbar → atención / variaciones de sentimiento
_R = "\033[91m"  # rojo  → riesgos
_C = "\033[96m"  # cian  → datos sueltos
_X = "\033[0m"


def imprimir_cambios(r: ResultadoComparacion) -> None:
    """Lista de cambios con el nivel de detalle justo para la consola."""
    print(f"{_R}◆ CAMBIOS DETECTADOS{_X} · {r.marca}")

    if r.nuevos:
        por_sent = {
            s: sum(1 for c in r.nuevos if c.sentimiento == s)
            for s in ("positivo", "neutro", "negativo")
        }
        print(
            f"  {_V}+ {len(r.nuevos)} comentarios nuevos{_X} "
            f"({por_sent['positivo']} pos · {por_sent['neutro']} neu · "
            f"{por_sent['negativo']} neg)"
        )
        for c in r.nuevos[:5]:
            print(f"    {_C}·{_X} {c.autor}: “{c.texto[:90]}” [{c.sentimiento}]")
        if len(r.nuevos) > 5:
            print(f"    … y {len(r.nuevos) - 5} más (detalle en el informe)")

    if r.cobertura and r.cobertura.get("analizados", 0) < r.cobertura.get("total", 0):
        print(f"  {_A}◐ cobertura: {r.cobertura['analizados']}/{r.cobertura['total']} "
              f"comentarios analizados (el resto quedó sin IA por rate limit){_X}")
        
    if r.eliminados:
        print(f"  {_A}− {r.eliminados} comentarios dejaron de aparecer{_X}")

    delta = r.delta_positivo
    if abs(delta) >= 1.0:
        flecha = "▼" if delta < 0 else "▲"
        print(
            f"  {_A}~ sentimiento positivo: "
            f"{r.sentimiento_anterior.get('positivo', 0):.0f}% → "
            f"{r.sentimiento_actual.get('positivo', 0):.0f}% "
            f"({flecha} {abs(delta):.0f} pts){_X}"
        )

    for riesgo in r.riesgos:
        print(f"  {_R}▲ RIESGO: {riesgo['titulo']} · {riesgo['detalle']}{_X}")


def imprimir_sin_novedades(nombre: str) -> None:
    """El caso feliz: no pasó nada, y está bien decirlo cortito."""
    print(f"{_V}■ {nombre}: SIN NOVEDADES{_X} (0 cambios vs. estado anterior)")
