# diagnosticar_html.py (v2)
import re, glob, os
from bs4 import BeautifulSoup

carpeta = os.path.join("instance", "uploads", "paginas_origen")
path = sorted(glob.glob(os.path.join(carpeta, "pagina_*.html")))[-1]
print("📄", os.path.basename(path))
soup = BeautifulSoup(open(path, encoding="utf-8").read(), "html.parser")

def norm(t): return " ".join(t.split())

def anidado(span):
    p = span.parent
    for _ in range(3):
        if p is None:
            break
        if getattr(p, "name", None) == "span" and p.get("dir") == "auto":
            return True
        p = p.parent
    return False

spans = soup.find_all("span", {"dir": "auto"})
print("TOTAL dir=auto:", len(spans))

print("\n=== SPANS CON SUSTANCIA (TEXTO = se captura | ANIDADO = se está perdiendo) ===")
for i, s in enumerate(spans):
    t = norm(s.get_text())
    if len(t) <= 15:
        continue
    if anidado(s):
        tag = "ANIDADO"
    elif " " not in t and re.fullmatch(r"[a-zA-Z0-9._-]+", t):
        tag = "USUARIO"
        continue
    else:
        tag = "TEXTO"
    print(f"{i:3} [{tag}] {t[:100]}")