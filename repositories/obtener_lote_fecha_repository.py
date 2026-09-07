from models.database import obtener_conexion
from models.lotes_produccion_model import Lotes_produccion


class ObtenerLoteFechaRepository:

    def obtener_lotes_por_fecha(
        self,
        fecha
    ) -> list[Lotes_produccion]:

        query = """
            SELECT
                a.nmro_lte AS LOTE,
                a.fcha_prdccion AS FECHA_PRODUCCION
            FROM ltes_prdccion a
            INNER JOIN espcies b
                ON a.espcie = b.espcie
            WHERE  a.fcha_prdccion = ?
              AND a.cntro_prcso = 1
              AND a.tpo_lte = 1
              AND a.estdo = 0
              --AND a.estdo_pt = 0
            ORDER BY a.nmro_lte
        """

        with obtener_conexion() as conexion:

            cursor = conexion.cursor()

            cursor.execute(
                query,
                fecha
            )

            filas = cursor.fetchall()

            lotes = []

            for fila in filas:

                lote = Lotes_produccion(
                    lote=str(fila.LOTE),
                    fecha_produccion = fila.FECHA_PRODUCCION
                )

                lotes.append(lote)

            return lotes

    # ==========================================================
    # FECHA + ESPECIE
    # ==========================================================

    def obtener_lotes_por_especie(
        self,
        fecha,
        num_especie
    ) -> list[Lotes_produccion]:

        query = """
            SELECT
                a.nmro_lte AS LOTE,
                a.fcha_prdccion AS FECHA_PRODUCCION,
                a.espcie AS NUM_ESPECIE,
                b.nmbre AS ESPECIE
            FROM ltes_prdccion a
            INNER JOIN espcies b
                ON a.espcie = b.espcie
            WHERE a.fcha_prdccion = ?
              AND a.cntro_prcso = 1
              AND a.tpo_lte = 1
              AND a.estdo = 0
              --AND a.estdo_pt = 0
              AND a.espcie = ?
            ORDER BY a.nmro_lte
        """

        with obtener_conexion() as conexion:

            cursor = conexion.cursor()

            cursor.execute(
                query,
                fecha,
                num_especie
            )

            filas = cursor.fetchall()

            lotes = []

            for fila in filas:

                lote = Lotes_produccion(
                    lote=str(fila.LOTE),
                    fecha_produccion=fila.FECHA_PRODUCCION,
                    numEspecie=int(
                        fila.NUM_ESPECIE
                    ),
                    especie=str(
                        fila.ESPECIE
                    )
                )

                lotes.append(lote)

            return lotes