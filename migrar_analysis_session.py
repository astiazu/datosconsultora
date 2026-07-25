# migrar_analysis_session.py
"""
Script para crear la tabla analysis_session en la base de datos de producción.
Ejecutar UNA VEZ después de hacer deploy con los cambios.
"""
from app import create_app, db

app = create_app()

with app.app_context():
    # Crear la tabla si no existe
    db.engine.execute("""
        CREATE TABLE IF NOT EXISTS analysis_session (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES user(id),
            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            red_social VARCHAR(50),
            contexto VARCHAR(500),
            total_comentarios INTEGER,
            resultado_json TEXT
        )
    """)
    print("✅ Tabla analysis_session creada exitosamente")
    
    # Agregar plan Free si no existe
    from app.models import Plan
    if not Plan.query.filter_by(nombre='free').first():
        plan_free = Plan(
            nombre='free',
            display_name='Free',
            descripcion='Plan de prueba para conocer la plataforma.',
            precio_mensual=0.0,
            precio_anual=0.0,
            precio_lifetime=0.0,
            es_lifetime=False,
            activo=True,
            orden=0,
            incluye_historial=False,
            incluye_motor_semantico=False,
            incluye_agentes=False,
            incluye_actividad_completa=False,
            limite_transcripciones_mes=3,
            limite_analisis_mes=2,
            icono='bi-gift-fill',
            color='info'
        )
        db.session.add(plan_free)
        db.session.commit()
        print("✅ Plan Free agregado exitosamente")
    else:
        print("ℹ️ Plan Free ya existe")