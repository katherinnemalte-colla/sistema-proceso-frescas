from typing import Optional
import os

from models.database import obtener_conexion

DB_PRODUCTOS = os.getenv("DB_DATABASE")

if not DB_PRODUCTOS:
    raise RuntimeError("Falta la variable de entorno DB_DATABASE")


def _consultar_valor_basicas(eleme_grup: str, nombr_grup: str = "FACTURA_POS") -> Optional[str]:
    """
    Helper común: consulta un valor puntual en BASICAS por
    (nombr_grup, eleme_grup) y devuelve codig_elem como texto, o None
    si no hay conexión, no hay filas, o el valor viene vacío.
    """
    query = f"""
        SELECT codig_elem AS valor
        FROM [{DB_PRODUCTOS}].dbo.BASICAS
        WHERE nombr_grup = ?
          AND eleme_grup = ?
    """

    with obtener_conexion() as conexion:
        cursor = conexion.cursor()
        cursor.execute(query, (nombr_grup, eleme_grup))
        fila = cursor.fetchone()
        cursor.close()

        if fila and fila.valor:
            return str(fila.valor).strip()

        return None


def obtener_nombre_empresa_bd() -> Optional[str]:
    return _consultar_valor_basicas(eleme_grup="EMPRESA")


def obtener_direccion_empresa_bd() -> Optional[str]:
    return _consultar_valor_basicas(eleme_grup="DIRECCION")