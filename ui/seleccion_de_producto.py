"""
Ventana "Selección de producto".
Se abre después de elegir la especie en VentanaPrincipal, solo cuando
sí hay lotes disponibles para esa fecha + especie.

Muestra:
- Número de lote, fecha de producción y especie (los datos ya elegidos).
- Una matriz de 4x5 (20 botones) de productos; cada botón abre
  su Ficha Técnica correspondiente (ficha_tecnica.py).
"""

from PySide6.QtWidgets import (
    QWidget, QLabel, QPushButton,
    QVBoxLayout, QHBoxLayout, QGridLayout
)
from PySide6.QtCore import Qt

from utils.ventana_utils import aplicar_tamano
from ui.ficha_tecnica import FichaTecnica

FILAS_MATRIZ = 4
COLUMNAS_MATRIZ = 5

# Lista temporal de productos para llenar la matriz.
# Reemplázala por la consulta real (repository) cuando esté lista.
PRODUCTOS_DEMO = [f"Producto {n}" for n in range(1, FILAS_MATRIZ * COLUMNAS_MATRIZ + 1)]

ANCHO_CONTENIDO = 760

from PySide6.QtWidgets import (
    QWidget,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QFrame,
    QLineEdit
)
from PySide6.QtCore import Qt, QSize, QTimer
from PySide6.QtGui import QPixmap, QIcon

from utils.ventana_utils import aplicar_tamano
from ui.ficha_tecnica import FichaTecnica

from models.database import conectar_bd


FILAS_MATRIZ = 4
COLUMNAS_MATRIZ = 5

PRODUCTOS_POR_PAGINA = 20

ANCHO_CONTENIDO = 1100


class SeleccionDeProducto(QWidget):

    def __init__(
        self,
        usuario,
        fecha_produccion: str,
        especie: str,
        numEspecie,
        lotes: list
    ):
        super().__init__()

        self.usuario = usuario
        self.fecha_produccion = fecha_produccion
        self.especie = especie
        self.numEspecie = int(numEspecie)
        self.lotes = lotes

        self.ventana_ficha_tecnica = None

        # Paginación
        self.pagina_actual = 1
        self.total_productos = 0
        self.total_paginas = 0

        self.setWindowTitle("Selección de producto")

        aplicar_tamano(self, modo="completo")

        self.setStyleSheet("""
            QWidget {
                background-color: #F5F8F8;
            }
        """)

        self._crear_interfaz()

        self._cargar_total_productos()

        self._cargar_pagina()

    # ==========================================================
    # INTERFAZ
    # ==========================================================

    def _crear_interfaz(self):

        fila_central = QHBoxLayout()
        fila_central.addStretch()

        layout = QVBoxLayout()
        layout.setContentsMargins(25, 20, 25, 20)
        layout.setSpacing(12)

        contenedor = QWidget()
        contenedor.setFixedWidth(ANCHO_CONTENIDO)
        contenedor.setLayout(layout)

        fila_central.addWidget(contenedor)
        fila_central.addStretch()
        
        layout_externo = QVBoxLayout()
        layout_externo.setContentsMargins(0, 0, 0, 0)
        layout_externo.addStretch()
        layout_externo.addLayout(fila_central)
        layout_externo.addStretch()

        # ======================================================
        # TÍTULO
        # ======================================================

        titulo = QLabel("SELECCIÓN DE PRODUCTO")
        titulo.setAlignment(Qt.AlignCenter)

        titulo.setStyleSheet("""
            QLabel {
                background-color: #115E67;
                color: white;
                font-size: 26px;
                font-weight: bold;
                padding: 14px;
                border-radius: 10px;
            }
        """)

        layout.addWidget(titulo)

        # ======================================================
        # DATOS
        # ======================================================
        fila_datos = QHBoxLayout()
        fila_datos.setSpacing(12)

        lote = self.lotes[0].lote if self.lotes else "Sin lote"

        fila_datos.addWidget(
            self._crear_dato(
                "LOTE",
                lote
            )
        )

        fila_datos.addWidget(
            self._crear_dato(
                "FECHA DE PRODUCCIÓN",
                self.fecha_produccion
            )
        )

        fila_datos.addWidget(
            self._crear_dato(
                "ESPECIE",
                self.especie
            )
        )

        layout.addLayout(fila_datos)

        # ======================================================
        # TÍTULO PRODUCTOS
        # ======================================================

        titulo_productos = QLabel("SELECCIONE UN PRODUCTO")

        titulo_productos.setAlignment(Qt.AlignCenter)

        titulo_productos.setStyleSheet("""
            QLabel {
                color: #115E67;
                font-size: 21px;
                font-weight: bold;
                padding: 5px;
            }
        """)

        layout.addWidget(titulo_productos)

        # ======================================================
        # MATRIZ 4 X 5
        # ======================================================

        self.matriz_productos = QGridLayout()
        self.matriz_productos.setSpacing(10)

        layout.addLayout(self.matriz_productos)

        # ======================================================
        # PAGINACIÓN
        # ======================================================

        self.layout_paginacion = QHBoxLayout()
        self.layout_paginacion.setSpacing(5)

        layout.addLayout(self.layout_paginacion)

        # ======================================================
        # ATRÁS
        # ======================================================

        # --- dentro de tu método que arma la interfaz (ej. _crear_interfaz) ---
        boton_atras = QPushButton("←  ATRÁS")
        boton_atras.setFixedHeight(45)
        boton_atras.setStyleSheet("""
            QPushButton {
                background-color: #115E67;
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 15px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0D4D55;
            }
        """)
        boton_atras.clicked.connect(self._volver_a_principal)
        layout.addWidget(boton_atras)
        self.setLayout(layout_externo)

    # --- método SEPARADO, al mismo nivel que __init__, NO adentro de él ---
    def _volver_a_principal(self):
        from ui.ventana_principal import VentanaPrincipal
        self.ventana_principal = VentanaPrincipal(self.usuario)
        self.ventana_principal.show()
        self.close()

    # ==========================================================
    # DATOS SUPERIORES
    # ==========================================================

    def _crear_dato(self, titulo, valor):

        contenedor = QFrame()

        contenedor.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #D9E2E4;
                border-radius: 10px;
            }
        """)

        layout = QVBoxLayout(contenedor)

        etiqueta_titulo = QLabel(titulo)
        etiqueta_titulo.setAlignment(Qt.AlignCenter)

        etiqueta_titulo.setStyleSheet("""
            QLabel {
                color: #555;
                font-size: 11px;
                border: none;
            }
        """)

        etiqueta_valor = QLabel(str(valor))
        etiqueta_valor.setAlignment(Qt.AlignCenter)

        etiqueta_valor.setStyleSheet("""
            QLabel {
                color: #115E67;
                font-size: 16px;
                font-weight: bold;
                border: none;
            }
        """)

        layout.addWidget(etiqueta_titulo)
        layout.addWidget(etiqueta_valor)

        return contenedor

    # ==========================================================
    # CONSULTA TOTAL
    # ==========================================================

    def _cargar_total_productos(self):

        conexion = conectar_bd(
            database_key="DB_DATABASE_1"
        )

        try:

            cursor = conexion.cursor()

            cursor.execute("""
                SELECT COUNT(*)
                FROM imagenes
                WHERE nom_prog <> 'productos'
            """)

            self.total_productos = cursor.fetchone()[0]

            self.total_paginas = (
                self.total_productos
                + PRODUCTOS_POR_PAGINA
                - 1
            ) // PRODUCTOS_POR_PAGINA

        finally:
            conexion.close()

    # ==========================================================
    # OBTENER PRODUCTOS DE LA PÁGINA
    # ==========================================================

    def _obtener_productos(self):

        conexion = conectar_bd(
            database_key="DB_DATABASE_1"
        )

        try:

            cursor = conexion.cursor()

            offset = (
                self.pagina_actual - 1
            ) * PRODUCTOS_POR_PAGINA
            
            cursor.execute("""
            SELECT 
                p.cdgo_plu, 
                p.nmbre_crto AS nom_prog,
                CAST(
                    CAST(i.con_arch AS VARCHAR(MAX))
                    AS VARBINARY(MAX)
                ) AS con_arch,
                CAST(i.con_arch_2 AS VARBINARY(MAX)) AS con_arch_2,
                CAST(i.con_arch_3 AS VARBINARY(MAX)) AS con_arch_3,
                CAST(i.con_arch_4 AS VARBINARY(MAX)) AS con_arch_4,
                CAST(i.con_arch_5 AS VARBINARY(MAX)) AS con_arch_5,
                CAST(i.con_arch_6 AS VARBINARY(MAX)) AS con_arch_6
            FROM GESDOCUM_PRUEBAS.dbo.imagenes i
            INNER JOIN SIPPCPRUEBAS2.dbo.prdctos p
                ON i.referencia = CAST(p.cdgo_plu AS VARCHAR(50))
            WHERE i.nom_prog = 'productos'
              AND p.cdgo_espcie = ?
            ORDER BY p.nmbre_crto
            OFFSET ? ROWS
            FETCH NEXT ? ROWS ONLY
            """,
                int(self.numEspecie),
                offset,
                PRODUCTOS_POR_PAGINA
            )

            productos = []

            for fila in cursor.fetchall():
                productos.append({
                    "nombre": fila.nom_prog,
                    "cdgo_plu": fila.cdgo_plu,
                    "imagen": bytes(fila.con_arch) if fila.con_arch is not None else None,
                    "imagen_2": bytes(fila.con_arch_2) if fila.con_arch_2 is not None else None,
                    "imagen_3": bytes(fila.con_arch_3) if fila.con_arch_3 is not None else None,
                    "imagen_4": bytes(fila.con_arch_4) if fila.con_arch_4 is not None else None,
                    "imagen_5": bytes(fila.con_arch_5) if fila.con_arch_5 is not None else None,
                    "imagen_6": bytes(fila.con_arch_6) if fila.con_arch_6 is not None else None,
                })

            return productos

        finally:
            conexion.close()

    # ==========================================================
    # CARGAR PÁGINA
    # ==========================================================

    def _cargar_pagina(self):

        self._limpiar_matriz()

        productos = self._obtener_productos()

        for indice, producto in enumerate(productos):

            fila = indice // COLUMNAS_MATRIZ
            columna = indice % COLUMNAS_MATRIZ

            boton = self._crear_boton_producto(
                producto
            )

            self.matriz_productos.addWidget(
                boton,
                fila,
                columna
            )

        self._actualizar_paginacion()

    # ==========================================================
    # BOTÓN PRODUCTO
    # ==========================================================

    def _crear_boton_producto(self, producto):

        boton = QPushButton()

        boton.setFixedSize(195, 140)

        boton.setStyleSheet("""
            QPushButton {
                background-color: white;
                border: 2px solid #D9E2E4;
                border-radius: 12px;
                color: #115E67;
                font-size: 14px;
                font-weight: bold;
            }

            QPushButton:hover {
                border: 3px solid #94B7BB;
                background-color: #F7FAFA;
            }

            QPushButton:pressed {
                background-color: #DDEEEF;
            }
        """)

        imagen = producto["imagen"]

        if imagen:

            pixmap = QPixmap()

            if pixmap.loadFromData(imagen):

                pixmap = pixmap.scaled(
                    175,
                    95,
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                )

                boton.setIcon(QIcon(pixmap))
                boton.setIconSize(
                    QSize(175, 95)
                )

        # NOMBRE REAL DESDE nom_prog
        boton.setText(
            producto["nombre"]
        )

        

        boton.clicked.connect(
            lambda checked=False,
                   producto=producto:
            self._abrir_ficha_tecnica(producto)
        )

        return boton

    # ==========================================================
    # PAGINACIÓN
    # ==========================================================

    def _actualizar_paginacion(self):

        self._limpiar_paginacion()

        inicio = (
            (self.pagina_actual - 1)
            * PRODUCTOS_POR_PAGINA
        ) + 1

        fin = min(
            self.pagina_actual
            * PRODUCTOS_POR_PAGINA,
            self.total_productos
        )

        informacion = QLabel(
            f"Mostrando {inicio} - {fin} "
            f"de {self.total_productos} productos"
        )

        informacion.setStyleSheet("""
            QLabel {
                background-color: white;
                color: #115E67;
                padding: 10px 15px;
                border: 1px solid #D9E2E4;
                border-radius: 8px;
                font-weight: bold;
            }
        """)

        self.layout_paginacion.addWidget(
            informacion
        )

        self.layout_paginacion.addStretch()

        # PRIMERA
        boton = self._boton_pagina("«")

        boton.clicked.connect(
            lambda: self._ir_a_pagina(1)
        )

        self.layout_paginacion.addWidget(boton)

        # ANTERIOR
        boton = self._boton_pagina("‹")

        boton.clicked.connect(
            lambda: self._ir_a_pagina(
                self.pagina_actual - 1
            )
        )

        boton.setEnabled(
            self.pagina_actual > 1
        )

        self.layout_paginacion.addWidget(boton)

        # NÚMEROS
        paginas = range(
            1,
            self.total_paginas + 1
        )

        for pagina in paginas:

            boton = self._boton_pagina(
                str(pagina),
                activo=(
                    pagina == self.pagina_actual
                )
            )

            boton.clicked.connect(
                lambda checked=False,
                       p=pagina:
                self._ir_a_pagina(p)
            )

            self.layout_paginacion.addWidget(
                boton
            )

        # SIGUIENTE
        boton = self._boton_pagina("›")

        boton.clicked.connect(
            lambda: self._ir_a_pagina(
                self.pagina_actual + 1
            )
        )

        boton.setEnabled(
            self.pagina_actual
            < self.total_paginas
        )

        self.layout_paginacion.addWidget(boton)

        # ÚLTIMA
        boton = self._boton_pagina("»")

        boton.clicked.connect(
            lambda: self._ir_a_pagina(
                self.total_paginas
            )
        )

        self.layout_paginacion.addWidget(boton)

    # ==========================================================
    # BOTÓN PAGINACIÓN
    # ==========================================================

    def _boton_pagina(
        self,
        texto,
        activo=False
    ):

        boton = QPushButton(texto)

        boton.setFixedSize(42, 42)

        if activo:

            boton.setStyleSheet("""
                QPushButton {
                    background-color: #115E67;
                    color: white;
                    border: none;
                    border-radius: 8px;
                    font-size: 15px;
                    font-weight: bold;
                }
            """)

        else:

            boton.setStyleSheet("""
                QPushButton {
                    background-color: white;
                    color: #115E67;
                    border: 1px solid #D9E2E4;
                    border-radius: 8px;
                    font-size: 15px;
                    font-weight: bold;
                }

                QPushButton:hover {
                    background-color: #DDEEEF;
                }
            """)

        return boton

    # ==========================================================
    # CAMBIAR PÁGINA
    # ==========================================================

    def _ir_a_pagina(self, pagina):

        if pagina < 1:
            return

        if pagina > self.total_paginas:
            return

        self.pagina_actual = pagina

        self._cargar_pagina()

    # ==========================================================
    # LIMPIAR MATRIZ
    # ==========================================================

    def _limpiar_matriz(self):

        while self.matriz_productos.count():

            item = self.matriz_productos.takeAt(0)

            widget = item.widget()

            if widget:
                widget.deleteLater()

    # ==========================================================
    # LIMPIAR PAGINACIÓN
    # ==========================================================

    def _limpiar_paginacion(self):

        while self.layout_paginacion.count():

            item = self.layout_paginacion.takeAt(0)

            widget = item.widget()

            if widget:
                widget.deleteLater()

    # ==========================================================
    # FICHA TÉCNICA
    # ==========================================================

    def _abrir_ficha_tecnica(self, producto):
        self.ventana_ficha_tecnica = FichaTecnica(
            usuario=self.usuario,
            producto=producto,  # ahora es el diccionario completo, no solo el nombre
            fecha_produccion=self.fecha_produccion,
            especie=self.especie,
            numEspecie=self.numEspecie,
            lote=self.campo_lote.currentText() if hasattr(self, "campo_lote") else (self.lotes[0].lote if self.lotes else ""),
        )
        self.ventana_ficha_tecnica.show()
        self.close()