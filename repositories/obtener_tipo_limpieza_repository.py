"""
obtener_tipo_limpieza_repository.py

Repositorio para el catálogo de tipos de limpieza (tabla tpo_lmpza),
usado en la sección "Tipo de limpieza" de Ficha Técnica.

Capa: Repository. Toda el acceso a datos vive acá; la UI no arma SQL.
"""

import os
from dataclasses import dataclass
from typing import List

# ⚠️ La consulta original decía "db.dbo.tpo_lmpza" — "db" es un
# nombre genérico, no el real. Usé la misma variable DB_PRODUCTOS que
# ya usas en obtener_tipo_pza_repository.py; ajústala si esta tabla
# en realidad vive en otra base de datos.
DB_PRODUCTOS = os.getenv("DB_DATABASE")


@dataclass
class TipoLimpieza:
    tpo_lmpza: int
    nmbre: str
    prfjo: str
    ctgria_ascda: str
    estdo: int


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