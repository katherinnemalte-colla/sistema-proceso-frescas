from PySide6.QtWidgets import (
    QWidget, QLabel, QPushButton, QFrame, QGridLayout,
    QVBoxLayout, QHBoxLayout, QDateEdit, QButtonGroup, QSizePolicy
)
from datetime import timedelta,date
from typing import Optional
from PySide6.QtCore import Qt, QSize, QDate
from PySide6.QtGui import QPixmap, QIcon
from types import SimpleNamespace
from utils.ventana_utils import aplicar_tamano
from repositories.obtener_tipo_pza_repository import ObtenerTipoPzaRepository
from repositories.obtener_tipo_limpieza_repository import ObtenerTipoLimpiezaRepository
from utils import fechas
from repositories.etiquetas.frescas_100x45 import construir_datos_etiqueta, imprimir_etiqueta_frescas, generar_vista_previa_pixmap,DatosEtiquetaFrescas
from services.bascula_service import bascula_service
import webbrowser
import tempfile
from pathlib import Path
ANCHO_CONTENIDO = 1150
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
                self.empresa,
                self.numEspecie,
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
        # Vista previa inicial + reutilizar los mismos parámetros al cambiar el peso
        self._parametros_etiqueta_actuales = self._construir_parametros_etiqueta()
        self.actualizar_vista_previa(
            construir_datos_etiqueta(**self._parametros_etiqueta_actuales)
        )
        #bascula_service.peso_actualizado.connect(self._on_peso_actualizado)

    # ==============================================================
    # CONEXIÓN A BD — mismo patrón que SeleccionDeProducto
    # ==============================================================
    def _obtener_conexion(self):
        from models.database import obtener_conexion  # import local para evitar ciclos
        return obtener_conexion()

    # ==============================================================
    # INTERFAZ
    # ==============================================================
    def _obtener_datos_vencimiento(self) -> tuple[Optional[int], Optional[int], Optional[date], Optional[date]]:
            """
            Devuelve (dias_ref, dias_cong, fecha_vencimiento_refrigeracion, fecha_vencimiento_congelacion),
            con una sola consulta al repositorio.
            """
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
            print(f"'lo que retorna en ficha tecnica de dias': {dias_ref}, {dias_cong}")
            return dias_ref, dias_cong, fecha_vencimiento_refrigeracion, fecha_vencimiento_congelacion
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
        # ENCABEZADO: Atrás
        # ----------------------------------------------------------
        encabezado = QHBoxLayout()

        boton_atras = QPushButton("←  Atrás")
        boton_atras.setMinimumHeight(40)          # altura mínima, en vez de tamaño fijo
        boton_atras.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)  # ancho: crece; alto: fijo
        boton_atras.setStyleSheet(
            f"""
            QPushButton {{
                background: {COLOR_PRIMARIO};
                color: white;
                font-size: 14px;
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

        espaciador = QLabel("")
        espaciador.setFixedSize(110, 40)
        #ncabezado.addWidget(espaciador)

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
                border-radius: 0px;
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
                border-radius: 0px;
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
        resultado_sacrificio = ObtenerTipoLimpiezaRepository.obtener_fecha_sacrificio(self,self.lote, self.numEspecie)

        self.fecha_sacrificio = resultado_sacrificio.scrfcio if resultado_sacrificio else None
        self.nom_impr_etiq = resultado_sacrificio.nom_impr_etiq if resultado_sacrificio else None
       
    
        layout = QVBoxLayout(marco)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)

        titulo = QLabel("Información del producto")
        titulo.setStyleSheet("font-size: 15px; font-weight: bold; color: #115E67;")
        layout.addWidget(titulo)


        dias_ref, dias_cong, fecha_vencimiento_refrigeracion, fecha_vencimiento_congelacion = (
            self._obtener_datos_vencimiento()
        )

        if dias_cong is not None:
            etiqueta_vencimiento = "F.Vto en Congelación:"

            self.fecha_vencimiento_str = fecha_vencimiento_congelacion

            fecha_vencimiento_str = (
                fecha_vencimiento_congelacion.strftime("%d/%m/%Y")
                if fecha_vencimiento_congelacion
                else "-"
            )

            dias_vencimiento = dias_cong

        else:
            etiqueta_vencimiento = "F.Vto en Refrigeración:"

            self.fecha_vencimiento_str = fecha_vencimiento_refrigeracion

            fecha_vencimiento_str = (
                fecha_vencimiento_refrigeracion.strftime("%d/%m/%Y")
                if fecha_vencimiento_refrigeracion
                else "-"
            )

            dias_vencimiento = dias_ref


        def formatear_fecha(fecha, formato="%d/%m/%Y", valor_defecto="N/A") -> str:
            """Formatea una fecha de forma segura; si es None, devuelve un valor por defecto."""
            if fecha is None:
                return valor_defecto
            return fecha.strftime(formato)
        
        
        
        datos = [
            [("PLU:", self.producto.get("cdgo_plu", "-")), ("Producto:", self.producto.get("nombre", "-"))],
            [("Especie:", self.especie), ("Empresa:", self.empresa)],
            [("Fecha Empaque:", self.fecha_produccion.strftime("%d/%m/%Y"))],
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

        # Contenedor donde se dibujarán los botones de la página actual
        self._contenedor_botones_limpieza = QHBoxLayout()
        self._contenedor_botones_limpieza.setSpacing(10)
        layout.addLayout(self._contenedor_botones_limpieza)

        # Fila de paginación (se crea aparte, debajo de los botones)
        fila_paginacion = QHBoxLayout()
        fila_paginacion.setSpacing(6)

        self._btn_primera = QPushButton("<<")
        self._btn_anterior = QPushButton("<")
        self._lbl_pagina = QLabel("")
        self._btn_siguiente = QPushButton(">")
        self._btn_ultima = QPushButton(">>")

        for boton in (self._btn_primera, self._btn_anterior, self._btn_siguiente, self._btn_ultima):
            boton.setCursor(Qt.PointingHandCursor)
            boton.setFixedWidth(36)
            boton.setStyleSheet("""
                QPushButton {
                    background-color: white;
                    color: #115E67;
                    border: 1px solid #D9E2E4;
                    border-radius: 6px;
                    font-weight: 600;
                }
                QPushButton:hover { background-color: #EAF4F5; }
                QPushButton:disabled { color: #BBB; border-color: #EEE; }
            """)

        self._lbl_pagina.setAlignment(Qt.AlignCenter)
        self._lbl_pagina.setStyleSheet("color: #115E67; font-size: 12px;")

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

        # --- Carga de datos ---
        try:
            repositorio_limpieza = ObtenerTipoLimpiezaRepository(self._obtener_conexion)
            self._tipos_limpieza = repositorio_limpieza.obtener_tipos_limpieza()
        except Exception as e:
            print("No fue posible cargar tipos de limpieza:", e)
            self._tipos_limpieza = []

        self._grupo_limpieza = QButtonGroup(self)
        self._grupo_limpieza.setExclusive(True)
        self._grupo_limpieza.buttonClicked.connect(self._tipo_limpieza_elegido)

        self._tamano_pagina_limpieza = 8  # <-- ajusta cuántos botones caben por fila
        self._pagina_actual_limpieza = 0
        self._total_paginas_limpieza = max(
            1, -(-len(self._tipos_limpieza) // self._tamano_pagina_limpieza)  # ceil
        )

        self._ir_a_pagina(0)

        return marco


    def _ir_a_pagina(self, numero_pagina: int):
        """Recalcula límites, limpia los botones actuales y dibuja los de la nueva página."""
        numero_pagina = max(0, min(numero_pagina, self._total_paginas_limpieza - 1))
        self._pagina_actual_limpieza = numero_pagina

        # 1. Sacar del QButtonGroup y borrar los botones actuales
        for boton in list(self._grupo_limpieza.buttons()):
            self._grupo_limpieza.removeButton(boton)
            self._contenedor_botones_limpieza.removeWidget(boton)
            boton.deleteLater()

        # 2. Calcular el slice de datos para esta página
        inicio = numero_pagina * self._tamano_pagina_limpieza
        fin = inicio + self._tamano_pagina_limpieza
        tipos_pagina = self._tipos_limpieza[inicio:fin]

        # 3. Crear los botones de la página actual
        if not tipos_pagina:
            etiqueta_vacio = QLabel("No hay tipos de limpieza configurados.")
            etiqueta_vacio.setStyleSheet("color: #999; font-size: 13px;")
            self._contenedor_botones_limpieza.addWidget(etiqueta_vacio)
        else:
            for tipo in tipos_pagina:
                boton = QPushButton(f"{tipo.tpo_lmpza}")
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
                    QPushButton:hover { background-color: #EAF4F5; }
                    QPushButton:checked {
                        background-color: #115E67;
                        color: white;
                        border: 1px solid #115E67;
                    }
                """)
                self._grupo_limpieza.addButton(boton)
                self._contenedor_botones_limpieza.addWidget(boton)

        # 4. Actualizar etiqueta e (des)habilitar flechas
        self._lbl_pagina.setText(f"{self._pagina_actual_limpieza + 1} / {self._total_paginas_limpieza}")
        self._btn_primera.setEnabled(self._pagina_actual_limpieza > 0)
        self._btn_anterior.setEnabled(self._pagina_actual_limpieza > 0)
        self._btn_siguiente.setEnabled(self._pagina_actual_limpieza < self._total_paginas_limpieza - 1)
        self._btn_ultima.setEnabled(self._pagina_actual_limpieza < self._total_paginas_limpieza - 1)

    def _tipo_limpieza_elegido(self, boton):
        self.tipo_limpieza_seleccionado = boton.property("tpo_lmpza")
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

        self.etiqueta_peso = QLabel(f"{self.peso_neto_kg:.3f}")
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

        self.etiqueta_peso_neto = QLabel(f"Peso neto        {self.peso_neto_kg:.3f} kg")
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

        self.lbl_vista_previa_etiqueta = QLabel()
        self.lbl_vista_previa_etiqueta.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_vista_previa_etiqueta.setMinimumHeight(160)
        layout.addWidget(self.lbl_vista_previa_etiqueta)

        layout.addStretch()
        return marco


    def actualizar_vista_previa(self, datos: DatosEtiquetaFrescas) -> None:
        pixmap = generar_vista_previa_pixmap(datos)

        pixmap_escalado = pixmap.scaled(
            self.lbl_vista_previa_etiqueta.width() or pixmap.width(),
            self.lbl_vista_previa_etiqueta.height() or pixmap.height(),
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
        )


    def _guardar_peso(self):
        self._parametros_etiqueta_actuales = self._construir_parametros_etiqueta()
        datos = construir_datos_etiqueta(**self._parametros_etiqueta_actuales)
        imprimir_etiqueta_frescas(datos, "ZDesigner ZD230-203dpi ZPL")


    def _volver_a_seleccion_de_producto(self):
        self._app.mostrar_seleccion_sin_recargar()


    def _on_peso_actualizado(self, nuevo_peso: float) -> None:
        if not getattr(self, "_parametros_etiqueta_actuales", None):
            return
        datos = construir_datos_etiqueta(**self._parametros_etiqueta_actuales)
        self.actualizar_vista_previa(datos)
  
    def _volver_a_inicio(self):
        self._app.mostrar_principal()