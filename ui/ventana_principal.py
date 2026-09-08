import os

from PySide6.QtWidgets import (
    QWidget,
    QLabel,
    QDateEdit,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QButtonGroup,
    QMessageBox,
    QComboBox,
    QFrame,
    QCalendarWidget,
    QSizePolicy,
    QStackedWidget,
)

from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtCore import Qt, QDate, QSize
from utils.ventana_utils import aplicar_tamano
from models.usuarios import Usuario
from repositories.obtener_lote_fecha_repository import (
    ObtenerLoteFechaRepository
)
from utils.colores import Colores
from utils.mensajes import MensajeVentanaFlujo
from PySide6.QtWidgets import QLineEdit, QComboBox, QDateEdit
from PySide6.QtCore import QDate
from PySide6.QtGui import QIntValidator
RUTA_ICONOS = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "assets",
    "icons"
)

ESPECIES = [
    (1, "RES", "res.png", "#C0392B"),
    (2, "CERDO", "cerdo.png", "#E75480"),
    (3, "TERNERA", "ternera.png", "#6D4C41"),
]
ID_ESPECIE_RES = 1
TIPOS_PIEZA = [
    (1, "DELANTERO", "#1E6FD9"),
    (2, "TRASERO", "#1E9E5A"),
]

ANCHO_CONTENIDO_MAX = 760
ANCHO_CONTENIDO_MIN = 380


class VentanaPrincipal(QWidget):

    def __init__(self, usuario: Usuario, obtener_conexion, app_ventana):
        super().__init__()
        self.usuario = usuario
        self._obtener_conexion = obtener_conexion
        self._app = app_ventana

        # ----------------------------------------------------------
        # REPOSITORIES
        # ----------------------------------------------------------

        self.repository = ObtenerLoteFechaRepository()

        # ----------------------------------------------------------
        # ESPECIE SELECCIONADA
        # ----------------------------------------------------------

        self.especie_seleccionada = None
        self.ventana_seleccion_producto = None

        # Datos de la especie/fecha pendientes mientras se muestra
        # el panel de tipo de pieza (solo aplica para RES).
        self._nombre_especie_pendiente = None

        # Tarjetas de especie, para poder resaltar la seleccionada
        # (solo afecta estilos, no la lógica de selección).
        self._tarjetas_especies = {}

        # ----------------------------------------------------------
        # CONFIGURACIÓN VENTANA
        # ----------------------------------------------------------

        self.setWindowTitle("Etiquetas para Piezas + Canastillas- 2 en 1")

        aplicar_tamano(
            self,
            modo="completo"
        )

        self.setStyleSheet("""
            QWidget {
                background-color: #F5F8F8;
                font-family: "Segoe UI";
            }
        """)

        # ==========================================================
        # LAYOUT EXTERNO: centra el bloque de contenido en la ventana
        # ==========================================================

        layout_externo = QVBoxLayout()
        layout_externo.setContentsMargins(0, 0, 0, 0)

        layout_externo.addStretch()

        fila_central = QHBoxLayout()
        fila_central.addStretch()

        # ----------------------------------------------------------
        # LAYOUT PRINCIPAL (el bloque de contenido en sí)
        # ----------------------------------------------------------

        layout = QVBoxLayout()
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(16)

        contenedor = QWidget()
        contenedor.setMinimumWidth(ANCHO_CONTENIDO_MIN)
        contenedor.setMaximumWidth(ANCHO_CONTENIDO_MAX)
        contenedor.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Preferred
        )
        contenedor.setLayout(layout)

        fila_central.addWidget(contenedor)
        fila_central.addStretch()

        layout_externo.addLayout(fila_central)
        layout_externo.addStretch()

        # ==========================================================
        # TÍTULO + SUBTÍTULO (centrados)
        # ==========================================================


        fila_icono = QHBoxLayout()
        fila_icono.addStretch()
        fila_icono.addStretch()

        layout.addLayout(fila_icono)

        titulo = QLabel(
            "Etiquetado Carnes Frescas"
        )

        titulo.setAlignment(Qt.AlignCenter)
        titulo.setStyleSheet(
            "color: #115E67; font-size: 22px; font-weight: 700; "
            "letter-spacing: 0.5px;"
        )

        layout.addWidget(titulo)

        subtitulo = QLabel(
            "Seleccione la información para iniciar el proceso"
        )

        subtitulo.setAlignment(Qt.AlignCenter)

        subtitulo.setStyleSheet("""
            font-size: 14px;
            color: #8A9A9C;
        """)

        layout.addWidget(subtitulo)

        layout.addSpacing(10)

        # ==========================================================
        # FECHA DE PRODUCCIÓN + LOTE (lado a lado)
        # ==========================================================

        fila_campos = QHBoxLayout()
        fila_campos.setSpacing(24)

        # --- Columna: fecha ---
        columna_fecha = QVBoxLayout()
        columna_fecha.setSpacing(6)

        etiqueta_fecha = QLabel("Fecha de producción")
        etiqueta_fecha.setStyleSheet("font-size: 13px; color: #444;")

        self.campo_fecha = QDateEdit()

        self._configurar_calendario(
            self.campo_fecha
        )

        self.campo_fecha.setDisplayFormat(
            "dd/MM/yyyy"
        )

        # Fecha actual por defecto
        self.campo_fecha.setDate(
            QDate.currentDate()
        )

        contenedor_fecha = self._envolver_campo(
            self.campo_fecha,
            "calendar.png"
        )

        columna_fecha.addWidget(etiqueta_fecha)
        columna_fecha.addWidget(contenedor_fecha)

        # --- Columna: lote ---
        columna_lote = QVBoxLayout()
        columna_lote.setSpacing(6)

        etiqueta_lote = QLabel("Lote a trabajar")
        etiqueta_lote.setStyleSheet("font-size: 13px; color: #444;")

        self.campo_lote = QComboBox()

        self.campo_lote.setPlaceholderText(
            "Seleccione un lote"
        )

        contenedor_lote = self._envolver_campo(
            self.campo_lote,
            "lote.png"
        )

        columna_lote.addWidget(etiqueta_lote)
        columna_lote.addWidget(contenedor_lote)
        
                # --- Columna: empresa ---
        columna_empresa = QVBoxLayout()
        columna_empresa.setSpacing(6)

        etiqueta_empresa = QLabel("Empresa")
        etiqueta_empresa.setStyleSheet("font-size: 13px; color: #444;")

        self.campo_empresa = QLineEdit()
        self.campo_empresa.setPlaceholderText("Ingrese el número de empresa")
        self.campo_empresa.setValidator(QIntValidator(0, 999999999, self))

        contenedor_empresa = self._envolver_campo(
            self.campo_empresa,
            "empresa.png"
        )

        columna_empresa.addWidget(etiqueta_empresa)
        columna_empresa.addWidget(contenedor_empresa)
        

        fila_campos.addLayout(columna_fecha, 1)
        fila_campos.addLayout(columna_lote, 1)
        fila_campos.addLayout(columna_empresa, 1)
        layout.addLayout(fila_campos)

        layout.addSpacing(6)

        # ==========================================================
        # ESPECIE (etiqueta centrada + botones)
        # ==========================================================

        etiqueta_especie = QLabel("Especie de animal")
        etiqueta_especie.setAlignment(Qt.AlignCenter)
        etiqueta_especie.setStyleSheet(
            "font-size: 13px; color: #444; font-weight: 600;"
        )

        layout.addWidget(etiqueta_especie)

        layout.addLayout(
            self._crear_selector_especies()
        )

        layout.addSpacing(6)

        # ==========================================================
        # PIE: se alterna entre "Continuar" y "Tipo de pieza"
        # ==========================================================
        # Usamos un QStackedWidget para que, al elegir RES, el
        # botón Continuar sea reemplazado por DELANTERO/TRASERO
        # en el mismo espacio, y vuelva a Continuar si se
        # deselecciona la especie o se elige una distinta de RES.

        self.stack_pie = QStackedWidget()

        self.pagina_continuar = self._crear_pagina_continuar()
        self.pagina_tipo_pieza = self._crear_pagina_tipo_pieza()

        self.stack_pie.addWidget(self.pagina_continuar)   # índice 0
        self.stack_pie.addWidget(self.pagina_tipo_pieza)  # índice 1

        layout.addWidget(self.stack_pie)

        self.setLayout(
            layout_externo
        )

        # ==========================================================
        # EVENTOS
        # ==========================================================

        self.campo_fecha.dateChanged.connect(
            self._fecha_cambiada
        )
        
        self.campo_lote.currentIndexChanged.connect(
        self._actualizar_estado_botones_especie
        )

        # ==========================================================
        # CARGA INICIAL
        # ==========================================================

        self._cargar_lotes()

    # ==============================================================
    # PÁGINA: BOTÓN CONTINUAR (pie por defecto)
    # ==============================================================

    def _crear_pagina_continuar(self) -> QWidget:

        pagina = QWidget()

        pie = QHBoxLayout(pagina)
        pie.setContentsMargins(0, 0, 0, 0)
        pie.addStretch()

        boton_continuar = QPushButton(
            "Reiniciar"
        )

        boton_continuar.setMinimumSize(220, 46)
        boton_continuar.setMaximumWidth(320)
        boton_continuar.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Fixed
        )

        boton_continuar.setStyleSheet("""
            QPushButton {
                background-color: #1E6FD9;
                color: white;
                font-size: 15px;
                font-weight: bold;
                border: none;
                border-radius: 10px;
            }

            QPushButton:hover {
                background-color: #1A62BE;
            }

            QPushButton:pressed {
                background-color: #164F9C;
            }
        """)

        boton_continuar.clicked.connect(
            self._continuar
        )

        pie.addWidget(
            boton_continuar
        )

        pie.addStretch()

        return pagina

    # ==============================================================
    # PÁGINA: TIPO DE PIEZA (DELANTERO / TRASERO) - solo RES
    # ==============================================================

    def _crear_pagina_tipo_pieza(self) -> QWidget:

        pagina = QWidget()

        layout_panel = QVBoxLayout(pagina)
        layout_panel.setContentsMargins(0, 0, 0, 0)
        layout_panel.setSpacing(8)

        etiqueta = QLabel("Seleccione la parte del animal")
        etiqueta.setAlignment(Qt.AlignCenter)
        etiqueta.setStyleSheet(
            "font-size: 13px; color: #444; font-weight: 600;"
        )

        layout_panel.addWidget(etiqueta)

        fila_botones = QHBoxLayout()
        fila_botones.setSpacing(16)

        for tpo_pza, nombre_tipo, color in TIPOS_PIEZA:

            boton = QPushButton(nombre_tipo)

            boton.setCursor(Qt.PointingHandCursor)
            boton.setMinimumSize(160, 52)
            boton.setSizePolicy(
                QSizePolicy.Expanding,
                QSizePolicy.Fixed
            )

            boton.setStyleSheet(f"""
                QPushButton {{
                    background-color: {color};
                    color: white;
                    font-size: 15px;
                    font-weight: 700;
                    border: none;
                    border-radius: 10px;
                }}
                QPushButton:hover {{
                    background-color: {color};
                    border: 2px solid #115E67;
                }}
                QPushButton:pressed {{
                    background-color: #115E67;
                }}
            """)

            boton.clicked.connect(
                lambda _=False, tp=tpo_pza, nt=nombre_tipo:
                    self._tipo_pieza_elegido(tp, nt)
            )

            fila_botones.addWidget(boton)

        # Se agrega UNA sola vez, después del for, en la misma fila
        boton_continuar = QPushButton("Reiniciar")
        boton_continuar.setCursor(Qt.PointingHandCursor)
        boton_continuar.setMinimumSize(220, 46)
        boton_continuar.setMaximumWidth(320)
        boton_continuar.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Fixed
        )
        boton_continuar.setStyleSheet("""
            QPushButton {
                background-color: #1E6FD9;
                color: white;
                font-size: 15px;
                font-weight: bold;
                border: none;
                border-radius: 10px;
            }
            QPushButton:hover { background-color: #1A62BE; }
            QPushButton:pressed { background-color: #164F9C; }
        """)
        boton_continuar.clicked.connect(self._continuar)

        fila_botones.addWidget(boton_continuar)

        layout_panel.addLayout(fila_botones)

        return pagina

    # ==============================================================
    # CAMPO CON ICONO (fecha / lote)
    # ==============================================================

    def _envolver_campo(self, campo, nombre_archivo_icono):
        """
        Envuelve un QDateEdit/QComboBox en un contenedor con borde
        redondeado y un ícono a la izquierda, cargado desde
        assets/icons/<nombre_archivo_icono> en vez de un emoji fijo
        en el código.
        """

        campo.setFixedHeight(38)
        campo.setFrame(False)
        campo.setStyleSheet("""
            QDateEdit, QComboBox {
                border: none;
                background-color: transparent;
                padding: 2px 4px;
            }
            QComboBox::drop-down {
                border: none;
                width: 22px;
            }
        """)

        icono = QLabel()
        icono.setFixedSize(20, 20)
        icono.setAlignment(Qt.AlignCenter)

        ruta_icono = os.path.join(RUTA_ICONOS, nombre_archivo_icono)

        if os.path.isfile(ruta_icono):
            pixmap = QIcon(ruta_icono).pixmap(QSize(16, 16))
            icono.setPixmap(pixmap)
        else:
            # Fallback si el archivo no existe, para no dejar la UI rota
            icono.setText("•")
            icono.setStyleSheet("font-size: 14px; color: #115E67;")
            print(f"no existe el ícono: {ruta_icono}")

        contenedor = QFrame()
        contenedor.setFixedHeight(38)
        contenedor.setStyleSheet("""
            QFrame {
                border: 1px solid #D9E2E4;
                border-radius: 8px;
                background-color: white;
            }
        """)

        fila = QHBoxLayout(contenedor)
        fila.setContentsMargins(10, 0, 10, 0)
        fila.setSpacing(6)
        fila.addWidget(icono)
        fila.addWidget(campo)

        return contenedor

    # ==============================================================
    # CALENDARIO (mes/año seleccionables, un solo widget reutilizado)
    # ==============================================================

    def _configurar_calendario(self, campo_fecha):
        """
        Crea UNA sola instancia de QCalendarWidget, ya estilizada,
        y la reutiliza en el QDateEdit. Antes Qt reconstruía el
        popup por defecto cada vez que se abría, lo que hacía sentir
        el calendario lento; con un widget propio y ya preparado,
        abrir el popup es prácticamente instantáneo.

        La barra de navegación integrada de QCalendarWidget ya
        permite hacer clic en el mes y en el año para elegirlos
        directamente, sin tener que ir flecha por flecha.
        """

        if getattr(self, "_calendario", None) is None:

            calendario = QCalendarWidget()

            calendario.setGridVisible(False)
            calendario.setVerticalHeaderFormat(
                QCalendarWidget.NoVerticalHeader
            )
            calendario.setHorizontalHeaderFormat(
                QCalendarWidget.SingleLetterDayNames
            )
            calendario.setNavigationBarVisible(True)
            calendario.setFirstDayOfWeek(Qt.Monday)

            calendario.setStyleSheet("""
                QCalendarWidget QWidget {
                    alternate-background-color: #F5F8F8;
                }
                QCalendarWidget QToolButton {
                    color: #115E67;
                    font-size: 13px;
                    font-weight: 600;
                    background-color: transparent;
                    border-radius: 6px;
                    padding: 4px 8px;
                }
                QCalendarWidget QToolButton:hover {
                    background-color: #E4F1F2;
                }
                QCalendarWidget QMenu {
                    background-color: white;
                }
                QCalendarWidget QSpinBox {
                    color: #115E67;
                    background-color: white;
                }
                #qt_calendar_navigationbar {
                    background-color: white;
                    border-top-left-radius: 10px;
                    border-top-right-radius: 10px;
                }
                QCalendarWidget QAbstractItemView:enabled {
                    background-color: white;
                    color: #333;
                    selection-background-color: #115E67;
                    selection-color: white;
                    outline: none;
                }
                QCalendarWidget QAbstractItemView:disabled {
                    color: #C7CFCF;
                }
            """)

            self._calendario = calendario

        campo_fecha.setCalendarPopup(True)
        campo_fecha.setCalendarWidget(self._calendario)

    # ==============================================================
    # VALIDACIONES
    # ==============================================================

    def validar_combo(self):
        if self.campo_lote.currentIndex() <= 0:
            QMessageBox.warning(
                self,
                "Error",
                MensajeVentanaFlujo.ERROR_SELECCION
            )
            return False
        return True

    def validar_fecha(self):
        if not self.campo_fecha.date().isValid():
            QMessageBox.warning(
                self,
                "Error",
                MensajeVentanaFlujo.ERROR_FECHA
            )
            return False
        return True

    def validar_especie(self, id_especie):
        if not id_especie:
            QMessageBox.warning(
                self,
                "Error",
                MensajeVentanaFlujo.ERROR_SELECCION
            )
            return False
        return True

    # ==============================================================
    # SELECTOR DE ESPECIES
    # ==============================================================

    def _crear_selector_especies(self) -> QHBoxLayout:
        """
        Crea las tarjetas de selección de especie: imagen arriba,
        nombre, y un pie de color con el botón "Seleccionar".

        El botón del pie es el que queda dentro del QButtonGroup
        ahora manejado de forma manual (setExclusive(False)) para
        poder soportar la deselección: si se hace clic sobre la
        tarjeta ya seleccionada, se quita la selección en vez de
        quedar "atascada" (comportamiento por defecto de un grupo
        exclusivo en Qt).
        """

        fila = QHBoxLayout()

        fila.setSpacing(20)
        fila.setContentsMargins(20, 15, 20, 15)

        self.grupo_especies = QButtonGroup(
            self
        )

        # Exclusividad manejada a mano en _especie_elegida, para
        # poder permitir deseleccionar la tarjeta activa.
        self.grupo_especies.setExclusive(
            False
        )

        for id_especie, etiqueta, archivo_icono, color in ESPECIES:

            tarjeta = QFrame()
            tarjeta.setSizePolicy(
                QSizePolicy.Expanding,
                QSizePolicy.Preferred
            )
            tarjeta.setMinimumWidth(160)
            tarjeta.setStyleSheet(f"""
                QFrame#tarjeta {{
                    background-color: white;
                    border: 2px solid #E7ECEC;
                    border-radius: 16px;
                }}
                QFrame#tarjeta:hover {{
                    border: 2px solid {color};
                }}
            """)
            tarjeta.setObjectName("tarjeta")

            layout_tarjeta = QVBoxLayout(tarjeta)
            layout_tarjeta.setContentsMargins(14, 18, 14, 0)
            layout_tarjeta.setSpacing(8)

            # ------------------------------------------------------
            # IMAGEN
            # ------------------------------------------------------

            imagen = QLabel()
            imagen.setAlignment(Qt.AlignCenter)
            imagen.setMinimumHeight(90)

            ruta_icono = os.path.join(
                RUTA_ICONOS,
                archivo_icono
            )

            if os.path.isfile(ruta_icono):
                pixmap = QPixmap(ruta_icono)

                if not pixmap.isNull():
                    pixmap = QIcon(ruta_icono).pixmap(
                        QSize(90, 90)
                    )
                    imagen.setPixmap(pixmap)
                else:
                    print(f"no se pudo cargar la imagen: {ruta_icono}")
            else:
                print(f"no existe la imagen {ruta_icono}")

            layout_tarjeta.addWidget(imagen)

            # ------------------------------------------------------
            # NOMBRE
            # ------------------------------------------------------

            nombre = QLabel(etiqueta)
            nombre.setAlignment(Qt.AlignCenter)
            nombre.setStyleSheet(
                f"color: {color}; font-size: 16px; font-weight: 700; "
                "border: none;"
            )
            layout_tarjeta.addWidget(nombre)

            # ------------------------------------------------------
            # BOTÓN "SELECCIONAR" (checkable, exclusividad manual)
            # ------------------------------------------------------

            boton = QPushButton("Seleccionar   ›")

            boton.setCheckable(True)
            boton.setCursor(Qt.PointingHandCursor)
            boton.setMinimumHeight(40)

            boton.setStyleSheet(f"""
                QPushButton {{
                    background-color: {color};
                    color: white;
                    font-size: 13px;
                    font-weight: 600;
                    border: none;
                    border-bottom-left-radius: 14px;
                    border-bottom-right-radius: 14px;
                }}
                QPushButton:hover {{
                    background-color: {color};
                }}
                QPushButton:checked {{
                    background-color: {color};
                }}
            """)

            boton.setProperty(
                "id_especie",
                id_especie
            )

            boton.setProperty(
                "nombre_especie",
                etiqueta
            )

            self.grupo_especies.addButton(
                boton
            )

            layout_tarjeta.addWidget(boton)

            self._tarjetas_especies[id_especie] = tarjeta

            fila.addWidget(
                tarjeta
            )

        # ==========================================================
        # EVENTO
        # ==========================================================
            
        self.grupo_especies.buttonClicked.connect(
            self._especie_elegida
        )

        return fila

    # ==============================================================
    # RESALTAR TARJETA SELECCIONADA (solo estilo)
    # ==============================================================

    def _resaltar_tarjeta(self, id_especie):

        for id_actual, tarjeta in self._tarjetas_especies.items():

            if id_actual == id_especie:

                tarjeta.setStyleSheet("""
                    QFrame#tarjeta {
                        background-color: #F5FAFA;
                        border: 2px solid #115E67;
                        border-radius: 16px;
                    }
                """)

            else:

                tarjeta.setStyleSheet("""
                    QFrame#tarjeta {
                        background-color: white;
                        border: 2px solid #E7ECEC;
                        border-radius: 16px;
                    }
                """)

    # ==============================================================
    # ESPECIE SELECCIONADA / DESELECCIONADA
    # ==============================================================

    def _especie_elegida(self, boton):

        id_especie = boton.property("id_especie")
        nombre_especie = boton.property("nombre_especie")

        # ------------------------------------------------------------
        # CASO 1: se hizo clic sobre la tarjeta ya seleccionada
        # -> se interpreta como "quitar selección".
        # ------------------------------------------------------------

        if self.especie_seleccionada == id_especie:

            boton.setChecked(False)

            self.especie_seleccionada = None
            self._nombre_especie_pendiente = None

            self._resaltar_tarjeta(id_especie)
            self._ocultar_panel_tipo_pieza()

            # Al deseleccionar, volvemos a cargar los lotes
            # solo por fecha (sin filtro de especie).
            self._cargar_lotes()

            return

        # ------------------------------------------------------------
        # CASO 2: nueva selección -> desmarcar las demás tarjetas
        # ------------------------------------------------------------

        for otro_boton in self.grupo_especies.buttons():
            if otro_boton is not boton:
                otro_boton.setChecked(False)

        boton.setChecked(True)

        self.especie_seleccionada = id_especie
        self._resaltar_tarjeta(id_especie)

        # ------------------------------------------------------------
        # RES: mostrar panel de tipo de pieza en vez de continuar
        # directo. Otras especies: comportamiento original.
        # ------------------------------------------------------------

        if id_especie == ID_ESPECIE_RES:

            self._nombre_especie_pendiente = nombre_especie
            self._mostrar_panel_tipo_pieza()

        else:

            self._ocultar_panel_tipo_pieza()
            self._avanzar_a_seleccion_producto(
                id_especie,
                nombre_especie,
                empresa = 0, tpo_pza = 0, nombre_tipo_pieza = None
                
            )

    # ==============================================================
    # MOSTRAR / OCULTAR PANEL DE TIPO DE PIEZA
    # ==============================================================

    def _mostrar_panel_tipo_pieza(self):
        self.stack_pie.setCurrentWidget(self.pagina_tipo_pieza)

    def _ocultar_panel_tipo_pieza(self):
        self.stack_pie.setCurrentWidget(self.pagina_continuar)

    # ==============================================================
    # TIPO DE PIEZA ELEGIDO (DELANTERO / TRASERO)
    # ==============================================================

    def _tipo_pieza_elegido(self, tpo_pza, nombre_tipo_pieza):

        if self.especie_seleccionada != ID_ESPECIE_RES:
            # Salvaguarda: el panel solo debería estar visible
            # cuando la especie seleccionada es RES.
            return

        print(f"Pieza seleccionada: {nombre_tipo_pieza}")

        self._avanzar_a_seleccion_producto(
            ID_ESPECIE_RES,
            self._nombre_especie_pendiente,
            tpo_pza=tpo_pza,
            nombre_tipo_pieza=nombre_tipo_pieza,
            empresa=self.campo_empresa.text(),
            
        )

    # ==============================================================
    # AVANZAR A LA VENTANA DE SELECCIÓN DE PRODUCTO
    # ==============================================================

    def _avanzar_a_seleccion_producto(
        self,
        id_especie,
        nombre_especie,
        empresa, 
        tpo_pza=None,
        nombre_tipo_pieza=None,
    ):
        if not self.validar_fecha():
            return
        if not self.validar_especie(id_especie):
            return
        
        fecha = self.campo_fecha.date()
        fecha_bd = fecha.toString("yyyy/MM/dd")
        try:
            lotes = self.repository.obtener_lotes_por_especie(
                fecha_bd,
                id_especie
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"No fue posible consultar los lotes.\n\n{e}"
            )
            return

        # ----------------------------------------------------------
        # SIN RESULTADOS PARA ESA ESPECIE
        # ----------------------------------------------------------

        if not lotes:
            QMessageBox.information(
                self,
                "Sin resultados",
                f"No se encontraron lotes para la especie \"{nombre_especie}\" "
                f"en la fecha seleccionada."
            )
            return 

        # --------------------------------------------------------------
        # tpo_pza / nombre_tipo_pieza / imagenes solo llegan con
        # datos cuando la especie es RES. SeleccionDeProducto necesita
        # aceptar estos kwargs (o ignorarlos) para que esto no rompa
        # el flujo de las demás especies.
        # --------------------------------------------------------------
        self._app.mostrar_seleccion(
            lotes=lotes,
            fecha_produccion=fecha.toString("yyyy-MM-dd"),
            especie=nombre_especie,
            numEspecie=id_especie,
            tpo_pza=tpo_pza,
            empresa=empresa,
        )

    # ==============================================================
    # FECHA CAMBIADA
    # ==============================================================

    def _obtener_id_especie_seleccionada(self):
        for boton in self.grupo_especies.buttons():
            if boton.isChecked():
                return boton.property("id_especie")
        return None
    
    def _actualizar_estado_botones_especie(self):
        """
        Habilita los botones "Seleccionar" de las especies solo
        cuando hay un lote válido elegido en campo_lote.
        """
        hay_lote_valido = self.campo_lote.currentData() is not None

        for boton in self.grupo_especies.buttons():
            boton.setEnabled(hay_lote_valido)

    def _fecha_cambiada(self, fecha):
        """
        Cuando cambia la fecha se actualiza inmediatamente
        el listado de lotes, manteniendo el filtro de especie
        si ya había una seleccionada.
        """

        id_especie = self._obtener_id_especie_seleccionada()

        self._cargar_lotes(
            id_especie=id_especie
        )

    # ==============================================================
    # CARGAR LOTES
    # ==============================================================

    def _cargar_lotes(
        self,
        id_especie=None
    ):
        """
        Obtiene los lotes según la fecha.

        Si se proporciona id_especie:
            fecha + especie -> obtener_lotes_por_especie(fecha, id_especie)

        Si no:
            solamente fecha -> obtener_lotes_por_fecha(fecha)
        """

        # ----------------------------------------------------------
        # FECHA PARA LA BD
        # ----------------------------------------------------------

        fecha = self.campo_fecha.date()

        fecha_bd = fecha.toString(
            "yyyy/MM/dd"
        )

        try:

            # ------------------------------------------------------
            # FECHA + ESPECIE
            # ------------------------------------------------------
            # obtener_lotes_por_especie requiere (fecha, num_especie).
            # Antes solo se mandaba id_especie, y num_especie quedaba
            # sin recibir valor -> TypeError "missing 1 required
            # positional argument: num_especie".
            # ------------------------------------------------------

            if id_especie:

                lotes = (
                    self.repository
                    .obtener_lotes_por_especie(
                        fecha_bd,
                        id_especie
                    )
                )

            # ------------------------------------------------------
            # SOLO FECHA
            # ------------------------------------------------------

            else:

                lotes = (
                    self.repository
                    .obtener_lotes_por_fecha(
                        fecha_bd
                    )
                )

            # ------------------------------------------------------
            # LIMPIAR COMBO
            # ------------------------------------------------------

            self.campo_lote.clear()

            # ------------------------------------------------------
            # SIN RESULTADOS
            # ------------------------------------------------------

            if not lotes:

                self.campo_lote.addItem(
                    "No hay lotes disponibles"
                )

                self.campo_lote.setCurrentIndex(
                    0
                )
                self._actualizar_estado_botones_especie()

                return

            # ------------------------------------------------------
            # CARGAR LOTES
            # ------------------------------------------------------

            self.campo_lote.addItem(
                "Seleccione un lote",
                None
            )

            for lote in lotes:

                self.campo_lote.addItem(
                    str(lote.lote),
                    lote
                )
                self._actualizar_estado_botones_especie()
            
        except Exception as e:

            QMessageBox.critical(
                self,
                "Error",
                f"No fue posible obtener los lotes.\n\n{e}"
            )

            self.campo_lote.clear()

            self.campo_lote.addItem(
                "Error al consultar lotes"
            )
    def _reiniciar_formulario(self):

        self.especie_seleccionada = None
        self._nombre_especie_pendiente = None
        self.campo_empresa.text() == None

        for boton in self.grupo_especies.buttons():
            boton.setChecked(False)

        # Vuelve a pintar todas las tarjetas sin resaltado
        self._resaltar_tarjeta(None)

        # ------------------------------------------------------------
        # PANEL DEL PIE
        # ------------------------------------------------------------

        self._ocultar_panel_tipo_pieza()

        # ------------------------------------------------------------
        # FECHA (esto dispara _fecha_cambiada -> _cargar_lotes)
        # ------------------------------------------------------------

        fecha_hoy = QDate.currentDate()

        if self.campo_fecha.date() == fecha_hoy:
            # Si ya está en la fecha de hoy, dateChanged no se
            # dispara solo, así que forzamos la recarga manualmente.
            self._cargar_lotes()
        else:
            self.campo_fecha.setDate(fecha_hoy)

        # ------------------------------------------------------------
        # BOTONES DE ESPECIE
        # ------------------------------------------------------------
        # _cargar_lotes ya llama a _actualizar_estado_botones_especie,
        # pero lo dejamos explícito por seguridad.

        self._actualizar_estado_botones_especie()
    # ==============================================================
    # CONTINUAR
    # ==============================================================
    def _continuar(self):

        self._reiniciar_formulario()