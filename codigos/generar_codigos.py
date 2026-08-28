"""
Script para volcar el contenido de archivos .py, .html y .css
en archivos de texto (codigos_py.txt, codigos_html.txt, codigos_css.txt, ...).

Uso:
    python generar_codigos_txt.py
"""

import os

# Directorio base del proyecto.
BASE_DIR = r"c:\Users\Jose\Downloads"
PROYECTO = os.path.join(BASE_DIR, "datosconsultora_app")

# Configuración: (carpeta, extensión, salida, recursivo, subcarpetas a excluir)
CONFIGURACIONES = [
    # app/ completo SIN routes ni utils (ellos tienen su propio archivo → sin duplicados)
    (os.path.join(PROYECTO, "app"), ".py", "codigos_py_carpeta_app.txt", True, {"routes", "utils"}),
    # routes y utils por separado
    (os.path.join(PROYECTO, "app", "routes"), ".py", "codigos_py_carpeta_app_routes.txt", True, set()),
    (os.path.join(PROYECTO, "app", "utils"), ".py", "codigos_py_carpeta_app_utils.txt", True, set()),
    # templates y css
    (os.path.join(PROYECTO, "app", "templates"), ".html", "codigos_html.txt", True, set()),
    (os.path.join(PROYECTO, "app", "static", "css"), ".css", "codigos_css.txt", True, set()),
    # scripts .py de la raíz (run.py, preflight.py, diagnosticar_modelos.py, ...)
    (PROYECTO, ".py", "codigos_py.txt", False, set()),
]


def volcar_archivos(carpeta, extension, archivo_salida, recursivo=True, excluir=None):
    excluir = excluir or set()

    if not os.path.isdir(carpeta):
        print(f"[AVISO] No se encontró la carpeta: {carpeta}")
        return

    archivos_encontrados = []

    if recursivo:
        for root, dirs, files in os.walk(carpeta):
            # Orden determinístico + exclusión de subcarpetas ya volcadas aparte
            dirs[:] = sorted(d for d in dirs if d not in excluir)
            for nombre in sorted(files):
                if nombre.lower().endswith(extension):
                    archivos_encontrados.append(os.path.join(root, nombre))
    else:
        # Solo nivel superior (para no meterse en venv/, instance/, etc.)
        for nombre in sorted(os.listdir(carpeta)):
            ruta = os.path.join(carpeta, nombre)
            if os.path.isfile(ruta) and nombre.lower().endswith(extension):
                archivos_encontrados.append(ruta)

    if not archivos_encontrados:
        print(f"[AVISO] No se encontraron archivos {extension} en: {carpeta}")
        return

    # Los .txt de salida se escriben siempre en la raíz del proyecto
    ruta_salida = os.path.join(PROYECTO, archivo_salida)
    with open(ruta_salida, "w", encoding="utf-8") as salida:
        for ruta_archivo in archivos_encontrados:
            ruta_relativa = os.path.relpath(ruta_archivo, carpeta)
            salida.write("=" * 80 + "\n")
            salida.write(f"ARCHIVO: {ruta_relativa}\n")
            salida.write("=" * 80 + "\n\n")
            try:
                with open(ruta_archivo, "r", encoding="utf-8") as f:
                    contenido = f.read()
            except UnicodeDecodeError:
                # Por si algún archivo no está en UTF-8
                with open(ruta_archivo, "r", encoding="latin-1") as f:
                    contenido = f.read()
            salida.write(contenido)
            salida.write("\n\n")

    print(f"[OK] {len(archivos_encontrados)} archivo(s) volcados en: {ruta_salida}")


def main():
    for carpeta, extension, archivo_salida, recursivo, excluir in CONFIGURACIONES:
        volcar_archivos(carpeta, extension, archivo_salida, recursivo, excluir)


if __name__ == "__main__":
    main()