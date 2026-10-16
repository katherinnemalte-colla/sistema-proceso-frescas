import json
import sys
from pathlib import Path

from cryptography.fernet import Fernet


def ruta_base():
    if getattr(sys, 'frozen', False):
        # Corriendo como exe: la carpeta donde está el .exe
        return Path(sys.executable).parent
    else:
        # Corriendo como script: subir un nivel desde config/ hasta la raíz del proyecto
        return Path(__file__).parent.parent


def _cargar_config() -> dict:
    """Lee y descifra la configuración incrustada (config/_secretos.py)."""
    try:
        from config._secretos import _K, _T
    except ImportError:
        raise RuntimeError(
            "No existe config/_secretos.py. Ejecuta generar_secretos.py "
            "(en la raíz del proyecto) antes de iniciar o compilar."
        )
    return json.loads(Fernet(_K).decrypt(_T))


BASE_DIR = ruta_base()
_cfg = _cargar_config()

DB_SERVER = _cfg.get("DB_SERVER")
DB_DATABASE = _cfg.get("DB_DATABASE")
DB_DATABASE_1 = _cfg.get("DB_DATABASE_1")
DB_USER = _cfg.get("DB_USER")
DB_PASSWORD = _cfg.get("DB_PASSWORD")

# Verificación temprana: si falta algo, te avisa apenas arranca el programa
faltantes = [nombre for nombre, valor in {
    "DB_SERVER": DB_SERVER,
    "DB_DATABASE": DB_DATABASE,
    "DB_DATABASE_1": DB_DATABASE_1,
    "DB_USER": DB_USER,
    "DB_PASSWORD": DB_PASSWORD,
}.items() if not valor]

if faltantes:
    raise RuntimeError(
        f"Faltan datos de configuración: {', '.join(faltantes)}. "
        f"Vuelve a ejecutar generar_secretos.py y recompila."
    )