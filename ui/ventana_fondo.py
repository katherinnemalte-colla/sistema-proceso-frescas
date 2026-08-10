"""
Ventana de fondo: ocupa toda la pantalla, muestra una imagen
de fondo, fecha/hora en vivo y versión de la aplicación.
El login se muestra ENCIMA de esta ventana.
"""

from PySide6.QtWidgets import (
    QWidget,
    QLabel,
    QVBoxLayout,
    QHBoxLayout
)

from PySide6.QtCore import (
    Qt,
    QTimer,
    QDateTime,
    QLocale
)

from PySide6.QtGui import QPixmap

from utils.ventana_utils import aplicar_tamano


VERSION_APP = "v1.0.0"


class VentanaFondo(QWidget):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Etiquetas 2 en 1")

        aplicar_tamano(
            self,
            modo="completo"
        )

        # ==========================================================
        # IMAGEN DE FONDO
        # ==========================================================

        self.imagen_fondo = QLabel(self)

        self.imagen_fondo.setAlignment(
            Qt.AlignCenter
        )

        self.imagen_fondo.setScaledContents(False)

        pixmap = QPixmap(
            "assets/icons/login/fondo_login.png"
        )

        self.imagen_fondo.setPixmap(
            pixmap
        )

        # La imagen debe quedar detrás de todo
        self.imagen_fondo.lower()

        # ==========================================================
        # CAPA OSCURA SOBRE LA IMAGEN
        # ==========================================================

        self.capa_oscura = QLabel(self)

        self.capa_oscura.setStyleSheet("""
            background-color: rgba(3, 35, 40, 175);
        """)

        self.capa_oscura.setAttribute(
            Qt.WA_TransparentForMouseEvents
        )

        # La capa queda encima de la imagen
        self.capa_oscura.raise_()

        # ==========================================================
        # RELOJ
        # ==========================================================

        self.etiqueta_reloj = QLabel()

        self.etiqueta_reloj.setAlignment(
            Qt.AlignLeft | Qt.AlignVCenter
        )

        self.etiqueta_reloj.setStyleSheet("""
            color: white;
            font-size: 18px;
            font-weight: 500;
            background: transparent;
        """)

        # ==========================================================
        # VERSION
        # ==========================================================

        self.etiqueta_version = QLabel(
            f"Versión {VERSION_APP}"
        )

        self.etiqueta_version.setAlignment(
            Qt.AlignRight | Qt.AlignVCenter
        )

        self.etiqueta_version.setStyleSheet("""
            color: #C5D4D6;
            font-size: 12px;
            background: transparent;
        """)

        # ==========================================================
        # PIE DE PANTALLA
        # ==========================================================

        pie = QHBoxLayout()

        pie.setContentsMargins(
            25,
            12,
            25,
            12
        )

        pie.addWidget(
            self.etiqueta_reloj
        )

        pie.addStretch()

        pie.addWidget(
            self.etiqueta_version
        )

        # ==========================================================
        # LAYOUT PRINCIPAL
        # ==========================================================

        layout = QVBoxLayout()

        layout.setContentsMargins(
            0,
            0,
            0,
            0
        )

        layout.addStretch()

        layout.addLayout(
            pie
        )

        self.setLayout(
            layout
        )

        # Fondo de respaldo por si la imagen tarda en cargar
        self.setStyleSheet("""
            background-color: #082F35;
        """)

        # ==========================================================
        # RELOJ
        # ==========================================================

        self._iniciar_reloj()

        # Ajustar imagen y capa al tamaño inicial
        self._ajustar_fondo()

    # ==============================================================
    # AJUSTAR IMAGEN AL TAMAÑO DE LA VENTANA
    # ==============================================================

    def _ajustar_fondo(self):

        self.imagen_fondo.setGeometry(
            self.rect()
        )

        self.capa_oscura.setGeometry(
            self.rect()
        )

        pixmap = self.imagen_fondo.pixmap()

        if pixmap is None:
            return

        pixmap_ajustado = pixmap.scaled(
            self.size(),
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation
        )

        self.imagen_fondo.setPixmap(
            pixmap_ajustado
        )

        # Orden de capas
        self.imagen_fondo.lower()
        self.capa_oscura.raise_()

    # ==============================================================
    # REDIMENSIONAMIENTO
    # ==============================================================

    def resizeEvent(self, event):

        super().resizeEvent(event)

        self._ajustar_fondo()

    # ==============================================================
    # INICIAR RELOJ
    # ==============================================================

    def _iniciar_reloj(self):

        self._actualizar_hora()

        self.temporizador = QTimer(self)

        self.temporizador.timeout.connect(
            self._actualizar_hora
        )

        self.temporizador.start(
            1000
        )

    # ==============================================================
    # ACTUALIZAR HORA
    # ==============================================================

    def _actualizar_hora(self):

        ahora = QDateTime.currentDateTime()

        locale = QLocale(
            QLocale.Language.Spanish,
            QLocale.Country.Colombia
        )

        fecha = locale.toString(
            ahora,
            "dddd, dd 'de' MMMM 'de' yyyy"
        )

        hora = ahora.toString(
            "hh:mm:ss"
        )

        self.etiqueta_reloj.setText(
            f"{fecha}   -   {hora}"
        )