import pyodbc
from contextlib import contextmanager
from config.settings import (
    DB_SERVER, DB_DATABASE, DB_DATABASE_1, DB_USER, DB_PASSWORD
)

BASES_DE_DATOS = {
    "DB_DATABASE": DB_DATABASE,
    "DB_DATABASE_1": DB_DATABASE_1,
}

# Cache de conexiones activas: {database_key: conexion}
_conexiones_activas = {}

def _obtener_driver_disponible():
    drivers = [d for d in pyodbc.drivers() if "SQL Server" in d]
    if not drivers:
        raise RuntimeError(
            "No se encontró ningún driver ODBC de SQL Server instalado en este sistema."
        )
    # Prioriza el más reciente si hay varios
    for preferido in ("ODBC Driver 18 for SQL Server", "ODBC Driver 17 for SQL Server"):
        if preferido in drivers:
            return preferido
    return drivers[0]  # cualquier otro disponible como último recurso


def _crear_conexion(nombre_bd: str):
    driver = _obtener_driver_disponible()
    conexion  = pyodbc.connect(
        f"DRIVER={{{driver}}};"
        f"SERVER=tcp:{DB_SERVER};"
        f"DATABASE={nombre_bd};"
        f"UID={DB_USER};"
        f"PWD={DB_PASSWORD};"
        f"Encrypt=yes;"
        f"TrustServerCertificate=yes;",
        timeout=7,
        autocommit=True,
    )
    
    cursor = conexion.cursor()
    cursor.execute("SET LOCK_TIMEOUT 15000")  # 15 segundos máximo esperando un lock
    cursor.close()
    
    return conexion

def conectar_bd(database_key: str = "DB_DATABASE"):
    """
    Devuelve una conexión reutilizable a la base indicada.
    Si ya existe una conexión abierta y viva, la reutiliza.
    Si no, crea una nueva.
    """
    nombre_bd = BASES_DE_DATOS.get(database_key)
    if nombre_bd is None:
        print(f"Error de conexión: base de datos no reconocida '{database_key}'")
        return None

    conexion = _conexiones_activas.get(database_key)

    # Verificar si la conexión sigue viva
    if conexion is not None:
        try:
            conexion.cursor().execute("SELECT 1")
            return conexion  # sigue viva, la reutilizamos
        except Exception:
            # se cayó (timeout, servidor reinició, etc.) -> descartar y recrear
            try:
                conexion.close()
            except Exception:
                pass
            _conexiones_activas.pop(database_key, None)

    try:
        conexion = _crear_conexion(nombre_bd)
        _conexiones_activas[database_key] = conexion
        return conexion
    except Exception as e:
        print(f"Error de conexión: {e}")
        return None


def cerrar_todas_las_conexiones():
    """Llamar al cerrar la aplicación."""
    for conexion in _conexiones_activas.values():
        try:
            conexion.close()
        except Exception:
            pass
    _conexiones_activas.clear()


@contextmanager
def obtener_conexion(database_key: str = "DB_DATABASE"):
    conn = conectar_bd(database_key)
    if conn is None:
        raise ConnectionError(
            f"No se pudo establecer conexión con la base de datos '{database_key}'."
        )
    yield conn  # sin conn.close() aquí