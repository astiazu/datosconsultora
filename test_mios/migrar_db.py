# migrar_db.py
import os
from app import create_app, db
from sqlalchemy import text

app = create_app()

def migrar():
    with app.app_context():
        print("🔧 Iniciando migración de base de datos en Render...")
        try:
            # 1. Agregar columna a UserPlan si no existe
            check_col = text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='user_plan' AND column_name='fecha_expiracion_cafecito'
            """)
            result = db.session.execute(check_col).fetchone()
            
            if not result:
                print("➕ Agregando columna fecha_expiracion_cafecito a user_plan...")
                db.session.execute(text(
                    "ALTER TABLE user_plan ADD COLUMN fecha_expiracion_cafecito TIMESTAMP"
                ))
                db.session.commit()
                print("✅ Columna agregada correctamente")
            else:
                print("✅ La columna fecha_expiracion_cafecito ya existe")
            
            # 2. Crear tabla Donation si no existe
            check_table = text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_name='donation'
            """)
            result = db.session.execute(check_table).fetchone()
            
            if not result:
                print("➕ Creando tabla donation...")
                db.session.execute(text("""
                    CREATE TABLE donation (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER REFERENCES "user"(id),
                        monto FLOAT NOT NULL,
                        moneda VARCHAR(10) DEFAULT 'ARS',
                        mp_payment_id VARCHAR(100) UNIQUE,
                        mp_preference_id VARCHAR(100),
                        estado VARCHAR(50) DEFAULT 'pending',
                        mensaje VARCHAR(500) DEFAULT '',
                        fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))
                db.session.commit()
                print("✅ Tabla donation creada correctamente")
            else:
                print("✅ La tabla donation ya existe")
            
            print("\n🎉 ¡Migración completada exitosamente!")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error en la migración: {e}")
            raise

if __name__ == "__main__":
    migrar()