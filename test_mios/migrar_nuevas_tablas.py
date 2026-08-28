# migrar_nuevas_tablas.py
"""
Script para crear las tablas nuevas y el plan Free en producción.
Ejecutar UNA VEZ en la Shell de Render.
"""
from app import create_app, db
from sqlalchemy import text

app = create_app()

with app.app_context():
    # ============================================
    # 1. Crear tabla analysis_session
    # ============================================
    with db.engine.connect() as conn:
        result = conn.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'analysis_session'
            )
        """))
        if not result.scalar():
            conn.execute(text("""
                CREATE TABLE analysis_session (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER REFERENCES "user"(id),
                    fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    red_social VARCHAR(50),
                    contexto VARCHAR(500),
                    total_comentarios INTEGER,
                    resultado_json TEXT
                )
            """))
            conn.commit()
            print("✅ Tabla analysis_session creada")
        else:
            print("ℹ️ analysis_session ya existe")

    # ============================================
    # 2. Crear tablas de agentes judiciales
    # ============================================
    with db.engine.connect() as conn:
        result = conn.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'expediente_monitoreado'
            )
        """))
        if not result.scalar():
            conn.execute(text("""
                CREATE TABLE expediente_monitoreado (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES "user"(id),
                    jurisdiccion VARCHAR(50) NOT NULL,
                    nombre VARCHAR(200) NOT NULL,
                    parametros_json TEXT DEFAULT '{}',
                    activo BOOLEAN DEFAULT TRUE,
                    creado TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.execute(text("""
                CREATE TABLE expediente_estado (
                    id SERIAL PRIMARY KEY,
                    expediente_monitoreado_id INTEGER NOT NULL REFERENCES expediente_monitoreado(id),
                    expediente_id_externo VARCHAR(100),
                    caratula VARCHAR(300),
                    estado VARCHAR(200),
                    fecha_inicio VARCHAR(100),
                    ultima_novedad VARCHAR(300),
                    actualizado TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.execute(text("""
                CREATE TABLE sesion_jurisdiccion (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES "user"(id),
                    jurisdiccion VARCHAR(50) NOT NULL,
                    storage_state_json TEXT,
                    actualizado TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expirada BOOLEAN DEFAULT FALSE,
                    CONSTRAINT uq_sesion_user_jurisdiccion UNIQUE (user_id, jurisdiccion)
                )
            """))
            conn.commit()
            print("✅ Tablas de agentes creadas")
        else:
            print("ℹ️ Tablas de agentes ya existen")

    # ============================================
    # 3. Crear plan Free si no existe
    # ============================================
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
        print("✅ Plan Free creado")
    else:
        print("ℹ️ Plan Free ya existe")

    print("\n🎉 Migración completada")

