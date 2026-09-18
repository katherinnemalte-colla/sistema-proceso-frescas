from dotenv import load_dotenv
import sys
import os
from pathlib import Path

def ruta_base():
    if getattr(sys, 'frozen', False):
        # Corriendo como exe: la carpeta donde está el .exe
        return Path(sys.executable).parent
    else:
        # Corriendo como script: subir un nivel desde config/ hasta la raíz del proyecto
        return Path(__file__).parent.parent

BASE_DIR = ruta_base()
load_dotenv(BASE_DIR / ".env")

DB_SERVER = os.getenv("DB_SERVER")
DB_DATABASE = os.getenv("DB_DATABASE")
DB_DATABASE_1 = os.getenv("DB_DATABASE_1")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

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
        f"Faltan variables de entorno: {', '.join(faltantes)}. "
        f"Verifica que exista el archivo .env en: {BASE_DIR}"
    )