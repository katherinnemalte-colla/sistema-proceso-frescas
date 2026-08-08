"""
Ventana de fondo: ocupa toda la pantalla, muestra la fecha/hora en vivo
y la versión de la app. El login se muestra ENCIMA de esta ventana.
"""

from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout
from PySide6.QtCore import Qt, QTimer, QDateTime
from utils.ventana_utils import aplicar_tamano

VERSION_APP = "v1.0.0"  # centraliza aquí y súbela con cada release


class VentanaFondo(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sistema de Inventarios")

        aplicar_tamano(self, modo="completo")

        self.etiqueta_reloj = QLabel()
        self.etiqueta_reloj.setAlignment(Qt.AlignCenter)
        self.etiqueta_reloj.setStyleSheet("font-size: 28px; color: white;")

        self.etiqueta_version = QLabel(f"Versión {VERSION_APP}")
        self.etiqueta_version.setAlignment(Qt.AlignRight | Qt.AlignBottom)
        self.etiqueta_version.setStyleSheet("font-size: 12px; color: #cccccc; padding: 10px;")

        layout = QVBoxLayout()
        layout.addStretch()
        layout.addWidget(self.etiqueta_reloj)
        layout.addStretch()
        layout.addWidget(self.etiqueta_version)
        self.setLayout(layout)
        self.setStyleSheet("background-color: #1e2430;")  # color de fondo de toda la app

        self._iniciar_reloj()

    def _iniciar_reloj(self):
        self._actualizar_hora()
        self.temporizador = QTimer(self)
        self.temporizador.timeout.connect(self._actualizar_hora)
        self.temporizador.start(1000)  # actualiza cada 1 segundo

    def _actualizar_hora(self):
        ahora = QDateTime.currentDateTime()
        self.etiqueta_reloj.setText(ahora.toString("dddd, dd 'de' MMMM 'de' yyyy   -   hh:mm:ss"))