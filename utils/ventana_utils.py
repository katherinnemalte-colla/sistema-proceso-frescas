import os
from PySide6.QtGui import QGuiApplication, QPixmap, QFont
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget


def _pantalla_disponible():
    pantalla = QGuiApplication.primaryScreen()
    if pantalla is None:
        raise RuntimeError("No se encontró una pantalla disponible.")
    return pantalla.availableGeometry()


def centrar_ventana(ventana: QWidget, referencia: QWidget = None):
    if referencia is not None:
        area = referencia.geometry()
    else:
        area = _pantalla_disponible()
    x = area.x() + (area.width() - ventana.width()) // 2
    y = area.y() + (area.height() - ventana.height()) // 2
    ventana.move(x, y)


def aplicar_tamano(
    ventana: QWidget,
    modo: str = "centrado",
    ancho_pct: float = 0.95,
    alto_pct: float = 0.95,
    referencia: QWidget = None,
):
    if modo == "completo":
        ventana.showMaximized()
    elif modo == "centrado":
        pantalla = _pantalla_disponible()
        ancho = int(pantalla.width() * ancho_pct)
        alto = int(pantalla.height() * alto_pct)
        ventana.resize(ancho, alto)
        centrar_ventana(ventana, referencia)
    else:
        raise ValueError(f"Modo de tamaño no reconocido: {modo}")


ANCHO_REFERENCIA = 1024
ALTO_REFERENCIA = 768
FACTOR_MINIMO = 0.70
FACTOR_MAXIMO = 1.4
_factor_actual = None


def factor_escala(forzar_recalculo: bool = False) -> float:
    global _factor_actual
    if _factor_actual is None or forzar_recalculo:
        pantalla = _pantalla_disponible()
        factor_x = pantalla.width() / ANCHO_REFERENCIA
        factor_y = pantalla.height() / ALTO_REFERENCIA
        factor = min(factor_x, factor_y)
        _factor_actual = max(FACTOR_MINIMO, min(FACTOR_MAXIMO, factor))
    return _factor_actual


def escalar(valor_base: int) -> int:
    return max(1, round(valor_base * factor_escala()))


def escalar_fuente(tamano_base: int) -> int:
    factor = max(0.75, factor_escala())
    return max(9, round(tamano_base * factor))


def fuente(tamano_base: int, negrita: bool = False, familia: str = "Recoleta") -> QFont:
    f = QFont(familia, escalar_fuente(tamano_base))
    f.setBold(negrita)
    return f


def _icono_pixmap(_ruta_icono, nombre_archivo, tamano):
    ruta = _ruta_icono(nombre_archivo)
    if not os.path.isfile(ruta):
        return None
    pixmap = QPixmap(ruta)
    if pixmap.isNull():
        return None
    return pixmap.scaledToWidth(escalar(tamano), Qt.SmoothTransformation)