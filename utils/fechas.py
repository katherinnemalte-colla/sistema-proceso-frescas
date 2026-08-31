"""
Utilidades para normalizar fechas que pueden llegar en distintos
tipos (date, datetime o string) desde diferentes fuentes: base de
datos, campos de la interfaz, u otros módulos del sistema.
"""

from datetime import date, datetime
from typing import Optional


def _asegurar_date(valor, formato: str = "%Y-%m-%d") -> Optional[date]:
    """
    Normaliza un valor de fecha a `date`, sin importar si llega como
    date, datetime o string. Evita que un string colado en algún punto
    del flujo rompa los cálculos más adelante (sumas con timedelta,
    comparaciones, etc.).

    Parámetros:
        valor: el valor a normalizar (date, datetime, str o None).
        formato: formato preferido a intentar primero si `valor` es
                 string (por defecto "%Y-%m-%d").

    Devuelve:
        Un objeto `date`, o `None` si `valor` era `None`.

    Lanza:
        ValueError si `valor` es un string que no coincide con
        ninguno de los formatos conocidos.
        TypeError si `valor` no es date, datetime, str ni None.
    """
    if valor is None:
        return None

    if isinstance(valor, datetime):
        return valor.date()

    if isinstance(valor, date):
        return valor

    if isinstance(valor, str):
        for fmt in (formato, "%Y-%m-%d", "%d/%m/%Y"):
            try:
                return datetime.strptime(valor, fmt).date()
            except ValueError:
                continue
        raise ValueError(
            f"No se pudo convertir '{valor}' a date con los formatos conocidos"
        )

    raise TypeError(f"Tipo de fecha no soportado: {type(valor)}")