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
)

from PySide6.QtGui import QIcon
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
# ==============================================================

ESPECIES = [
    (1, "Res", "res.png"),
    (2, "Cerdo", "cerdo.png"),
    (3, "Ternera", "ternera.png"),
]

# Ancho fijo del bloque central de contenido.
# Todo (título, campos, botones) se alinea dentro de este ancho,
# y ese bloque se centra dentro de la ventana.
ANCHO_CONTENIDO = 720


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
        layout.setContentsMargins(30, 25, 30, 25)
        layout.setSpacing(18)

        contenedor = QWidget()
        contenedor.setFixedWidth(ANCHO_CONTENIDO)
        contenedor.setLayout(layout)

        fila_central.addWidget(contenedor)
        fila_central.addStretch()

        layout_externo.addLayout(fila_central)
        layout_externo.addStretch()

        # ==========================================================
        # TÍTULO (grande, centrado)
        # ==========================================================

        titulo = QLabel(
            "Lote y datos"
        )

        titulo.setAlignment(Qt.AlignCenter)

        titulo.setStyleSheet("""
            font-size: 32px;
            font-weight: bold;
            color: #115E67;
        """)

        layout.addWidget(titulo)

        # ==========================================================
        # SUBTÍTULO (centrado, debajo del título)
        # ==========================================================

        subtitulo = QLabel(
            "Configuración de lote"
        )

        subtitulo.setAlignment(Qt.AlignCenter)

        subtitulo.setStyleSheet("""
            font-size: 14px;
            color: #888;
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

        self.campo_fecha.setCalendarPopup(
            True
        )

        self.campo_fecha.setDisplayFormat(
            "dd/MM/yyyy"
        )

        # Fecha actual por defecto
        self.campo_fecha.setDate(
            QDate.currentDate()
        )

        self.campo_fecha.setFixedHeight(38)

        self.campo_fecha.setStyleSheet("""
            QDateEdit {
                border: 1px solid #D9E2E4;
                border-radius: 8px;
                padding: 4px 10px;
                background-color: white;
            }
        """)

        columna_fecha.addWidget(etiqueta_fecha)
        columna_fecha.addWidget(self.campo_fecha)

        # --- Columna: lote ---
        columna_lote = QVBoxLayout()
        columna_lote.setSpacing(6)

        etiqueta_lote = QLabel("Lote a trabajar")
        etiqueta_lote.setStyleSheet("font-size: 13px; color: #444;")

        self.campo_lote = QComboBox()

        self.campo_lote.setPlaceholderText(
            "Seleccione un lote"
        )

        self.campo_lote.setFixedHeight(38)

        self.campo_lote.setStyleSheet("""
            QComboBox {
                border: 1px solid #D9E2E4;
                border-radius: 8px;
                padding: 4px 10px;
                background-color: white;
            }
        """)

        columna_lote.addWidget(etiqueta_lote)
        columna_lote.addWidget(self.campo_lote)

        fila_campos.addLayout(columna_fecha)
        fila_campos.addLayout(columna_lote)

        layout.addLayout(fila_campos)

        layout.addSpacing(10)

        # ==========================================================
        # ESPECIE (etiqueta centrada + botones)
        # ==========================================================

        etiqueta_especie = QLabel("Especie de animal")
        etiqueta_especie.setAlignment(Qt.AlignCenter)
        etiqueta_especie.setStyleSheet("font-size: 13px; color: #444;")

        layout.addWidget(etiqueta_especie)

        layout.addLayout(
            self._crear_selector_especies()
        )

        layout.addSpacing(10)

        # ==========================================================
        # PIE - CONTINUAR (botón grande, azul, centrado)
        # ==========================================================

        pie = QHBoxLayout()

        pie.addStretch()

        boton_continuar = QPushButton(
            "Continuar"
        )

        boton_continuar.setFixedSize(260, 48)

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
    # SELECTOR DE ESPECIES
    # ==============================================================

    def _crear_selector_especies(self) -> QHBoxLayout:
        """
        Crea los botones de selección de especie.

        Los tres botones:
        - Tienen exactamente el mismo tamaño.
        - Muestran una imagen grande.
        - Mantienen márgenes uniformes.
        - Están centrados horizontalmente.
        - Son de selección exclusiva.
        """

        fila = QHBoxLayout()

        fila.setSpacing(20)

        fila.setContentsMargins(
            20,
            15,
            20,
            15
        )

        self.grupo_especies = QButtonGroup(
            self
        )

        self.grupo_especies.setExclusive(
            True
        )

        # Centrar los botones horizontalmente
        fila.addStretch()

        for id_especie, etiqueta, archivo_icono in ESPECIES:

            boton = QPushButton()

            boton.setCheckable(True)

            # ======================================================
            # TAMAÑO DEL BOTÓN
            # ======================================================

            boton.setFixedSize(
                220,
                220
            )

            # ======================================================
            # TAMAÑO DE LA IMAGEN
            # ======================================================

            boton.setIconSize(
                QSize(
                    220,
                    150
                )
            )

            boton.setText(
                etiqueta
            )

            # ======================================================
            # ESTILO
            # ======================================================

            boton.setStyleSheet("""
                QPushButton {
                    background-color: white;
                    border: 2px solid #D9E2E4;
                    border-radius: 16px;
                    padding: 15px;
                    color: #115E67;
                    font-size: 16px;
                    font-weight: bold;
                }

                QPushButton:hover {
                    border: 2px solid #94B7BB;
                    background-color: #F5FAFA;
                }

                QPushButton:checked {
                    border: 3px solid #115E67;
                    background-color: #EAF4F5;
                    color: #115E67;
                }

                QPushButton:pressed {
                    background-color: #DDEEEF;
                }
            """)

            # ======================================================
            # CARGAR ICONO
            # ======================================================

            ruta_icono = os.path.join(
                RUTA_ICONOS,
                archivo_icono
            )

            if os.path.exists(ruta_icono):

                boton.setIcon(
                    QIcon(ruta_icono)
                )

            # ======================================================
            # PROPIEDADES
            # ======================================================

            boton.setProperty(
                "id_especie",
                id_especie
            )

            boton.setProperty(
                "nombre_especie",
                etiqueta
            )

            # ======================================================
            # GRUPO
            # ======================================================

            self.grupo_especies.addButton(
                boton
            )

            fila.addWidget(
                boton
            )

        # Centrar los botones
        fila.addStretch()

        # ==========================================================
        # EVENTO
        # ==========================================================

        self.grupo_especies.buttonClicked.connect(
            self._especie_elegida
        )

        return fila

    # Con esto necesitamos agregar el stretch
    # antes de los botones también.

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

        # ----------------------------------------------------------
        # FILTRAR POR FECHA + ESPECIE
        # ----------------------------------------------------------

        fecha = self.campo_fecha.date()
        fecha_bd = fecha.toString("yyyy/MM/dd")
        try:
            lotes = self.repository.obtener_lotes_por_fecha_especie(
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
            # FILTRO FECHA + ESPECIE
            # ------------------------------------------------------

            if nombre_especie:

                lotes = (
                    self.repository
                    .obtener_lotes_por_fecha_especie(
                        fecha_bd,
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