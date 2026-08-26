"""
obtener_tipo_limpieza_repository.py

Repositorio para el catálogo de tipos de limpieza (tabla tpo_lmpza) y para la
fecha de sacrificio, usado en la sección "Tipo de limpieza" de Ficha Técnica.

Capa: Repository. Toda el acceso a datos vive acá; la UI no arma SQL.
"""

import os
from dataclasses import dataclass
from typing import List, Optional
from datetime import date

DB_PRODUCTOS = os.getenv("DB_DATABASE")


@dataclass
class TipoLimpieza:
    tpo_lmpza: int
    nmbre: str
    prfjo: str
    ctgria_ascda: str
    estdo: int 

@dataclass
class SacrificioEtiqueta:          # 👈 este es el dataclass
    scrfcio: Optional[date]
    nom_impr_etiq: Optional[str]

class ObtenerTipoLimpiezaRepository:

    def __init__(self, obtener_conexion):
        self._obtener_conexion = obtener_conexion

    def obtener_tipos_limpieza(self) -> List[TipoLimpieza]:

        consulta = f"""
            SELECT tpo_lmpza, nmbre, prfjo, ctgria_ascda, estdo
            FROM [{DB_PRODUCTOS}].dbo.tpo_lmpza
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

    def obtener_fecha_sacrificio(self, nmro_lte: int) -> Optional[SacrificioEtiqueta]:
        consulta = f"""
            SELECT a.scrfcio, b.nom_impr_etiq
            FROM [{DB_PRODUCTOS}].dbo.LTES_CMPRA_ESPCIE a,
                [{DB_PRODUCTOS}].dbo.tipo_ctgria_gndo b
            WHERE a.nmro_lte = ?
            AND a.cntro_pr = 1
            AND a.tpo_ctgria = b.cod_cat
            AND a.tpo_cmpra = 'P'
            AND a.espcie = 1
        """
        with self._obtener_conexion() as conexion:
            cursor = conexion.cursor()
            cursor.execute(consulta, (nmro_lte,))
            fila = cursor.fetchone()
            if fila is None:
                return None
            return SacrificioEtiqueta(
                scrfcio=fila[0],
                nom_impr_etiq=fila[1],
            )