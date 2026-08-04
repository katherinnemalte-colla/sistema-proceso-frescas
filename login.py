import sys
from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, 
    QPushButton, QVBoxLayout, QMessageBox
)

class LoginWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sistema de Inventarios - Login")
        self.setFixedSize(300, 200)

        # Widgets
        self.label_user = QLabel("Usuario:")
        self.input_user = QLineEdit()

        self.label_pass = QLabel("Contraseña:")
        self.input_pass = QLineEdit()
        self.input_pass.setEchoMode(QLineEdit.Password)  # oculta el texto

        self.btn_login = QPushButton("Ingresar")
        self.btn_login.clicked.connect(self.verificar_login)

        # Layout (organiza los widgets verticalmente)
        layout = QVBoxLayout()
        layout.addWidget(self.label_user)
        layout.addWidget(self.input_user)
        layout.addWidget(self.label_pass)
        layout.addWidget(self.input_pass)
        layout.addWidget(self.btn_login)

        self.setLayout(layout)

    def verificar_login(self):
        usuario = self.input_user.text()
        contrasena = self.input_pass.text()

        # Aquí luego conectarás con tu base de datos real
        if usuario == "admin" and contrasena == "1234":
            QMessageBox.information(self, "Éxito", "¡Bienvenido!")
        else:
            QMessageBox.warning(self, "Error", "Usuario o contraseña incorrectos")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    ventana = LoginWindow()
    ventana.show()
    sys.exit(app.exec())