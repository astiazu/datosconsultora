# migrar_analysis_session.py
"""
Script para crear la tabla analysis_session en la base de datos de producción.
Ejecutar UNA VEZ después de hacer deploy con los cambios.
Compatible con SQLAlchemy 2.0+
"""
from app import create_app, db
from sqlalchemy import text

app = create_app()

with app.app_context():
    # ============================================
    # 1. Crear la tabla analysis_session
    # ============================================
    try:
        with db.engine.connect() as conn:
            # Verificar si la tabla ya existe
            result = conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'analysis_session'
                )
            """))
            tabla_existe = result.scalar()
            
            if not tabla_existe:
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
                print("✅ Tabla analysis_session creada exitosamente")
            else:
                print("ℹ️ La tabla analysis_session ya existe")
    except Exception as e:
        print(f"❌ Error creando tabla: {e}")
        import traceback
        traceback.print_exc()
    
    # ============================================
    # 2. Agregar plan Free si no existe
    # ============================================
    try:
        from app.models import Plan
        plan_free = Plan.query.filter_by(nombre='free').first()
        
        if not plan_free:
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
    except Exception as e:
        print(f"❌ Error creando plan Free: {e}")
        db.session.rollback()
        import traceback
        traceback.print_exc()
    
    # ============================================
    # 3. Verificación final
    # ============================================
    print("\n📊 Estado actual de la BD:")
    try:
        from app.models import Plan
        planes = Plan.query.all()
        print(f"   - Planes disponibles: {len(planes)}")
        for p in planes:
            print(f"     • {p.display_name} (orden: {p.orden})")
    except Exception as e:
        print(f"   ⚠️ No se pudo verificar planes: {e}")
    
    print("\n🎉 ¡Migración completada!")