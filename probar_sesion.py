# probar_sesion.py
import base64, os, tempfile
import instaloader

b64 = open("sesion_instagram.b64.txt", "r", encoding="ascii").read().strip()
tmp = tempfile.NamedTemporaryFile("wb", suffix=".pkl", delete=False)
tmp.write(base64.b64decode(b64))
tmp.close()

L = instaloader.Instaloader(quiet=True)
L.load_session_from_file("", tmp.name)
os.unlink(tmp.name)

usuario = L.test_login()
if usuario:
    print(f"✅ Sesión válida para: {usuario}")
else:
    print("❌ Instagram rechazó la sesión: completá verificación en navegador y regenerá el archivo.")