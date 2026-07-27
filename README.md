# DatosConsultora – App Python

Flask + Flask-Login + SQLAlchemy
Colores: azul petróleo #004d5c / gris peltre #8a8d93

pip install -r requirements.txt
python run.py
http://localhost:5000

Configurá en `.env` como mínimo `SECRET_KEY` y `ADMIN_PASSWORD`; nunca uses
credenciales de ejemplo en producción. Para Mercado Pago también se requieren
`MP_ACCESS_TOKEN` y `MP_WEBHOOK_SECRET`.

Features:
- Login de clientes, solo cuentas activas entran al panel
- /dashboard: subir audio/video para transcribir
  Hook listo para Whisper: pip install openai-whisper
- /admin/perfil: editar hasta 3 emails, WhatsApp y teléfono fijo
- Botón WhatsApp flotante: https://wa.me/{{numero}} – se actualiza solo
