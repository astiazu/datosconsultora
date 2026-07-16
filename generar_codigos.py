"""
Script para volcar el contenido de archivos .py, .html y .css
en archivos de texto (codigos_py.txt, codigos_html.txt, codigos_css.txt).

Uso:
    1. Ajustá la variable BASE_DIR si tu proyecto no está en el mismo
       directorio desde donde ejecutás el script.
    2. Ejecutá: python generar_codigos_txt.py
"""

import os

# Directorio base del proyecto. Si el script está fuera de la carpeta
# del proyecto, poné acá la ruta completa, por ejemplo:
# BASE_DIR = r"C:\Users\TuUsuario\Documents\datosconsultora_app"
BASE_DIR = r"c:\Users\Jose\Downloads"

# Configuración: (carpeta a recorrer, extensión de archivo, archivo de salida)
CONFIGURACIONES = [
    (os.path.join(BASE_DIR, "datosconsultora_app", "app"), ".py", "codigos_py_carpeta_app.txt"),
    (os.path.join(BASE_DIR, "datosconsultora_app", "app", "routes"), ".py", "codigos_py_carpeta_app_routes.txt"),
    (os.path.join(BASE_DIR, "datosconsultora_app", "app", "utils"), ".py", "codigos_py_carpeta_app_utils.txt"),
    (os.path.join(BASE_DIR, "datosconsultora_app", "app", "templates"), ".html", "codigos_html.txt"),
    (os.path.join(BASE_DIR, "datosconsultora_app", "app", "static", "css"), ".css", "codigos_css.txt"),
]


def volcar_archivos(carpeta, extension, archivo_salida):
    if not os.path.isdir(carpeta):
        print(f"[AVISO] No se encontró la carpeta: {carpeta}")
        return

    # Buscamos los archivos recursivamente dentro de la carpeta
    archivos_encontrados = []
    for root, _dirs, files in os.walk(carpeta):
        for nombre in sorted(files):
            if nombre.lower().endswith(extension):
                archivos_encontrados.append(os.path.join(root, nombre))

    if not archivos_encontrados:
        print(f"[AVISO] No se encontraron archivos {extension} en: {carpeta}")
        return

    with open(archivo_salida, "w", encoding="utf-8") as salida:
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

    print(f"[OK] {len(archivos_encontrados)} archivo(s) volcados en: {archivo_salida}")


def main():
    for carpeta, extension, archivo_salida in CONFIGURACIONES:
        volcar_archivos(carpeta, extension, archivo_salida)


if __name__ == "__main__":
    main()