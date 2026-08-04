from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
    QTableWidgetItem, QPushButton, QLabel
)
from PySide6.QtCore import Qt


class ProductosView(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Listado de Productos")
        self.resize(500, 500)

        # Tabla
        self.tabla = QTableWidget()
        self.tabla.setColumnCount(2)
        self.tabla.setHorizontalHeaderLabels(["Código PLU", "Nombre del Producto"])
        self.tabla.horizontalHeader().setStretchLastSection(True)
        self.tabla.setEditTriggers(QTableWidget.NoEditTriggers)  # no editable directo

        # Controles de paginación
        self.btn_anterior = QPushButton("← Anterior")
        self.btn_siguiente = QPushButton("Siguiente →")
        self.label_pagina = QLabel("Página 1")
        self.label_pagina.setAlignment(Qt.AlignCenter)

        layout_paginacion = QHBoxLayout()
        layout_paginacion.addWidget(self.btn_anterior)
        layout_paginacion.addWidget(self.label_pagina)
        layout_paginacion.addWidget(self.btn_siguiente)

        # Layout principal
        layout = QVBoxLayout()
        layout.addWidget(self.tabla)
        layout.addLayout(layout_paginacion)
        self.setLayout(layout)

    def mostrar_productos(self, productos):
        """Llena la tabla con la lista de productos (tuplas: cdgo_plu, nmbre_prdcto)"""
        self.tabla.setRowCount(0)  # limpia la tabla antes de llenar
        for fila, (codigo, nombre) in enumerate(productos):
            self.tabla.insertRow(fila)
            self.tabla.setItem(fila, 0, QTableWidgetItem(str(codigo)))
            self.tabla.setItem(fila, 1, QTableWidgetItem(str(nombre)))

    def actualizar_label_pagina(self, pagina_actual, total_paginas):
        self.label_pagina.setText(f"Página {pagina_actual} de {total_paginas}")