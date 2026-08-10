"""
Ventana "Ficha Técnica".
Se abre al presionar cualquiera de los productos en la matriz
de SeleccionDeProducto. Por ahora es un placeholder: reemplaza
el contenido del layout cuando tengas el diseño real de la ficha.
"""

from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout
from PySide6.QtCore import Qt

from utils.ventana_utils import aplicar_tamano


class FichaTecnica(QWidget):
    def __init__(self, usuario, producto: str, lote: str, fecha_produccion: str, especie: str):
        super().__init__()
        self.usuario = usuario
        self.producto = producto
        self.lote = lote
        self.fecha_produccion = fecha_produccion
        self.especie = especie

        self.setWindowTitle(f"Ficha Técnica - {producto}")
        aplicar_tamano(self, modo="completo")
        self.setStyleSheet("QWidget { background-color: #F5F8F8; }")

        layout = QVBoxLayout()
        layout.setContentsMargins(40, 40, 40, 40)

        titulo = QLabel(f"Ficha Técnica: {producto}")
        titulo.setAlignment(Qt.AlignCenter)
        titulo.setStyleSheet("font-size: 26px; font-weight: bold; color: #115E67;")
        layout.addWidget(titulo)

        info = QLabel(
            f"Lote: {lote}\n"
            f"Fecha de producción: {fecha_produccion}\n"
            f"Especie: {especie}"
        )
        info.setAlignment(Qt.AlignCenter)
        info.setStyleSheet("font-size: 14px; color: #444; margin-top: 20px;")
        layout.addWidget(info)

        layout.addStretch()

        # Aquí va el contenido real de la ficha técnica cuando lo definas.

        self.setLayout(layout)