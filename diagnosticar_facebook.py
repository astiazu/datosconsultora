# diagnosticar_facebook.py
import glob, os, traceback
from app.services.conversation_service import ConversationService

carpeta = os.path.join("origen")
archivos = sorted(
    glob.glob(os.path.join(carpeta, "*.html")) +
    glob.glob(os.path.join(carpeta, "*.htm"))
)
if not archivos:
    print("❌ No hay archivos .html/.htm en:", os.path.abspath(carpeta))
    raise SystemExit(1)

path = archivos[-1]
print("📄 Archivo:", path)
html = open(path, encoding="utf-8", errors="ignore").read()

svc = ConversationService()
try:
    r = svc.from_saved_page(html, "", "")
    if r["success"]:
        conv = r["conversation"]
        print(f"✅ SUCCESS — red: {r.get('red_social')} | comentarios: {conv.total_messages}")
        print("\n--- Primeros 10 comentarios ---")
        for m in conv.messages[:10]:
            print(" ·", m.text[:90])
    else:
        print("⚠️ Sin éxito:", r.get("error_msg"))
except Exception:
    print("💥 EXCEPCIÓN en from_saved_page:")
    traceback.print_exc()