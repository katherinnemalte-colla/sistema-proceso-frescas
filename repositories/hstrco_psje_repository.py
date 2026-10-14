import os
from models.database import obtener_conexion
from PySide6.QtGui import QIntValidator
from typing import Optional
from config.settings import DB_DATABASE

DB_PRODUCTOS = DB_DATABASE

def guardar_historico_pesaje(datos: dict) -> bool:
    """
    Inserta el pesaje solo si la posta (nmro_psta) no existe todavía.
    Devuelve True si insertó, False si ya existía (en ese caso se debe reimprimir).
    """
    sql = f"""
        INSERT INTO [{DB_PRODUCTOS}].dbo.hstrco_psje (
            nmro_psta, prcso, cdgo_plu, nmbre_plu, tpo_lmpza, nmro_lte,
            fcha_prdccion, fcha_vnce_ref, fcha_vnce_cong, fcha_scrfcio,
            pso_nto, pso_tra, pso_brto, cdgo_emprsa, pddo, prcndor,
            actlzcion, oprdor, estdo
        )
        SELECT
            ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?,
            GETDATE(), ?, ?
        WHERE NOT EXISTS (
            SELECT 1
            FROM [{DB_PRODUCTOS}].dbo.hstrco_psje WITH (UPDLOCK, HOLDLOCK)
            WHERE nmro_psta = ?
        )
    """

    nmro_psta = datos.get("nmro_psta", 0)

    valores = (
        nmro_psta,
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
        nmro_psta,  # parámetro del NOT EXISTS
    )
    with obtener_conexion() as conexion:
        cursor = conexion.cursor()
        cursor.execute(sql, valores)
        insertado = cursor.rowcount > 0
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
def marcar_historico_reimpreso(
    cnsctvo: int,
    oprdor: str = "",
    estado: Optional[int] = None,
) -> None:
    """
    Marca un registro de hstrco_psje como reimpreso, SIN tocar los datos
    de negocio (producto, lote, peso, fechas, etc.).

    Solo actualiza:
      - actlzcion (fecha/hora de la reimpresión)
      - oprdor    (quién reimprimió)
      - estdo     (opcional, para inactivar con 9)
    """
    campo_estado_sql = ", estdo = ?" if estado is not None else ""

    sql = f"""
        UPDATE [{DB_PRODUCTOS}].dbo.hstrco_psje
        SET
            actlzcion = GETDATE(),
            oprdor = ?{campo_estado_sql}
        WHERE cnsctvo = ?
    """

    valores = [oprdor]
    if estado is not None:
        valores.append(estado)
    valores.append(cnsctvo)

    with obtener_conexion() as conexion:
        cursor = conexion.cursor()
        cursor.execute(sql, tuple(valores))
        conexion.commit()
        cursor.close()


def obtener_ultimos_historicos_pesaje(nmro_psta: int) -> list[dict]:
    sql = f"""
        SELECT TOP 3
            cnsctvo, nmro_psta, cdgo_plu, nmbre_plu,
            nmro_lte, tpo_lmpza,
            fcha_prdccion, fcha_scrfcio,
            fcha_vnce_ref, fcha_vnce_cong,
            pso_nto, pso_tra, pso_brto,
            cdgo_emprsa, pddo, prcndor,
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
                "nmro_psta": f.nmro_psta, "cnsctvo": f.cnsctvo,
                "cdgo_plu": f.cdgo_plu, "nmbre_plu": f.nmbre_plu,
                "nmro_lte": f.nmro_lte, "tpo_lmpza": f.tpo_lmpza,
                "fcha_prdccion": f.fcha_prdccion, "fcha_scrfcio": f.fcha_scrfcio,
                "fcha_vnce_ref": f.fcha_vnce_ref, "fcha_vnce_cong": f.fcha_vnce_cong,
                "pso_nto": f.pso_nto, "pso_tra": f.pso_tra, "pso_brto": f.pso_brto,
                "cdgo_emprsa": f.cdgo_emprsa, "pddo": f.pddo, "prcndor": f.prcndor,
                "actlzcion": f.actlzcion,
            }
            for f in filas
        ]
        
def obtener_ultimos_pesajes_recientes(limite: int = 3) -> list[dict]:
    sql = f"""
        SELECT TOP (?)
            nmro_psta, cnsctvo, cdgo_plu, nmbre_plu,
            nmro_lte, tpo_lmpza,
            fcha_prdccion, fcha_scrfcio,
            fcha_vnce_ref, fcha_vnce_cong,
            pso_nto, pso_tra, pso_brto,
            cdgo_emprsa, pddo, prcndor,
            actlzcion, estdo
        FROM [{DB_PRODUCTOS}].dbo.hstrco_psje where estdo <> 9
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
                "nmro_lte": f.nmro_lte, "tpo_lmpza": f.tpo_lmpza,
                "fcha_prdccion": f.fcha_prdccion, "fcha_scrfcio": f.fcha_scrfcio,
                "fcha_vnce_ref": f.fcha_vnce_ref, "fcha_vnce_cong": f.fcha_vnce_cong,
                "pso_nto": f.pso_nto, "pso_tra": f.pso_tra, "pso_brto": f.pso_brto,
                "cdgo_emprsa": f.cdgo_emprsa, "pddo": f.pddo, "prcndor": f.prcndor,
                "actlzcion": f.actlzcion, "estdo": f.estdo,
            }
            for f in filas
        ]
