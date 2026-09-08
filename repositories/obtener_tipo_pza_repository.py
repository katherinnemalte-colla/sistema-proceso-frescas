"""
obtener_tipo_pza_repository.py

Repositorio para el flujo de RES (vaca): en vez de filtrar por especie
(como hace ImagenRepository con cdgo_espcie), filtra por tipo de pieza
(tpo_pza: 1 = DELANTERO, 2 = TRASERO).

Expone la MISMA interfaz pública que ImagenRepository (mismos nombres
de método, mismo dataclass PaginaLetra) para que SeleccionDeProducto
pueda usar cualquiera de los dos repositorios de forma intercambiable,
solo cambiando qué instancia y qué valor de filtro le pasa.
"""

import os
from dataclasses import dataclass
from typing import List, Optional


import os
from dataclasses import dataclass
from typing import List, Optional


DB_PRODUCTOS = os.getenv("DB_DATABASE")
DB_IMAGENES = os.getenv("DB_DATABASE_1")

# Cantidad de productos por página dentro de una misma letra.
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
    cdgo_plu: str
    nom_prog: str
    con_arch: Optional[bytes]
    con_arch_2: Optional[bytes]
    con_arch_3: Optional[bytes]
    con_arch_4: Optional[bytes]
    con_arch_5: Optional[bytes]
    con_arch_6: Optional[bytes]

    def imagenes(self) -> List[bytes]:
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

    def __init__(self, obtener_conexion):
        self._obtener_conexion = obtener_conexion

    # ------------------------------------------------------------
    # LETRAS DISPONIBLES
    # ------------------------------------------------------------
    def obtener_letras_disponibles(
        self,
        cod_emprsa: int,
        cdgo_espcie: int,
        tpo_pza: int,
    ) -> List[str]:

        consulta = f"""
            SELECT DISTINCT
                LEFT(p.nmbre_crto, 1) AS letra

            FROM [{DB_PRODUCTOS}].dbo.tpo_pzas_espcies a

            INNER JOIN [{DB_PRODUCTOS}].dbo.prdctos p
                ON p.tpo_pza = a.tpo_pza

            INNER JOIN [{DB_IMAGENES}].dbo.imagenes img
                ON img.referencia = CAST(p.cdgo_plu AS VARCHAR(50))

            WHERE a.tpo_pza = ?
              AND p.cntro_prcso = 1
              AND p.cdgo_espcie = ?
              AND p.estdo = 0
              AND img.nom_prog = 'productos'
              AND LTRIM(
                    RTRIM(
                        ISNULL(p.nmbre_crto, '')
                    )
                  ) <> ''

              AND EXISTS (
                  SELECT 1
                  FROM [{DB_PRODUCTOS}].dbo.ficha_tec_prod_cli ft
                  WHERE 
                  --ft.cod_emprsa = ?
                  (? IS NULL OR ? = 1 OR ft.cod_emprsa = ?)
                    AND ft.cdgo_plu = p.cdgo_plu
              )

            ORDER BY letra
        """

        with self._obtener_conexion() as conexion:
            cursor = conexion.cursor()
            cursor.execute(
                consulta,
                (
                    tpo_pza,
                    cdgo_espcie,
                    cod_emprsa,
                    cod_emprsa,
                    cod_emprsa,
                ),
            )

            return [fila[0] for fila in cursor.fetchall()]

    # ------------------------------------------------------------
    # CONTAR PRODUCTOS POR LETRA
    # ------------------------------------------------------------
    def contar_productos_por_letra(
        self,
        cod_emprsa: int,
        cdgo_espcie: int,
        tpo_pza: int,
        letra: str,
    ) -> int:

        consulta = f"""
            SELECT COUNT(*)
            FROM [{DB_PRODUCTOS}].dbo.tpo_pzas_espcies a
            INNER JOIN [{DB_PRODUCTOS}].dbo.prdctos p
                ON p.tpo_pza = a.tpo_pza
            INNER JOIN [{DB_IMAGENES}].dbo.imagenes img
                ON img.referencia = CAST(p.cdgo_plu AS VARCHAR(50))
            WHERE a.tpo_pza = ?
              AND p.cntro_prcso = 1
              AND p.cdgo_espcie = ?
              AND p.estdo = 0
              AND img.nom_prog = 'productos'
              AND LEFT(p.nmbre_crto, 1) = ?
              AND EXISTS (
                  SELECT 1
                  FROM [{DB_PRODUCTOS}].dbo.ficha_tec_prod_cli ft
                  WHERE 
                  --ft.cod_emprsa = ?
                  (? IS NULL OR ? = 1 OR ft.cod_emprsa = ?)
                    AND ft.cdgo_plu = p.cdgo_plu
              )
        """
        with self._obtener_conexion() as conexion:
            cursor = conexion.cursor()
            cursor.execute(
                consulta,
                (
                    tpo_pza,
                    cdgo_espcie,
                    letra,
                    cod_emprsa,
                    cod_emprsa,
                    cod_emprsa,
                ),
            )

            return cursor.fetchone()[0]

    # ------------------------------------------------------------
    # CONSTRUIR PÁGINAS POR LETRA
    # ------------------------------------------------------------
    def construir_paginas_letras(
        self,
        cod_emprsa: int,
        cdgo_espcie: int,
        tpo_pza: int,
    ) -> List[PaginaLetra]:

        letras = self.obtener_letras_disponibles(
            cod_emprsa,
            cdgo_espcie,
            tpo_pza,
        )
        paginas: List[PaginaLetra] = []

        for letra in letras:
            total = self.contar_productos_por_letra(
                cod_emprsa,
                cdgo_espcie,
                tpo_pza,
                letra,
            )
            for offset in range(0, total, TAMANO_PAGINA):
                paginas.append(
                    PaginaLetra(
                        letra=letra,
                        offset=offset,
                        cantidad=min(
                            TAMANO_PAGINA,
                            total - offset,
                        ),
                    )
                )

        return paginas

    # ------------------------------------------------------------
    # PRODUCTOS POR LETRA — PAGINADO
    # ------------------------------------------------------------
    def obtener_productos_por_letra(
        self,
        cod_emprsa: Optional[int],
        cdgo_espcie: int,
        tpo_pza: int,
        letra: str,
        offset: int,
        tamano_pagina: int = TAMANO_PAGINA,
    ) -> List[Producto]:

        consulta = f"""
            WITH pagina AS (
                SELECT DISTINCT
                    p.cdgo_plu,
                    p.nmbre_crto
                FROM [{DB_PRODUCTOS}].dbo.tpo_pzas_espcies a
                INNER JOIN [{DB_PRODUCTOS}].dbo.prdctos p
                    ON p.tpo_pza = a.tpo_pza
                WHERE a.tpo_pza = ?
                  AND p.cntro_prcso = 1
                  AND p.cdgo_espcie = ?
                  AND p.estdo = 0
                  
                  AND LEFT(p.nmbre_crto, 1) = ?
                  AND EXISTS (
                    SELECT 1
                    FROM [{DB_PRODUCTOS}].dbo.ficha_tec_prod_cli ft
                    WHERE ft.cdgo_plu = p.cdgo_plu
                    AND (? IS NULL OR ? = 1 OR ft.cod_emprsa = ?)
                )

                ORDER BY p.nmbre_crto
                OFFSET ? ROWS
                FETCH NEXT ? ROWS ONLY
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
                AND img.nom_prog = 'productos'
            ORDER BY pagina.nmbre_crto
        """

        with self._obtener_conexion() as conexion:
            cursor = conexion.cursor()

            cursor.execute(
                consulta,
                (
                    tpo_pza,
                    cdgo_espcie,
                    letra,
                    cod_emprsa,
                    cod_emprsa,
                    cod_emprsa,
                    offset,
                    tamano_pagina,
                ),
            )

            return [
                Producto(
                    cdgo_plu=fila[0],
                    nom_prog=fila[1],
                    imagen_principal=fila[2],
                )
                for fila in cursor.fetchall()
            ]

    # ------------------------------------------------------------
    # BUSCAR POR PLU — SOLO IMAGEN PRINCIPAL
    # ------------------------------------------------------------
    def buscar_productos_por_plu(
        self,
        cod_emprsa: int,
        cdgo_espcie: int,
        tpo_pza: int,
        texto_plu: str,
    ) -> List[Producto]:

        consulta = f"""
            SELECT DISTINCT
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
                ON img.referencia =
                   CAST(p.cdgo_plu AS VARCHAR(50))
            WHERE a.tpo_pza = ?
              AND p.cntro_prcso = 1
              AND p.cdgo_espcie = ?
              AND p.estdo = 0
              AND img.nom_prog = 'productos'
              AND CAST(p.cdgo_plu AS VARCHAR(50)) LIKE ?
              AND EXISTS (
                  SELECT 1
                  FROM [{DB_PRODUCTOS}].dbo.ficha_tec_prod_cli ft
                  WHERE 
                  --ft.cod_emprsa = ?
                  (? IS NULL OR ? = 1 OR ft.cod_emprsa = ?)
                    AND ft.cdgo_plu = p.cdgo_plu
              )
            ORDER BY p.nmbre_crto
        """

        with self._obtener_conexion() as conexion:
            cursor = conexion.cursor()
            cursor.execute(
                consulta,
                (
                    tpo_pza,
                    cdgo_espcie,
                    f"%{texto_plu}%",
                    cod_emprsa,
                    cod_emprsa,
                    cod_emprsa,
                ),
            )
            return [
                Producto(
                    cdgo_plu=fila[0],
                    nom_prog=fila[1],
                    imagen_principal=fila[2],
                )
                for fila in cursor.fetchall()
            ]

    # ------------------------------------------------------------
    # PRODUCTO COMPLETO — 6 IMÁGENES
    # ------------------------------------------------------------
    def obtener_producto_completo(
        self,
        cod_emprsa: int,
        cdgo_espcie: int,
        tpo_pza: int,
        cdgo_plu: str,
    ) -> Optional[ProductoConImagenes]:

        consulta = f"""
            SELECT
                p.cdgo_plu,
                p.nmbre_crto AS nom_prog,
                CAST(
                    CAST(img.con_arch AS VARCHAR(MAX))
                    AS VARBINARY(MAX)
                ) AS con_arch,
                img.con_arch_2 AS con_arch_2,
                img.con_arch_3 AS con_arch_3,
                img.con_arch_4 AS con_arch_4,
                img.con_arch_5 AS con_arch_5,
                img.con_arch_6 AS con_arch_6
            FROM [{DB_PRODUCTOS}].dbo.tpo_pzas_espcies a
            INNER JOIN [{DB_PRODUCTOS}].dbo.prdctos p
                ON p.tpo_pza = a.tpo_pza
            INNER JOIN [{DB_IMAGENES}].dbo.imagenes img
                ON img.referencia =
                   CAST(p.cdgo_plu AS VARCHAR(50))
            WHERE a.tpo_pza = ?
              AND p.cntro_prcso = 1
              AND p.cdgo_espcie = ?
              AND p.estdo = 0
              AND img.nom_prog = 'productos'
              AND p.cdgo_plu = ?
              AND EXISTS (
                  SELECT 1
                  FROM [{DB_PRODUCTOS}].dbo.ficha_tec_prod_cli ft
                  WHERE 
                  --ft.cod_emprsa = ?
                  (? IS NULL OR ? = 1 OR ft.cod_emprsa = ?)
                    AND ft.cdgo_plu = p.cdgo_plu
              )
        """

        with self._obtener_conexion() as conexion:
            cursor = conexion.cursor()

            cursor.execute(
                consulta,
                (
                    tpo_pza,
                    cdgo_espcie,
                    cdgo_plu,
                    cod_emprsa,
                    cod_emprsa,
                    cod_emprsa,
                ),
            )
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