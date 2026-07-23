# migrar_db_planes.py
"""
Script para migrar la BD agregando la tabla Plan y los campos nuevos en UserPlan.
Ejecutar UNA VEZ en Render vía Shell.
"""
from app import create_app, db
from sqlalchemy import text

app = create_app()


def migrar():
    with app.app_context():
        print("🔧 Iniciando migración de planes...")
        engine_name = db.engine.name
        
        if engine_name in ("postgresql", "postgres"):
            print("🌐 PostgreSQL detectado")
            
            # 1. Crear tabla Plan si no existe
            check = text("SELECT table_name FROM information_schema.tables WHERE table_name='plan'")
            if not db.session.execute(check).fetchone():
                print("➕ Creando tabla plan...")
                db.session.execute(text("""
                    CREATE TABLE plan (
                        id SERIAL PRIMARY KEY,
                        nombre VARCHAR(50) UNIQUE NOT NULL,
                        display_name VARCHAR(100) NOT NULL,
                        descripcion TEXT DEFAULT '',
                        precio_mensual FLOAT DEFAULT 0.0,
                        precio_anual FLOAT DEFAULT 0.0,
                        precio_lifetime FLOAT,
                        es_lifetime BOOLEAN DEFAULT FALSE,
                        activo BOOLEAN DEFAULT TRUE,
                        orden INTEGER DEFAULT 0,
                        incluye_historial BOOLEAN DEFAULT FALSE,
                        incluye_motor_semantico BOOLEAN DEFAULT FALSE,
                        incluye_agentes BOOLEAN DEFAULT FALSE,
                        incluye_actividad_completa BOOLEAN DEFAULT FALSE,
                        limite_transcripciones_mes INTEGER DEFAULT 5,
                        limite_analisis_mes INTEGER DEFAULT 3,
                        icono VARCHAR(50) DEFAULT 'bi-award',
                        color VARCHAR(20) DEFAULT 'secondary'
                    )
                """))
                db.session.commit()
                print("✅ Tabla plan creada")
            else:
                print("✅ Tabla plan ya existe")
            
            # 2. Agregar columnas nuevas a user_plan
            columnas_nuevas = [
                ("plan_id", "INTEGER"),
                ("fecha_inicio", "TIMESTAMP"),
                ("fecha_fin", "TIMESTAMP"),
                ("es_lifetime", "BOOLEAN DEFAULT FALSE"),
                ("fecha_expiracion_cafecito", "TIMESTAMP"),
                ("consumo_transcripciones", "INTEGER DEFAULT 0"),
                ("consumo_analisis", "INTEGER DEFAULT 0"),
                ("limite_transcripciones", "INTEGER DEFAULT 5"),
                ("limite_analisis", "INTEGER DEFAULT 3"),
            ]
            
            for col_name, col_type in columnas_nuevas:
                check_col = text(f"""
                    SELECT column_name FROM information_schema.columns 
                    WHERE table_name='user_plan' AND column_name='{col_name}'
                """)
                if not db.session.execute(check_col).fetchone():
                    print(f"➕ Agregando columna {col_name}...")
                    db.session.execute(text(f"ALTER TABLE user_plan ADD COLUMN {col_name} {col_type}"))
                    db.session.commit()
                else:
                    print(f"✅ Columna {col_name} ya existe")
            
            # 3. Insertar los 4 planes por defecto
            from app.services.plan_service import inicializar_planes_por_defecto
            inicializar_planes_por_defecto()
            
        else:
            print(f"💾 SQLite detectado - usando db.create_all()")
            db.create_all()
            from app.services.plan_service import inicializar_planes_por_defecto
            inicializar_planes_por_defecto()
        
        print("\n🎉 ¡Migración completada!")


if __name__ == "__main__":
    migrar()