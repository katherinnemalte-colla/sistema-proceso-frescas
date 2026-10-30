from PySide6.QtWidgets import (
    QWidget, QLabel, QPushButton, QFrame,
    QVBoxLayout, QHBoxLayout, QButtonGroup, QSizePolicy,
    QScrollArea,QCheckBox,QComboBox,QDialog, QMessageBox, QPushButton,QGridLayout
)
from datetime import timedelta, date
from typing import Optional
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QPixmap
from types import SimpleNamespace
from utils.ventana_utils import escalar, escalar_fuente,establecer_factor_temporal, limpiar_factor_temporal, factor_para_contenido
from repositories.obtener_tipo_pza_repository import ObtenerTipoPzaRepository
from repositories.obtener_tipo_limpieza_repository import ObtenerTipoLimpiezaRepository
from utils import fechas
from repositories.etiquetas.frescas_100x45 import (
    construir_datos_etiqueta, imprimir_etiqueta_frescas,
    generar_vista_previa_pixmap, DatosEtiquetaFrescas,
    CODIGO_PROCESO_DEFAULT, siguiente_consecutivo_etiqueta_canasta,
)
from services.bascula_service import bascula_service
import shiboken6
import logging
from PySide6.QtPrintSupport import QPrinterInfo
from services.hstrco_psje_service import registrar_historico_pesaje
from repositories.hstrco_psje_repository import  guardar_historico_pesaje,obtener_ultimos_pesajes_recientes, obtener_ultimos_historicos_pesaje, marcar_historico_reimpreso
from ui.dialogo_ajuste_etiqueta import DialogoAjusteEtiqueta
from repositories.obtener_tipo_limpieza_repository import normalizar_empresa

ANCHO_CONTENIDO = 1150  # valor BASE, se escala con escalar() al usarlo
COLOR_PRIMARIO = "#1a6b6b"
COLOR_PRIMARIO_OSCURO = "#134f4f"
logger = logging.getLogger(__name__)
def _linea_horizontal() -> QFrame:
    linea = QFrame()
    linea.setFixedHeight(1)
    linea.setStyleSheet("background-color: #E3EAEB; border: none;")
    return linea


def _linea_vertical() -> QFrame:
    linea = QFrame()
    linea.setFixedWidth(1)
    linea.setStyleSheet("background-color: #E3EAEB; border: none;")
    return linea

class FichaTecnica(QWidget):
    mensaje_temporal = Signal(str, str)   # (texto, tipo: "error" | "info")
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
        tipo_conservacion=None,        # NUEVO
        nmro_psta,
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
        self.empresa = normalizar_empresa(empresa)
        self.fecha_vencimiento_str = fechas._asegurar_date(fecha_vencimiento_str)
        self._tipo_conservacion_forzado = tipo_conservacion   # NUEVO: lo que mandó la pantalla
        self.tipo_conservacion = tipo_conservacion or "refrigerado"   # NUEVO: valor inicial, antes de _crear_interfaz()
        self.nmro_psta = nmro_psta
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
        try:
            self._crear_interfaz()
        finally:
            limpiar_factor_temporal()
        establecer_factor_temporal(factor)

        #self._crear_interfaz()
        #limpiar_factor_temporal()
        self._timer_mensaje = QTimer(self)
        self._timer_mensaje.setSingleShot(True)
        self._timer_mensaje.timeout.connect(self._ocultar_mensaje)
        self.mensaje_temporal.connect(self._mostrar_mensaje)
        self.numero_ticket = self.nmro_psta  
        self._parametros_etiqueta_actuales = self._construir_parametros_etiqueta()
    
        bascula_service.peso_actualizado.connect(self._on_peso_actualizado)
        self._cargar_historicos_pesaje()
    # ==============================================================
    # CONEXIÓN A BD
    # ==============================================================

    def _obtener_conexion(self):
        from models.database import obtener_conexion
        return obtener_conexion()

    # ==============================================================
    # DATOS DE VENCIMIENTO
    # ==============================================================
    def _mostrar_mensaje(self, texto: str, tipo: str = "error"):
        self.lbl_mensaje.setStyleSheet(self._estilos_mensaje.get(tipo, self._estilos_mensaje["error"]))
        self.lbl_mensaje.setText(texto)
        self._timer_mensaje.start(3000)   # si llega otro mensaje, reinicia los 3 s

    def _ocultar_mensaje(self):
        self.lbl_mensaje.setText("")
        self.lbl_mensaje.setStyleSheet("")
    def _obtener_datos_vencimiento(self) -> tuple[Optional[int], Optional[int], Optional[date], Optional[date]]:
        codigo_producto = self.producto.get("cdgo_plu")
        codigo_empresa = self.empresa

        repo = ObtenerTipoLimpiezaRepository(self._obtener_conexion)
        dias_ref, dias_cong = repo.obtener_dias_vencimiento(codigo_producto, codigo_empresa)
        hoy = date.today()
        
        def calcular(dias) -> Optional[date]:
            # Solo es válido si hay días (> 0) y la fecha resultante es posterior a hoy
            if dias is None or int(dias) <= 0:
                return None
            fecha = self.fecha_produccion + timedelta(days=int(dias))
            return fecha if fecha > hoy else None

        fecha_vencimiento_refrigeracion = calcular(dias_ref)
        fecha_vencimiento_congelacion = calcular(dias_cong)
        
        return dias_ref, dias_cong, fecha_vencimiento_refrigeracion, fecha_vencimiento_congelacion
    
    def _crear_etiqueta(self, texto, color="#222", tamano=16, negrita=False) -> QLabel:
        etiqueta = QLabel(texto)
        etiqueta.setStyleSheet(
            f"color: {color}; font-size: {escalar_fuente(tamano)}px; "
            f"font-weight: {'700' if negrita else '400'}; "
            f"background: transparent; border: none;"
        )
        return etiqueta
    # ==============================================================
    # INTERFAZ
    # ==============================================================
    def _crear_interfaz(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(escalar(12), escalar(12), escalar(12), escalar(12))
        layout.setSpacing(escalar(10))

        contenedor = QWidget()
        contenedor.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        contenedor.setLayout(layout)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(contenedor)
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
        # FILA SUPERIOR: imagen grande | (información + galería)
        # ----------------------------------------------------------
        fila_superior = QHBoxLayout()
        fila_superior.setSpacing(escalar(12))

        fila_superior.addWidget(self._crear_imagen_principal(), 36)

        columna_derecha = QVBoxLayout()
        columna_derecha.setSpacing(escalar(10))
        columna_derecha.addWidget(self._crear_info_producto())
        columna_derecha.addWidget(self._crear_galeria_imagenes())
        fila_superior.addLayout(columna_derecha, 64)

        layout.addLayout(fila_superior)

        # ----------------------------------------------------------
        # FILA MEDIA: (limpieza + báscula) | (vista previa + consecutiva)
        # ----------------------------------------------------------
        fila_media = QHBoxLayout()
        fila_media.setSpacing(escalar(16))

        columna_izquierda = QVBoxLayout()
        columna_izquierda.setSpacing(escalar(10))
        self._seccion_limpieza = self._crear_seccion_tipo_limpieza()
        columna_izquierda.addWidget(self._seccion_limpieza)
        columna_izquierda.addWidget(self._crear_bascula(), 1)

        fila_media.addLayout(columna_izquierda, 1)
        fila_media.addWidget(self._crear_datos_adicionales(), 1)
        layout.addLayout(fila_media, 1)

        # Los estilos se construyen aquí porque el factor de escala temporal está activo
        base = (f"font-size: {escalar_fuente(13)}px; font-weight: bold; "
                f"border-radius: {escalar(6)}px; padding: {escalar(6)}px;")
        self._estilos_mensaje = {
            "error": f"background-color: #FDECEA; color: #B00020; {base}",
            "info":  f"background-color: #E8F5E9; color: #1B5E20; {base}",
        }

        self.lbl_mensaje = QLabel("")
        self.lbl_mensaje.setAlignment(Qt.AlignCenter)
        self.lbl_mensaje.setMinimumHeight(escalar(36))  # reserva espacio: los botones no "saltan"
        layout.addWidget(self.lbl_mensaje)

        # ----------------------------------------------------------
        # BOTONES: Ir a inicio | Imprime
        # ----------------------------------------------------------
        fila_botones = QHBoxLayout()
        fila_botones.setSpacing(escalar(16))

        boton_inicio = QPushButton("Ir a inicio")
        boton_inicio.setFixedHeight(escalar(56))
        boton_inicio.setCursor(Qt.PointingHandCursor)
        boton_inicio.setStyleSheet(f"""
            QPushButton {{
                background-color: white;
                color: #115E67;
                border: 1px solid #D9E2E4;
                border-radius: {escalar(4)}px;
                font-size: {escalar_fuente(16)}px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #EAF4F5;
            }}
        """)
        boton_inicio.clicked.connect(self._volver_a_inicio)

        self.boton_guardar = QPushButton("Imprime")
        self.boton_guardar.setFixedHeight(escalar(56))
        self.boton_guardar.setCursor(Qt.PointingHandCursor)
        self.boton_guardar.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLOR_PRIMARIO};
                color: white;
                border: none;
                border-radius: {escalar(4)}px;
                font-size: {escalar_fuente(16)}px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {COLOR_PRIMARIO_OSCURO};
            }}
        """)
        self.boton_guardar.clicked.connect(self._accion_boton_principal)

        fila_botones.addWidget(boton_inicio, 1)
        fila_botones.addWidget(self.boton_guardar, 1)
        layout.addLayout(fila_botones)
    # ==============================================================
    # IMAGEN PRINCIPAL
    # ==============================================================
    def _crear_imagen_principal(self) -> QFrame:
        marco = QFrame()
        marco.setObjectName("tarjeta")
        marco.setMinimumSize(escalar(420), escalar(330))
        marco.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        marco.setStyleSheet(f"""
            QFrame#tarjeta {{
                background-color: white;
                border: 1px solid #D9E2E4;
                border-radius: {escalar(4)}px;
            }}
        """)

        layout = QVBoxLayout(marco)
        layout.setContentsMargins(escalar(8), escalar(8), escalar(8), escalar(8))

        etiqueta_imagen = QLabel()
        etiqueta_imagen.setAlignment(Qt.AlignCenter)
        etiqueta_imagen.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)

        imagen_raw = self.producto.get("imagen")
        imagen_bytes = self._normalizar_imagen_bytes(imagen_raw)

        pixmap = QPixmap()
        if imagen_bytes and pixmap.loadFromData(imagen_bytes):
            pixmap = pixmap.scaled(
                escalar(580), escalar(330),
                Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            etiqueta_imagen.setPixmap(pixmap)
            etiqueta_imagen.setStyleSheet("background: transparent; border: none;")
        else:
            etiqueta_imagen.setText("Sin imagen")
            etiqueta_imagen.setStyleSheet(
                f"color: #999; font-size: {escalar_fuente(33)}px; background: transparent; border: none;"
            )

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
        marco.setObjectName("tarjeta")
        marco.setStyleSheet(f"""
            QFrame#tarjeta {{
                background-color: white;
                border: 1px solid #D9E2E4;
                border-radius: {escalar(4)}px;
            }}
        """)
        resultado_sacrificio = ObtenerTipoLimpiezaRepository.obtener_fecha_sacrificio(
            self, self.lote, self.numEspecie
        )

        self.fecha_sacrificio = resultado_sacrificio.scrfcio if resultado_sacrificio else None
        self.nom_impr_etiq = resultado_sacrificio.nom_impr_etiq if resultado_sacrificio else None

        layout = QVBoxLayout(marco)
        layout.setContentsMargins(escalar(8), escalar(8), escalar(8), escalar(8))
        layout.setSpacing(escalar(6))

        # Título dentro de una banda clara
        titulo = QLabel(f"INFORMACION DE {self.producto.get("nombre", "-")}")
        titulo.setStyleSheet(
            f"font-size: {escalar_fuente(16)}px; font-weight: bold; color: #115E67; "
            f"background-color: #E8F0EF; border: none; "
            f"border-radius: {escalar(4)}px; padding: {escalar(6)}px {escalar(10)}px;"
        )
        layout.addWidget(titulo)

        dias_ref, dias_cong, fecha_vencimiento_refrigeracion, fecha_vencimiento_congelacion = (
            self._obtener_datos_vencimiento()
        )

        forzado = self._tipo_conservacion_forzado

        if forzado == "congelado" or (forzado is None and fecha_vencimiento_congelacion is not None):
            self.tipo_conservacion = "congelado"
            etiqueta_vencimiento = "F.Vto en Congelación:"
            self.fecha_vencimiento_str = fecha_vencimiento_congelacion
            fecha_vencimiento_str = (
                fecha_vencimiento_congelacion.strftime("%d/%m/%Y")
                if fecha_vencimiento_congelacion else "-"
            )
            dias_vencimiento = dias_cong
        else:
            self.tipo_conservacion = "refrigerado"
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
            [("PLU:", self.producto.get("cdgo_plu", "-")), ("Fecha Empacado:", self.fecha_produccion.strftime("%d/%m/%Y"))],
            [("Especie:", self.especie), ("Fecha Beneficio:", formatear_fecha(self.fecha_sacrificio))],
            [("Empresa:", self.empresa), (etiqueta_vencimiento, fecha_vencimiento_str), ("Días Vence:", dias_vencimiento if dias_vencimiento is not None else "-")],
        ]
        if self.tpo_pza is not None and self.nombre_tipo_pieza:
            datos.append([("Tipo de pieza:", self.nombre_tipo_pieza)])

        # --- Distribución visual: columna izq | columna der, y fila inferior ---
        def crear_celda(etiqueta_texto, valor_texto, ancho_etiqueta=150) -> QFrame:
            celda = QFrame()
            celda.setObjectName("celda")
            celda.setStyleSheet(
                "QFrame#celda { background: transparent; border: none; "
                "border-bottom: 1px solid #E3EAEB; }"
            )
            fila = QHBoxLayout(celda)
            fila.setContentsMargins(escalar(8), escalar(6), escalar(8), escalar(6))
            etiqueta = self._crear_etiqueta(etiqueta_texto, "#4F7F84", 15)
            etiqueta.setMinimumWidth(escalar(ancho_etiqueta))
            valor = self._crear_etiqueta(str(valor_texto), "#115E67", 17, True)
            valor.setWordWrap(True)
            fila.addWidget(etiqueta)
            fila.addWidget(valor, stretch=1)
            return celda

        celdas_izq, celdas_der, celdas_inf = [], [], []
        for grupo in datos:
            if len(grupo) >= 3:
                celdas_izq.append(grupo[0])
                celdas_inf.extend(grupo[1:])
            elif len(grupo) == 2:
                celdas_izq.append(grupo[0])
                celdas_der.append(grupo[1])
            else:
                celdas_izq.append(grupo[0])

        cuerpo = QHBoxLayout()
        cuerpo.setSpacing(escalar(10))

        columna_izq = QVBoxLayout()
        columna_izq.setSpacing(0)
        for etiqueta_texto, valor_texto in celdas_izq:
            columna_izq.addWidget(crear_celda(etiqueta_texto, valor_texto))
        columna_izq.addStretch()

        columna_der = QVBoxLayout()
        columna_der.setSpacing(0)
        for etiqueta_texto, valor_texto in celdas_der:
            columna_der.addWidget(crear_celda(etiqueta_texto, valor_texto, 170))
        columna_der.addStretch()

        cuerpo.addLayout(columna_izq, 1)
        cuerpo.addWidget(_linea_vertical())
        cuerpo.addLayout(columna_der, 1)
        layout.addLayout(cuerpo)

        if celdas_inf:
            fila_inferior = QHBoxLayout()
            fila_inferior.setSpacing(escalar(10))
            for i, (etiqueta_texto, valor_texto) in enumerate(celdas_inf):
                if i > 0:
                    fila_inferior.addWidget(_linea_vertical())
                fila_inferior.addWidget(
                    crear_celda(etiqueta_texto, valor_texto, 200 if i == 0 else 110),
                    3 if i == 0 else 2,
                )
            layout.addLayout(fila_inferior)

        return marco

    def _crear_galeria_imagenes(self) -> QFrame:
           marco = QFrame()
           marco.setObjectName("tarjeta")
           marco.setStyleSheet(f"""
               QFrame#tarjeta {{
                   background-color: white;
                   border: 1px solid #D9E2E4;
                   border-radius: {escalar(4)}px;
               }}
           """)
   
           layout_externo = QVBoxLayout(marco)
           layout_externo.setContentsMargins(escalar(16), escalar(10), escalar(16), escalar(12))
           layout_externo.setSpacing(escalar(8))
   
           fila_miniaturas = QHBoxLayout()
           fila_miniaturas.setSpacing(escalar(10))
   
           if self.producto_completo is not None:
               imagenes_extra = [
                   self.producto_completo.con_arch_3,
                   self.producto_completo.con_arch_4,
                   self.producto_completo.con_arch_5,
                   self.producto_completo.con_arch_6,
               ]
           else:
               imagenes_extra = [None, None, None, None, None]
   
           for numero, imagen_bytes in enumerate(imagenes_extra, start=2):
               fila_miniaturas.addWidget(self._crear_miniatura(numero, imagen_bytes))
   
           #fila_miniaturas.addStretch()
           layout_externo.addLayout(fila_miniaturas)
   
           return marco
   
    def _crear_miniatura(self, numero: int, imagen_bytes) -> QFrame:
        contenedor = QFrame()
        contenedor.setObjectName("miniatura")
        contenedor.setFixedHeight(escalar(115))
        contenedor.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        layout = QVBoxLayout(contenedor)
        layout.setContentsMargins(escalar(4), escalar(4), escalar(4), escalar(4))

        etiqueta = QLabel()
        etiqueta.setAlignment(Qt.AlignCenter)
        etiqueta.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)

        estilo_numero = (
            f"color: #8A9A9C; font-size: {escalar_fuente(20)}px; font-weight: bold; "
            f"background: transparent; border: none;"
        )
        fondo = "#EEF3F3"   # casilla vacía

        datos = self._normalizar_imagen_bytes(imagen_bytes)

        if datos:
            pixmap = QPixmap()
            if pixmap.loadFromData(datos):
                pixmap = pixmap.scaled(
                    escalar(200), escalar(105),
                    Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
                etiqueta.setPixmap(pixmap)
                etiqueta.setStyleSheet("background: transparent; border: none;")
                fondo = "white"
            else:
                etiqueta.setText(str(numero))
                etiqueta.setStyleSheet(estilo_numero)
        else:
            etiqueta.setText(str(numero))
            etiqueta.setStyleSheet(estilo_numero)

        contenedor.setStyleSheet(f"""
            QFrame#miniatura {{
                background-color: {fondo};
                border: 1px solid #D9E2E4;
                border-radius: {escalar(6)}px;
            }}
        """)

        layout.addWidget(etiqueta)
        return contenedor
   
       # ==============================================================
       # TIPO DE LIMPIEZA
       # ==============================================================
    def _crear_seccion_tipo_limpieza(self) -> QFrame:
        marco = QFrame()
        marco.setObjectName("tarjeta")
        marco.setStyleSheet(f"""
            QFrame#tarjeta {{
                background-color: white;
                border: 1px solid #D9E2E4;
                border-radius: {escalar(4)}px;
            }}
        """)

        layout = QVBoxLayout(marco)
        layout.setContentsMargins(escalar(12), escalar(8), escalar(12), escalar(8))
        layout.setSpacing(escalar(6))

        layout.addWidget(
            self._crear_etiqueta("Nivel de Limpieza", "#115E67", 16, True)
        )

        # Dimensiones de la matriz (3 filas x 4 columnas, botones cuadrados)
        self._filas_limpieza = 2
        self._columnas_limpieza = 7
        self._lado_boton_limpieza = escalar(90)

        self._contenedor_botones_limpieza = QGridLayout()
        self._contenedor_botones_limpieza.setSpacing(escalar(8))
        self._contenedor_botones_limpieza.setContentsMargins(0, 0, 0, 0)
        self._contenedor_botones_limpieza.setAlignment(Qt.AlignCenter)

        for columna in range(self._columnas_limpieza):
            self._contenedor_botones_limpieza.setColumnStretch(columna, 0)

        layout.addLayout(self._contenedor_botones_limpieza)

        # Paginación
        fila_paginacion = QHBoxLayout()
        fila_paginacion.setSpacing(escalar(6))

        self._btn_primera = QPushButton("<<")
        self._btn_anterior = QPushButton("<")
        self._lbl_pagina = QLabel("")
        self._btn_siguiente = QPushButton(">")
        self._btn_ultima = QPushButton(">>")

        for boton in (
            self._btn_primera,
            self._btn_anterior,
            self._btn_siguiente,
            self._btn_ultima,
        ):
            boton.setCursor(Qt.PointingHandCursor)
            boton.setFixedSize(escalar(34), escalar(22))
            boton.setStyleSheet(f"""
                QPushButton {{
                    background-color: white;
                    color: #115E67;
                    border: 1px solid #D9E2E4;
                    border-radius: {escalar(4)}px;
                    font-weight: 500;
                    font-size: {escalar_fuente(11)}px;
                }}
                QPushButton:hover {{
                    background-color: #EAF4F5;
                }}
                QPushButton:disabled {{
                    color: #BBB;
                    border-color: #EEE;
                }}
            """)

        self._lbl_pagina.setAlignment(Qt.AlignCenter)
        self._lbl_pagina.setStyleSheet(
            f"color: #115E67; font-size: {escalar_fuente(12)}px;"
            " background: transparent; border: none;"
        )

        self._btn_primera.clicked.connect(lambda: self._ir_a_pagina(0))
        self._btn_anterior.clicked.connect(
            lambda: self._ir_a_pagina(self._pagina_actual_limpieza - 1)
        )
        self._btn_siguiente.clicked.connect(
            lambda: self._ir_a_pagina(self._pagina_actual_limpieza + 1)
        )
        self._btn_ultima.clicked.connect(
            lambda: self._ir_a_pagina(self._total_paginas_limpieza - 1)
        )

        fila_paginacion.addStretch()
        fila_paginacion.addWidget(self._btn_primera)
        fila_paginacion.addWidget(self._btn_anterior)
        fila_paginacion.addWidget(self._lbl_pagina)
        fila_paginacion.addWidget(self._btn_siguiente)
        fila_paginacion.addWidget(self._btn_ultima)
        fila_paginacion.addStretch()

        layout.addLayout(fila_paginacion)

        # Obtener niveles de limpieza
        try:
            repositorio_limpieza = ObtenerTipoLimpiezaRepository(
                self._obtener_conexion
            )
            self._tipos_limpieza = repositorio_limpieza.obtener_tipos_limpieza()
        except Exception as e:
            print("No fue posible cargar tipos de limpieza:", e)
            self._tipos_limpieza = []

        # Grupo exclusivo de selección
        self._grupo_limpieza = QButtonGroup(self)
        self._grupo_limpieza.setExclusive(True)
        self._grupo_limpieza.buttonClicked.connect(self._tipo_limpieza_elegido)

        # Paginación: 12 niveles por página (3 x 4)
        self._tamano_pagina_limpieza = (
            self._filas_limpieza * self._columnas_limpieza
        )
        self._pagina_actual_limpieza = 0
        self._total_paginas_limpieza = max(
            1,
            -(-len(self._tipos_limpieza) // self._tamano_pagina_limpieza)
        )

        self._ir_a_pagina(0)

        return marco
 
    def _ir_a_pagina(self, numero_pagina: int):
        numero_pagina = max(0, min(numero_pagina, self._total_paginas_limpieza - 1))
        self._pagina_actual_limpieza = numero_pagina

        # Limpiar botones (y cualquier etiqueta) de la página anterior
        for boton in list(self._grupo_limpieza.buttons()):
            self._grupo_limpieza.removeButton(boton)
        while self._contenedor_botones_limpieza.count():
            item = self._contenedor_botones_limpieza.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        inicio = numero_pagina * self._tamano_pagina_limpieza
        fin = inicio + self._tamano_pagina_limpieza
        tipos_pagina = self._tipos_limpieza[inicio:fin]

        if not tipos_pagina:
            etiqueta_vacio = QLabel("No hay tipos de limpieza configurados.")
            etiqueta_vacio.setStyleSheet(
                f"color: #999; font-size: {escalar_fuente(13)}px;"
                " background: transparent; border: none;"
            )
            self._contenedor_botones_limpieza.addWidget(
                etiqueta_vacio, 0, 0, 1, self._columnas_limpieza
            )
        else:
            for indice, tipo in enumerate(tipos_pagina):
                fila, columna = divmod(indice, self._columnas_limpieza)

                boton = QPushButton(f"{tipo.tpo_lmpza}")
                boton.setCheckable(True)
                boton.setCursor(Qt.PointingHandCursor)
                boton.setFixedSize(
                    self._lado_boton_limpieza, self._lado_boton_limpieza
                )
                boton.setProperty("tpo_lmpza", tipo.tpo_lmpza)
                boton.setProperty("nombre_limpieza", tipo.nmbre)
                boton.setStyleSheet(f"""
                    QPushButton {{
                        background-color: white;
                        color: #115E67;
                        border: 1px solid #D9E2E4;
                        border-radius: {escalar(4)}px;
                        font-size: {escalar_fuente(14)}px;
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
                self._contenedor_botones_limpieza.addWidget(boton, fila, columna)

        self._lbl_pagina.setText(
            f"{self._pagina_actual_limpieza + 1} / {self._total_paginas_limpieza}"
        )
        hay_anterior = self._pagina_actual_limpieza > 0
        hay_siguiente = self._pagina_actual_limpieza < self._total_paginas_limpieza - 1
        self._btn_primera.setEnabled(hay_anterior)
        self._btn_anterior.setEnabled(hay_anterior)
        self._btn_siguiente.setEnabled(hay_siguiente)
        self._btn_ultima.setEnabled(hay_siguiente)
    # ==============================================================
    # BÁSCULA - PESO
    # ==============================================================
    def _crear_bascula(self) -> QFrame:
        marco = QFrame()
        marco.setObjectName("tarjeta")
        marco.setStyleSheet(f"""
            QFrame#tarjeta {{
                background-color: white;
                border: 1px solid #D9E2E4;
                border-radius: {escalar(4)}px;
            }}
        """)

        layout = QVBoxLayout(marco)
        layout.setContentsMargins(escalar(16), escalar(10), escalar(16), escalar(12))
        layout.setSpacing(escalar(8))

        layout.addWidget(self._crear_etiqueta("Báscula - Peso", "#115E67", 20, True))

        self.etiqueta_peso = QLabel(f"{self.peso_neto_kg:.3f}")
        self.etiqueta_peso.setAlignment(Qt.AlignCenter)
        self.etiqueta_peso.setMinimumHeight(escalar(120))
        self.etiqueta_peso.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.etiqueta_peso.setStyleSheet(f"""
            background-color: #E8F0EF;
            color: #115E67;
            font-size: {escalar_fuente(68)}px;
            font-weight: bold;
            font-family: 'Courier New';
            border: 2px solid #115E67;
            border-radius: 0px;
            padding: {escalar(6)}px;
        """)
        layout.addWidget(self.etiqueta_peso)

        self.etiqueta_peso_neto = QLabel(f"{self.peso_neto_kg:.3f}")
        self.etiqueta_peso_neto.setStyleSheet(
            f"color: #115E67; font-size: {escalar_fuente(25)}px; background: transparent; border: none;"
        )
        layout.addWidget(self.etiqueta_peso_neto)

        layout.addWidget(_linea_horizontal())

        etiqueta_impresora = self._crear_etiqueta("Impresora:", "#4F7F84", 13)
        layout.addWidget(etiqueta_impresora)

        self.combo_impresora = QComboBox()
        self.combo_impresora.setMinimumHeight(escalar(36))
        self.combo_impresora.setStyleSheet(f"""
            QComboBox {{
                background-color: white;
                border: 1px solid #D9E2E4;
                border-radius: {escalar(4)}px;
                padding: {escalar(4)}px {escalar(8)}px;
                font-size: {escalar_fuente(13)}px;
                color: #115E67;
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

        self.btn_ajustar_etiqueta = QPushButton("Ajustar etiqueta…")
        self.btn_ajustar_etiqueta.setMinimumHeight(escalar(34))
        self.btn_ajustar_etiqueta.setCursor(Qt.PointingHandCursor)
        self.btn_ajustar_etiqueta.setStyleSheet(f"""
            QPushButton {{
                background-color: #F0F4F4;
                color: #115E67;
                border: 1px solid #D9E2E4;
                border-radius: {escalar(4)}px;
                font-size: {escalar_fuente(13)}px;
            }}
            QPushButton:hover {{ background-color: #E3EEEE; }}
        """)
        self.btn_ajustar_etiqueta.clicked.connect(self._abrir_ajuste_etiqueta)

        layout.addWidget(self.combo_impresora)
        layout.addWidget(self.btn_ajustar_etiqueta)
        layout.addStretch()
        return marco
    
    def _tipo_limpieza_elegido(self, boton):
        self.tipo_limpieza_seleccionado = boton.property("tpo_lmpza")
        self._refrescar_preview_segun_seleccion()

    def _abrir_ajuste_etiqueta(self):
        nombre = self.combo_impresora.currentText().strip()
        if not nombre:
            QMessageBox.warning(self, "Ajuste de etiqueta", "Seleccione primero una impresora.")
            return
        try:
            dialogo = DialogoAjusteEtiqueta(nombre, parent=self)
            guardado = dialogo.exec() == QDialog.DialogCode.Accepted
        except Exception:
            logger.exception("No se pudo abrir la ventana de ajuste")
            QMessageBox.critical(self, "Ajuste de etiqueta", "No se pudo abrir la ventana de ajuste.")
            return
        if guardado:
            pass  # aquí refrescas tu vista previa si lo necesitas

    def _on_impresora_cambiada(self, nombre_impresora: str) -> None:
        self.impresora_seleccionada = nombre_impresora

    # ==============================================================
    # DATOS ADICIONALES
    # ==============================================================
    def _crear_datos_adicionales(self) -> QFrame:
        marco = QFrame()
        marco.setObjectName("tarjeta")
        marco.setStyleSheet(f"""
            QFrame#tarjeta {{
                background-color: white;
                border: 1px solid #D9E2E4;
                border-radius: {escalar(4)}px;
            }}
        """)

        layout = QVBoxLayout(marco)
        layout.setContentsMargins(escalar(14), escalar(14), escalar(14), escalar(14))
        layout.setSpacing(escalar(34))

        self.lbl_vista_previa_etiqueta = QLabel()
        self.lbl_vista_previa_etiqueta.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_vista_previa_etiqueta.setMinimumHeight(escalar(280))
        self.lbl_vista_previa_etiqueta.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.lbl_vista_previa_etiqueta.setStyleSheet(f"""
            background-color: white;
            border: 1px solid #D9E2E4;
            border-radius: {escalar(4)}px;
        """)
        layout.addWidget(self.lbl_vista_previa_etiqueta)

        # --- Consecutivo de pesaje + Inactivar ---
        fila_historico = QHBoxLayout()
        fila_historico.setSpacing(escalar(10))

        etiqueta_historico = self._crear_etiqueta("Consecutivo:", "#115E67", 15)
        etiqueta_historico.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        fila_historico.addWidget(etiqueta_historico)

        self.combo_historico_pesaje = QComboBox()
        self.combo_historico_pesaje.setFixedWidth(escalar(220))
        self.combo_historico_pesaje.setMinimumHeight(escalar(44))
        self.combo_historico_pesaje.setEditable(True)
        self.combo_historico_pesaje.setStyleSheet(f"""
            QComboBox {{
                background-color: white;
                border: 1px solid #D9E2E4;
                border-radius: {escalar(4)}px;
                padding: 4px 8px;
                font-size: {escalar_fuente(13)}px;
                color: #115E67;
            }}
        """)
        self.combo_historico_pesaje.activated.connect(self._on_historico_combo_cambiado)
        self.combo_historico_pesaje.editTextChanged.connect(self._on_historico_texto_editado)
        self.combo_historico_pesaje.lineEdit().editingFinished.connect(self._on_historico_texto_confirmado)
        fila_historico.addWidget(self.combo_historico_pesaje)

        self.check_inactivar = QCheckBox("Inactivar")
        self.check_inactivar.setStyleSheet(f"""
            QCheckBox {{
                color: #B00020;
                font-size: {escalar_fuente(15)}px;
                background: transparent;
                border: none;
                spacing: {escalar(8)}px;
            }}
            QCheckBox::indicator {{
                width: {escalar(22)}px;
                height: {escalar(22)}px;
                border: 1px solid #D9E2E4;
                border-radius: {escalar(4)}px;
                background: white;
            }}
            QCheckBox::indicator:checked {{
                background: #B00020;
                border: 1px solid #B00020;
            }}
        """)
        self.check_inactivar.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        fila_historico.addWidget(self.check_inactivar)
        fila_historico.addStretch()
        layout.addLayout(fila_historico)
        layout.addStretch()
        return marco

    def actualizar_vista_previa(self, datos: DatosEtiquetaFrescas) -> None:
        if not shiboken6.isValid(self):
            return

        pixmap = generar_vista_previa_pixmap(datos)

        # Zoom: recorta márgenes blancos (fracción de cada lado; 0 = sin recorte)
        MARGEN_X = 0.04
        MARGEN_Y = 0.06
        ancho, alto = pixmap.width(), pixmap.height()
        pixmap = pixmap.copy(
            int(ancho * MARGEN_X),
            int(alto * MARGEN_Y),
            int(ancho * (1 - 2 * MARGEN_X)),
            int(alto * (1 - 2 * MARGEN_Y)),
        )

        ancho_max_preview = escalar(760)   # antes 588
        alto_max_preview = escalar(280)    # antes 150

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
            tipo_conservacion=self.tipo_conservacion,
            numero_ticket=self.numero_ticket,
        )
        
    def _parametros_con_historico(self) -> dict:
        parametros = self._construir_parametros_etiqueta()

        if self._historico_seleccionado is not None:
            historico = self._historico_seleccionado
            parametros["peso_bascula"] = historico.get("pso_nto", self.peso_neto_kg)
            parametros["tipo_limpieza_seleccionado"] = historico.get("tpo_lmpza", self.tipo_limpieza_seleccionado)
            parametros["numero_ticket"] = historico.get("nmro_psta", self.numero_ticket)

        return parametros
    def _guardar_peso(self):
        # Punto 2: nivel de limpieza obligatorio (solo registros nuevos)
        if self.tipo_limpieza_seleccionado is None:
            self.mensaje_temporal.emit("Seleccione un nivel de limpieza antes de imprimir", "error")
            return

        # Punto 1: la posta no puede existir todavía
        try:
            ya_existe = bool(obtener_ultimos_historicos_pesaje(self.numero_ticket))
        except Exception as e:
            print("No fue posible verificar la posta:", e)
            self.mensaje_temporal.emit("No se pudo verificar el número de posta", "error")
            return

        if ya_existe:
            self.mensaje_temporal.emit(f"La posta {self.numero_ticket} ya existe. Use Reimprime.", "error")
            self._sincronizar_consecutivo()
            self._cargar_historicos_pesaje()
            return

        self._parametros_etiqueta_actuales = self._construir_parametros_etiqueta()
        datos = construir_datos_etiqueta(**self._parametros_etiqueta_actuales)

        try:
            registrar_historico_pesaje(
                self._parametros_etiqueta_actuales,
                oprdor=self.usuario.nombre_usuario + "-" + CODIGO_PROCESO_DEFAULT,
                nmro_psta=self.numero_ticket,
            )
        except Exception as e:
            print("Error guardando el histórico:", e)
            self.mensaje_temporal.emit("No se pudo guardar el pesaje; la etiqueta no se imprimió", "error")
            return

        imprimir_etiqueta_frescas(datos, self.impresora_seleccionada)

        self._sincronizar_consecutivo()    # siguiente posta, sin tocar nada
        self._cargar_historicos_pesaje()   # refresca combo y preview con la nueva posta

    def _sincronizar_consecutivo(self):
        try:
            self.numero_ticket = siguiente_consecutivo_etiqueta_canasta()
        except Exception as e:
            print("No fue posible obtener el siguiente consecutivo:", e)
            self.mensaje_temporal.emit("No se pudo obtener el siguiente número de posta", "error")
           
    def _cargar_historicos_pesaje(self, seleccionar_posta=None):
        try:
            self._historicos_disponibles = obtener_ultimos_pesajes_recientes(limite=3)
        except Exception as e:
            print("No fue posible cargar históricos de pesaje:", e)
            self._historicos_disponibles = []

        self.combo_historico_pesaje.blockSignals(True)
        self.combo_historico_pesaje.clear()
        self.combo_historico_pesaje.addItem("", None)
        indice_sel = 0
        for i, h in enumerate(self._historicos_disponibles, start=1):
            self.combo_historico_pesaje.addItem(f"{h['nmro_psta']} - {h['pso_nto']} kg", h)
            if seleccionar_posta is not None and h["nmro_psta"] == seleccionar_posta:
                indice_sel = i
        self.combo_historico_pesaje.setCurrentIndex(indice_sel)
        self.combo_historico_pesaje.blockSignals(False)

        self._historico_seleccionado = self.combo_historico_pesaje.itemData(indice_sel)
        self._actualizar_texto_boton()
        self._refrescar_preview_segun_seleccion()

    def _on_historico_combo_cambiado(self, indice: int):
        self._historico_seleccionado = self.combo_historico_pesaje.itemData(indice)
        self._actualizar_texto_boton()
        self._refrescar_preview_segun_seleccion()
    
    def _on_historico_texto_confirmado(self):
        texto = self.combo_historico_pesaje.currentText().strip()
        if not texto:
            self._historico_seleccionado = None
            self._actualizar_texto_boton()
            self._refrescar_preview_segun_seleccion()
            return

        indice = self.combo_historico_pesaje.findText(texto)
        if indice != -1:
            self._historico_seleccionado = self.combo_historico_pesaje.itemData(indice)
            self._actualizar_texto_boton()
            self._refrescar_preview_segun_seleccion()
            return

        primer_token = texto.split(" - ")[0].strip()
        try:
            nmro_psta_tecleado = int(primer_token)
        except ValueError:
            self._historico_seleccionado = None
            self._actualizar_texto_boton()
            self._refrescar_preview_segun_seleccion()
            return

        try:
            resultados = obtener_ultimos_historicos_pesaje(nmro_psta_tecleado)
        except Exception as e:
            print("No fue posible verificar la posta digitada:", e)
            resultados = []

        self._historico_seleccionado = resultados[0] if resultados else None
        if not resultados:
            self.mensaje_temporal.emit(f"No se encontró la posta {nmro_psta_tecleado}", "error")
        self._actualizar_texto_boton()
        self._refrescar_preview_segun_seleccion()
    def _refrescar_preview_segun_seleccion(self):
        if self._historico_seleccionado is not None:
            parametros = self._construir_parametros_etiqueta_desde_historico(self._historico_seleccionado)
        else:
            self._parametros_etiqueta_actuales = self._construir_parametros_etiqueta()
            parametros = self._parametros_etiqueta_actuales

        datos = construir_datos_etiqueta(**parametros)
        self.actualizar_vista_previa(datos)

        
    def _refrescar_vista_previa_actual(self):
        self._parametros_etiqueta_actuales = self._parametros_con_historico()
        datos = construir_datos_etiqueta(**self._parametros_etiqueta_actuales)
        self.actualizar_vista_previa(datos)

    def _reimprimir_historico(self):
        cnsctvo = self._historico_seleccionado["cnsctvo"]
        estado_a_enviar = 9 if self.check_inactivar.isChecked() else None

        marcar_historico_reimpreso(
            cnsctvo,
            oprdor=self.usuario.nombre_usuario + "-" + CODIGO_PROCESO_DEFAULT,
            estado=estado_a_enviar,
        )

        parametros = self._construir_parametros_etiqueta_desde_historico(self._historico_seleccionado)
        datos_etiqueta = construir_datos_etiqueta(**parametros)
        imprimir_etiqueta_frescas(datos_etiqueta, self.impresora_seleccionada)
        
    def _on_historico_texto_editado(self, texto: str):
        if self.combo_historico_pesaje.findText(texto) == -1 and self._historico_seleccionado is not None:
            self._historico_seleccionado = None
            self._actualizar_texto_boton()
            self._refrescar_preview_segun_seleccion()

        # ¿Coincide con uno de los 3 ya cargados?
        indice = self.combo_historico_pesaje.findText(texto)
        if indice != -1:
            self._historico_seleccionado = self.combo_historico_pesaje.itemData(indice)
            self._actualizar_texto_boton()
            return

        # Texto libre: se interpreta el primer token como nmro_psta y se valida en BD.
        primer_token = texto.split(" - ")[0].strip()
        try:
            nmro_psta_tecleado = int(primer_token)
        except ValueError:
            self._historico_seleccionado = None
            self._actualizar_texto_boton()
            return

        try:
            resultados = obtener_ultimos_historicos_pesaje(nmro_psta_tecleado)
        except Exception as e:
            print("No fue posible verificar la posta digitada:", e)
            resultados = []

        self._historico_seleccionado = resultados[0] if resultados else None
        self._actualizar_texto_boton()
        

    def _actualizar_texto_boton(self):
        reimpresion = self._historico_seleccionado is not None
        self.boton_guardar.setText("Reimprime" if reimpresion else "Imprime")
        self._seccion_limpieza.setEnabled(not reimpresion)   # nada editable al reimprimir
        self.check_inactivar.setEnabled(reimpresion)         # solo tiene sentido al reimprimir
        if not reimpresion:
            self.check_inactivar.setChecked(False)
            
    def _accion_boton_principal(self):
        if self._historico_seleccionado is not None:
            self._reimprimir_historico()
        else:
            self._guardar_peso()
            
    def _construir_parametros_etiqueta_desde_historico(self, historico: dict) -> dict:
        producto_para_etiqueta = SimpleNamespace(
            cdgo_plu=historico.get("cdgo_plu"),
            nom_prog=historico.get("nmbre_plu", ""),
        )
        vence_ref = historico.get("fcha_vnce_ref")
        vence_cong = historico.get("fcha_vnce_cong")

        return dict(
            producto=producto_para_etiqueta,
            lote=historico.get("nmro_lte"),
            fecha_produccion=historico.get("fcha_prdccion"),
            nombre_usuario=self.usuario.nombre_usuario,
            cod_empresa=historico.get("cdgo_emprsa"),
            tipo_limpieza_seleccionado=historico.get("tpo_lmpza"),
            peso_bascula=historico.get("pso_nto"),
            fecha_sacrificio=historico.get("fcha_scrfcio"),
            nom_impr_etiq=self.nom_impr_etiq,
            numEspecie=self.numEspecie,
            #fecha_vencimiento_str=( historico.get("fcha_vnce_ref") or historico.get("fcha_vnce_cong")),
            fecha_vencimiento_str=vence_ref or vence_cong,
            numero_ticket=historico.get("nmro_psta"),  # clave: reutiliza el consecutivo, no genera uno nuevo
        )
    def _construir_datos_historico_actualizado(self) -> dict:
        # Como los campos de _crear_info_producto no son editables,
        # se reutilizan los valores ya cargados en la sesión actual.
        # pso_tra, pso_brto, pddo y prcndor no se capturan hoy en la interfaz;
        # quedan en 0 hasta que definas de dónde deben salir.
        es_cong = self.tipo_conservacion == "congelado"
        return {
            "cdgo_plu": self.producto.get("cdgo_plu", 0),
            "nmbre_plu": self.producto.get("nombre", ""),
            "tpo_lmpza": self.tipo_limpieza_seleccionado or 0,
            "nmro_lte": self.lote,
            "fcha_prdccion": self.fecha_produccion,
            "fcha_vnce_ref": None if es_cong else self.fecha_vencimiento_str,
            "fcha_vnce_cong": self.fecha_vencimiento_str if es_cong else None,
            #"fcha_vnce_ref": self.fecha_vencimiento_str,
            #"fcha_vnce_cong": self.fecha_vencimiento_str,
            "fcha_scrfcio": self.fecha_sacrificio,
            "pso_nto": self.peso_neto_kg,
            "pso_tra": 0,
            "pso_brto": 0,
            "cdgo_emprsa": self.empresa,
            "pddo": 0,
            "prcndor": 0,
        }

    def _limpiar_y_volver(self):
        try:
            bascula_service.peso_actualizado.disconnect(self._on_peso_actualizado)
        except (RuntimeError, TypeError):
            pass
        bascula_service.detener()
        self._app.mostrar_seleccion_sin_recargar()

    def closeEvent(self, event):
        self._limpiar_y_volver()
        super().closeEvent(event)

    def _volver_a_seleccion_de_producto(self):
        self._limpiar_y_volver()
    
    def _on_peso_actualizado(self, nuevo_peso: float) -> None:
        cambio = nuevo_peso != self.peso_neto_kg
        if not hasattr(self, "_puerto_config_cache"):
            self._puerto_config_cache = bascula_service._obtener_puerto_configurado()
        self.peso_neto_kg = nuevo_peso
        self.etiqueta_peso.setText(f"{nuevo_peso:.3f}")
        self.etiqueta_peso_neto.setText(f"Peso Neto: {nuevo_peso:.3f} kg "+ f"Puerto: {self._puerto_config_cache}")

        if not cambio:
            return
        if getattr(self, "_historico_seleccionado", None) is not None:
            return
        if not getattr(self, "_parametros_etiqueta_actuales", None):
            return
        self._parametros_etiqueta_actuales = self._construir_parametros_etiqueta()
        datos = construir_datos_etiqueta(**self._parametros_etiqueta_actuales)
        self.actualizar_vista_previa(datos)

    def _volver_a_inicio(self):
        bascula_service.peso_actualizado.disconnect(self._on_peso_actualizado)
        bascula_service.detener()
        self._app.mostrar_principal()