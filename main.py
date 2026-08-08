from PySide6.QtWidgets import QApplication, QDialog
from controllers.etiquetas_controller import EtiquetasController
import sys
from ui.ventana_login import VentanaLogin
from ui.ventana_principal import VentanaPrincipal
from ui.ventana_fondo import VentanaFondo
from models.usuarios import Usuario

#app = QApplication(sys.argv)

#controller = EtiquetasController()
#controller.mostrar()

#sys.exit(app.exec())
class ControladorApp:
    """
    Mantiene referencias vivas a las ventanas.
    (Si no guardamos la referencia en algún lado, Python las destruye
    apenas termina la función y la ventana desaparece de golpe.)
    """
 
    def __init__(self):
        #self.ventana_login = VentanaLogin()
        #self.ventana_login.login_exitoso.connect(self.abrir_ventana_principal)
        self.ventana_fondo = VentanaFondo()
        self.ventana_principal = None
 
        #self.ventana_login.show()
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
        #self.ventana_login.close()
        self.ventana_principal = VentanaPrincipal(usuario)
        self.ventana_principal.show()
 
 
def main():
    app = QApplication(sys.argv)
    controlador = ControladorApp()  # noqa: F841 (se mantiene viva mientras corre la app)
    sys.exit(app.exec())
 
 
if __name__ == "__main__":
    main()