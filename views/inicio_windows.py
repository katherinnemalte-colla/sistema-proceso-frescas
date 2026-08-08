"""
Ventana principal (placeholder).
Reemplaza el contenido de esta clase cuando diseñes la ventana real
del sistema de inventarios/códigos de barras.
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from models.usuarios import Usuario


class VentanaPrincipal(QWidget):
    def __init__(self, usuario: Usuario):
        super().__init__()
        self.usuario = usuario  # guardamos quién inició sesión, útil para permisos/rol
        self.setWindowTitle("Sistema de Inventarios")
        self.resize(800, 600)

        layout = QVBoxLayout()
        layout.addWidget(QLabel(f"Bienvenido, {usuario.nombre_completo} (rol: {usuario.rol})"))
        # aquí irán los módulos reales: inventario, códigos de barras, etc.
        self.setLayout(layout)