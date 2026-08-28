# tree.py
import os
from pathlib import Path

def print_tree(start_path='.', prefix='', exclude_dirs=None, exclude_files=None):
    """Imprime el árbol de archivos y carpetas."""
    if exclude_dirs is None:
        exclude_dirs = {'__pycache__', '.git', 'venv', 'env', '.pytest_cache', 'node_modules'}
    if exclude_files is None:
        exclude_files = {'.pyc', '.pyo', '__pycache__'}
    
    start_path = Path(start_path)
    
    # Imprimir raíz
    print(f"📁 {start_path.name}/")
    
    # Obtener todos los archivos y carpetas
    items = sorted(start_path.iterdir(), key=lambda x: (x.is_file(), x.name.lower()))
    
    for i, item in enumerate(items):
        is_last = (i == len(items) - 1)
        
        # Excluir carpetas y archivos no deseados
        if item.is_dir() and item.name in exclude_dirs:
            continue
        if item.is_file() and item.suffix in exclude_files:
            continue
        if item.name.startswith('.'):
            continue
            
        # Crear conector
        connector = "└── " if is_last else "├── "
        
        if item.is_dir():
            print(f"{prefix}{connector}📁 {item.name}/")
            # Recursión
            new_prefix = prefix + ("    " if is_last else "│   ")
            print_tree(item, new_prefix, exclude_dirs, exclude_files)
        else:
            print(f"{prefix}{connector}📄 {item.name}")

if __name__ == "__main__":
    print("=" * 60)
    print("📊 ESTRUCTURA DEL PROYECTO - DatosConsultora")
    print("=" * 60)
    print_tree('.')
    print("=" * 60)