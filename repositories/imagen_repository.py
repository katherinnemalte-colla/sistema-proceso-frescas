import pyodbc

from models.database import conectar_bd


class ImagenRepository:

    def obtener_imagenes_productos(self, pagina: int = 1, por_pagina: int = 20):

        conexion = conectar_bd(database_key="DB_DATABASE_1")

        try:
            cursor = conexion.cursor()

            offset = (pagina - 1) * por_pagina

            consulta = """
                SELECT
                    nom_prog,
                    CAST(CAST(con_arch AS VARCHAR(MAX)) AS VARBINARY(MAX)) AS con_arch
                FROM imagenes
                WHERE nom_prog <> 'productos'
                ORDER BY nom_prog
                OFFSET ? ROWS
                FETCH NEXT ? ROWS ONLY
            """

            cursor.execute(
                consulta,
                offset,
                por_pagina
            )

            imagenes = []

            for fila in cursor.fetchall():
                imagenes.append({
                    "nom_prog": fila.nom_prog,
                    "imagen": bytes(fila.con_arch)
                    if fila.con_arch is not None
                    else None
                })

            return imagenes

        finally:
            conexion.close()

    def contar_imagenes_productos(self):
        """Devuelve cuántas imágenes de productos existen."""

        conexion = conectar_bd(database_key="DB_DATABASE_1")

        try:
            cursor = conexion.cursor()

            cursor.execute("""
                SELECT COUNT(*)
                FROM imagenes
                WHERE nom_prog = 'productos'
            """)

            return cursor.fetchone()[0]

        finally:
            conexion.close()