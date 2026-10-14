from PySide6.QtWidgets import QApplication, QDialog

import sys
import os
from ui.ventana_login import VentanaLogin
from ui.ventana_fondo import VentanaFondo
from ui.app_ventana import VentanaApp
from models.usuarios import Usuario
from models.database import obtener_conexion
from PySide6.QtGui import QIcon
import ctypes
from PySide6.QtCore import QTimer
import logging

def _obtener_directorio_base() -> str:
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))


def configurar_logging():
    carpeta_logs = os.path.join(_obtener_directorio_base(), "logs")
    os.makedirs(carpeta_logs, exist_ok=True)

    ruta_log = os.path.join(carpeta_logs, "sistema.log")

    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(ruta_log, encoding="utf-8"),
        ],
    )

class ControladorApp:

    def __init__(self):
        self.ventana_fondo = VentanaFondo()
        self.ventana_app = None

        self.ventana_fondo.show()
        QApplication.processEvents()
        self._mostrar_login()

    def _mostrar_login(self):
        login = VentanaLogin(self.ventana_fondo)
        resultado = login.exec()  # bloquea aquí hasta que el usuario entra o cancela

        if resultado == QDialog.Accepted:
            self.abrir_ventana_principal(login.usuario_autenticado)
        else:
            sys.exit(0)  # el usuario cerró/canceló el login
    
    def abrir_ventana_principal(self, usuario: Usuario):
        self.ventana_fondo.close()
        self.ventana_app = VentanaApp(usuario, obtener_conexion)
        self.ventana_app.show()
        QTimer.singleShot(0, self.ventana_app.showMaximized)


def main():
    configurar_logging()
    if sys.platform == "win32":
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("cialta.frescas.1.0")
    app = QApplication(sys.argv)
    controlador = ControladorApp()  # noqa: F841 (se mantiene viva mientras corre la app)

    base_dir = os.path.dirname(os.path.abspath(__file__))
    icon_path = os.path.join(base_dir, "assets", "icons", "icons", "cialtaicono.ico")
    app.setWindowIcon(QIcon(icon_path))
    print(os.path.exists(icon_path), icon_path)
    sys.exit(app.exec())
 
 
if __name__ == "__main__":
    main()