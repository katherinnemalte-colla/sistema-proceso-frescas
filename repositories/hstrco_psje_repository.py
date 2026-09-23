import os
from models.database import obtener_conexion
from PySide6.QtGui import QIntValidator
from typing import Optional


DB_PRODUCTOS = os.getenv("DB_DATABASE")
if not DB_PRODUCTOS:
    raise RuntimeError("Falta la variable de entorno DB_DATABASE")

def guardar_historico_pesaje(datos: dict) -> None:
    sql = f"""
        INSERT INTO [{DB_PRODUCTOS}].dbo.hstrco_psje (
            nmro_psta,
            prcso,
            cdgo_plu,
            nmbre_plu,
            tpo_lmpza,
            nmro_lte,
            fcha_prdccion,
            fcha_vnce_ref,
            fcha_vnce_cong,
            fcha_scrfcio,
            pso_nto,
            pso_tra,
            pso_brto,
            cdgo_emprsa,
            pddo,
            prcndor,
            actlzcion,
            oprdor,
            estdo
        )
        VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?, GETDATE(), ? , ?
        )
    """

    valores = (
        datos.get("nmro_psta", 0),
        datos.get("prcso", 1),
        datos.get("cdgo_plu", 0),
        datos.get("nmbre_plu", ""),
        datos.get("tpo_lmpza", 0),
        datos.get("nmro_lte", 0),
        datos.get("fcha_prdccion", "1900-01-01"),
        datos.get("fcha_vnce_ref", "1900-01-01"),
        datos.get("fcha_vnce_cong", "1900-01-01"),
        datos.get("fcha_scrfcio", "1900-01-01"),
        datos.get("pso_nto", 0),
        datos.get("pso_tra", 0),
        datos.get("pso_brto", 0),
        datos.get("cdgo_emprsa", 0),
        datos.get("pddo", 0),
        datos.get("prcndor", 0),
        datos.get("oprdor", ""),
        datos.get("estdo", 1),
    )
    with obtener_conexion() as conexion:
        cursor = conexion.cursor()
        cursor.execute(sql, valores)
        conexion.commit()
        cursor.close()


def actualizar_historico_pesaje(
    cnsctvo: int,
    datos: dict,
    oprdor: str = "",
    estado: Optional[int] = None,
) -> None:
    """
    Actualiza un registro de hstrco_psje.
    Si 'estado' es None, esa columna no se toca (se conserva el valor actual).
    Para inactivar el registro, pasar estdo=9.
    """
    campo_estado_sql = ", estdo = ?" if estado is not None else ""

    sql = f"""
        UPDATE [{DB_PRODUCTOS}].dbo.hstrco_psje
        SET
            cdgo_plu = ?,
            nmbre_plu = ?,
            tpo_lmpza = ?,
            nmro_lte = ?,
            fcha_prdccion = ?,
            fcha_vnce_ref = ?,
            fcha_vnce_cong = ?,
            fcha_scrfcio = ?,
            pso_nto = ?,
            pso_tra = ?,
            pso_brto = ?,
            cdgo_emprsa = ?,
            pddo = ?,
            prcndor = ?,
            actlzcion = GETDATE(),
            oprdor = ?{campo_estado_sql}
        WHERE cnsctvo = ?
    """

    valores = [
        datos.get("cdgo_plu", 0),
        datos.get("nmbre_plu", ""),
        datos.get("tpo_lmpza", 0),
        datos.get("nmro_lte", 0),
        datos.get("fcha_prdccion", "1900-01-01"),
        datos.get("fcha_vnce_ref", "1900-01-01"),
        datos.get("fcha_vnce_cong", "1900-01-01"),
        datos.get("fcha_scrfcio", "1900-01-01"),
        datos.get("pso_nto", 0),
        datos.get("pso_tra", 0),
        datos.get("pso_brto", 0),
        datos.get("cdgo_emprsa", 0),
        datos.get("pddo", 0),
        datos.get("prcndor", 0),
        oprdor,
    ]
    if estado is not None:
        valores.append(estado)
    valores.append(cnsctvo)

    with obtener_conexion() as conexion:
        cursor = conexion.cursor()
        cursor.execute(sql, tuple(valores))
        conexion.commit()
        cursor.close()


def obtener_ultimos_historicos_pesaje(nmro_psta: int) -> list[dict]:
    """
    Obtiene los 3 registros más recientes de una pista,
    ordenados desde el más reciente al más antiguo.
    """

    sql = f"""
        SELECT TOP 3
            cnsctvo,
            cdgo_plu,
            nmbre_plu,
            nmro_lte,
            pso_nto,
            actlzcion
        FROM [{DB_PRODUCTOS}].dbo.hstrco_psje
        WHERE nmro_psta = ?
        AND (estdo IS NULL OR estdo <> 9)
        ORDER BY actlzcion DESC
    """

    with obtener_conexion() as conexion:
        cursor = conexion.cursor()
        cursor.execute(sql, (nmro_psta,))
        filas = cursor.fetchall()
        cursor.close()

        return [
            {
                "cnsctvo": fila.cnsctvo,
                "cdgo_plu": fila.cdgo_plu,
                "nmbre_plu": fila.nmbre_plu,
                "nmro_lte": fila.nmro_lte,
                "pso_nto": fila.pso_nto,
                "actlzcion": fila.actlzcion,
            }
            for fila in filas
        ]
def obtener_ultimos_pesajes_recientes(limite: int = 3) -> list[dict]:
    sql = f"""
        SELECT TOP (?)
            nmro_psta, cnsctvo, cdgo_plu, nmbre_plu,
            nmro_lte, pso_nto, actlzcion, estdo
        FROM [{DB_PRODUCTOS}].dbo.hstrco_psje
        ORDER BY actlzcion DESC
    """
    with obtener_conexion() as conexion:
        cursor = conexion.cursor()
        cursor.execute(sql, (limite,))
        filas = cursor.fetchall()
        cursor.close()
        return [
            {
                "nmro_psta": f.nmro_psta, "cnsctvo": f.cnsctvo,
                "cdgo_plu": f.cdgo_plu, "nmbre_plu": f.nmbre_plu,
                "nmro_lte": f.nmro_lte, "pso_nto": f.pso_nto,
                "actlzcion": f.actlzcion, "estdo": f.estdo,
            }
            for f in filas
        ]
