
import sys
import os
import ctypes
import logging

from PySide6.QtWidgets import QApplication, QDialog
from PySide6.QtGui import QIcon
from PySide6.QtCore import QTimer

from ui.ventana_login import VentanaLogin
from ui.ventana_fondo import VentanaFondo
from ui.app_ventana import VentanaApp
from models.usuarios import Usuario
from models.database import obtener_conexion
from utils.logs import configurar_logging
from config.settings import DB_SERVER

def _obtener_directorio_base() -> str:
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


class ControladorApp:

    def __init__(self):
        self.ventana_fondo = VentanaFondo()
        self.ventana_app = None

        self.ventana_fondo.show()
        QApplication.processEvents()
        self._mostrar_login()

    def _mostrar_login(self):
        login = VentanaLogin(self.ventana_fondo)
        resultado = login.exec()

        if resultado == QDialog.Accepted:
            self.abrir_ventana_principal(login.usuario_autenticado)
        else:
            sys.exit(0)
            
    def abrir_ventana_principal(self, usuario: Usuario):
        self.ventana_fondo.close()

        # Obtener el nombre del usuario autenticado.
        # Cambia "nombre" si tu modelo Usuario utiliza otro atributo.
        nombre_usuario = usuario.nombre_usuario

        self.ventana_app = VentanaApp(usuario, obtener_conexion)

        # Título de la ventana con el nombre del usuario.
        self.ventana_app.setWindowTitle(
            f"Etiquetas 2 en 1"+ f"  Usuario: {nombre_usuario}"+f" Entorno : {DB_SERVER}" 
        )

        self.ventana_app.show()
        QTimer.singleShot(0, self.ventana_app.showMaximized)


def main():
    configurar_logging()
    if sys.platform == "win32":
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            "cialta.frescas.1.0"
        )

    app = QApplication(sys.argv)
    app.setApplicationDisplayName("Etiquetas")

    # Icono global de la aplicación.
    base_dir = _obtener_directorio_base()
    icon_path = os.path.join(
        base_dir, "assets", "icons", "icons", "cialtaicono.ico"
    )
    app.setWindowIcon(QIcon(icon_path))

    controlador = ControladorApp()

    sys.exit(app.exec())
 
 
if __name__ == "__main__":
    main()