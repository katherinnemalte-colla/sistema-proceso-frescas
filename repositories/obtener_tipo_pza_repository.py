"""
obtener_tipo_pza_repository.py

Repositorio para el flujo de RES (vaca): en vez de filtrar por especie
(como hace ImagenRepository con cdgo_espcie), filtra por tipo de pieza
(tpo_pza: 1 = DELANTERO, 2 = TRASERO).

Expone la MISMA interfaz pública que ImagenRepository (mismos nombres
de método, mismo dataclass PaginaLetra) para que SeleccionDeProducto
pueda usar cualquiera de los dos repositorios de forma intercambiable,
solo cambiando qué instancia y qué valor de filtro le pasa.

Capa: Repository. Toda el acceso a datos vive acá; la UI no arma SQL.

NOTA: self._obtener_conexion es un context manager (@contextmanager),
por eso todos los métodos usan "with self._obtener_conexion() as
conexion:" en vez de abrir/cerrar la conexión a mano.
"""

import os
from dataclasses import dataclass
from typing import List, Optional


DB_PRODUCTOS = os.getenv("DB_DATABASE")
DB_IMAGENES = os.getenv("DB_DATABASE_1")

# Cantidad de productos que se traen por "página" dentro de una misma letra.
TAMANO_PAGINA = 12


@dataclass
class PaginaLetra:
    letra: str
    offset: int
    cantidad: int


@dataclass
class Producto:
    """Fila liviana para las grillas paginadas: solo imagen principal."""
    cdgo_plu: str
    nom_prog: str
    imagen_principal: Optional[bytes]


@dataclass
class ProductoConImagenes:
    """Fila completa para Ficha Técnica: las 6 imágenes de la pieza."""
    cdgo_plu: str
    nom_prog: str
    con_arch: Optional[bytes]
    con_arch_2: Optional[bytes]
    con_arch_3: Optional[bytes]
    con_arch_4: Optional[bytes]
    con_arch_5: Optional[bytes]
    con_arch_6: Optional[bytes]

    def imagenes(self) -> List[bytes]:
        """Solo las imágenes que sí vienen con datos, en orden."""
        campos = [
            self.con_arch,
            self.con_arch_2,
            self.con_arch_3,
            self.con_arch_4,
            self.con_arch_5,
            self.con_arch_6,
        ]
        return [img for img in campos if img]


class ObtenerTipoPzaRepository:
    """
    Igual que ImagenRepository, pero el criterio de filtro es
    tpo_pza (DELANTERO/TRASERO) en vez de cdgo_espcie.
    """

    def __init__(self, obtener_conexion):
        self._obtener_conexion = obtener_conexion

    def obtener_letras_disponibles(self, tpo_pza: int) -> List[str]:
        # Mismo criterio de inclusión que obtener_productos_por_letra
        # (INNER JOIN con imagenes) para que una letra "disponible" siempre
        # tenga al menos un producto recuperable. Además se descartan
        # nombres vacíos/nulos para que no aparezca una letra en blanco.
        consulta = f"""
            SELECT DISTINCT LEFT(p.nmbre_crto, 1) AS letra
            FROM [{DB_PRODUCTOS}].dbo.tpo_pzas_espcies a
            INNER JOIN [{DB_PRODUCTOS}].dbo.prdctos p
                ON p.tpo_pza = a.tpo_pza
            INNER JOIN [{DB_IMAGENES}].dbo.imagenes img
                ON img.referencia = CAST(p.cdgo_plu AS VARCHAR(50))
            WHERE a.tpo_pza = ?
            AND p.cntro_prcso = 1
            AND LTRIM(RTRIM(ISNULL(p.nmbre_crto, ''))) <> ''
            ORDER BY letra
        """
        with self._obtener_conexion() as conexion:
            cursor = conexion.cursor()
            cursor.execute(consulta, (tpo_pza,))
            return [fila[0] for fila in cursor.fetchall()]


    def contar_productos_por_letra(self, tpo_pza: int, letra: str) -> int:
        # OJO: debe llevar el MISMO INNER JOIN con imagenes que
        # obtener_productos_por_letra. Si aquí cuentas sin ese join,
        # el total queda inflado respecto a lo que la consulta paginada
        # realmente puede traer, y eso es lo que te da "no se encontraron
        # productos" al entrar (offset 0 calculado sobre un total que no
        # coincide con las filas reales disponibles).
        consulta = f"""
            SELECT COUNT(*)
            FROM [{DB_PRODUCTOS}].dbo.tpo_pzas_espcies a
            INNER JOIN [{DB_PRODUCTOS}].dbo.prdctos p
                ON p.tpo_pza = a.tpo_pza
            INNER JOIN [{DB_IMAGENES}].dbo.imagenes img
                ON img.referencia = CAST(p.cdgo_plu AS VARCHAR(50))
            WHERE a.tpo_pza = ?
            AND p.cntro_prcso = 1
            AND LEFT(p.nmbre_crto, 1) = ?
        """
        with self._obtener_conexion() as conexion:
            cursor = conexion.cursor()
            cursor.execute(consulta, (tpo_pza, letra))
            return cursor.fetchone()[0]


    def construir_paginas_letras(self, tpo_pza: int) -> List[PaginaLetra]:
        # Se mantiene la lógica de "chunks" por letra (necesaria si una
        # letra tiene más productos que TAMANO_PAGINA), pero ahora el total
        # que usa para calcular los offsets es consistente con lo que
        # obtener_productos_por_letra puede traer realmente.
        letras = self.obtener_letras_disponibles(tpo_pza)
        paginas: List[PaginaLetra] = []

        for letra in letras:
            total = self.contar_productos_por_letra(tpo_pza, letra)
            for offset in range(0, total, TAMANO_PAGINA):
                paginas.append(
                    PaginaLetra(
                        letra=letra,
                        offset=offset,
                        cantidad=min(TAMANO_PAGINA, total - offset),
                    )
                )

        return paginas

    # ------------------------------------------------------------
    # PRODUCTOS POR LETRA — paginado, SOLO imagen principal
    # (para la grilla de SeleccionDeProducto)
    # ------------------------------------------------------------
    def obtener_productos_por_letra(
        self,
        tpo_pza: int,
        letra: str,
        offset: int,
        tamano_pagina: int = TAMANO_PAGINA,
    ) -> List[Producto]:

        # La paginación (ORDER BY + OFFSET/FETCH) fuerza un Sort/Spool
        # en SQL Server. Si la columna TEXT (con_arch) pasa por ese
        # Sort, el motor puede materializarla usando su puntero interno
        # en vez del contenido real. Por eso paginamos primero SOLO con
        # columnas livianas (CTE "pagina"), y el CAST de con_arch se
        # hace después, ya sobre las 12 filas resultantes — nunca
        # dentro del Sort.
        consulta = f"""
            WITH pagina AS (
                SELECT p.cdgo_plu, p.nmbre_crto
                FROM [{DB_PRODUCTOS}].dbo.tpo_pzas_espcies a
                INNER JOIN [{DB_PRODUCTOS}].dbo.prdctos p
                    ON p.tpo_pza = a.tpo_pza
                WHERE a.tpo_pza = ?
                  AND p.cntro_prcso = 1
                  AND LEFT(p.nmbre_crto, 1) = ?
                ORDER BY p.nmbre_crto
                OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
            )
            SELECT
                pagina.cdgo_plu,
                pagina.nmbre_crto AS nom_prog,
                CAST(
                    CAST(img.con_arch AS VARCHAR(MAX))
                    AS VARBINARY(MAX)
                ) AS con_arch
            FROM pagina
            INNER JOIN [{DB_IMAGENES}].dbo.imagenes img
                ON img.referencia = CAST(pagina.cdgo_plu AS VARCHAR(50))
            ORDER BY pagina.nmbre_crto
        """

        with self._obtener_conexion() as conexion:
            cursor = conexion.cursor()
            cursor.execute(consulta, (tpo_pza, letra, offset, tamano_pagina))
            return [
                Producto(
                    cdgo_plu=fila[0],
                    nom_prog=fila[1],
                    imagen_principal=fila[2],
                )
                for fila in cursor.fetchall()
            ]

    # ------------------------------------------------------------
    # BUSCAR POR PLU — sin paginado, SOLO imagen principal
    # ------------------------------------------------------------
    def buscar_productos_por_plu(
        self,
        tpo_pza: int,
        texto_plu: str,
    ) -> List[Producto]:

        consulta = f"""
            SELECT
                p.cdgo_plu,
                p.nmbre_crto AS nom_prog,
                CAST(
                    CAST(img.con_arch AS VARCHAR(MAX))
                    AS VARBINARY(MAX)
                ) AS con_arch
            FROM [{DB_PRODUCTOS}].dbo.tpo_pzas_espcies a
            INNER JOIN [{DB_PRODUCTOS}].dbo.prdctos p
                ON p.tpo_pza = a.tpo_pza
            INNER JOIN [{DB_IMAGENES}].dbo.imagenes img
                ON img.referencia = CAST(p.cdgo_plu AS VARCHAR(50))
            WHERE a.tpo_pza = ?
              AND p.cntro_prcso = 1
              AND CAST(p.cdgo_plu AS VARCHAR(50)) LIKE ?
            ORDER BY p.nmbre_crto
        """

        with self._obtener_conexion() as conexion:
            cursor = conexion.cursor()
            cursor.execute(consulta, (tpo_pza, f"%{texto_plu}%"))
            return [
                Producto(
                    cdgo_plu=fila[0],
                    nom_prog=fila[1],
                    imagen_principal=fila[2],
                )
                for fila in cursor.fetchall()
            ]

    # ------------------------------------------------------------
    # PRODUCTO COMPLETO (6 imágenes) — para FICHA TÉCNICA, SIN paginado
    # ------------------------------------------------------------
    def obtener_producto_completo(
        self,
        tpo_pza: int,
        cdgo_plu: str,
    ) -> Optional[ProductoConImagenes]:

        consulta = f"""
            SELECT
                p.cdgo_plu,
                p.nmbre_crto AS nom_prog,
                CAST(CAST(img.con_arch AS VARCHAR(MAX)) AS VARBINARY(MAX)) AS con_arch,
                img.con_arch_2 AS con_arch_2,
                img.con_arch_3 AS con_arch_3,
                img.con_arch_4 AS con_arch_4,
                img.con_arch_5 AS con_arch_5,
                img.con_arch_6 AS con_arch_6
            FROM [{DB_PRODUCTOS}].dbo.tpo_pzas_espcies a
            INNER JOIN [{DB_PRODUCTOS}].dbo.prdctos p
                ON p.tpo_pza = a.tpo_pza
            INNER JOIN [{DB_IMAGENES}].dbo.imagenes img
                ON img.referencia = CAST(p.cdgo_plu AS VARCHAR(50))
            WHERE a.tpo_pza = ?
              AND p.cntro_prcso = 1
              AND p.cdgo_plu = ?
        """

        with self._obtener_conexion() as conexion:
            cursor = conexion.cursor()
            cursor.execute(consulta, (tpo_pza, cdgo_plu))
            fila = cursor.fetchone()

            if fila is None:
                return None

            return ProductoConImagenes(
                cdgo_plu=fila[0],
                nom_prog=fila[1],
                con_arch=fila[2],
                con_arch_2=fila[3],
                con_arch_3=fila[4],
                con_arch_4=fila[5],
                con_arch_5=fila[6],
                con_arch_6=fila[7],
            )