"""
Ejemplo simplificado de la ventana de login con PySide6.
Fíjate: en ningún momento aparece SQL aquí. Solo llama a auth_service.
"""
import sys
from PySide6.QtWidgets import (
    QDialog, QLineEdit, QPushButton, 
    QVBoxLayout, QLabel, QMessageBox, QWidget,QHBoxLayout
)
from PySide6.QtCore import Signal, Qt
from services import auth_service
from utils.mensajes import MensajesLogin
from utils.ventana_utils import aplicar_tamano


class VentanaLogin(QDialog):
    # Señal que emite el Usuario autenticado; main.py se conecta a esto
    # para saber cuándo abrir la ventana principal.
    login_exitoso = Signal(object)

    def __init__(self, ventana_fondo):
        super().__init__(ventana_fondo)
        self.usuario_autenticado = None
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        #self.setModal(True)  # bloquea la interacción con el fondo mientras el login está abierto
        #aplicar_tamano(self, modo="centrado", ancho_pct=0.22, alto_pct=0.30, referencia= ventana_fondo)

        self.setAttribute(Qt.WA_TranslucentBackground)
 
        self.setModal(True)
 
        aplicar_tamano(self, modo="centrado", ancho_pct=0.22, alto_pct=0.30, referencia=ventana_fondo)
        self.setFixedSize(self.size())  # tamaño fijo: no se puede redimensionar arrastrando bordes
 
        # --- Panel visual con el fondo y las esquinas redondeadas ---
        panel = QWidget(self)
        panel.setObjectName("panel")
        panel.setGeometry(self.rect())  # el panel ocupa todo el diálogo
        panel.setStyleSheet("""
            #panel {
                background-color: #2b3242;
                border-radius: 16px;
            }
            QLabel {
                color: white;
            }
            QLineEdit {
                padding: 8px;
                border-radius: 6px;
                border: 1px solid #4a5468;
                background-color: #1e2430;
                color: white;
            }
            QPushButton {
                padding: 8px;
                border-radius: 6px;
                background-color: #3d7eff;
                color: white;
            }
            QPushButton:hover {
                background-color: #5a90ff;
            }
            #boton_cancelar {
                background-color: #4a5468;
            }
            #boton_cancelar:hover {
                background-color: #5c6883;
            }
        """)


        self.campo_usuario = QLineEdit()
        self.campo_usuario.setPlaceholderText("Usuario")

        self.campo_clave = QLineEdit()
        self.campo_clave.setPlaceholderText("Contraseña")
        self.campo_clave.setEchoMode(QLineEdit.Password)

        boton_entrar = QPushButton("Entrar")
        boton_entrar.clicked.connect(self.intentar_login)

        boton_cancelar = QPushButton("Cancelar")
        boton_cancelar.setObjectName("boton_cancelar")
        boton_cancelar.clicked.connect(self.cerrar_programa)
 
        fila_botones = QHBoxLayout()
        fila_botones.addWidget(boton_cancelar)
        fila_botones.addWidget(boton_entrar)

        layout = QVBoxLayout()
        layout.addWidget(QLabel("Ingrese sus credenciales"))
        layout.addWidget(self.campo_usuario)
        layout.addWidget(self.campo_clave)
        layout.addWidget(boton_entrar)
        self.setLayout(layout)
        
    def cerrar_programa(self):
        sys.exit(0)    

    def intentar_login(self):
        if not self.campo_usuario.text() or not self.campo_clave.text():
            QMessageBox.warning(self, "Error", MensajesLogin.CAMPOS_VACIOS)
            return
 
        usuario = auth_service.autenticar(
            self.campo_usuario.text(),
            self.campo_clave.text(),
        )
 
        if usuario is None:
            QMessageBox.warning(self, "Error", MensajesLogin.USUARIO_O_CLAVE_INCORRECTA)
            return
 
        self.usuario_autenticado = usuario
        self.accept()