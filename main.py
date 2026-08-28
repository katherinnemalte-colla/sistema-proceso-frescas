from PySide6.QtWidgets import QApplication, QDialog

import sys
import os
from ui.ventana_login import VentanaLogin
from ui.ventana_fondo import VentanaFondo
from ui.app_ventana import VentanaApp
from models.usuarios import Usuario
from models.database import obtener_conexion


class ControladorApp:

    def __init__(self):
        self.ventana_fondo = VentanaFondo()
        self.ventana_app = None

        self.ventana_fondo.show()
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
        #self.ventana_app = VentanaApp(usuario, _crear_conexion)
        self.ventana_app.show()


def main():
    app = QApplication(sys.argv)
    controlador = ControladorApp()  # noqa: F841 (se mantiene viva mientras corre la app)
    sys.exit(app.exec())
 
 
if __name__ == "__main__":
    main()