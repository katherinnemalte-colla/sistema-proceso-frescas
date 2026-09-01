"""
obtener_tipo_limpieza_repository.py

Repositorio para el catálogo de tipos de limpieza (tabla tpo_lmpza) y para la
fecha de sacrificio, usado en la sección "Tipo de limpieza" de Ficha Técnica.

Capa: Repository. Toda el acceso a datos vive acá; la UI no arma SQL.
"""

import os
from dataclasses import dataclass
from typing import List, Optional
from datetime import date, timedelta
from typing import Optional

DB_PRODUCTOS = os.getenv("DB_DATABASE")

@dataclass
class FichaTecnicaProducto:
    cdgo_plu: int
    grmje: Optional[float]
    dia_refr: Optional[int]
    dia_cong: Optional[int]

@dataclass
class TipoLimpieza:
    tpo_lmpza: int
    nmbre: str
    prfjo: str
    ctgria_ascda: str
    estdo: int 

@dataclass
class SacrificioEtiqueta:
    scrfcio: Optional[date]
    nom_impr_etiq: Optional[str]

class ObtenerTipoLimpiezaRepository:

    def __init__(self, obtener_conexion):
        self._obtener_conexion = obtener_conexion

    def obtener_tipos_limpieza(self) -> List[TipoLimpieza]:

        consulta = f"""
            SELECT tpo_lmpza, nmbre, prfjo, ctgria_ascda, estdo
            FROM [{DB_PRODUCTOS}].dbo.tpo_lmpza
            WHERE estdo = 1 order by tpo_lmpza 
        """

        with self._obtener_conexion() as conexion:
            cursor = conexion.cursor()
            cursor.execute(consulta)
            return [
                TipoLimpieza(
                    tpo_lmpza=fila[0],
                    nmbre=fila[1],
                    prfjo=fila[2],
                    ctgria_ascda=fila[3],
                    estdo=fila[4],
                )
                for fila in cursor.fetchall()
            ]

    def obtener_fecha_sacrificio(self, nmro_lte: int, espcie: int ) -> Optional[SacrificioEtiqueta]:
        consulta = f"""
            SELECT a.scrfcio, b.nom_impr_etiq
            FROM [{DB_PRODUCTOS}].dbo.LTES_CMPRA_ESPCIE a,
                [{DB_PRODUCTOS}].dbo.tipo_ctgria_gndo b
            WHERE a.nmro_lte = ?
            AND a.cntro_pr = 1
            AND a.tpo_ctgria = b.cod_cat
            AND a.tpo_cmpra = 'P'
            AND a.espcie = ?
        """
        with self._obtener_conexion() as conexion:
            cursor = conexion.cursor()
            cursor.execute(consulta, (nmro_lte,espcie,))
            fila = cursor.fetchone()
            if fila is None:
                return None
            return SacrificioEtiqueta(
                scrfcio=fila[0],
                nom_impr_etiq=fila[1],
            )

    def obtener_dias_vencimiento(
        self,
        codigo_producto: int,
        codigo_empresa: int,
    ) -> tuple[Optional[int], Optional[int]]:
        """
        Trae (dias_ref, dias_cong) en una sola consulta.
        """
        with self._obtener_conexion() as conexion:
            cursor = conexion.cursor()

            if codigo_empresa == 1:
                cursor.execute("""
                    SELECT dias_ref, dias_cong
                    FROM PRDCTOS
                    WHERE cdgo_plu = ?
                """, (codigo_producto,))
            else:
                cursor.execute("""
                    SELECT dia_refr, dia_cong
                    FROM ficha_tec_prod_cli
                    WHERE cdgo_plu = ?
                    AND cod_emprsa = ?
                    order by grmje
                """, (codigo_producto, codigo_empresa))

            row = cursor.fetchone()
            if not row:
                return None, None

            return row[0], row[1]

    def obtener_fecha_vencimiento(
        self,
        codigo_producto: int,
        codigo_empresa: int,
        fecha_produccion: date,
        tipo_conservacion: str
    ) -> Optional[date]:
        
        with self._obtener_conexion() as conexion:
            cursor = conexion.cursor()
        
            if codigo_empresa == 1:
                cursor.execute("""
                    SELECT dias_ref, dias_cong
                    FROM PRDCTOS
                    WHERE cdgo_plu = ?
                """, (codigo_producto,))
        
                row = cursor.fetchone()
        
                if not row:
                    return None
        
                dias_ref = row.dias_ref
                dias_cong = row.dias_cong
        
            else:
                cursor.execute("""
                    SELECT dia_refr, dia_cong
                    FROM ficha_tec_prod_cli
                    WHERE cdgo_plu = ?
                      AND cod_emprsa = ?
                      order by grmje
                """, (codigo_producto, codigo_empresa))
        
                row = cursor.fetchone()
        
                if not row:
                    return None
        
                dias_ref = row.dia_refr
                dias_cong = row.dia_cong
        
            if tipo_conservacion == "refrigerado":
                dias = dias_ref
        
            elif tipo_conservacion == "congelado":
                dias = dias_cong
        
            else:
                raise ValueError(
                    "Tipo de conservación debe ser 'refrigerado' o 'congelado'"
                )
        
            if dias is None:
                return None
        
            return fecha_produccion + timedelta(days=int(dias))