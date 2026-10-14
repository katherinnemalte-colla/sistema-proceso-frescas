from dotenv import load_dotenv
import sys
import os
import json
from pathlib import Path


def ruta_base():
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    else:
        return Path(__file__).parent.parent


def _credenciales():
    """Exe: lee las credenciales incrustadas. Script: usa el .env como respaldo."""
    try:
        from cryptography.fernet import Fernet
        from config._secretos import _K, _T
        datos = json.loads(Fernet(_K).decrypt(_T))
        return datos["user"], datos["password"]
    except ImportError:
        if getattr(sys, 'frozen', False):
            return None, None
        return os.getenv("DB_USER"), os.getenv("DB_PASSWORD")


BASE_DIR = ruta_base()
load_dotenv(BASE_DIR / ".env")

DB_SERVER = os.getenv("DB_SERVER")
DB_DATABASE = os.getenv("DB_DATABASE")
DB_DATABASE_1 = os.getenv("DB_DATABASE_1")
DB_USER, DB_PASSWORD = _credenciales()

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
        f"Verifica el .env en {BASE_DIR} y que el exe se haya compilado "
        f"con generar_secretos.py."
    )