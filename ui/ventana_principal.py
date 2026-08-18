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
)

from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtCore import Qt, QDate, QSize
from utils.ventana_utils import aplicar_tamano
from models.usuarios import Usuario
from repositories.obtener_lote_fecha_repository import (
    ObtenerLoteFechaRepository
)
from ui.seleccion_de_producto import SeleccionDeProducto


# ==============================================================
# RUTA DE ICONOS
# ==============================================================

RUTA_ICONOS = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "assets",
    "icons"
)


# ==============================================================
# ESPECIES
# ==============================================================
#
# id_especie:
#   identificador interno de la aplicación.
#
# etiqueta:
#   nombre que ve el usuario.
#
# archivo_icono:
#   imagen que se muestra en el botón.
#
# color:
#   color de acento de la tarjeta (encabezado + pie "Seleccionar").
#
# ==============================================================

ESPECIES = [
    (1, "RES", "res.png", "#C0392B"),
    (2, "CERDO", "cerdo.png", "#E75480"),
    (3, "TERNERA", "ternera.png", "#6D4C41"),
]

# Ancho máximo del bloque central de contenido.
# Todo (título, campos, botones) se alinea dentro de este ancho,
# y ese bloque se centra dentro de la ventana. Ya no es un ancho
# fijo: puede encogerse en pantallas pequeñas.
ANCHO_CONTENIDO_MAX = 760
ANCHO_CONTENIDO_MIN = 380


class VentanaPrincipal(QWidget):

    def __init__(self, usuario: Usuario):
        super().__init__()

        # ----------------------------------------------------------
        # USUARIO
        # ----------------------------------------------------------

        self.usuario = usuario

        # ----------------------------------------------------------
        # REPOSITORY
        # ----------------------------------------------------------

        self.repository = ObtenerLoteFechaRepository()

        # ----------------------------------------------------------
        # ESPECIE SELECCIONADA
        # ----------------------------------------------------------

        self.especie_seleccionada = None
        self.ventana_seleccion_producto = None

        # Tarjetas de especie, para poder resaltar la seleccionada
        # (solo afecta estilos, no la lógica de selección).
        self._tarjetas_especies = {}

        # ----------------------------------------------------------
        # CONFIGURACIÓN VENTANA
        # ----------------------------------------------------------

        self.setWindowTitle("Lote y Datos")

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
        # ICONO CIRCULAR + TÍTULO + SUBTÍTULO (centrados)
        # ==========================================================

        icono_encabezado = QLabel("📋")
        icono_encabezado.setAlignment(Qt.AlignCenter)
        icono_encabezado.setFixedSize(56, 56)
        icono_encabezado.setStyleSheet("""
            QLabel {
                background-color: #E4F1F2;
                border-radius: 28px;
                font-size: 22px;
            }
        """)

        fila_icono = QHBoxLayout()
        fila_icono.addStretch()
        fila_icono.addWidget(icono_encabezado)
        fila_icono.addStretch()

        layout.addLayout(fila_icono)

        titulo = QLabel(
            "Lote y datos"
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
            "📅"
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
            "📦"
        )

        columna_lote.addWidget(etiqueta_lote)
        columna_lote.addWidget(contenedor_lote)

        fila_campos.addLayout(columna_fecha, 1)
        fila_campos.addLayout(columna_lote, 1)

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
        # PIE - CONTINUAR (botón grande, azul, centrado)
        # ==========================================================

        pie = QHBoxLayout()

        pie.addStretch()

        boton_continuar = QPushButton(
            "Continuar"
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

        layout.addLayout(
            pie
        )

        self.setLayout(
            layout_externo
        )

        # ==========================================================
        # EVENTOS
        # ==========================================================

        self.campo_fecha.dateChanged.connect(
            self._fecha_cambiada
        )

        # ==========================================================
        # CARGA INICIAL
        # ==========================================================

        self._cargar_lotes()

    # ==============================================================
    # CAMPO CON ICONO (fecha / lote)
    # ==============================================================

    def _envolver_campo(self, campo, emoji_icono):
        """
        Envuelve un QDateEdit/QComboBox en un contenedor con borde
        redondeado y un pequeño icono a la izquierda, para que el
        icono se vea "dentro" del campo, como en el diseño.
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

        icono = QLabel(emoji_icono)
        icono.setStyleSheet("font-size: 14px; color: #115E67;")
        icono.setFixedWidth(20)

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
    # SELECTOR DE ESPECIES
    # ==============================================================

    def _crear_selector_especies(self) -> QHBoxLayout:
        """
        Crea las tarjetas de selección de especie: imagen arriba,
        nombre, y un pie de color con el botón "Seleccionar".

        El botón del pie es el que queda dentro del QButtonGroup
        (checkable, exclusivo), exactamente como antes: conserva
        las propiedades id_especie / nombre_especie y sigue siendo
        el que dispara _especie_elegida. Lo único nuevo es la
        tarjeta que lo envuelve visualmente.
        """

        fila = QHBoxLayout()

        fila.setSpacing(20)
        fila.setContentsMargins(20, 15, 20, 15)

        self.grupo_especies = QButtonGroup(
            self
        )

        self.grupo_especies.setExclusive(
            True
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
            # BOTÓN "SELECCIONAR" (el checkable real, en el grupo)
            # ------------------------------------------------------

            #lote = self.campo_lote.
            
            boton = QPushButton("Seleccionar   ›")

            

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
    # ESPECIE SELECCIONADA
    # ==============================================================

    def _especie_elegida(self, boton):

        self.especie_seleccionada = boton.property(
            "id_especie"
        )
        id_especie = boton.property(
            "id_especie"
        )
        nombre_especie = boton.property(
            "nombre_especie"
        )

        self._resaltar_tarjeta(id_especie)

        # ----------------------------------------------------------
        # FILTRAR POR FECHA + ESPECIE
        # ----------------------------------------------------------

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

        # ----------------------------------------------------------
        # SÍ HAY RESULTADOS: avanzar a Selección de producto
        # ----------------------------------------------------------

        self.ventana_seleccion_producto = SeleccionDeProducto(
            usuario=self.usuario,
            fecha_produccion=fecha.toString("yyyy-MM-dd"),
            especie=nombre_especie,
            numEspecie= id_especie,
            lotes=lotes,
            
        )
        print("ID:", id_especie)
        self.ventana_seleccion_producto.show()
        self.close()

    # ==============================================================
    # FECHA CAMBIADA
    # ==============================================================

    def _fecha_cambiada(self, fecha):
        """
        Cuando cambia la fecha se actualiza inmediatamente
        el listado de lotes.
        """

        # Si ya había una especie seleccionada,
        # mantenemos ese filtro.
        nombre_especie = self._obtener_nombre_especie()

        self._cargar_lotes(
            nombre_especie=nombre_especie
        )

    # ==============================================================
    # OBTENER NOMBRE DE ESPECIE ACTUAL
    # ==============================================================

    def _obtener_nombre_especie(self):

        boton = self.grupo_especies.checkedButton()

        if boton is None:
            return None

        return boton.property(
            "nombre_especie"
        )

    # ==============================================================
    # CARGAR LOTES
    # ==============================================================

    def _cargar_lotes(
        self,
        nombre_especie=None
    ):
        """
        Obtiene los lotes según la fecha.

        Si se proporciona nombre_especie:
            fecha + especie

        Si no:
            solamente fecha.
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
            # ESPECIE
            # ------------------------------------------------------

            if nombre_especie:

                lotes = (
                    self.repository
                    .obtener_lotes_por_especie(
                        nombre_especie
                    )
                )

            # ------------------------------------------------------
            # FILTRO SOLO FECHA
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

    # ==============================================================
    # CONTINUAR
    # ==============================================================

    def _continuar(self):

        # ----------------------------------------------------------
        # OBTENER OBJETO LOTE
        # ----------------------------------------------------------

        lote_seleccionado = (
            self.campo_lote.currentData()
        )

        # ----------------------------------------------------------
        # VALIDAR LOTE
        # ----------------------------------------------------------

        if lote_seleccionado is None:

            QMessageBox.warning(
                self,
                "Lote",
                "Seleccione un lote para continuar."
            )

            return

        # ----------------------------------------------------------
        # VALIDAR ESPECIE
        # ----------------------------------------------------------

        if self.especie_seleccionada is None:

            QMessageBox.warning(
                self,
                "Especie",
                "Seleccione una especie para continuar."
            )

            return

        # ----------------------------------------------------------
        # DATOS DEL LOTE
        # ----------------------------------------------------------

        datos_lote = {
            "lote": lote_seleccionado.lote,
            "fecha_produccion": self.campo_fecha.date().toString(
                "yyyy-MM-dd"
            ),
            "numEspecie": lote_seleccionado.numEspecie,
            "especie": lote_seleccionado.especie,
        }

        # ----------------------------------------------------------
        # TEMPORAL
        # ----------------------------------------------------------

        print(
            "Datos seleccionados:",
            datos_lote
        )