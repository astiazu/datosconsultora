# app/services/agentes/monitor_service.py
"""
Logica de negocio del modulo de agentes: comparar el estado nuevo contra el
guardado en la base (ExpedienteEstado) y armar el resumen de cambios.
Es deliberadamente independiente de Playwright: el worker (que si importa
Playwright y los proveedores) le pasa los datos ya extraidos.
"""

from app import db
from app.models import ExpedienteEstado

CAMPOS_A_COMPARAR = ("estado", "fecha_inicio", "ultima_novedad")


def obtener_estado_guardado(expediente_monitoreado_id: int, expediente_id_externo: str):
    return ExpedienteEstado.query.filter_by(
        expediente_monitoreado_id=expediente_monitoreado_id,
        expediente_id_externo=expediente_id_externo,
    ).first()


def guardar_o_actualizar_estado(expediente_monitoreado_id: int, datos: dict) -> ExpedienteEstado:
    from app.utils.datetime_utils import utc_now

    registro = obtener_estado_guardado(expediente_monitoreado_id, datos["id"])
    if registro is None:
        registro = ExpedienteEstado(
            expediente_monitoreado_id=expediente_monitoreado_id,
            expediente_id_externo=datos["id"],
        )
        db.session.add(registro)

    registro.caratula = datos.get("caratula")
    registro.estado = datos.get("estado")
    registro.fecha_inicio = datos.get("fecha_inicio")
    registro.ultima_novedad = datos.get("ultima_novedad")
    registro.actualizado = utc_now()

    db.session.commit()
    return registro


def comparar_con_guardado(anterior: ExpedienteEstado, actual: dict) -> list[str]:
    """Devuelve la lista de campos que cambiaron entre lo guardado y lo
    recien extraido. Lista vacia = sin novedades."""
    cambios = []
    for campo in CAMPOS_A_COMPARAR:
        valor_anterior = getattr(anterior, campo)
        valor_actual = actual.get(campo)
        if valor_anterior != valor_actual:
            cambios.append(f"{campo}: '{valor_anterior}' -> '{valor_actual}'")
    return cambios
