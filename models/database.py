"""
Manejo de conexiones a SQL Server.
Ahora soporta VARIAS bases de datos en el mismo servidor: se elige
cuál usar con el parámetro `database_key`.
"""

import pyodbc
from contextlib import contextmanager
from config.settings import (
    DB_SERVER, DB_DATABASE, DB_DATABASE_1, DB_USER, DB_PASSWORD
)

# Mapa de "nombre corto" -> nombre real de la base de datos.
# Agrega aquí cualquier base nueva que necesites en el futuro.
BASES_DE_DATOS = {
    "DB_DATABASE": DB_DATABASE,       # base principal (usuarios, lotes, etc.)
    "DB_DATABASE_1": DB_DATABASE_1,   # base de imágenes de productos
}


def conectar_bd(database_key: str = "DB_DATABASE"):
    """
    Abre una conexión a la base indicada por `database_key`.
    Si no se pasa nada, usa la base principal por defecto.
    """
    nombre_bd = BASES_DE_DATOS.get(database_key)

    if nombre_bd is None:
        print(f"Error de conexión: base de datos no reconocida '{database_key}'")
        return None

    try:
        conexion = pyodbc.connect(
            f"DRIVER={{ODBC Driver 17 for SQL Server}};"
            f"SERVER={DB_SERVER};"
            f"DATABASE={nombre_bd};"
            f"UID={DB_USER};"
            f"PWD={DB_PASSWORD};"
        )
        return conexion
    except Exception as e:
        print(f"Error de conexión: {e}")
        return None


def probar_conexion(database_key: str = "DB_DATABASE"):
    conexion = conectar_bd(database_key)
    if conexion:
        print(f"Conexión exitosa a {database_key}")
        conexion.close()
    else:
        print(f"No se pudo conectar a {database_key}")


@contextmanager
def obtener_conexion(database_key: str = "DB_DATABASE"):
    """
    Uso:
        with obtener_conexion() as conn:                      # base principal
            ...
        with obtener_conexion("DB_DATABASE_1") as conn:        # base de imágenes
            ...
    Garantiza que la conexión siempre se cierre, incluso si hay error.
    """
    conn = conectar_bd(database_key)
    if conn is None:
        raise ConnectionError(
            f"No se pudo establecer conexión con la base de datos '{database_key}'."
        )
    try:
        yield conn
    finally:
        conn.close()