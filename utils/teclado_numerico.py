
from PySide6.QtWidgets import (
    QDialog,
    QGridLayout,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QLineEdit,
    QApplication,
)
import os
from PySide6.QtCore import Qt, QEvent, QTimer, QPoint
from PySide6.QtGui import QGuiApplication
from utils.rutas import ruta_recurso
from utils.ventana_utils import escalar, escalar_fuente,establecer_factor_temporal, limpiar_factor_temporal, factor_para_contenido,_icono_pixmap
RUTA_ICONOS = ruta_recurso(os.path.join("assets", "icons", "icons"))
def _ruta_icono(nombre_archivo):
    return os.path.join(RUTA_ICONOS, nombre_archivo)
class TecladoNumerico(QDialog):

    def __init__(self, parent=None):
        super().__init__(
            parent,
            Qt.Tool |
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.WindowDoesNotAcceptFocus
        )

        self.campo_objetivo = None
        self._cerrando = False
        #self.setWindowTitle("Teclado numérico")
        self.setFixedSize(270, 300)

        # Evita que el teclado quite el foco del campo.
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setFocusPolicy(Qt.NoFocus)

        self._crear_interfaz()
        
    def ocultar(self):
        """Oculta el teclado sin alterar el contenido del campo."""
        self._cerrando = True
        self.hide()


    def mostrar(self):
        if self.campo_objetivo is None:
            return

        self._cerrando = False
        self._posicionar()
        self.show()


    def eventFilter(self, objeto, evento):

        if objeto is self.campo_objetivo:

            if evento.type() in (
                QEvent.FocusIn,
                QEvent.MouseButtonPress
            ):
                if not self._cerrando:
                    self.mostrar()

        return super().eventFilter(objeto, evento)


    def _crear_interfaz(self):

        principal = QVBoxLayout(self)
        principal.setContentsMargins(10, 10, 10, 10)
        principal.setSpacing(8)

        # Encabezado
        encabezado = QHBoxLayout()

        titulo = QPushButton("TECLADO NUMÉRICO")
        titulo.setEnabled(False)
        titulo.setFixedHeight(30)
        titulo.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: #134f4f;
                font-size: 12px;
                font-weight: bold;
            }
        """)

        #encabezado.addWidget(titulo)
        principal.addLayout(encabezado)

        # Distribución numérica
        rejilla = QGridLayout()
        rejilla.setSpacing(7)

        numeros = [
            ("1", 0, 0), ("2", 0, 1), ("3", 0, 2),
            ("4", 1, 0), ("5", 1, 1), ("6", 1, 2),
            ("7", 2, 0), ("8", 2, 1), ("9", 2, 2),
        ]

        for numero, fila, columna in numeros:
            boton = self._crear_boton(numero)
            boton.clicked.connect(
                lambda checked=False, n=numero: self._insertar(n)
            )
            rejilla.addWidget(boton, fila, columna)

        # Fila inferior
        boton_limpiar = self._crear_boton("C", secundario=True)
        boton_limpiar.clicked.connect(self._limpiar)
        rejilla.addWidget(boton_limpiar, 3, 0)

        boton_cero = self._crear_boton("0")
        boton_cero.clicked.connect(lambda: self._insertar("0"))
        rejilla.addWidget(boton_cero, 3, 1)

        boton_borrar = self._crear_boton("⌫", secundario=True)
        boton_borrar.clicked.connect(self._borrar)
        rejilla.addWidget(boton_borrar, 3, 2)

        principal.addLayout(rejilla)

        # Aceptar
        boton_aceptar = QPushButton("ACEPTAR")
        boton_aceptar.setFixedHeight(42)
        boton_aceptar.setCursor(Qt.PointingHandCursor)
        boton_aceptar.setFocusPolicy(Qt.NoFocus)
        boton_aceptar.setStyleSheet("""
            QPushButton {
                background: #1a6b6b;
                color: white;
                border: none;
                border-radius: 8px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:pressed {
                background: #134f4f;
            }
        """)
        boton_aceptar.clicked.connect(self.ocultar)

        principal.addWidget(boton_aceptar)

        self.setStyleSheet("""
            QDialog {
                background: #ffffff;
                border: 1px solid #dfe6e6;
                border-radius: 12px;
            }
        """)

    def _crear_boton(self, texto, secundario=False):

        boton = QPushButton(texto)
        boton.setFixedSize(76, 43)
        boton.setCursor(Qt.PointingHandCursor)
        boton.setFocusPolicy(Qt.NoFocus)

        if secundario:
            fondo = "#e6f2f2"
            color = "#134f4f"
        else:
            fondo = "#f3f7f7"
            color = "#263b3b"

        boton.setStyleSheet(f"""
            QPushButton {{
                background: {fondo};
                color: {color};
                border: 1px solid #dfe6e6;
                border-radius: 8px;
                font-size: 19px;
                font-weight: bold;
            }}
            QPushButton:pressed {{
                background: #cce2e2;
                border: 1px solid #1a6b6b;
            }}
        """)

        return boton

    # --------------------------------------------------
    # Vincular campo
    # --------------------------------------------------

    def vincular(self, campo: QLineEdit):

        if self.campo_objetivo is not None:
            self.campo_objetivo.removeEventFilter(self)

        self.campo_objetivo = campo
        campo.installEventFilter(self)

    # --------------------------------------------------
    # Eventos del campo
    # --------------------------------------------------

    def eventFilter(self, objeto, evento):

        if objeto is self.campo_objetivo:

            if evento.type() in (
                QEvent.FocusIn,
                QEvent.MouseButtonPress
            ):
                self.mostrar()

            elif evento.type() == QEvent.FocusOut:
                QTimer.singleShot(
                    150,
                    self._verificar_perdida_foco
                )

        return super().eventFilter(objeto, evento)

    def _verificar_perdida_foco(self):

        if not self.isVisible():
            return

        foco = QApplication.focusWidget()

        if foco is not self.campo_objetivo:
            self.ocultar()

    # --------------------------------------------------
    # Operaciones numéricas
    # --------------------------------------------------

    def _insertar(self, numero):

        if self.campo_objetivo is None:
            return

        self.campo_objetivo.insert(numero)

    def _borrar(self):

        campo = self.campo_objetivo

        if campo is None:
            return

        posicion = campo.cursorPosition()

        if posicion > 0:
            texto = campo.text()
            campo.setText(
                texto[:posicion - 1] + texto[posicion:]
            )
            campo.setCursorPosition(posicion - 1)

    def _limpiar(self):

        if self.campo_objetivo is not None:
            self.campo_objetivo.clear()

    # --------------------------------------------------
    # Mostrar y ocultar
    # --------------------------------------------------

    def mostrar(self):

        if self.campo_objetivo is None:
            return

        self._posicionar()
        self.show()

    def ocultar(self):
        self.hide()

    def _posicionar(self):

        campo = self.campo_objetivo

        if campo is None:
            return

        # Posición global debajo del campo.
        punto = campo.mapToGlobal(
            QPoint(0, campo.height() + 6)
        )

        pantalla = QGuiApplication.screenAt(punto)

        if pantalla is None:
            pantalla = QGuiApplication.primaryScreen()

        if pantalla is None:
            return

        area = pantalla.availableGeometry()

        x = punto.x()
        y = punto.y()

        # Evitar que el teclado salga de la pantalla.
        if x + self.width() > area.right():
            x = area.right() - self.width() + 1

        if x < area.left():
            x = area.left()

        if y + self.height() > area.bottom():
            y = campo.mapToGlobal(
                QPoint(0, -self.height() - 6)
            ).y()

        if y < area.top():
            y = area.top()

        self.move(x, y)
