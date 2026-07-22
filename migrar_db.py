# migrar.py
from app import create_app, init_db

app = create_app()
init_db(app)

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.migrar(host="0.0.0.0", port=port, debug=False)
# migrar_db.py
"""
Script para migrar la base de datos de Render agregando columnas y tablas faltantes.
Ejecutar una sola vez después de agregar Donation y UserPlan.fecha_expiracion_cafecito
"""
import os
from app import create_app, db
from sqlalchemy import text

app = create_app()

def migrar():
    with app.app_context():
        print("🔧 Iniciando migración de base de datos...")
        
        # Verificar qué motor estamos usando
        engine_name = db.engine.name
        print(f"📦 Motor: {engine_name}")
        
        if engine_name == "postgresql" or engine_name.startswith("postgresql"):
            # PostgreSQL (Render)
            print("🌐 Ejecutando migración para PostgreSQL...")
            
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
                    print("✅ Columna agregada")
                else:
                    print("✅ Columna fecha_expiracion_cafecito ya existe")
                
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
                    print("✅ Tabla donation creada")
                else:
                    print("✅ Tabla donation ya existe")
                
                print("\n🎉 Migración completada exitosamente!")
                
            except Exception as e:
                db.session.rollback()
                print(f"❌ Error en migración: {e}")
                raise
                
        elif engine_name == "sqlite":
            # SQLite (local)
            print("💾 Ejecutando migración para SQLite...")
            
            try:
                import sqlite3
                db_path = app.config["SQLALCHEMY_DATABASE_URI"].replace("sqlite:///", "")
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                
                # 1. Agregar columna a UserPlan si no existe
                cursor.execute("PRAGMA table_info(user_plan)")
                columns = [col[1] for col in cursor.fetchall()]
                
                if 'fecha_expiracion_cafecito' not in columns:
                    print("➕ Agregando columna fecha_expiracion_cafecito...")
                    cursor.execute("ALTER TABLE user_plan ADD COLUMN fecha_expiracion_cafecito TIMESTAMP")
                    conn.commit()
                    print("✅ Columna agregada")
                else:
                    print("✅ Columna ya existe")
                
                # 2. Crear tabla Donation si no existe
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='donation'")
                if not cursor.fetchone():
                    print("➕ Creando tabla donation...")
                    cursor.execute("""
                        CREATE TABLE donation (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            user_id INTEGER REFERENCES user(id),
                            monto REAL NOT NULL,
                            moneda TEXT DEFAULT 'ARS',
                            mp_payment_id TEXT UNIQUE,
                            mp_preference_id TEXT,
                            estado TEXT DEFAULT 'pending',
                            mensaje TEXT DEFAULT '',
                            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    """)
                    conn.commit()
                    print("✅ Tabla donation creada")
                else:
                    print("✅ Tabla donation ya existe")
                
                conn.close()
                print("\n🎉 Migración completada exitosamente!")
                
            except Exception as e:
                print(f"❌ Error en migración: {e}")
                raise
        else:
            print(f"⚠️ Motor no soportado: {engine_name}")


if __name__ == "__main__":
    migrar()