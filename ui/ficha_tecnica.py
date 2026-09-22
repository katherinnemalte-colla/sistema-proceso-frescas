from PySide6.QtWidgets import (
    QWidget, QLabel, QPushButton, QFrame, QGridLayout,
    QVBoxLayout, QHBoxLayout, QDateEdit, QButtonGroup, QSizePolicy,
    QScrollArea
)
from datetime import timedelta, date
from typing import Optional
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from types import SimpleNamespace
from utils.ventana_utils import aplicar_tamano, escalar, escalar_fuente,establecer_factor_temporal, limpiar_factor_temporal, factor_para_contenido
from repositories.obtener_tipo_pza_repository import ObtenerTipoPzaRepository
from repositories.obtener_tipo_limpieza_repository import ObtenerTipoLimpiezaRepository
from utils import fechas
from repositories.etiquetas.frescas_100x45 import (
    construir_datos_etiqueta, imprimir_etiqueta_frescas,
    generar_vista_previa_pixmap, DatosEtiquetaFrescas,
    siguiente_consecutivo_etiqueta_canasta, CODIGO_PROCESO_DEFAULT
)
from services.bascula_service import bascula_service
import shiboken6
from PySide6.QtPrintSupport import QPrinterInfo
from PySide6.QtWidgets import QComboBox, QLineEdit
from services.hstrco_psje_service import registrar_historico_pesaje, guardar_historico_pesaje
from PySide6.QtGui import QIntValidator

ANCHO_CONTENIDO = 1150  # valor BASE, se escala con escalar() al usarlo
COLOR_PRIMARIO = "#1a6b6b"
COLOR_PRIMARIO_OSCURO = "#134f4f"


class FichaTecnica(QWidget):
    def __init__(
        self,
        usuario,
        producto: dict,
        fecha_produccion,
        especie: str,
        numEspecie,
        lote: str,
        obtener_conexion,
        app_ventana,
        *,
        tpo_pza=None,
        nombre_tipo_pieza=None,
        peso_neto_kg: Optional[float],
        fecha_sacrificio,
        nom_impr_etiq=None,
        empresa,
        fecha_vencimiento_str,
    ):
        super().__init__()
        
        self.usuario = usuario
        self._obtener_conexion = obtener_conexion
        self._app = app_ventana
        self.producto = producto
        self.fecha_produccion = fechas._asegurar_date(fecha_produccion)
        self.especie = especie
        self.numEspecie = int(numEspecie)
        self.lote = int(lote)
        self.tpo_pza = tpo_pza
        self.nombre_tipo_pieza = nombre_tipo_pieza

        self.seleccion_de_producto = None
        self.peso_neto_kg = bascula_service.obtener_peso_neto()
        self.fecha_sacrificio = fechas._asegurar_date(fecha_sacrificio)
        self.nom_impr_etiq = nom_impr_etiq
        self.empresa = empresa
        self.fecha_vencimiento_str = fechas._asegurar_date(fecha_vencimiento_str)

        self.producto_completo = None
        if self.tpo_pza is not None:
            repositorio_imagenes = ObtenerTipoPzaRepository(self._obtener_conexion)
            self.producto_completo = repositorio_imagenes.obtener_producto_completo(
                self.empresa,
                self.numEspecie,
                self.tpo_pza,
                str(self.producto.get("cdgo_plu", "")),
            )

        self.tipo_limpieza_seleccionado = None
        self._grupo_limpieza = None

        self.setWindowTitle(f"Ficha técnica - {producto.get('nombre', '')}")
        self.setStyleSheet("QWidget { background-color: #F5F8F8; }")
        # --- NUEVO: fuerza el factor de escala según el alto real de este contenido ---
        ALTO_CONTENIDO_BASE_FICHA = 1100  # ajusta este valor midiendo tu contenido a factor 1
        factor = factor_para_contenido(ALTO_CONTENIDO_BASE_FICHA, minimo=0.55, maximo=1.2)
        establecer_factor_temporal(factor)

        self._crear_interfaz()
        limpiar_factor_temporal()
        self.numero_ticket = siguiente_consecutivo_etiqueta_canasta()
        self._parametros_etiqueta_actuales = self._construir_parametros_etiqueta()
        self.actualizar_vista_previa(
            construir_datos_etiqueta(**self._parametros_etiqueta_actuales)
        )
        bascula_service.peso_actualizado.connect(self._on_peso_actualizado)

    # ==============================================================
    # CONEXIÓN A BD
    # ==============================================================

    def _obtener_conexion(self):
        from models.database import obtener_conexion
        return obtener_conexion()

    # ==============================================================
    # DATOS DE VENCIMIENTO
    # ==============================================================
    def _obtener_datos_vencimiento(self) -> tuple[Optional[int], Optional[int], Optional[date], Optional[date]]:
        codigo_producto = self.producto.get("cdgo_plu")
        codigo_empresa = self.empresa

        repo = ObtenerTipoLimpiezaRepository(self._obtener_conexion)
        dias_ref, dias_cong = repo.obtener_dias_vencimiento(codigo_producto, codigo_empresa)

        fecha_vencimiento_refrigeracion = (
            self.fecha_produccion + timedelta(days=int(dias_ref)) if dias_ref is not None else None
        )
        fecha_vencimiento_congelacion = (
            self.fecha_produccion + timedelta(days=int(dias_cong)) if dias_cong is not None else None
        )
        return dias_ref, dias_cong, fecha_vencimiento_refrigeracion, fecha_vencimiento_congelacion

    # ==============================================================
    # INTERFAZ
    # ==============================================================
    def _crear_interfaz(self):
        # ------------------------------------------------------------
        # Contenido real (todo lo que va dentro del scroll)
        # ------------------------------------------------------------
        layout = QVBoxLayout()
        layout.setContentsMargins(
            escalar(25), escalar(20), escalar(25), escalar(20)
        )
        layout.setSpacing(escalar(16))

        contenedor = QWidget()
        #contenedor.setMaximumWidth(escalar(ANCHO_CONTENIDO))
        contenedor.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        contenedor.setLayout(layout)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(contenedor)          # el contenedor va directo al scroll
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        layout_externo = QVBoxLayout(self)
        layout_externo.setContentsMargins(escalar(0), escalar(0), escalar(0), escalar(0))
        layout_externo.addWidget(scroll)

        # ----------------------------------------------------------
        # ENCABEZADO: Atrás
        # ----------------------------------------------------------
        encabezado = QHBoxLayout()

        boton_atras = QPushButton("←  Atrás")
        boton_atras.setMinimumHeight(escalar(40))
        boton_atras.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        boton_atras.setStyleSheet(
            f"""
            QPushButton {{
                background: {COLOR_PRIMARIO};
                color: white;
                font-size: {escalar_fuente(14)}px;
                font-weight: 700;
                border: none;
                letter-spacing: 1px;
            }}
            QPushButton:hover {{
                background: {COLOR_PRIMARIO_OSCURO};
            }}"""
        )
        boton_atras.clicked.connect(self._volver_a_seleccion_de_producto)
        encabezado.addWidget(boton_atras, stretch=1)

        layout.addLayout(encabezado)

        # ----------------------------------------------------------
        # FILA: imagen principal + información del producto
        # ----------------------------------------------------------
        fila_superior = QHBoxLayout()
        fila_superior.setSpacing(escalar(16))

        fila_superior.addWidget(self._crear_imagen_principal())
        fila_superior.addWidget(self._crear_info_producto())

        layout.addLayout(fila_superior)

        # ----------------------------------------------------------
        # IMÁGENES DEL PRODUCTO (galería numerada)
        # ----------------------------------------------------------
        layout.addWidget(self._crear_galeria_imagenes())

        # ----------------------------------------------------------
        # TIPO DE LIMPIEZA
        # ----------------------------------------------------------
        layout.addWidget(self._crear_seccion_tipo_limpieza())

        # ----------------------------------------------------------
        # FILA: báscula + datos adicionales
        # ----------------------------------------------------------
        fila_inferior = QHBoxLayout()
        fila_inferior.setSpacing(escalar(16))

        fila_inferior.addWidget(self._crear_bascula())
        fila_inferior.addWidget(self._crear_datos_adicionales())

        layout.addLayout(fila_inferior)

        # ----------------------------------------------------------
        # BOTONES: Ir a inicio + Guardar peso
        # ----------------------------------------------------------
        fila_botones = QHBoxLayout()
        fila_botones.setSpacing(escalar(12))

        boton_inicio = QPushButton("Ir a inicio")
        boton_inicio.setFixedHeight(escalar(50))
        boton_inicio.setStyleSheet(f"""
            QPushButton {{
                background-color: white;
                color: #115E67;
                border: 1px solid #D9E2E4;
                border-radius: 0px;
                font-size: {escalar_fuente(15)}px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #EAF4F5;
            }}
        """)
        boton_inicio.clicked.connect(self._volver_a_inicio)

        boton_guardar = QPushButton("Imprime")
        boton_guardar.setFixedHeight(escalar(50))
        boton_guardar.setStyleSheet(f"""
            QPushButton {{
                background-color: #115E67;
                color: white;
                border: none;
                border-radius: 0px;
                font-size: {escalar_fuente(15)}px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #0D4D55;
            }}
        """)

        boton_guardar.clicked.connect(self._guardar_peso)

        fila_botones.addWidget(boton_inicio)
        fila_botones.addWidget(boton_guardar)
        layout.addLayout(fila_botones)

    # ==============================================================
    # IMAGEN PRINCIPAL
    # ==============================================================
    def _crear_imagen_principal(self) -> QFrame:
        marco = QFrame()
        marco.setFixedSize(escalar(300), escalar(260))
        marco.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #D9E2E4;
                border-radius: 12px;
            }
        """)

        layout = QVBoxLayout(marco)
        layout.setContentsMargins(escalar(8), escalar(8), escalar(8), escalar(8))

        etiqueta_imagen = QLabel()
        etiqueta_imagen.setAlignment(Qt.AlignCenter)

        imagen_raw = self.producto.get("imagen")
        imagen_bytes = self._normalizar_imagen_bytes(imagen_raw)

        pixmap = QPixmap()
        if imagen_bytes and pixmap.loadFromData(imagen_bytes):
            pixmap = pixmap.scaled(
                escalar(280), escalar(240),
                Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            etiqueta_imagen.setPixmap(pixmap)
        else:
            etiqueta_imagen.setText("Sin imagen")
            etiqueta_imagen.setStyleSheet(f"color: #999; font-size: {escalar_fuente(13)}px;")

        layout.addWidget(etiqueta_imagen)
        return marco

    def _normalizar_imagen_bytes(self, valor):
        if not valor:
            return None
        if isinstance(valor, (bytes, bytearray)):
            return bytes(valor)
        if isinstance(valor, str):
            import base64
            try:
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
        resultado_sacrificio = ObtenerTipoLimpiezaRepository.obtener_fecha_sacrificio(
            self, self.lote, self.numEspecie
        )

        self.fecha_sacrificio = resultado_sacrificio.scrfcio if resultado_sacrificio else None
        self.nom_impr_etiq = resultado_sacrificio.nom_impr_etiq if resultado_sacrificio else None

        layout = QVBoxLayout(marco)
        layout.setContentsMargins(escalar(20), escalar(16), escalar(20), escalar(16))
        layout.setSpacing(escalar(10))

        titulo = QLabel("Información del producto")
        titulo.setStyleSheet(
            f"font-size: {escalar_fuente(15)}px; font-weight: bold; color: #115E67;"
        )
        layout.addWidget(titulo)

        dias_ref, dias_cong, fecha_vencimiento_refrigeracion, fecha_vencimiento_congelacion = (
            self._obtener_datos_vencimiento()
        )

        if dias_cong is not None:
            etiqueta_vencimiento = "F.Vto en Congelación:"
            self.fecha_vencimiento_str = fecha_vencimiento_congelacion
            fecha_vencimiento_str = (
                fecha_vencimiento_congelacion.strftime("%d/%m/%Y")
                if fecha_vencimiento_congelacion else "-"
            )
            dias_vencimiento = dias_cong
        else:
            etiqueta_vencimiento = "F.Vto en Refrigeración:"
            self.fecha_vencimiento_str = fecha_vencimiento_refrigeracion
            fecha_vencimiento_str = (
                fecha_vencimiento_refrigeracion.strftime("%d/%m/%Y")
                if fecha_vencimiento_refrigeracion else "-"
            )
            dias_vencimiento = dias_ref

        def formatear_fecha(fecha, formato="%d/%m/%Y", valor_defecto="N/A") -> str:
            if fecha is None:
                return valor_defecto
            return fecha.strftime(formato)

        datos = [
            [("PLU:", self.producto.get("cdgo_plu", "-")), ("Producto:", self.producto.get("nombre", "-"))],
            [("Especie:", self.especie), ("Empresa:", self.empresa)],
            [("Fecha Empacado:", self.fecha_produccion.strftime("%d/%m/%Y"))],
            [("Fecha Beneficio:", formatear_fecha(self.fecha_sacrificio))],
            [(etiqueta_vencimiento, fecha_vencimiento_str)],
            [("Días Vence:", dias_vencimiento if dias_vencimiento is not None else "-")],
        ]
        if self.tpo_pza is not None and self.nombre_tipo_pieza:
            datos.append([("Tipo de pieza:", self.nombre_tipo_pieza)])

        for grupo in datos:
            fila = QHBoxLayout()
            for etiqueta_texto, valor_texto in grupo:
                etiqueta = QLabel(etiqueta_texto)
                etiqueta.setMinimumWidth(escalar(90))
                etiqueta.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
                etiqueta.setStyleSheet(f"color: #666; font-size: {escalar_fuente(13)}px;")

                valor = QLabel(str(valor_texto))
                valor.setWordWrap(True)
                valor.setStyleSheet(
                    f"color: #222; font-size: {escalar_fuente(13)}px; font-weight: bold;"
                )

                fila.addWidget(etiqueta)
                fila.addWidget(valor, stretch=1)

            layout.addLayout(fila)
        layout.addStretch()
        return marco

    # ==============================================================
    # GALERÍA DE IMÁGENES
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
        layout_externo.setContentsMargins(escalar(16), escalar(12), escalar(16), escalar(16))
        layout_externo.setSpacing(escalar(10))

        titulo = QLabel("Imágenes del producto")
        titulo.setStyleSheet(
            f"font-size: {escalar_fuente(14)}px; font-weight: bold; color: #115E67;"
        )
        layout_externo.addWidget(titulo)

        fila_miniaturas = QHBoxLayout()
        fila_miniaturas.setSpacing(escalar(12))

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
        contenedor.setFixedSize(escalar(90), escalar(90))
        contenedor.setStyleSheet("""
            QFrame {
                background-color: #F5F8F8;
                border: 1px solid #D9E2E4;
                border-radius: 10px;
            }
        """)

        layout = QVBoxLayout(contenedor)
        layout.setContentsMargins(escalar(4), escalar(4), escalar(4), escalar(4))

        etiqueta = QLabel()
        etiqueta.setAlignment(Qt.AlignCenter)

        datos = self._normalizar_imagen_bytes(imagen_bytes)

        if datos:
            pixmap = QPixmap()
            if pixmap.loadFromData(datos):
                pixmap = pixmap.scaled(
                    escalar(80), escalar(80),
                    Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
                etiqueta.setPixmap(pixmap)
            else:
                etiqueta.setText(str(numero))
                etiqueta.setStyleSheet(
                    f"color: #999; font-size: {escalar_fuente(20)}px; font-weight: bold;"
                )
        else:
            etiqueta.setText(str(numero))
            etiqueta.setStyleSheet(
                f"color: #999; font-size: {escalar_fuente(20)}px; font-weight: bold;"
            )

        layout.addWidget(etiqueta)
        return contenedor

    # ==============================================================
    # TIPO DE LIMPIEZA
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
        layout.setContentsMargins(escalar(16), escalar(12), escalar(16), escalar(16))
        layout.setSpacing(escalar(10))

        titulo = QLabel("Nivel de Limpieza")
        titulo.setStyleSheet(
            f"font-size: {escalar_fuente(14)}px; font-weight: bold; color: #115E67;"
        )
        layout.addWidget(titulo)

        self._contenedor_botones_limpieza = QHBoxLayout()
        self._contenedor_botones_limpieza.setSpacing(escalar(10))
        layout.addLayout(self._contenedor_botones_limpieza)

        fila_paginacion = QHBoxLayout()
        fila_paginacion.setSpacing(escalar(6))

        self._btn_primera = QPushButton("<<")
        self._btn_anterior = QPushButton("<")
        self._lbl_pagina = QLabel("")
        self._btn_siguiente = QPushButton(">")
        self._btn_ultima = QPushButton(">>")

        for boton in (self._btn_primera, self._btn_anterior, self._btn_siguiente, self._btn_ultima):
            boton.setCursor(Qt.PointingHandCursor)
            boton.setFixedWidth(escalar(36))
            boton.setStyleSheet(f"""
                QPushButton {{
                    background-color: white;
                    color: #115E67;
                    border: 1px solid #D9E2E4;
                    border-radius: {escalar(6)}px;
                    font-weight: 600;
                    font-size: {escalar_fuente(13)}px;
                }}
                QPushButton:hover {{ background-color: #EAF4F5; }}
                QPushButton:disabled {{ color: #BBB; border-color: #EEE; }}
            """)

        self._lbl_pagina.setAlignment(Qt.AlignCenter)
        self._lbl_pagina.setStyleSheet(f"color: #115E67; font-size: {escalar_fuente(12)}px;")

        self._btn_primera.clicked.connect(lambda: self._ir_a_pagina(0))
        self._btn_anterior.clicked.connect(lambda: self._ir_a_pagina(self._pagina_actual_limpieza - 1))
        self._btn_siguiente.clicked.connect(lambda: self._ir_a_pagina(self._pagina_actual_limpieza + 1))
        self._btn_ultima.clicked.connect(lambda: self._ir_a_pagina(self._total_paginas_limpieza - 1))

        fila_paginacion.addStretch()
        fila_paginacion.addWidget(self._btn_primera)
        fila_paginacion.addWidget(self._btn_anterior)
        fila_paginacion.addWidget(self._lbl_pagina)
        fila_paginacion.addWidget(self._btn_siguiente)
        fila_paginacion.addWidget(self._btn_ultima)
        fila_paginacion.addStretch()
        layout.addLayout(fila_paginacion)

        try:
            repositorio_limpieza = ObtenerTipoLimpiezaRepository(self._obtener_conexion)
            self._tipos_limpieza = repositorio_limpieza.obtener_tipos_limpieza()
        except Exception as e:
            print("No fue posible cargar tipos de limpieza:", e)
            self._tipos_limpieza = []

        self._grupo_limpieza = QButtonGroup(self)
        self._grupo_limpieza.setExclusive(True)
        self._grupo_limpieza.buttonClicked.connect(self._tipo_limpieza_elegido)

        self._tamano_pagina_limpieza = 8
        self._pagina_actual_limpieza = 0
        self._total_paginas_limpieza = max(
            1, -(-len(self._tipos_limpieza) // self._tamano_pagina_limpieza)
        )

        self._ir_a_pagina(0)

        return marco

    def _ir_a_pagina(self, numero_pagina: int):
        numero_pagina = max(0, min(numero_pagina, self._total_paginas_limpieza - 1))
        self._pagina_actual_limpieza = numero_pagina

        for boton in list(self._grupo_limpieza.buttons()):
            self._grupo_limpieza.removeButton(boton)
            self._contenedor_botones_limpieza.removeWidget(boton)
            boton.deleteLater()

        inicio = numero_pagina * self._tamano_pagina_limpieza
        fin = inicio + self._tamano_pagina_limpieza
        tipos_pagina = self._tipos_limpieza[inicio:fin]

        if not tipos_pagina:
            etiqueta_vacio = QLabel("No hay tipos de limpieza configurados.")
            etiqueta_vacio.setStyleSheet(f"color: #999; font-size: {escalar_fuente(13)}px;")
            self._contenedor_botones_limpieza.addWidget(etiqueta_vacio)
        else:
            for tipo in tipos_pagina:
                boton = QPushButton(f"{tipo.tpo_lmpza}")
                boton.setCheckable(True)
                boton.setCursor(Qt.PointingHandCursor)
                boton.setMinimumHeight(escalar(42))
                boton.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
                boton.setProperty("tpo_lmpza", tipo.tpo_lmpza)
                boton.setProperty("nombre_limpieza", tipo.nmbre)
                boton.setStyleSheet(f"""
                    QPushButton {{
                        background-color: white;
                        color: #115E67;
                        border: 1px solid #D9E2E4;
                        border-radius: {escalar(10)}px;
                        font-size: {escalar_fuente(13)}px;
                        font-weight: 600;
                    }}
                    QPushButton:hover {{ background-color: #EAF4F5; }}
                    QPushButton:checked {{
                        background-color: #115E67;
                        color: white;
                        border: 1px solid #115E67;
                    }}
                """)
                self._grupo_limpieza.addButton(boton)
                self._contenedor_botones_limpieza.addWidget(boton)

        self._lbl_pagina.setText(f"{self._pagina_actual_limpieza + 1} / {self._total_paginas_limpieza}")
        self._btn_primera.setEnabled(self._pagina_actual_limpieza > 0)
        self._btn_anterior.setEnabled(self._pagina_actual_limpieza > 0)
        self._btn_siguiente.setEnabled(self._pagina_actual_limpieza < self._total_paginas_limpieza - 1)
        self._btn_ultima.setEnabled(self._pagina_actual_limpieza < self._total_paginas_limpieza - 1)

    def _tipo_limpieza_elegido(self, boton):
        self.tipo_limpieza_seleccionado = boton.property("tpo_lmpza")

    # ==============================================================
    # BÁSCULA - PESO
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
        layout.setContentsMargins(escalar(20), escalar(16), escalar(20), escalar(16))
        layout.setSpacing(escalar(8))

        titulo = QLabel("Báscula - Peso")
        titulo.setStyleSheet(
            f"font-size: {escalar_fuente(15)}px; font-weight: bold; color: #115E67;"
        )
        layout.addWidget(titulo)

        self.etiqueta_peso = QLabel(f"{self.peso_neto_kg:.3f}")
        self.etiqueta_peso.setAlignment(Qt.AlignCenter)
        self.etiqueta_peso.setStyleSheet(f"""
            background-color: #E8F0EF;
            color: #115E67;
            font-size: {escalar_fuente(40)}px;
            font-weight: bold;
            font-family: 'Courier New';
            border-radius: {escalar(8)}px;
            padding: {escalar(10)}px;
        """)
        layout.addWidget(self.etiqueta_peso)

        self.etiqueta_peso_neto = QLabel(f"Peso neto        {self.peso_neto_kg:.3f} kg")
        self.etiqueta_peso_neto.setStyleSheet(f"color: #444; font-size: {escalar_fuente(13)}px;")
        layout.addWidget(self.etiqueta_peso_neto)

        etiqueta_impresora = QLabel("Impresora:")
        etiqueta_impresora.setStyleSheet(
            f"color: #666; font-size: {escalar_fuente(13)}px; margin-top: {escalar(6)}px;"
        )
        layout.addWidget(etiqueta_impresora)

        self.combo_impresora = QComboBox()
        self.combo_impresora.setStyleSheet(f"""
            QComboBox {{
                background-color: white;
                border: 1px solid #D9E2E4;
                border-radius: {escalar(6)}px;
                padding: {escalar(6)}px;
                font-size: {escalar_fuente(13)}px;
                color: #222;
            }}
        """)

        nombres_impresoras = [impresora.printerName() for impresora in QPrinterInfo.availablePrinters()]
        self.combo_impresora.addItems(nombres_impresoras)

        impresora_por_defecto = QPrinterInfo.defaultPrinter().printerName()
        if "Godex ZX420i GZPL" in nombres_impresoras:
            self.combo_impresora.setCurrentText("Godex ZX420i GZPL")
        elif impresora_por_defecto in nombres_impresoras:
            self.combo_impresora.setCurrentText(impresora_por_defecto)

        self.impresora_seleccionada = self.combo_impresora.currentText()
        self.combo_impresora.currentTextChanged.connect(self._on_impresora_cambiada)

        layout.addWidget(self.combo_impresora)

        layout.addStretch()
        return marco

    def _on_impresora_cambiada(self, nombre_impresora: str) -> None:
        self.impresora_seleccionada = nombre_impresora

    # ==============================================================
    # DATOS ADICIONALES
    # ==============================================================
    def _crear_datos_adicionales(self) -> QFrame:
        marco = QFrame()
        marco.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #D9E2E4;
                border-radius: 10px;
            }
        """)

        layout = QVBoxLayout(marco)
        layout.setContentsMargins(escalar(20), escalar(16), escalar(20), escalar(16))
        layout.setSpacing(escalar(10))

        self.lbl_vista_previa_etiqueta = QLabel()
        self.lbl_vista_previa_etiqueta.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_vista_previa_etiqueta.setMinimumHeight(escalar(150))
        layout.addWidget(self.lbl_vista_previa_etiqueta)

        layout.addStretch()
        return marco

    def actualizar_vista_previa(self, datos: DatosEtiquetaFrescas) -> None:
        if not shiboken6.isValid(self):
            return

        pixmap = generar_vista_previa_pixmap(datos)

        ancho_max_preview = escalar(575)
        alto_max_preview = escalar(150)

        pixmap_escalado = pixmap.scaled(
            ancho_max_preview,
            alto_max_preview,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

        self.lbl_vista_previa_etiqueta.setPixmap(pixmap_escalado)

    def _construir_parametros_etiqueta(self) -> dict:
        producto_para_etiqueta = self.producto_completo or SimpleNamespace(
            cdgo_plu=self.producto.get("cdgo_plu"),
            nom_prog=self.producto.get("nom_prog", self.producto.get("nombre", "")),
        )

        return dict(
            producto=producto_para_etiqueta,
            lote=self.lote,
            fecha_produccion=self.fecha_produccion,
            nombre_usuario=self.usuario.nombre_usuario,
            cod_empresa=self.empresa,
            tipo_limpieza_seleccionado=self.tipo_limpieza_seleccionado,
            peso_bascula=self.peso_neto_kg,
            fecha_sacrificio=self.fecha_sacrificio,
            nom_impr_etiq=self.nom_impr_etiq,
            numEspecie=self.numEspecie,
            fecha_vencimiento_str=self.fecha_vencimiento_str,
            numero_ticket=self.numero_ticket,
        )

    def _guardar_peso(self):
        self._parametros_etiqueta_actuales = self._construir_parametros_etiqueta()
        datos = construir_datos_etiqueta(**self._parametros_etiqueta_actuales)
        imprimir_etiqueta_frescas(datos, self.impresora_seleccionada)
        registrar_historico_pesaje(
            self._parametros_etiqueta_actuales,
            oprdor=self.usuario.nombre_usuario + "-" + CODIGO_PROCESO_DEFAULT,
            nmro_psta=self.numero_ticket,
        )

    def _limpiar_y_volver(self):
        bascula_service.peso_actualizado.disconnect(self._on_peso_actualizado)
        bascula_service.detener()
        self._app.mostrar_seleccion_sin_recargar()

    def closeEvent(self, event):
        self._limpiar_y_volver()
        super().closeEvent(event)

    def _volver_a_seleccion_de_producto(self):
        bascula_service.peso_actualizado.disconnect(self._on_peso_actualizado)
        self._limpiar_y_volver()
        bascula_service.detener()
        self._app.mostrar_seleccion_sin_recargar()

    def _on_peso_actualizado(self, nuevo_peso: float) -> None:
        self.peso_neto_kg = nuevo_peso

        self.etiqueta_peso.setText(f"{nuevo_peso:.3f}")
        self.etiqueta_peso_neto.setText(f"Peso neto        {nuevo_peso:.3f} kg ")

        if not getattr(self, "_parametros_etiqueta_actuales", None):
            return

        datos = construir_datos_etiqueta(**self._parametros_etiqueta_actuales)
        self.actualizar_vista_previa(datos)

    def _volver_a_inicio(self):
        bascula_service.peso_actualizado.disconnect(self._on_peso_actualizado)
        bascula_service.detener()
        self._app.mostrar_principal()