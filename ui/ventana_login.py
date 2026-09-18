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
from utils.rutas import ruta_recurso
from services import auth_service
from utils.mensajes import MensajesLogin
from utils.ventana_utils import aplicar_tamano,escalar, escalar_fuente


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
            ancho_pct=0.58,   # login no necesita 95% de pantalla
            alto_pct=0.55,
            referencia=ventana_fondo
        )
        # SIN setFixedSize: dejamos que resize() haga su trabajo,
        # y opcionalmente ponemos límites razonables:
        self.setMinimumSize(escalar(480), escalar(340))
        self.setMaximumSize(escalar(900), escalar(650))

        panel = QWidget(self)
        panel.setObjectName("panel")
        panel.setGeometry(self.rect())

        panel.setStyleSheet(f"""
            #panel {{ background-color: #082F35; }}
            QLabel {{ color: white; }}
            #logo {{ background: transparent; }}
            #titulo_bienvenida {{
                color: white;
                font-size: {escalar_fuente(24)}px;
                font-weight: bold;
            }}
            #subtitulo {{
                color: #B8C9CB;
                font-size: {escalar_fuente(13)}px;
            }}
            #linea {{ background-color: #2C8992; }}
            QLineEdit {{
                padding: {escalar(12)}px;
                border-radius: {escalar(7)}px;
                border: 1px solid #47777D;
                background-color: rgba(255, 255, 255, 0.08);
                color: white;
                font-size: {escalar_fuente(14)}px;
            }}
            QLineEdit:focus {{
                border: 1px solid #94B7BB;
                background-color: rgba(255, 255, 255, 0.12);
            }}
            QLineEdit::placeholder {{ color: #A8BCBF; }}
            QPushButton {{
                padding: {escalar(11)}px;
                border-radius: {escalar(7)}px;
                background-color: #0F7C87;
                color: white;
                font-size: {escalar_fuente(14)}px;
                font-weight: bold;
                border: none;
            }}
            QPushButton:hover {{ background-color: #1595A1; }}
            #boton_cancelar {{
                background-color: transparent;
                border: 1px solid #47777D;
                color: #B8C9CB;
            }}
            #boton_cancelar:hover {{ background-color: rgba(255, 255, 255, 0.08); }}
            #enlace_contrasena {{
                color: #94B7BB;
                font-size: {escalar_fuente(12)}px;
                background: transparent;
            }}
            #version {{
                color: #78969A;
                font-size: {escalar_fuente(10)}px;
            }}
        """)

        # ==========================================================
        # FONDO
        # ==========================================================

        fondo = QLabel(panel)
        fondo.setObjectName("fondo")
        
        pixmap_fondo = QPixmap(str(ruta_recurso("assets/icons/login/fondo_login.png")))

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
                border-radius: 0px;
            }
        """)

        # ==========================================================
        # LOGO
        # ==========================================================

        logo = QLabel()
        logo.setObjectName("logo")
        pixmap_logo = QPixmap(str(ruta_recurso("assets/icons/cialta.png")))

        logo.setPixmap(
            pixmap_logo.scaled(
                escalar(260),
                escalar(130),
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
        linea.setFixedHeight(escalar(1) or 1)

        # ==========================================================
        # CAMPOS
        # ==========================================================

        self.campo_usuario = QLineEdit()
        self.campo_usuario.setPlaceholderText("Usuario")
        #self.campo_usuario.textChanged.connect(self.forzar_mayusculas)
        self.campo_usuario.textChanged.connect(
        lambda texto: self.campo_usuario.setText(texto.upper()))

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

        contenedor_login.setFixedWidth(escalar(350))

        contenedor_login.setLayout(
            columna_login
        )

        # ==========================================================
        # LAYOUT PRINCIPAL
        # ==========================================================

        layout_principal = QHBoxLayout(panel)

        layout_principal.setContentsMargins(escalar(60), escalar(35), escalar(60), escalar(20))

        layout_principal.setSpacing(escalar(50))

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
        self.panel = panel
        self.fondo = fondo
        self.capa = capa
    # ==============================================================
    # CERRAR
    # ==============================================================
    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "panel"):
            self.panel.setGeometry(self.rect())
            if hasattr(self, "fondo"):
                self.fondo.setGeometry(self.panel.rect())
                pixmap_fondo = QPixmap("assets/icons/login/fondo_login.png")
                self.fondo.setPixmap(
                    pixmap_fondo.scaled(
                        self.panel.size(),
                        Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                        Qt.TransformationMode.SmoothTransformation
                    )
                )
            if hasattr(self, "capa"):
                self.capa.setGeometry(self.panel.rect())
                
    def cerrar_programa(self):
        sys.exit(0)

    # ==============================================================
    # LOGIN
    # ==============================================================

    def intentar_login(self):
        try:
            usuario = auth_service.autenticar(
                self.campo_usuario.text(),
                self.campo_clave.text(),
            )
        except ConnectionError as e:
            QMessageBox.warning(
                self, "Error de conexión",
                "No se pudo conectar al servidor.\nVerifique su conexión de red e intente nuevamente."
            )
            return
        except Exception as e:
            QMessageBox.critical(self, "Error inesperado", f"Ocurrió un error:\n{e}")
            return

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