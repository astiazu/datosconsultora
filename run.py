# run.py - REEMPLAZAR COMPLETO
from app import create_app, init_db

app = create_app()
init_db(app)  # ← Ahora pasa 'app' como argumento

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
    