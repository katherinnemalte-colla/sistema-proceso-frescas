"""
Funciones reutilizables para el tamaño y posición de las ventanas.
En vez de repetir esta lógica en cada ventana, todas llaman a
`aplicar_tamano()` con el modo que necesiten.
"""

from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QWidget


def _pantalla_disponible():
    return QGuiApplication.primaryScreen().availableGeometry()


def centrar_ventana(ventana: QWidget, referencia: QWidget = None):
    """
    Centra `ventana` en la pantalla, o dentro de `referencia` si se indica
    (útil para centrar el login sobre la ventana de fondo).
    """
    if referencia is not None:
        area = referencia.geometry()
    else:
        area = _pantalla_disponible()

    x = area.x() + (area.width() - ventana.width()) // 2
    y = area.y() + (area.height() - ventana.height()) // 2
    ventana.move(x, y)


def aplicar_tamano(ventana: QWidget, modo: str = "centrado", ancho_pct: float = 0.3, alto_pct: float = 0.4, referencia: QWidget = None):
    """
    Modo global para dimensionar cualquier ventana. Se llama UNA vez,
    típicamente en el __init__ de cada ventana, antes de mostrarla.

    modo="completo"  -> ocupa toda la pantalla disponible (para la ventana de fondo).
    modo="centrado"  -> toma un porcentaje de la pantalla y se centra
                         (para diálogos como el login).
    """
    if modo == "completo":
        area = _pantalla_disponible()
        ventana.setGeometry(area)

    elif modo == "centrado":
        pantalla = _pantalla_disponible()
        ancho = int(pantalla.width() * ancho_pct)
        alto = int(pantalla.height() * alto_pct)
        ventana.resize(ancho, alto)
        centrar_ventana(ventana, referencia)

    else:
        raise ValueError(f"Modo de tamaño no reconocido: {modo}")