# diagnosticar_modelos.py
import os
from pathlib import Path

# ✅ Cargar .env manualmente (igual que hace Flask con python-dotenv)
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    for linea in env_path.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#") or "=" not in linea:
            continue
        clave, _, valor = linea.partition("=")
        clave = clave.strip()
        valor = valor.strip().strip('"').strip("'")
        os.environ.setdefault(clave, valor)

from groq import Groq

api_key = os.environ.get("GROQ_API_KEY")
if not api_key:
    print("❌ No se encontró GROQ_API_KEY en .env ni en el entorno.")
    print(f"   Busqué en: {env_path}")
    raise SystemExit(1)

client = Groq(api_key=api_key)
print(f"✅ Cliente Groq conectado. Probando modelos...\n")

modelos = [
    "llama-3.1-8b-instant",
    "llama-3.3-70b-versatile",
    "qwen-2.5-32b",
    "qwen/qwen3-32b",
    "qwen-qwq-32b",
    "meta-llama/llama-4-scout-17b-16e-instruct",
    "meta-llama/llama-4-maverick-17b-128e-instruct",
    "openai/gpt-oss-20b",
    "openai/gpt-oss-120b",
    "moonshotai/kimi-k2-instruct",
    "gemma2-9b-it",
    "mixtral-8x7b-32768",
]

vivos = []
for m in modelos:
    try:
        r = client.chat.completions.create(
            model=m,
            messages=[{"role": "user", "content": "Respondé únicamente: ok"}],
            max_tokens=5,
        )
        print(f"✅ {m} → VIVO ({r.choices[0].message.content.strip()})")
        vivos.append(m)
    except Exception as e:
        err = str(e)
        if "decommissioned" in err or "no longer supported" in err:
            print(f"💀 {m} → DECOMMISSIONED (retirado)")
        elif "does not exist" in err or "model_not_found" in err:
            print(f"❌ {m} → NO EXISTE")
        elif "rate_limit" in err.lower() or "429" in err:
            print(f"⏸  {m} → VIVO pero sin cuota ahora")
            vivos.append(m)
        else:
            print(f"⚠️  {m} → {err[:100]}")

print(f"\n🎯 MODELOS VIVOS DETECTADOS ({len(vivos)}):")
for m in vivos:
    print(f"   • {m}")