import logging
import re
from typing import Callable, Optional
import os

logger = logging.getLogger(__name__)

DB_PRODUCTOS = os.getenv("DB_DATABASE")


def obtener_puerto_com(
    obtener_conexion: Callable,
    codigo_proceso: str,
) -> Optional[str]:
    """
    Consulta en BASICAS el puerto COM configurado para este equipo
    (codigo_proceso = nombre del host).

    Retorna:
        str: nombre del puerto normalizado (ej. "COM7").
        None: si no hay conexión configurada, falta la variable de
              entorno DB_DATABASE, la consulta falla, no hay fila,
              o el valor recibido no es válido.
    """

    if obtener_conexion is None:
        logger.warning("No se configuró la conexión SQL para consultar el puerto.")
        return None

    if not DB_PRODUCTOS:
        logger.error(
            "La variable de entorno DB_DATABASE no está definida. "
            "No se puede construir la consulta a BASICAS."
        )
        return None

    try:
        with obtener_conexion() as conexion:
            consulta = f"""
                SELECT VALOR1
                FROM [{DB_PRODUCTOS}].dbo.BASICAS
                WHERE nombr_grup = ?
                  AND ELEME_GRUP = ?
                  AND codig_elem = ?
            """

            cursor = conexion.cursor()
            try:
                cursor.execute(
                    consulta,
                    (
                        "COMUNICACION",
                        "PUERTO_COM",
                        codigo_proceso,
                    ),
                )
                
                
                
                
                fila = cursor.fetchone()

                if not fila or fila[0] is None:
                    logger.warning(
                        "No existe un puerto configurado en BASICAS para %s.",
                        codigo_proceso,
                    )
                    return None

                valor = str(fila[0]).strip().upper()

                if not valor:
                    logger.warning("VALOR1 está vacío para %s.", codigo_proceso)
                    return None

                # Si el valor viene con ceros de relleno pegados (ej. "70000" en vez de "7"),
                # nos quedamos solo con el primer dígito significativo.
                solo_numeros = re.sub(r"\D", "", valor)

                if solo_numeros:
                    valor = solo_numeros[0]

                puerto = valor if valor.startswith("COM") else f"COM{valor}"

                if not re.fullmatch(r"COM\d+", puerto):
                    logger.warning(
                        "Puerto inválido recibido desde BASICAS: %s",
                        valor,
                    )
                    return None

                logger.info("Puerto configurado para %s: %s", codigo_proceso, puerto)

                return puerto

            finally:
                cursor.close()

    except Exception:
        logger.exception(
            "Error consultando el puerto configurado para %s en la base %s.",
            codigo_proceso,
            DB_PRODUCTOS,
        )
        return None