# app/utils/logs.py
"""
Helper centralizado para registrar actividad en ActivityLog.

Antes este mismo bloque (crear ActivityLog, add, commit) se repetía
textualmente en casi cada vista de admin.py y auth.py. Centralizarlo acá
evita divergencias (por ejemplo, olvidarse de guardar la IP en algún lado)
y hace más simple agregar nuevos tipos de log en el futuro.
"""

from app import db
from app.models import ActivityLog


def registrar_log(user_id, accion, detalle, request):
    """Crea y guarda un ActivityLog.

    :param user_id: id del usuario relacionado con la acción (puede ser None
                     para intentos fallidos de login con email inexistente).
    :param accion: string corto que identifica el tipo de acción (ej: "login").
    :param detalle: descripción legible de lo que pasó.
    :param request: objeto request de Flask, para extraer la IP.
    """
    log = ActivityLog(
        user_id=user_id,
        accion=accion,
        detalle=detalle,
        ip=request.remote_addr,
    )
    db.session.add(log)
    db.session.commit()
    return log
