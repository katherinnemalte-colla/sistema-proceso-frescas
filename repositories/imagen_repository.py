import os
import math
from dataclasses import dataclass, field
from typing import List, Optional

DB_PRODUCTOS = os.getenv("DB_DATABASE")
DB_IMAGENES = os.getenv("DB_DATABASE_1")



# Cantidad de productos que se traen por "página" dentro de una misma letra.
TAMANO_PAGINA = 12


@dataclass
class Producto:

    cdgo_plu: str
    nom_prog: str
    imagenes: List[Optional[bytes]] = field(default_factory=list)

    @property
    def imagen_principal(self) -> Optional[bytes]:
        """Primera imagen no nula de la lista (con_arch, con_arch_2, ...)."""
        for imagen in self.imagenes:
            if imagen:
                return imagen
        return None


@dataclass
class PaginaLetra:
    """
    Representa un botón del paginador alfabético.
    Si una letra tiene más productos de los que caben en TAMANO_PAGINA,
    se generan varias PaginaLetra con la MISMA letra pero distinto offset,
    de forma que el botón de esa letra se repite (una por cada página).
    """
    letra: str
    offset: int
    pagina: int  # 1, 2, 3... dentro de esa letra


class ImagenRepository:
    """
    Repositorio encargado de traer, desde SQL Server, los productos
    (con sus imágenes) que se muestran en la pantalla de selección
    de producto, ya sea navegando por letra o filtrando por PLU.
    """

    _SELECT_PRODUCTO_IMAGEN = f"""
        SELECT
            p.cdgo_plu,
            p.nmbre_crto AS nom_prog,
            CAST(
                CAST(i.con_arch AS VARCHAR(MAX))
                AS VARBINARY(MAX)
            ) AS con_arch
        FROM [{DB_IMAGENES}].dbo.imagenes i
        INNER JOIN [{DB_PRODUCTOS}].dbo.prdctos p
            ON i.referencia = CAST(p.cdgo_plu AS VARCHAR(50))
        WHERE i.nom_prog = 'productos'
          AND p.cntro_prcso = 1
          AND p.cdgo_espcie = ?
    """

    def __init__(self, conexion_factory):

        self._conexion_factory = conexion_factory

    # ------------------------------------------------------------------
    # Letras disponibles (paginador alfabético)
    # ------------------------------------------------------------------
    def obtener_letras_disponibles(self, cdgo_espcie: int) -> List[str]:
        
        query = f"""
        SELECT DISTINCT
            UPPER(LEFT(LTRIM(p.nmbre_crto), 1)) AS letra
        FROM [{DB_PRODUCTOS}].dbo.prdctos AS p
        INNER JOIN [{DB_IMAGENES}].dbo.imagenes AS i
            ON i.referencia = CAST(p.cdgo_plu AS VARCHAR(50))
        WHERE i.nom_prog = 'productos'
        AND p.cntro_prcso = 1
        AND p.cdgo_espcie = ?
        ORDER BY letra
    """
        with self._conexion_factory() as conexion:
            cursor = conexion.cursor()
            cursor.execute(query, (cdgo_espcie,))
            filas = cursor.fetchall()
        return [fila.letra for fila in filas if fila.letra]

    def contar_productos_por_letra(self, cdgo_espcie: int, letra: str) -> int:
        """Cantidad total de productos cuyo nombre empieza por `letra`."""
        query = f"""
            SELECT COUNT(*) AS total
            FROM [{DB_PRODUCTOS}].dbo.prdctos p
            INNER JOIN [{DB_IMAGENES}].dbo.imagenes i
                ON i.referencia = CAST(p.cdgo_plu AS VARCHAR(50))
            WHERE i.nom_prog = 'productos'
              AND p.cntro_prcso = 1
              AND p.cdgo_espcie = ?
              AND UPPER(LEFT(LTRIM(p.nmbre_crto), 1)) = ?
        """
        with self._conexion_factory() as conexion:
            cursor = conexion.cursor()
            cursor.execute(query, (cdgo_espcie, letra))
            return int(cursor.fetchone().total)

    def construir_paginas_letras(self, cdgo_espcie: int) -> List[PaginaLetra]:
        """
        Arma la lista completa de botones del paginador alfabético,
        repitiendo la letra tantas veces como páginas necesite para
        mostrar todos sus productos (TAMANO_PAGINA por página).
        """
        paginas: List[PaginaLetra] = []
        for letra in self.obtener_letras_disponibles(cdgo_espcie):
            total = self.contar_productos_por_letra(cdgo_espcie, letra)
            num_paginas = max(1, math.ceil(total / TAMANO_PAGINA))
            for pagina in range(num_paginas):
                paginas.append(
                    PaginaLetra(
                        letra=letra,
                        offset=pagina * TAMANO_PAGINA,
                        pagina=pagina + 1,
                    )
                )
        return paginas

    # ------------------------------------------------------------------
    # Productos de una letra (paginados)
    # ------------------------------------------------------------------
    def obtener_productos_por_letra(
        self,
        cdgo_espcie: int,
        letra: str,
        offset: int = 0,
        limite: int = TAMANO_PAGINA,
    ) -> List[Producto]:
        query = (
            self._SELECT_PRODUCTO_IMAGEN
            + """
              AND UPPER(LEFT(LTRIM(p.nmbre_crto), 1)) = ?
            ORDER BY p.nmbre_crto
            OFFSET ? ROWS
            FETCH NEXT ? ROWS ONLY
            """
        )
        with self._conexion_factory() as conexion:
            cursor = conexion.cursor()
            cursor.execute(query, (cdgo_espcie, letra, offset, limite))
            filas = cursor.fetchall()
        return [self._fila_a_producto(fila) for fila in filas]

    # ------------------------------------------------------------------
    # Filtro por N° PLU (p.cdgo_plu)
    # ------------------------------------------------------------------
    def buscar_productos_por_plu(self, cdgo_espcie: int, texto_plu: str) -> List[Producto]:
        """
        Filtra productos cuyo p.cdgo_plu contenga `texto_plu`.
        Se usa cuando el usuario escribe en el campo "Filtro por N° PLU".
        """
        query = (
            self._SELECT_PRODUCTO_IMAGEN
            + """
              AND CAST(p.cdgo_plu AS VARCHAR(50)) LIKE ?
            ORDER BY p.nmbre_crto
            """
        )
        texto_busqueda = f"%{texto_plu.strip()}%"
        with self._conexion_factory() as conexion:
            cursor = conexion.cursor()
            cursor.execute(query, (cdgo_espcie, texto_busqueda))
            filas = cursor.fetchall()
        return [self._fila_a_producto(fila) for fila in filas]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _fila_a_producto(fila) -> Producto:
        return Producto(
            cdgo_plu=str(fila.cdgo_plu),
            nom_prog=fila.nom_prog,
            imagenes=fila.con_arch,
        )