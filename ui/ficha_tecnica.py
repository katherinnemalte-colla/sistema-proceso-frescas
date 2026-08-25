from PySide6.QtWidgets import (
    QWidget, QLabel, QPushButton, QFrame, QGridLayout,
    QVBoxLayout, QHBoxLayout, QDateEdit, QButtonGroup, QSizePolicy
)
from PySide6.QtCore import Qt, QSize, QDate
from PySide6.QtGui import QPixmap, QIcon
from types import SimpleNamespace
from utils.ventana_utils import aplicar_tamano
from repositories.obtener_tipo_pza_repository import ObtenerTipoPzaRepository
from repositories.obtener_tipo_limpieza_repository import ObtenerTipoLimpiezaRepository
#from repositories.etiquetas.frescas_100x45 import DatosEtiquetaFrescas
from repositories.etiquetas.frescas_100x45 import construir_datos_etiqueta, imprimir_etiqueta_frescas

ANCHO_CONTENIDO = 950


class FichaTecnica(QWidget):
    def __init__(
        self,
        usuario,
        producto: dict,
        fecha_produccion: str,
        especie: str,
        numEspecie,
        lote: str,
        tpo_pza=None,
        nombre_tipo_pieza=None,
    ):
        super().__init__()
        self.usuario = usuario
        self.producto = producto
        self.fecha_produccion = fecha_produccion
        self.especie = especie
        self.numEspecie = int(numEspecie)
        self.lote = lote
        self.tpo_pza = tpo_pza
        self.nombre_tipo_pieza = nombre_tipo_pieza

        self.seleccion_de_producto = None
        self.peso_actual = 0.000  # placeholder: aquí se conectará la báscula real

        # ------------------------------------------------------------
        # LAS 6 IMÁGENES: solo se consultan cuando viene de RES
        # (tpo_pza no es None). El diccionario "producto" que llega de
        # SeleccionDeProducto solo trae la imagen principal, así que
        # las 5 adicionales se piden acá con obtener_producto_completo.
        # ------------------------------------------------------------
        self.producto_completo = None
        if self.tpo_pza is not None:
            repositorio_imagenes = ObtenerTipoPzaRepository(self._obtener_conexion)
            self.producto_completo = repositorio_imagenes.obtener_producto_completo(
                self.tpo_pza,
                str(self.producto.get("cdgo_plu", "")),
            )

        # ------------------------------------------------------------
        # TIPOS DE LIMPIEZA (catálogo, botón seleccionable exclusivo)
        # ------------------------------------------------------------
        self.tipo_limpieza_seleccionado = None
        self._grupo_limpieza = None

        self.setWindowTitle(f"Ficha técnica - {producto.get('nombre', '')}")
        aplicar_tamano(self, modo="completo")
        self.setStyleSheet("QWidget { background-color: #F5F8F8; }")

        self._crear_interfaz()

    # ==============================================================
    # CONEXIÓN A BD — mismo patrón que SeleccionDeProducto
    # ==============================================================
    def _obtener_conexion(self):
        from models.database import obtener_conexion  # import local para evitar ciclos
        return obtener_conexion()

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
        # TIPO DE LIMPIEZA (catálogo dinámico, selección exclusiva)
        # ----------------------------------------------------------
        layout.addWidget(self._crear_seccion_tipo_limpieza())

        # ----------------------------------------------------------
        # FILA: báscula + datos adicionales
        # ----------------------------------------------------------
        fila_inferior = QHBoxLayout()
        fila_inferior.setSpacing(16)

        fila_inferior.addWidget(self._crear_bascula())
        fila_inferior.addWidget(self._crear_datos_adicionales())

        layout.addLayout(fila_inferior)

        # ----------------------------------------------------------
        # BOTONES: Ir a inicio + Guardar peso
        # ----------------------------------------------------------
        fila_botones = QHBoxLayout()
        fila_botones.setSpacing(12)

        boton_inicio = QPushButton("Ir a inicio")
        boton_inicio.setFixedHeight(50)
        boton_inicio.setStyleSheet("""
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
        boton_inicio.clicked.connect(self._volver_a_inicio)

        boton_guardar = QPushButton("Imprime")
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

        fila_botones.addWidget(boton_inicio)
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

        imagen_raw = self.producto.get("imagen")
        imagen_bytes = self._normalizar_imagen_bytes(imagen_raw)

        pixmap = QPixmap()
        if imagen_bytes and pixmap.loadFromData(imagen_bytes):  # sin formato forzado
            pixmap = pixmap.scaled(280, 240, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            etiqueta_imagen.setPixmap(pixmap)
        else:
            etiqueta_imagen.setText("Sin imagen")
            etiqueta_imagen.setStyleSheet("color: #999; font-size: 13px;")

        layout.addWidget(etiqueta_imagen)
        return marco

    def _normalizar_imagen_bytes(self, valor):
        """Convierte lo que venga de la BD a bytes reales, o None si no hay nada usable."""
        if not valor:
            return None
        if isinstance(valor, (bytes, bytearray)):
            return bytes(valor)
        if isinstance(valor, str):
            import base64
            try:
                # Caso típico: string base64 (con o sin prefijo data:image/...;base64,)
                if valor.startswith("data:image"):
                    valor = valor.split(",", 1)[1]
                return base64.b64decode(valor)
            except Exception:
                return None
        return None

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

        # Solo aparece en el flujo RES, cuando sí hay tipo de pieza.
        if self.tpo_pza is not None and self.nombre_tipo_pieza:
            datos.append(("Tipo de pieza:", self.nombre_tipo_pieza))

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

        # Antes se leían de self.producto.get("imagen_2".."imagen_6"),
        # que nunca llegaban ahí. Ahora salen de self.producto_completo,
        # traído con ObtenerTipoPzaRepository.obtener_producto_completo.
        if self.producto_completo is not None:
            imagenes_extra = [
                self.producto_completo.con_arch_2,
                self.producto_completo.con_arch_3,
                self.producto_completo.con_arch_4,
                self.producto_completo.con_arch_5,
                self.producto_completo.con_arch_6,
            ]
        else:
            imagenes_extra = [None, None, None, None, None]

        for numero, imagen_bytes in enumerate(imagenes_extra, start=2):
            fila_miniaturas.addWidget(self._crear_miniatura(numero, imagen_bytes))

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

        datos = self._normalizar_imagen_bytes(imagen_bytes)

        if datos:
            pixmap = QPixmap()
            # Sin forzar "JPG": algunas de estas imágenes pueden ser
            # PNG u otro formato, y loadFromData detecta el formato
            # solo si no se lo forzamos.
            if pixmap.loadFromData(datos):
                pixmap = pixmap.scaled(80, 80, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                etiqueta.setPixmap(pixmap)
            else:
                etiqueta.setText(str(numero))
                etiqueta.setStyleSheet("color: #999; font-size: 20px; font-weight: bold;")
        else:
            etiqueta.setText(str(numero))
            etiqueta.setStyleSheet("color: #999; font-size: 20px; font-weight: bold;")

        layout.addWidget(etiqueta)
        return contenedor

    # ==============================================================
    # TIPO DE LIMPIEZA (catálogo dinámico desde tpo_lmpza)
    # ==============================================================

    def _crear_seccion_tipo_limpieza(self) -> QFrame:
        marco = QFrame()
        marco.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #D9E2E4;
                border-radius: 12px;
            }
        """)

        layout = QVBoxLayout(marco)
        layout.setContentsMargins(16, 12, 16, 16)
        layout.setSpacing(10)

        titulo = QLabel("Tipo de limpieza")
        titulo.setStyleSheet("font-size: 14px; font-weight: bold; color: #115E67;")
        layout.addWidget(titulo)

        fila_botones = QHBoxLayout()
        fila_botones.setSpacing(10)

        try:
            repositorio_limpieza = ObtenerTipoLimpiezaRepository(self._obtener_conexion)
            tipos_limpieza = repositorio_limpieza.obtener_tipos_limpieza()
        except Exception as e:
            print("No fue posible cargar tipos de limpieza:", e)
            tipos_limpieza = []

        self._grupo_limpieza = QButtonGroup(self)
        self._grupo_limpieza.setExclusive(True)

        if not tipos_limpieza:
            etiqueta_vacio = QLabel("No hay tipos de limpieza configurados.")
            etiqueta_vacio.setStyleSheet("color: #999; font-size: 13px;")
            fila_botones.addWidget(etiqueta_vacio)
        else:
            for tipo in tipos_limpieza:
                boton = QPushButton(tipo.nmbre or f"Tipo {tipo.tpo_lmpza}")
                boton.setCheckable(True)
                boton.setCursor(Qt.PointingHandCursor)
                boton.setMinimumHeight(42)
                boton.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
                boton.setProperty("tpo_lmpza", tipo.tpo_lmpza)
                boton.setProperty("nombre_limpieza", tipo.nmbre)

                boton.setStyleSheet("""
                    QPushButton {
                        background-color: white;
                        color: #115E67;
                        border: 1px solid #D9E2E4;
                        border-radius: 10px;
                        font-size: 13px;
                        font-weight: 600;
                    }
                    QPushButton:hover {
                        background-color: #EAF4F5;
                    }
                    QPushButton:checked {
                        background-color: #115E67;
                        color: white;
                        border: 1px solid #115E67;
                    }
                """)

                self._grupo_limpieza.addButton(boton)
                fila_botones.addWidget(boton)

            self._grupo_limpieza.buttonClicked.connect(self._tipo_limpieza_elegido)

        fila_botones.addStretch()
        layout.addLayout(fila_botones)

        return marco

    def _tipo_limpieza_elegido(self, boton):
        self.tipo_limpieza_seleccionado = boton.property("tpo_lmpza")
        print("Tipo de limpieza seleccionado:", boton.property("nombre_limpieza"))

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


        layout.addStretch()
        return marco

    # ==============================================================
    # ACCIONES
    # ==============================================================
    def _guardar_peso(self):
        producto_para_etiqueta = self.producto_completo or SimpleNamespace(
            cdgo_plu=self.producto.get("cdgo_plu"),
            nom_prog=self.producto.get("nom_prog", self.producto.get("nombre", "")),
        )

        datos = construir_datos_etiqueta(
            producto=producto_para_etiqueta,
            lote=self.lote,
            fecha_produccion=self.fecha_produccion,
            nombre_usuario=self.usuario,
            tipo_limpieza_seleccionado=self.tipo_limpieza_seleccionado,
    )
        """
    def _guardar_peso(self):

        datos = construir_datos_etiqueta(
            #cdgo_plu=11
            producto=self.producto_completo,        # o el objeto Producto que tengas
            lote=self.lote,
            fecha_produccion=self.fecha_produccion,
            nombre_usuario=self.usuario,      # ajusta al atributo real de tu Usuario
            #tipo_limpieza_seleccionado=self.tipo_limpieza_seleccionado,
        )
        #print(f"el nombre del usuario{self.producto}" )
        #print(f"el nombre del usuario{self.producto_completo}" )
        """
        imprimir_etiqueta_frescas(datos, "ZDesigner GK420t (Copiar 1)")
        # Placeholder: aquí se guardará el peso + fecha de vencimiento en la base de datos.
        """
        datos = {
            "producto": self.producto.get("nombre"),
            "cdgo_plu": self.producto.get("cdgo_plu"),
            "lote": self.lote,
            "peso": self.peso_actual,
            "tipo_limpieza": self.tipo_limpieza_seleccionado,
        }
        print("Guardar peso:", datos)
        """
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
            tpo_pza=self.tpo_pza,
            nombre_tipo_pieza=self.nombre_tipo_pieza,
            lotes=lotes,
        )
        self.seleccion_de_producto.show()
        self.close()

    def _volver_a_inicio(self):
        from ui.ventana_principal import VentanaPrincipal

        self.ventana_principal = VentanaPrincipal(self.usuario)
        self.ventana_principal.show()
        self.close()