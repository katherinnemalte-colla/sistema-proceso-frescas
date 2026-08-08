from PySide6.QtWidgets import (
    QWidget,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QHBoxLayout
)
from PySide6.QtGui import QFont
from PySide6.QtCore import Qt

class EtiquetasWindow(QWidget):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Etiquetas Canastillas y Postas (2 en 1)")
        
        self.lblTitulo = QLabel("CENTRO DE PROCESOS")
        fuente = QFont("Arial", 20)
        fuente.setBold(True)

        self.lblTitulo.setFont(fuente)
        self.lblTitulo.setAlignment(Qt.AlignCenter)

        self.lblEspecie = QLabel("Especie")
        self.txtEspecie = QLineEdit()
        self.txtEspecie.setReadOnly(True)

        self.lblEspecieNombre = QLabel("Nombre Especie")
        self.txtEspecieNombre =QLineEdit()
        self.txtEspecieNombre.setReadOnly(True)

        self.lblPlu = QLabel("PLU")
        self.txtPlu = QLineEdit()

        self.lblNombre = QLabel("Nombre Producto")
        self.txtNombre = QLineEdit()
        self.txtNombre.setReadOnly(True)

        layout = QVBoxLayout()
        layout.addWidget(self.lblTitulo)
        fila1 = QHBoxLayout()
        fila1.addWidget(self.lblEspecie)
        fila1.addWidget(self.txtEspecie)
        fila1.addWidget(self.lblEspecieNombre)
        fila1.addWidget(self.txtEspecieNombre)

        fila2 = QHBoxLayout()
        fila2.addWidget(self.lblPlu)
        fila2.addWidget(self.txtPlu)

        fila2.addWidget(self.lblNombre)
        fila2.addWidget(self.txtNombre)

        layout.addLayout(fila1)
        layout.addLayout(fila2)

        self.setLayout(layout)