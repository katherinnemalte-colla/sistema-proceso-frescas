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

from utils.ventana_utils import (
    aplicar_tamano,
    escalar,
    escalar_fuente,
    establecer_factor_temporal,
    limpiar_factor_temporal,
    factor_para_contenido
)

from PySide6.QtGui import QPixmap
from utils.rutas import ruta_recurso


VERSION_APP = "v1.0.0"


class VentanaFondo(QWidget):

    def __init__(self):
        super().__init__()

        self.setWindowFlags(
            Qt.Window
            | Qt.WindowMinimizeButtonHint
            | Qt.WindowCloseButtonHint
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
            str(
                ruta_recurso(
                    "assets/icons/login/fondo_login.jpg"
                )
            )
        )

        self.pixmap_original = pixmap

        self.imagen_fondo.setPixmap(
            pixmap
        )

        # ==========================================================
        # CAPA OSCURA
        # ==========================================================

        self.capa_oscura = QLabel(self)

        self.capa_oscura.setStyleSheet("""
            background-color: rgba(3, 35, 40, 175);
        """)

        self.capa_oscura.setAttribute(
            Qt.WA_TransparentForMouseEvents
        )

        # ==========================================================
        # RELOJ
        # ==========================================================

        self.etiqueta_reloj = QLabel()

        self.etiqueta_reloj.setAlignment(
            Qt.AlignLeft | Qt.AlignVCenter
        )

        self.etiqueta_reloj.setStyleSheet(f"""
            QLabel {{
                color: #FFFFFF;
                font-size: {escalar_fuente(25)}px;
                font-weight: 500;
                background: transparent;
            }}
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

        self.etiqueta_version.setStyleSheet(f"""
            QLabel {{
                color: #FFFFFF;
                font-size: {escalar_fuente(12)}px;
                font-weight: 500;
                background: transparent;
            }}
        """)

        # ==========================================================
        # PIE DE PANTALLA
        # ==========================================================

        pie = QHBoxLayout()

        pie.setContentsMargins(
            escalar(25),
            escalar(12),
            escalar(25),
            escalar(45)
        )

        pie.setSpacing(
            escalar(10)
        )

        pie.addWidget(
            self.etiqueta_reloj,
            0,
            Qt.AlignLeft | Qt.AlignBottom
        )

        pie.addStretch()

        pie.addWidget(
            self.etiqueta_version,
            0,
            Qt.AlignRight | Qt.AlignBottom
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

        layout.setSpacing(0)

        # Espacio superior
        layout.addStretch(1)

        # Pie completamente abajo
        layout.addLayout(
            pie
        )

        self.setLayout(
            layout
        )

        # ==========================================================
        # FONDO DE RESPALDO
        # ==========================================================

        self.setStyleSheet("""
            QWidget {
                background-color: #082F35;
            }
        """)

        # ==========================================================
        # INICIAR
        # ==========================================================

        self._ajustar_fondo()
        self._iniciar_reloj()

        # ==========================================================
        # TAMAÑO
        # ==========================================================

        aplicar_tamano(
            self,
            modo="completo"
        )

        # ==========================================================
        # ORDEN DE CAPAS
        # ==========================================================

        self.imagen_fondo.lower()

        self.capa_oscura.raise_()

        # El contenido debe quedar ENCIMA de la capa oscura
        self.etiqueta_reloj.raise_()
        self.etiqueta_version.raise_()

    # ==============================================================
    # AJUSTAR IMAGEN Y CAPA
    # ==============================================================

    def _ajustar_fondo(self):

        if (
            not hasattr(self, "imagen_fondo")
            or not hasattr(self, "capa_oscura")
        ):
            return

        # Imagen ocupa toda la ventana
        self.imagen_fondo.setGeometry(
            self.rect()
        )

        # Capa ocupa toda la ventana
        self.capa_oscura.setGeometry(
            self.rect()
        )

        pixmap = getattr(
            self,
            "pixmap_original",
            None
        )

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

        # ==========================================================
        # ORDEN DE CAPAS
        # ==========================================================

        self.imagen_fondo.lower()

        self.capa_oscura.raise_()

        # Las etiquetas siempre encima de la capa
        self.etiqueta_reloj.raise_()
        self.etiqueta_version.raise_()

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
