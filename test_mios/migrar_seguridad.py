"""Migración puntual para la corrección de pagos seguros.

Ejecutar una única vez por entorno, antes de desplegar la versión nueva:
    python migrar_seguridad.py
"""
from sqlalchemy import inspect, text

from app import app, db

with app.app_context():
    columns = {column["name"] for column in inspect(db.engine).get_columns("donation")}
    if "external_reference" not in columns:
        db.session.execute(text("ALTER TABLE donation ADD COLUMN external_reference VARCHAR(100)"))
        db.session.execute(text("UPDATE donation SET external_reference = 'legacy-' || id WHERE external_reference IS NULL"))
        db.session.commit()
    print("Migración de seguridad completada.")
