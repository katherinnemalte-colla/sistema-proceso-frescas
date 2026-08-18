
from PySide6.QtWidgets import (
    QWidget, QLabel, QPushButton, QFrame, QGridLayout,
    QVBoxLayout, QHBoxLayout, QDateEdit
)
from PySide6.QtCore import Qt, QSize, QDate
from PySide6.QtGui import QPixmap, QIcon

from utils.ventana_utils import aplicar_tamano

ANCHO_CONTENIDO = 950


class FichaTecnica(QWidget):
    def __init__(self, usuario, producto: dict, fecha_produccion: str, especie: str, numEspecie, lote: str):
        super().__init__()
        self.usuario = usuario
        self.producto = producto
        self.fecha_produccion = fecha_produccion
        self.especie = especie
        self.numEspecie = int(numEspecie)
        self.lote = lote

        self.seleccion_de_producto = None
        self.peso_actual = 0.000  # placeholder: aquí se conectará la báscula real

        self.setWindowTitle(f"Ficha técnica - {producto.get('nombre', '')}")
        aplicar_tamano(self, modo="completo")
        self.setStyleSheet("QWidget { background-color: #F5F8F8; }")

        self._crear_interfaz()

    # ==============================================================
    # INTERFAZ
    # ==============================================================

    def _crear_interfaz(self):
        layout_externo = QVBoxLayout()
        layout_externo.setContentsMargins(0, 0, 0, 0)

        fila_central = QHBoxLayout()
        fila_central.addStretch()

        layout = QVBoxLayout()
        layout.setContentsMargins(25, 20, 25, 20)
        layout.setSpacing(16)

        contenedor = QWidget()
        contenedor.setFixedWidth(ANCHO_CONTENIDO)
        contenedor.setLayout(layout)

        fila_central.addWidget(contenedor)
        fila_central.addStretch()

        layout_externo.addStretch()
        layout_externo.addLayout(fila_central)
        layout_externo.addStretch()

        # ----------------------------------------------------------
        # ENCABEZADO: Atrás + título
        # ----------------------------------------------------------
        encabezado = QHBoxLayout()

        boton_atras = QPushButton("←  Atrás")
        boton_atras.setFixedSize(110, 40)
        boton_atras.setStyleSheet("""
            QPushButton {
                background-color: white;
                color: #115E67;
                border: 1px solid #D9E2E4;
                border-radius: 8px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #EAF4F5;
            }
        """)
        boton_atras.clicked.connect(self._volver_a_seleccion_de_producto)
        encabezado.addWidget(boton_atras)

        titulo = QLabel("Ficha técnica del producto")
        titulo.setAlignment(Qt.AlignCenter)
        titulo.setStyleSheet("font-size: 22px; font-weight: bold; color: #115E67;")
        encabezado.addWidget(titulo, stretch=1)

        espaciador = QLabel("")
        espaciador.setFixedSize(110, 40)
        encabezado.addWidget(espaciador)

        layout.addLayout(encabezado)

        # ----------------------------------------------------------
        # FILA: imagen principal + información del producto
        # ----------------------------------------------------------
        fila_superior = QHBoxLayout()
        fila_superior.setSpacing(16)

        fila_superior.addWidget(self._crear_imagen_principal())
        fila_superior.addWidget(self._crear_info_producto())

        layout.addLayout(fila_superior)

        # ----------------------------------------------------------
        # IMÁGENES DEL PRODUCTO (galería numerada)
        # ----------------------------------------------------------
        layout.addWidget(self._crear_galeria_imagenes())

        # ----------------------------------------------------------
        # FILA: báscula + datos adicionales
        # ----------------------------------------------------------
        fila_inferior = QHBoxLayout()
        fila_inferior.setSpacing(16)

        fila_inferior.addWidget(self._crear_bascula())
        fila_inferior.addWidget(self._crear_datos_adicionales())

        layout.addLayout(fila_inferior)

        # ----------------------------------------------------------
        # BOTONES: Tara + Guardar peso
        # ----------------------------------------------------------
        fila_botones = QHBoxLayout()
        fila_botones.setSpacing(12)

        boton_tara = QPushButton("⚖  Tara")
        boton_tara.setFixedHeight(50)
        boton_tara.setStyleSheet("""
            QPushButton {
                background-color: white;
                color: #115E67;
                border: 1px solid #D9E2E4;
                border-radius: 10px;
                font-size: 15px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #EAF4F5;
            }
        """)
        boton_tara.clicked.connect(self._aplicar_tara)

        boton_guardar = QPushButton("💾  Guardar peso")
        boton_guardar.setFixedHeight(50)
        boton_guardar.setStyleSheet("""
            QPushButton {
                background-color: #115E67;
                color: white;
                border: none;
                border-radius: 10px;
                font-size: 15px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0D4D55;
            }
        """)
        boton_guardar.clicked.connect(self._guardar_peso)

        fila_botones.addWidget(boton_tara)
        fila_botones.addWidget(boton_guardar)
        layout.addLayout(fila_botones)

        self.setLayout(layout_externo)

    # ==============================================================
    # IMAGEN PRINCIPAL (con_arch)
    # ==============================================================

    def _crear_imagen_principal(self) -> QFrame:
        marco = QFrame()
        marco.setFixedSize(300, 260)
        marco.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #D9E2E4;
                border-radius: 12px;
            }
        """)

        layout = QVBoxLayout(marco)
        layout.setContentsMargins(8, 8, 8, 8)

        etiqueta_imagen = QLabel()
        etiqueta_imagen.setAlignment(Qt.AlignCenter)

        imagen_bytes = self.producto.get("imagen")
        if imagen_bytes:
            pixmap = QPixmap()
            if pixmap.loadFromData(imagen_bytes, "JPG"):
                pixmap = pixmap.scaled(280, 240, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                etiqueta_imagen.setPixmap(pixmap)
        else:
            etiqueta_imagen.setText("Sin imagen")
            etiqueta_imagen.setStyleSheet("color: #999; font-size: 13px;")

        layout.addWidget(etiqueta_imagen)
        return marco

    # ==============================================================
    # INFORMACIÓN DEL PRODUCTO
    # ==============================================================

    def _crear_info_producto(self) -> QFrame:
        marco = QFrame()
        marco.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #D9E2E4;
                border-radius: 12px;
            }
        """)

        layout = QVBoxLayout(marco)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)

        titulo = QLabel("Información del producto")
        titulo.setStyleSheet("font-size: 15px; font-weight: bold; color: #115E67;")
        layout.addWidget(titulo)

        datos = [
            ("Producto:", self.producto.get("nombre", "-")),
            ("PLU:", str(self.producto.get("cdgo_plu", "-"))),
            ("Especie:", self.especie),
        ]

        for etiqueta_texto, valor_texto in datos:
            fila = QHBoxLayout()
            etiqueta = QLabel(etiqueta_texto)
            etiqueta.setFixedWidth(110)
            etiqueta.setStyleSheet("color: #666; font-size: 13px;")

            valor = QLabel(str(valor_texto))
            valor.setWordWrap(True)
            valor.setStyleSheet("color: #222; font-size: 13px; font-weight: bold;")

            fila.addWidget(etiqueta)
            fila.addWidget(valor, stretch=1)
            layout.addLayout(fila)

        layout.addStretch()
        return marco

    # ==============================================================
    # GALERÍA DE IMÁGENES (con_arch_2 .. con_arch_6)
    # ==============================================================

    def _crear_galeria_imagenes(self) -> QFrame:
        marco = QFrame()
        marco.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #D9E2E4;
                border-radius: 12px;
            }
        """)

        layout_externo = QVBoxLayout(marco)
        layout_externo.setContentsMargins(16, 12, 16, 16)
        layout_externo.setSpacing(10)

        titulo = QLabel("Imágenes del producto")
        titulo.setStyleSheet("font-size: 14px; font-weight: bold; color: #115E67;")
        layout_externo.addWidget(titulo)

        fila_miniaturas = QHBoxLayout()
        fila_miniaturas.setSpacing(12)

        claves_imagenes = ["imagen_2", "imagen_3", "imagen_4", "imagen_5", "imagen_6"]

        for numero, clave in enumerate(claves_imagenes, start=1):
            fila_miniaturas.addWidget(self._crear_miniatura(numero, self.producto.get(clave)))

        fila_miniaturas.addStretch()
        layout_externo.addLayout(fila_miniaturas)

        return marco

    def _crear_miniatura(self, numero: int, imagen_bytes) -> QFrame:
        contenedor = QFrame()
        contenedor.setFixedSize(90, 90)
        contenedor.setStyleSheet("""
            QFrame {
                background-color: #F5F8F8;
                border: 1px solid #D9E2E4;
                border-radius: 10px;
            }
        """)

        layout = QVBoxLayout(contenedor)
        layout.setContentsMargins(4, 4, 4, 4)

        etiqueta = QLabel()
        etiqueta.setAlignment(Qt.AlignCenter)

        if imagen_bytes:
            pixmap = QPixmap()
            if pixmap.loadFromData(imagen_bytes, "JPG"):
                pixmap = pixmap.scaled(80, 80, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                etiqueta.setPixmap(pixmap)
        else:
            etiqueta.setText(str(numero))
            etiqueta.setStyleSheet("color: #999; font-size: 20px; font-weight: bold;")

        layout.addWidget(etiqueta)
        return contenedor

    # ==============================================================
    # BÁSCULA - PESO (placeholder, sin hardware conectado todavía)
    # ==============================================================

    def _crear_bascula(self) -> QFrame:
        marco = QFrame()
        marco.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #D9E2E4;
                border-radius: 12px;
            }
        """)

        layout = QVBoxLayout(marco)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(8)

        titulo = QLabel("Báscula - Peso")
        titulo.setStyleSheet("font-size: 15px; font-weight: bold; color: #115E67;")
        layout.addWidget(titulo)

        self.etiqueta_peso = QLabel(f"{self.peso_actual:.3f}")
        self.etiqueta_peso.setAlignment(Qt.AlignCenter)
        self.etiqueta_peso.setStyleSheet("""
            background-color: #E8F0EF;
            color: #115E67;
            font-size: 40px;
            font-weight: bold;
            font-family: 'Courier New';
            border-radius: 8px;
            padding: 10px;
        """)
        layout.addWidget(self.etiqueta_peso)

        self.etiqueta_peso_neto = QLabel(f"Peso neto        {self.peso_actual:.3f} kg")
        self.etiqueta_peso_neto.setStyleSheet("color: #444; font-size: 13px;")
        layout.addWidget(self.etiqueta_peso_neto)

        layout.addStretch()
        return marco

    # ==============================================================
    # DATOS ADICIONALES
    # ==============================================================

    def _crear_datos_adicionales(self) -> QFrame:
        marco = QFrame()
        marco.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #D9E2E4;
                border-radius: 12px;
            }
        """)

        layout = QVBoxLayout(marco)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(8)

        titulo = QLabel("Datos adicionales")
        titulo.setStyleSheet("font-size: 15px; font-weight: bold; color: #115E67;")
        layout.addWidget(titulo)

        etiqueta_fecha = QLabel("Fecha de vencimiento:")
        etiqueta_fecha.setStyleSheet("color: #666; font-size: 13px;")
        layout.addWidget(etiqueta_fecha)

        self.campo_fecha_vencimiento = QDateEdit()
        self.campo_fecha_vencimiento.setCalendarPopup(True)
        self.campo_fecha_vencimiento.setDisplayFormat("dd/MM/yyyy")
        self.campo_fecha_vencimiento.setDate(QDate.currentDate().addDays(7))  # QUEMADO: +7 días por defecto
        self.campo_fecha_vencimiento.setFixedHeight(38)
        self.campo_fecha_vencimiento.setStyleSheet("""
            QDateEdit {
                border: 1px solid #D9E2E4;
                border-radius: 8px;
                padding: 4px 10px;
                background-color: white;
            }
        """)
        layout.addWidget(self.campo_fecha_vencimiento)

        layout.addStretch()
        return marco

    # ==============================================================
    # ACCIONES
    # ==============================================================

    def _aplicar_tara(self):
        # Placeholder: aquí se conectará la báscula física real más adelante.
        self.peso_actual = 0.000
        self.etiqueta_peso.setText(f"{self.peso_actual:.3f}")
        self.etiqueta_peso_neto.setText(f"Peso neto        {self.peso_actual:.3f} kg")

    def _guardar_peso(self):
        # Placeholder: aquí se guardará el peso + fecha de vencimiento en la base de datos.
        datos = {
            "producto": self.producto.get("nombre"),
            "cdgo_plu": self.producto.get("cdgo_plu"),
            "lote": self.lote,
            "peso": self.peso_actual,
            "fecha_vencimiento": self.campo_fecha_vencimiento.date().toString("yyyy-MM-dd"),
        }
        print("Guardar peso:", datos)

    def _volver_a_seleccion_de_producto(self):
        from ui.seleccion_de_producto import SeleccionDeProducto
        from repositories.obtener_lote_fecha_repository import ObtenerLoteFechaRepository

        repository = ObtenerLoteFechaRepository()
        fecha_bd = self.fecha_produccion.replace("-", "/")
        lotes = repository.obtener_lotes_por_especie(fecha_bd, self.numEspecie)

        self.seleccion_de_producto = SeleccionDeProducto(
            usuario=self.usuario,
            fecha_produccion=self.fecha_produccion,
            especie=self.especie,
            numEspecie=self.numEspecie,
            lotes=lotes,
        )
        self.seleccion_de_producto.show()
        self.close()