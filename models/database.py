# models/database.py
import pyodbc
from config.settings import DB_SERVER, DB_DATABASE, DB_USER, DB_PASSWORD

def conectar_bd():
    try:
        conexion = pyodbc.connect(
            f"DRIVER={{ODBC Driver 17 for SQL Server}};"
            f"SERVER={DB_SERVER};"
            f"DATABASE={DB_DATABASE};"
            f"UID={DB_USER};"
            f"PWD={DB_PASSWORD};"
        )
        return conexion
    except Exception as e:
        print(f"Error de conexión: {e}")
        return None

def probar_conexion():
    conexion = conectar_bd()
    if conexion:
        print("Conexión exitosa")
        conexion.close()
    else:
        print("No se pudo conectar")    