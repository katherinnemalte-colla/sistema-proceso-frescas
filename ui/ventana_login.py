"""
Ventana de login de la aplicación Cialta.
La lógica de autenticación continúa delegada a auth_service.
"""

import sys

from PySide6.QtWidgets import (
    QDialog, QLineEdit, QPushButton, 
    QVBoxLayout, QLabel, QMessageBox, QWidget,QHBoxLayout,
    QDialog,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QLabel,
    QMessageBox,
    QWidget,
    QHBoxLayout,
    QFrame
)

from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QPixmap

from services import auth_service
from utils.mensajes import MensajesLogin
from utils.ventana_utils import aplicar_tamano


class VentanaLogin(QDialog):

    # Señal que emite el Usuario autenticado.
    login_exitoso = Signal(object)

    def __init__(self, ventana_fondo):
        super().__init__(ventana_fondo)

        self.usuario_autenticado = None

        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.Dialog
        )

        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setModal(True)

        aplicar_tamano(
            self,
            modo="centrado",
            ancho_pct=0.45,
            alto_pct=0.45,
            referencia=ventana_fondo
        )

        self.setFixedSize(self.size())

        # ==========================================================
        # PANEL PRINCIPAL
        # ==========================================================

        panel = QWidget(self)
        panel.setObjectName("panel")
        panel.setGeometry(self.rect())

        panel.setStyleSheet("""
            #panel {
                background-color: #082F35;
                border-radius: 0px;
            }

            QLabel {
                color: white;
            }

            #logo {
                background: transparent;
            }

            #titulo_bienvenida {
                color: white;
                font-size: 24px;
                font-weight: bold;
            }

            #subtitulo {
                color: #B8C9CB;
                font-size: 13px;
            }

            #linea {
                background-color: #2C8992;
            }

            QLineEdit {
                padding: 12px;
                border-radius: 7px;
                border: 1px solid #47777D;
                background-color: rgba(255, 255, 255, 0.08);
                color: white;
                font-size: 14px;
            }

            QLineEdit:focus {
                border: 1px solid #94B7BB;
                background-color: rgba(255, 255, 255, 0.12);
            }

            QLineEdit::placeholder {
                color: #A8BCBF;
            }

            QPushButton {
                padding: 11px;
                border-radius: 7px;
                background-color: #0F7C87;
                color: white;
                font-size: 14px;
                font-weight: bold;
                border: none;
            }

            QPushButton:hover {
                background-color: #1595A1;
            }

            #boton_cancelar {
                background-color: transparent;
                border: 1px solid #47777D;
                color: #B8C9CB;
            }

            #boton_cancelar:hover {
                background-color: rgba(255, 255, 255, 0.08);
            }

            #enlace_contrasena {
                color: #94B7BB;
                font-size: 12px;
                background: transparent;
            }

            #version {
                color: #78969A;
                font-size: 10px;
            }
        """)

        # ==========================================================
        # FONDO
        # ==========================================================

        fondo = QLabel(panel)
        fondo.setObjectName("fondo")

        pixmap_fondo = QPixmap(
            "assets/login/fondo_login.jpg"
        )

        fondo.setPixmap(
        pixmap_fondo.scaled(
        panel.size(),
        Qt.AspectRatioMode.KeepAspectRatioByExpanding,
        Qt.TransformationMode.SmoothTransformation
            )
        )

        fondo.setGeometry(panel.rect())
        fondo.lower()

        # Oscurecer el fondo
        capa = QWidget(panel)
        capa.setObjectName("capa")

        capa.setGeometry(panel.rect())

        capa.setStyleSheet("""
            #capa {
                background-color: rgba(3, 30, 34, 190);
                border-radius: 18px;
            }
        """)

        # ==========================================================
        # LOGO
        # ==========================================================

        logo = QLabel()
        logo.setObjectName("logo")

        pixmap_logo = QPixmap(
            "assets/icons/cialta.png"
        )

        logo.setPixmap(
            pixmap_logo.scaled(
                260,
                130,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
        )

        logo.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        # ==========================================================
        # TITULO
        # ==========================================================

        titulo_bienvenida = QLabel("Bienvenido")
        titulo_bienvenida.setObjectName("titulo_bienvenida")

        subtitulo = QLabel(
            "Inicia sesión para continuar"
        )
        subtitulo.setObjectName("subtitulo")

        # ==========================================================
        # LINEA DECORATIVA
        # ==========================================================

        linea = QFrame()
        linea.setObjectName("linea")
        linea.setFixedHeight(1)

        # ==========================================================
        # CAMPOS
        # ==========================================================

        self.campo_usuario = QLineEdit()
        self.campo_usuario.setPlaceholderText("Usuario")

        self.campo_clave = QLineEdit()
        self.campo_clave.setPlaceholderText("Contraseña")
        self.campo_clave.setEchoMode(
            QLineEdit.Password
        )

        # ==========================================================
        # BOTON ENTRAR
        # ==========================================================

        boton_entrar = QPushButton("Iniciar sesión")
        boton_entrar.clicked.connect(
            self.intentar_login
        )

        # ==========================================================
        # BOTON CANCELAR
        # ==========================================================

        boton_cancelar = QPushButton("Cancelar")
        boton_cancelar.setObjectName(
            "boton_cancelar"
        )

        boton_cancelar.clicked.connect(
            self.cerrar_programa
        )

        # ==========================================================
        # ENLACE CONTRASEÑA
        # ==========================================================

        enlace_contrasena = QLabel(
            "¿Olvidaste tu contraseña?"
        )

        enlace_contrasena.setObjectName(
            "enlace_contrasena"
        )

        enlace_contrasena.setAlignment(
            Qt.AlignCenter
        )

        # ==========================================================
        # FORMULARIO
        # ==========================================================

        formulario = QVBoxLayout()

        formulario.setSpacing(12)

        formulario.addWidget(
            titulo_bienvenida
        )

        formulario.addWidget(
            subtitulo
        )

        formulario.addSpacing(8)

        formulario.addWidget(linea)

        formulario.addSpacing(12)

        formulario.addWidget(
            self.campo_usuario
        )

        formulario.addWidget(
            self.campo_clave
        )

        formulario.addSpacing(4)

        formulario.addWidget(
            boton_entrar
        )

        formulario.addWidget(
            enlace_contrasena
        )

        formulario.addSpacing(15)

        formulario.addWidget(
            boton_cancelar
        )

        # ==========================================================
        # COLUMNA DEL LOGIN
        # ==========================================================

        columna_login = QVBoxLayout()

        columna_login.setContentsMargins(
            0, 0, 0, 0
        )

        columna_login.addLayout(
            formulario
        )

        # ==========================================================
        # CONTENEDOR DERECHO
        # ==========================================================

        contenedor_login = QWidget()

        contenedor_login.setFixedWidth(350)

        contenedor_login.setLayout(
            columna_login
        )

        # ==========================================================
        # LAYOUT PRINCIPAL
        # ==========================================================

        layout_principal = QHBoxLayout(panel)

        layout_principal.setContentsMargins(
            60,
            35,
            60,
            20
        )

        layout_principal.setSpacing(50)

        # Parte izquierda
        columna_izquierda = QVBoxLayout()

        columna_izquierda.addWidget(
            logo
        )

        columna_izquierda.addStretch()

        # Parte derecha
        columna_derecha = QVBoxLayout()

        columna_derecha.addStretch()

        columna_derecha.addWidget(
            contenedor_login
        )

        columna_derecha.addStretch()

        layout_principal.addLayout(
            columna_izquierda,
            1
        )

        layout_principal.addLayout(
            columna_derecha,
            1
        )

    # ==============================================================
    # CERRAR
    # ==============================================================

    def cerrar_programa(self):
        sys.exit(0)

    # ==============================================================
    # LOGIN
    # ==============================================================

    def intentar_login(self):

        if (
            not self.campo_usuario.text()
            or not self.campo_clave.text()
        ):
            QMessageBox.warning(
                self,
                "Error",
                MensajesLogin.CAMPOS_VACIOS
            )
            return

        usuario = auth_service.autenticar(
            self.campo_usuario.text(),
            self.campo_clave.text(),
        )

        if usuario is None:

            QMessageBox.warning(
                self,
                "Error",
                MensajesLogin.USUARIO_O_CLAVE_INCORRECTA
            )

            return

        self.usuario_autenticado = usuario

        self.accept()