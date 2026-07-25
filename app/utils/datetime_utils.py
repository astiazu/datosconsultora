# app/utils/datetime_utils.py
from datetime import datetime, timezone

def utc_now():
    """
    Devuelve la fecha/hora actual en UTC como datetime naive.
    Reemplaza a datetime.utcnow() que está deprecado en Python 3.12+.
    
    Usamos .replace(tzinfo=None) para mantener compatibilidad con SQLAlchemy
    y evitar problemas de comparación entre timezone-aware y naive datetimes.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)