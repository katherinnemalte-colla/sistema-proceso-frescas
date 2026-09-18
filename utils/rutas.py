import sys
from pathlib import Path

def ruta_recurso(rel_path):
    if getattr(sys, 'frozen', False):
        base = Path(sys._MEIPASS)
    else:
        base = Path(__file__).parent.parent  # sube de utils/ a la raíz del proyecto
    return base / rel_path