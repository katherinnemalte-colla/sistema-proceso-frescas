import os

from PySide6.QtCore import Qt, Signal, QTimer, QByteArray
from PySide6.QtGui import QPixmap, QColor
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QFrame,
    QScrollArea,
    QSizePolicy,
    QGraphicsDropShadowEffect,
)
from PySide6.QtGui import QIntValidator
from utils.ventana_utils import aplicar_tamano
from repositories.imagen_repository import ImagenRepository, TAMANO_PAGINA
from repositories.obtener_tipo_pza_repository import ObtenerTipoPzaRepository
from utils import fechas
from utils.colores import Colores
from collections import namedtuple

CriterioFiltroRes = namedtuple(
    "CriterioFiltroRes",
    ["tpo_pza", "cdgo_espcie", "cdgo_plu", "cod_emprsa"],
)


# Cuántos botones de letra se muestran a la vez en el paginador.
BOTONES_LETRA_VISIBLES = 19

# Columnas de la grilla de productos.
COLUMNAS_GRILLA = 4

# --- Paleta ---------------------------------------------------------------
COLOR_PRIMARIO = "#1a6b6b"
COLOR_PRIMARIO_OSCURO = "#134f4f"
COLOR_PRIMARIO_CLARO = "#e6f2f2"
COLOR_SELECCIONADO = "#1a6b6b"
COLOR_BORDE = "#dfe6e6"
COLOR_TEXTO_SECUNDARIO = "#8a97a0"
COLOR_FONDO = "#eef3f3"

RUTA_ICONOS = os.path.join("assets", "icons", "icons")

def _ruta_icono(nombre_archivo):
    return os.path.join(RUTA_ICONOS, nombre_archivo)


def _icono_pixmap(nombre_archivo, tamano):
    """Carga un ícono desde RUTA_ICONOS ya escalado; None si no existe."""
    ruta = _ruta_icono(nombre_archivo)
    if not os.path.isfile(ruta):
        return None
    pixmap = QPixmap(ruta)
    if pixmap.isNull():
        return None
    return pixmap.scaled(tamano, tamano, Qt.KeepAspectRatio, Qt.SmoothTransformation)


def _aplicar_sombra(widget, blur=18, dx=0, dy=4, alfa=40):
    """Sombra suave reutilizable para tarjetas."""
    sombra = QGraphicsDropShadowEffect(widget)
    sombra.setBlurRadius(blur)
    sombra.setOffset(dx, dy)
    sombra.setColor(QColor(0, 0, 0, alfa))
    widget.setGraphicsEffect(sombra)


class ImagenEscalable(QLabel):

    def __init__(self, parent=None):
        super().__init__(parent)
        self._pixmap_original = None
        self.setAlignment(Qt.AlignCenter)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumHeight(60)

    def set_pixmap_original(self, pixmap):
        self._pixmap_original = pixmap
        self._actualizar_pixmap_escalado()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._actualizar_pixmap_escalado()

    def _actualizar_pixmap_escalado(self):
        if self._pixmap_original is None:
            return
        margen = 16
        ancho_disponible = max(1, self.width() - margen)
        alto_disponible = max(1, self.height() - margen)
        super().setPixmap(
            self._pixmap_original.scaled(
                ancho_disponible,
                alto_disponible,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
        )


class ProductoWidget(QFrame):
    """Tarjeta clickeable de un producto: imagen + N° PLU + nombre."""

    clicked = Signal(object)  # emite el Producto

    def __init__(self, producto, parent=None):
        super().__init__(parent)
        self.producto = producto
        self.setCursor(Qt.PointingHandCursor)
        self.setObjectName("tarjetaProducto")
        self.setStyleSheet(
            f"""
            #tarjetaProducto {{
                background: white;
                border: 1px solid {Colores.BORDE};
                border-radius: 14px;
            }}
            #tarjetaProducto:hover {{
                border: 1px solid {Colores.PRIMARIO};
            }}
            """
        )
        _aplicar_sombra(self, blur=16, dy=3, alfa=30)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # --- Imagen, con aire alrededor y esquinas redondeadas propias ---
        contenedor_imagen = QFrame()
        contenedor_imagen.setObjectName("contenedorImagen")
        contenedor_imagen.setStyleSheet(
            "#contenedorImagen { background: #f4f6f6; border-top-left-radius: 14px; "
            "border-top-right-radius: 14px; }"
        )
        layout_imagen = QVBoxLayout(contenedor_imagen)
        layout_imagen.setContentsMargins(10, 10, 10, 10)

        etiqueta_imagen = ImagenEscalable()
        etiqueta_imagen.setMinimumHeight(120)
        etiqueta_imagen.setMaximumHeight(220)
        etiqueta_imagen.setStyleSheet("background: transparent; border-radius: 8px;")

        pixmap = self._cargar_pixmap(producto.imagen_principal)
        if pixmap is not None:
            etiqueta_imagen.set_pixmap_original(pixmap)
        else:
            etiqueta_imagen.setText("Sin imagen")
            etiqueta_imagen.setStyleSheet(
                "background: transparent; color: #aab3b3; border-radius: 8px;"
            )

        layout_imagen.addWidget(etiqueta_imagen)

        # --- PLU + nombre, juntos, con una franja inferior de color ---
        bloque_texto = QVBoxLayout()
        bloque_texto.setContentsMargins(12, 10, 12, 12)
        bloque_texto.setSpacing(2)

        etiqueta_plu = QLabel(f"PLU {producto.cdgo_plu}")
        etiqueta_plu.setAlignment(Qt.AlignCenter)
        etiqueta_plu.setStyleSheet(
            f"color: {COLOR_TEXTO_SECUNDARIO}; font-size: 11px; letter-spacing: 0.5px;"
        )

        etiqueta_nombre = QLabel(producto.nom_prog.upper())
        etiqueta_nombre.setAlignment(Qt.AlignCenter)
        etiqueta_nombre.setWordWrap(True)
        etiqueta_nombre.setStyleSheet(
            f"color: {COLOR_PRIMARIO}; font-size: 14px; font-weight: 700;"
        )

        bloque_texto.addWidget(etiqueta_plu)
        bloque_texto.addWidget(etiqueta_nombre)

        # Franja delgada de acento, pegada abajo de la tarjeta.
        franja_acento = QFrame()
        franja_acento.setFixedHeight(4)
        franja_acento.setStyleSheet(
            f"background: {COLOR_PRIMARIO}; border-bottom-left-radius: 14px; "
            "border-bottom-right-radius: 14px;"
        )

        layout.addWidget(contenedor_imagen)
        layout.addLayout(bloque_texto)
        layout.addWidget(franja_acento)

    @staticmethod
    def _cargar_pixmap(datos_binarios):
        if not datos_binarios:
            return None

        if not isinstance(datos_binarios, (bytes, bytearray, memoryview)):
            #revisar el esquema
            print(
                "con_arch llegó con tipo inesperado:",
                type(datos_binarios),
                repr(datos_binarios)[:100],
            )
            return None

        pixmap = QPixmap()
        if pixmap.loadFromData(QByteArray(bytes(datos_binarios))):
            return pixmap
        return None

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.producto)
        super().mousePressEvent(event)


class SeleccionDeProducto(QWidget):

  
    def __init__(
        self,
        usuario,
        lotes,
        obtener_conexion,
        app_ventana,
        parent=None,
        *,
        fecha_produccion,
        especie,
        numEspecie,
        tpo_pza=None,
        nombre_tipo_pieza=None,
        empresa,
    ):
        super().__init__(parent)
        self.usuario = usuario
        self._obtener_conexion = obtener_conexion
        self._app = app_ventana
        self.fecha_produccion = fecha_produccion
        self.especie = especie
        self.numEspecie = numEspecie
        self.tpo_pza = tpo_pza
        self.nombre_tipo_pieza = nombre_tipo_pieza
        self.empresa = empresa
        #self.peso_neto_kg = peso_neto_kg


        # ------------------------------------------------------------
        # REPOSITORIO: cuál usar depende de si viene tpo_pza (RES) o no.
        # Ambos repositorios exponen los mismos métodos, así que el
        # resto de esta clase llama siempre a self.repositorio y usa
        # self._criterio_filtro, sin ramificar por especie.
        # ------------------------------------------------------------

        if self.tpo_pza is not None:
            self.repositorio = ObtenerTipoPzaRepository(self._obtener_conexion)
            self._criterio_filtro = self._obtener_criterio_filtro()
        else:
            self.repositorio = ImagenRepository(self._obtener_conexion)
            self._criterio_filtro = self.numEspecie

        # Estado del paginador alfabético
        self._paginas_letras = []      # list[PaginaLetra]
        self._indice_pagina_actual = 0
        self._indice_ventana = 0
        self.lotes = lotes
        self._ventana_ficha_tecnica = None

        self._construir_ui()
        self._cargar_paginador_alfabetico()
        aplicar_tamano(self, modo="completo", ancho_pct=0.7, alto_pct=0.85)

    # ------------------------------------------------------------------
    # Conexión a BD — ajustar según el módulo real del proyecto
    # ------------------------------------------------------------------
    # ------------------------------------------------------------------
    # Construcción de la UI
    # ------------------------------------------------------------------
    def _construir_ui(self):
        self.setStyleSheet(f"background: {COLOR_FONDO};")
        layout_principal = QVBoxLayout(self)
        layout_principal.setContentsMargins(0, 0, 0, 0)
        layout_principal.setSpacing(0)

        #layout_principal.addWidget(self._crear_cabecera())
        layout_principal.addWidget(self._crear_boton_atras())
        layout_principal.addWidget(self._crear_tarjetas_info())
        layout_principal.addWidget(self._crear_fila_filtros())
        layout_principal.addWidget(self._crear_titulo_seccion())

        # Área con scroll para la grilla de productos
        self._area_scroll = QScrollArea()
        self._area_scroll.setWidgetResizable(True)
        self._area_scroll.setStyleSheet("border: none; background: transparent;")

        self._contenedor_grilla = QWidget()
        self._contenedor_grilla.setStyleSheet("background: transparent;")
        self._layout_grilla = QGridLayout(self._contenedor_grilla)
        self._layout_grilla.setContentsMargins(28, 16, 28, 16)
        self._layout_grilla.setSpacing(20)
        self._area_scroll.setWidget(self._contenedor_grilla)

        layout_principal.addWidget(self._area_scroll, stretch=1)

        layout_principal.addWidget(self._crear_paginador_alfabetico())
        layout_principal.addWidget(self._crear_boton_atras())


    def _crear_boton_atras(self):
        contenedor = QFrame()
        contenedor.setFixedHeight(64)   # misma altura que tenía la cabecera, para no mover el resto del layout

        layout = QHBoxLayout(contenedor)
        layout.setContentsMargins(24, 12, 24, 12)

        boton_atras = QPushButton("←  Atrás")
        boton_atras.setMinimumHeight(40)
        boton_atras.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        boton_atras.setStyleSheet(f"""
            QPushButton {{
                background: {COLOR_PRIMARIO};
                color: white;
                border: 1px solid #D9E2E4;
                border-radius: 0px;
                font-size: 13px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background: {COLOR_PRIMARIO_OSCURO};
            }}
        """)
        boton_atras.clicked.connect(self._volver_a_principal)

        layout.addWidget(boton_atras)  # sin stretch aparte: al ser el único widget, ya ocupa todo el ancho

        return contenedor
    # ------------------------------------------------------------------
    # Tarjetas de información (LOTE / FECHA / ESPECIE / PIEZA)
    # ------------------------------------------------------------------

    def _crear_tarjetas_info(self):
        contenedor = QWidget()
        contenedor.setStyleSheet("background: transparent;")
        layout = QHBoxLayout(contenedor)
        layout.setContentsMargins(24, 16, 24, 8)
        layout.setSpacing(16)

        layout.addWidget(
            self._crear_tarjeta("LOTE", self._obtener_valor_lote(), "box.png")
        )
        layout.addWidget(
            self._crear_tarjeta("FECHA DE PRODUCCIÓN", self.fecha_produccion, "calendar.png")
        )
        layout.addWidget(
            self._crear_tarjeta("ESPECIE", str(self.especie), "cow.png")
        )

        # Solo aparece en el flujo RES, cuando sí hay tipo de pieza.
        if self.tpo_pza is not None and self.nombre_tipo_pieza:
            layout.addWidget(
                self._crear_tarjeta("TIPO DE PIEZA", str(self.nombre_tipo_pieza), "box.png")
            )

        return contenedor

    def _obtener_valor_lote(self):
        """
        Devuelve el valor del lote como texto simple, sin importar si
        self.lotes llega como una lista de objetos (con atributo .lote),
        una lista de diccionarios (con clave "lote"), una lista de
        strings, o directamente un valor único.
        """
        valor = self.lotes

        if isinstance(valor, (list, tuple)):
            if not valor:
                return ""
            valor = valor[0]

        if hasattr(valor, "lote"):
            return str(valor.lote)
        if isinstance(valor, dict):
            return str(valor.get("lote", ""))
        return str(valor)

    @staticmethod
    def _crear_tarjeta(etiqueta, valor, nombre_icono):
        tarjeta = QFrame()
        tarjeta.setStyleSheet(
            f"background: white; border: 1px solid {COLOR_BORDE}; border-radius: 12px;"
        )
        _aplicar_sombra(tarjeta, blur=14, dy=2, alfa=18)

        layout = QHBoxLayout(tarjeta)
        layout.setContentsMargins(14, 10, 18, 10)
        layout.setSpacing(12)

        circulo_icono = QLabel()
        circulo_icono.setFixedSize(48, 48)
        circulo_icono.setAlignment(Qt.AlignCenter)
        circulo_icono.setStyleSheet(
            f"background: {COLOR_PRIMARIO_CLARO}; border-radius: 24px;"
        )
        icono = _icono_pixmap(nombre_icono, 26)
        if icono is not None:
            circulo_icono.setPixmap(icono)
            # Fondo del color primario para que el ícono blanco resalte.
            circulo_icono.setStyleSheet(
                f"background: {COLOR_PRIMARIO}; border-radius: 24px;"
            )

        bloque_texto = QVBoxLayout()
        bloque_texto.setSpacing(2)

        etq_titulo = QLabel(etiqueta)
        etq_titulo.setStyleSheet(
            f"color: {COLOR_TEXTO_SECUNDARIO}; font-size: 10px; letter-spacing: 1px; "
            "font-weight: 600;"
        )

        etq_valor = QLabel(valor)
        etq_valor.setStyleSheet(
            f"color: {COLOR_PRIMARIO}; font-size: 17px; font-weight: 700;"
        )

        bloque_texto.addWidget(etq_titulo)
        bloque_texto.addWidget(etq_valor)

        layout.addWidget(circulo_icono)
        layout.addLayout(bloque_texto)
        layout.addStretch(1)
        return tarjeta

    # ------------------------------------------------------------------
    # Filtro por PLU
    # ------------------------------------------------------------------
    def _crear_fila_filtros(self):
        contenedor = QWidget()
        layout = QHBoxLayout(contenedor)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        layout.addWidget(self._crear_filtro())

        return contenedor
    
    def _crear_filtro(self):
        contenedor = QFrame()
        contenedor.setStyleSheet(
            f"background: white; border: 1px solid {COLOR_BORDE}; border-radius: 12px;"
        )
        _aplicar_sombra(contenedor, blur=14, dy=2, alfa=18)

        layout = QHBoxLayout(contenedor)
        layout.setContentsMargins(10, 8, 16, 8)
        layout.setSpacing(12)

        circulo_buscar = QLabel()
        circulo_buscar.setFixedSize(36, 36)
        circulo_buscar.setAlignment(Qt.AlignCenter)
        circulo_buscar.setStyleSheet(
            f"background: {COLOR_PRIMARIO}; border-radius: 18px;"
        )
        icono_buscar = _icono_pixmap("search.png", 18)
        if icono_buscar is not None:
            circulo_buscar.setPixmap(icono_buscar)

        etiqueta = QLabel("Filtro por N° PLU")
        etiqueta.setStyleSheet(f"color: {COLOR_PRIMARIO}; font-weight: 700; font-size: 13px;")

        self.campo_filtro_plu = QLineEdit()
        self.campo_filtro_plu.setStyleSheet(
            f"""
            QLineEdit {{
                border: none;
                border-left: 1px solid {COLOR_BORDE};
                padding: 6px 12px;
                font-size: 13px;
            }}
            """
        )

        self._temporizador_filtro = QTimer(self)
        self._temporizador_filtro.setSingleShot(True)
        self._temporizador_filtro.setInterval(350)
        self._temporizador_filtro.timeout.connect(self._aplicar_filtro_plu)
        self.campo_filtro_plu.textChanged.connect(lambda _texto: self._temporizador_filtro.start())

        layout.addWidget(circulo_buscar)
        layout.addWidget(etiqueta)
        layout.addWidget(self.campo_filtro_plu, stretch=1)

        envoltorio = QWidget()
        envoltorio.setStyleSheet("background: transparent;")
        layout_envoltorio = QVBoxLayout(envoltorio)
        layout_envoltorio.setContentsMargins(24, 8, 24, 8)
        layout_envoltorio.addWidget(contenedor)
        return envoltorio

    # ------------------------------------------------------------------
    # Título de sección con el mismo adorno de la cabecera
    # ------------------------------------------------------------------
    def _crear_titulo_seccion(self):
        contenedor = QWidget()
        contenedor.setStyleSheet("background: transparent;")
        layout = QHBoxLayout(contenedor)
        layout.setContentsMargins(24, 16, 24, 8)
        layout.setSpacing(10)

        titulo = QLabel("SELECCIONE UN PRODUCTO")
        titulo.setStyleSheet(
            f"color: {COLOR_PRIMARIO}; font-size: 16px; font-weight: 700; letter-spacing: 1px;"
        )

        layout.addStretch(1)
        layout.addWidget(titulo)
        layout.addStretch(1)

        return contenedor

    # ------------------------------------------------------------------
    # Paginador alfabético
    # ------------------------------------------------------------------
    def _crear_paginador_alfabetico(self):
        contenedor = QWidget()
        contenedor.setStyleSheet("background: transparent;")
        self._layout_paginador = QHBoxLayout(contenedor)
        self._layout_paginador.setContentsMargins(24, 8, 24, 16)
        self._layout_paginador.setSpacing(6)

        self.boton_primero = QPushButton("«")
        self.boton_anterior = QPushButton("‹")
        self.boton_siguiente = QPushButton("›")
        self.boton_ultimo = QPushButton("»")

        for boton in (self.boton_primero, self.boton_anterior, self.boton_siguiente, self.boton_ultimo):
            boton.setFixedSize(34, 34)
            boton.setStyleSheet(self._estilo_boton_navegacion())

        self.boton_primero.clicked.connect(self._ir_al_inicio)
        self.boton_anterior.clicked.connect(self._desplazar_izquierda)
        self.boton_siguiente.clicked.connect(self._desplazar_derecha)
        self.boton_ultimo.clicked.connect(self._ir_al_final)

        self._layout_paginador.addWidget(self.boton_primero)
        self._layout_paginador.addWidget(self.boton_anterior)

        self._layout_letras = QHBoxLayout()
        self._layout_letras.setSpacing(6)
        self._layout_paginador.addLayout(self._layout_letras)
        self._layout_paginador.addStretch(1)

        self._layout_paginador.addWidget(self.boton_siguiente)
        self._layout_paginador.addWidget(self.boton_ultimo)

        return contenedor

    @staticmethod
    def _estilo_boton_navegacion():
        return f"""
            QPushButton {{
                border: 1px solid {COLOR_BORDE};
                border-radius: 8px;
                background: white;
                color: {COLOR_PRIMARIO};
                font-weight: 700;
            }}
            QPushButton:disabled {{
                color: #c7cfcf;
                border-color: #eef2f2;
            }}
            QPushButton:hover:!disabled {{
                background: {COLOR_PRIMARIO_CLARO};
            }}
        """

    # ------------------------------------------------------------------
    # Paginador alfabético — carga y navegación
    # ------------------------------------------------------------------
    def _cargar_paginador_alfabetico(self):
        if self.tpo_pza is not None:
            criterio = self._obtener_criterio_filtro()
            print("tpo_pza:", criterio.tpo_pza)
            print("cdgo_espcie:", criterio.cdgo_espcie)
            print("cdgo_plu:", criterio.cdgo_plu)
            print("cod_emprsa:", criterio.cod_emprsa)
            
            self._paginas_letras = self.repositorio.construir_paginas_letras(
                criterio.cod_emprsa,
                criterio.cdgo_espcie,
                criterio.tpo_pza,
            )
        else:
            self._paginas_letras = self.repositorio.construir_paginas_letras(
                self._criterio_filtro
            )
        self._indice_pagina_actual = 0
        self._indice_ventana = 0

        if self._paginas_letras:
            self._renderizar_botones_letras()
            self._cargar_productos_de_pagina_actual()
        else:
            self._mostrar_mensaje_vacio()
    """
    def _cargar_paginador_alfabetico(self):
        self._paginas_letras = self.repositorio.construir_paginas_letras(
            #self._criterio_filtro = 
            self._obtener_criterio_filtro()
        )
        self._indice_pagina_actual = 0
        self._indice_ventana = 0

        if self._paginas_letras:
            self._renderizar_botones_letras()
            self._cargar_productos_de_pagina_actual()
        else:
            self._mostrar_mensaje_vacio()
    """

    def _renderizar_botones_letras(self):
        while self._layout_letras.count():
            item = self._layout_letras.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        inicio = self._indice_ventana
        fin = min(inicio + BOTONES_LETRA_VISIBLES, len(self._paginas_letras))

        for indice in range(inicio, fin):
            pagina_letra = self._paginas_letras[indice]
            boton = QPushButton(pagina_letra.letra)
            boton.setFixedSize(34, 34)
            es_seleccionado = indice == self._indice_pagina_actual
            boton.setStyleSheet(self._estilo_boton_letra(es_seleccionado))
            boton.clicked.connect(lambda _=False, i=indice: self._ir_a_pagina(i))
            self._layout_letras.addWidget(boton)

        self.boton_primero.setEnabled(self._indice_ventana > 0)
        self.boton_anterior.setEnabled(self._indice_ventana > 0)
        self.boton_siguiente.setEnabled(fin < len(self._paginas_letras))
        self.boton_ultimo.setEnabled(fin < len(self._paginas_letras))

    @staticmethod
    def _estilo_boton_letra(seleccionado):
        if seleccionado:
            return f"""
                QPushButton {{
                    background: {COLOR_SELECCIONADO};
                    color: white;
                    border: none;
                    border-radius: 8px;
                    font-weight: 700;
                }}
            """
        return f"""
            QPushButton {{
                background: white;
                color: {COLOR_PRIMARIO};
                border: 1px solid {COLOR_BORDE};
                border-radius: 8px;
                font-weight: 700;
            }}
            QPushButton:hover {{
                background: {COLOR_PRIMARIO_CLARO};
            }}
        """

    def _ir_a_pagina(self, indice):
        self._indice_pagina_actual = indice
        if indice < self._indice_ventana:
            self._indice_ventana = indice
        elif indice >= self._indice_ventana + BOTONES_LETRA_VISIBLES:
            self._indice_ventana = indice - BOTONES_LETRA_VISIBLES + 1
        self._renderizar_botones_letras()
        self._cargar_productos_de_pagina_actual()

    def _desplazar_izquierda(self):
        self._indice_ventana = max(0, self._indice_ventana - 1)
        self._renderizar_botones_letras()

    def _desplazar_derecha(self):
        maximo = max(0, len(self._paginas_letras) - BOTONES_LETRA_VISIBLES)
        self._indice_ventana = min(maximo, self._indice_ventana + 1)
        self._renderizar_botones_letras()

    def _ir_al_inicio(self):
        self._indice_ventana = 0
        self._renderizar_botones_letras()

    def _ir_al_final(self):
        self._indice_ventana = max(0, len(self._paginas_letras) - BOTONES_LETRA_VISIBLES)
        self._renderizar_botones_letras()

    def _cargar_productos_de_pagina_actual(self):
        pagina = self._paginas_letras[self._indice_pagina_actual]
        #productos = self.repositorio.obtener_productos_por_letra(
        #    self._criterio_filtro, pagina.letra, pagina.offset, TAMANO_PAGINA
        #)
        criterio = self._obtener_criterio_filtro()  # o self._criterio_filtro si ya está guardado
        productos = self.repositorio.obtener_productos_por_letra(
            cod_emprsa=self.empresa,      # o de donde saques ese dato
            cdgo_espcie=self.numEspecie,    # idem
            tpo_pza=criterio.tpo_pza,   # si esto es lo que representa tpo_pza
            letra=pagina.letra,
            offset=pagina.offset,
            tamano_pagina=TAMANO_PAGINA,
        )
        self._mostrar_productos(productos)

    # ------------------------------------------------------------------
    # Filtro por PLU
    # ------------------------------------------------------------------
    def _aplicar_filtro_plu(self):
        texto = self.campo_filtro_plu.text().strip()
        if not texto:
            self._layout_paginador_visible(True)
            self._cargar_productos_de_pagina_actual()
            return

        self._layout_paginador_visible(False)
        criterio = self._obtener_criterio_filtro()
        productos = self.repositorio.buscar_productos_por_plu(
            tpo_pza=criterio.tpo_pza,
            cdgo_espcie=self.numEspecie,    # idem
            texto_plu=texto,
            cod_emprsa=self.empresa
        )
        self._mostrar_productos(productos)

    def _layout_paginador_visible(self, visible):
        for boton in (self.boton_primero, self.boton_anterior, self.boton_siguiente, self.boton_ultimo):
            boton.setVisible(visible)
        for i in range(self._layout_letras.count()):
            widget = self._layout_letras.itemAt(i).widget()
            if widget is not None:
                widget.setVisible(visible)

    # ------------------------------------------------------------------
    # Grilla de productos
    # ------------------------------------------------------------------
    def _mostrar_productos(self, productos):
        while self._layout_grilla.count():
            item = self._layout_grilla.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        if not productos:
            self._mostrar_mensaje_vacio()
            return

        for indice, producto in enumerate(productos):
            fila, columna = divmod(indice, COLUMNAS_GRILLA)
            tarjeta = ProductoWidget(producto)
            tarjeta.clicked.connect(self._abrir_ficha_tecnica)
            self._layout_grilla.addWidget(tarjeta, fila, columna)

    def _mostrar_mensaje_vacio(self):
        while self._layout_grilla.count():
            item = self._layout_grilla.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        mensaje = QLabel("No se encontraron productos.")
        mensaje.setAlignment(Qt.AlignCenter)
        mensaje.setStyleSheet(f"color: {COLOR_TEXTO_SECUNDARIO}; font-size: 14px; margin: 24px;")
        self._layout_grilla.addWidget(mensaje, 0, 0, 1, COLUMNAS_GRILLA)

    # ------------------------------------------------------------------
    # Navegación a otras pantallas
    # ------------------------------------------------------------------
    def _abrir_ficha_tecnica(self, producto):

        producto_dict = {
            "cdgo_plu": producto.cdgo_plu,
            "nombre": producto.nom_prog,
            "imagen": producto.imagen_principal,
        }
        self._app.mostrar_ficha(
            producto=producto_dict,
            fecha_produccion=self.fecha_produccion,
            especie=self.especie,
            numEspecie=self.numEspecie,
            lote=self._obtener_valor_lote(),
            tpo_pza=self.tpo_pza,
            nombre_tipo_pieza=self.nombre_tipo_pieza,
            peso_neto_kg=0.0,
            fecha_sacrificio = None,
            empresa=self.empresa,
            fecha_vencimiento_str = None,
            
        )
        
    def _obtener_criterio_filtro(self):
        if self.tpo_pza is not None:
            return CriterioFiltroRes(
                tpo_pza=self.tpo_pza,
                cdgo_espcie=self.numEspecie,
                cdgo_plu=getattr(self, "campo_filtro_plu", None)
                and self.campo_filtro_plu.text().strip()
                or None,
                cod_emprsa=self.empresa.strip() if self.empresa else None,

            )
        
        return self._criterio_filtro

    def _volver_a_principal(self):
        self._app.mostrar_principal()
        