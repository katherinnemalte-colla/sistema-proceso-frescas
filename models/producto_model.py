from models.database import conectar_bd


def contar_productos():
    """Cuenta el total de productos, para calcular cuántas páginas hay"""
    conexion = conectar_bd()
    cursor = conexion.cursor()
    cursor.execute("SELECT COUNT(*) FROM prdctos")
    total = cursor.fetchone()[0]
    conexion.close()
    return total


def obtener_productos_paginado(pagina=1, tamano_pagina=20):
    """
    Trae solo los productos de la página solicitada, usando
    OFFSET/FETCH de SQL Server (paginación eficiente a nivel de servidor)
    """
    offset = (pagina - 1) * tamano_pagina

    conexion = conectar_bd()
    cursor = conexion.cursor()
    cursor.execute(
        """
        SELECT cdgo_plu, nmbre_prdcto
        FROM prdctos
        ORDER BY cdgo_plu
        OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
        """,
        (offset, tamano_pagina)
    )
    resultados = cursor.fetchall()
    conexion.close()
    return resultados