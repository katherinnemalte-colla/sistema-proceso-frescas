import sys
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit,
    QPushButton, QVBoxLayout, QMessageBox, QProgressDialog
)
import pyodbc  # para capturar sus excepciones específicas también
import traceback
from services.auth_service import authService


class LoginWorker(QThread):
    exito = Signal(str)
    error = Signal(str)

    def __init__(self, usuario, contrasena):
        super().__init__()
        self.usuario = usuario
        self.contrasena = contrasena

    def run(self):
        try:
            usuario_db = authService.autenticar(self.usuario, self.contrasena)

            if usuario_db:
                self.exito.emit(usuario_db.nombre)
            else:
                self.error.emit("Usuario o contraseña incorrectos.")

        except ConnectionError:
            self.error.emit(
                "No se pudo conectar al servidor.\n"
                "Verifique su conexión de red e intente nuevamente."
            )

        except pyodbc.Error as e:
            # Cualquier error propio de pyodbc que no sea ConnectionError
            self.error.emit(
                "Error al comunicarse con la base de datos.\n"
                "Intente nuevamente en unos segundos."
            )
            print(f"[pyodbc.Error] {e}")  # log técnico para ti, no para el usuario

        except Exception as e:
            # Red de seguridad: CUALQUIER otro error, conocido o no,
            # queda atrapado aquí y el proceso sigue vivo.
            self.error.emit(f"Ocurrió un error inesperado:\n{e}")
            print("[Error inesperado en LoginWorker]")
            traceback.print_exc()  # imprime detalle completo solo en consola/log


class LoginWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(
            "MÓDULO DE PESAJE PRODUCTOS EN POSTAS Y A GRANEL DEL "
            "CENTRO DE PROCESO CARNES FRESCAS - Login"
        )
        self.setFixedSize(300, 200)

        self.login_worker = None
        self.dialogo_espera = None

        # Widgets
        self.label_user = QLabel("Usuario:")
        self.input_user = QLineEdit()

        self.label_pass = QLabel("Contraseña:")
        self.input_pass = QLineEdit()
        self.input_pass.setEchoMode(QLineEdit.Password)

        self.btn_login = QPushButton("Ingresar")
        self.btn_login.clicked.connect(self.verificar_login)

        layout = QVBoxLayout()
        layout.addWidget(self.label_user)
        layout.addWidget(self.input_user)
        layout.addWidget(self.label_pass)
        layout.addWidget(self.input_pass)
        layout.addWidget(self.btn_login)

        self.setLayout(layout)

        # Permite iniciar sesión con Enter
        self.input_pass.returnPressed.connect(self.verificar_login)

    def verificar_login(self):
        usuario = self.input_user.text().strip()
        contrasena = self.input_pass.text()

        if not usuario or not contrasena:
            QMessageBox.warning(self, "Datos incompletos", "Ingrese usuario y contraseña.")
            return

        # Evita doble clic mientras ya hay un intento en curso
        self.btn_login.setEnabled(False)

        # Aviso visual de "conectando..."
        self.dialogo_espera = QProgressDialog("Conectando...", None, 0, 0, self)
        self.dialogo_espera.setWindowTitle("Por favor espere")
        self.dialogo_espera.setWindowModality(Qt.WindowModal)
        self.dialogo_espera.setCancelButton(None)
        self.dialogo_espera.setMinimumDuration(0)
        self.dialogo_espera.show()

        # Lanza la verificación en un hilo aparte
        self.login_worker = LoginWorker(usuario, contrasena)
        self.login_worker.exito.connect(self._on_login_exitoso)
        self.login_worker.error.connect(self._on_login_error)
        self.login_worker.finished.connect(self._finalizar_intento)
        self.login_worker.start()

    def _on_login_exitoso(self, nombre_usuario):
        self.dialogo_espera.close()
        QMessageBox.information(self, "Éxito", f"¡Bienvenido, {nombre_usuario}!")
        # TODO: aquí abrir la ventana principal de la app

    def _on_login_error(self, mensaje):
        self.dialogo_espera.close()
        QMessageBox.warning(self, "Error", mensaje)

    def _finalizar_intento(self):
        """Se ejecuta siempre al terminar el hilo, haya éxito o error."""
        self.btn_login.setEnabled(True)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    ventana = LoginWindow()
    ventana.show()
    sys.exit(app.exec())