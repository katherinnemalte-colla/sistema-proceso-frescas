from PySide6.QtWidgets import QMainWindow, QStackedWidget
from ui.ventana_principal import VentanaPrincipal
from ui.seleccion_de_producto import SeleccionDeProducto
from ui.ficha_tecnica import FichaTecnica


class VentanaApp(QMainWindow):
    def __init__(self, usuario, obtener_conexion):
        super().__init__()
        self.usuario = usuario
        self._obtener_conexion = obtener_conexion

        self.stack_principal = QStackedWidget()
        self.setCentralWidget(self.stack_principal)

        # no depende de datos externos
        self.pantalla_principal = VentanaPrincipal(self.usuario, self._obtener_conexion, self)
        self.stack_principal.addWidget(self.pantalla_principal)  # índice 0

        # Estas se crean bajo demanda, cuando haya datos para construirlas
        self.pantalla_seleccion = None
        self.pantalla_ficha = None

        self.stack_principal.setCurrentWidget(self.pantalla_principal)
        #self.showFullScreen()
        self.showMaximized()

    # --- navegación centralizada ---
    def mostrar_principal(self):
        self.stack_principal.setCurrentWidget(self.pantalla_principal)

    def mostrar_seleccion(self, *, lotes, fecha_produccion, especie, numEspecie, tpo_pza=None, empresa):
        if self.pantalla_seleccion is not None:
            self.stack_principal.removeWidget(self.pantalla_seleccion)
            self.pantalla_seleccion.deleteLater()

        self.pantalla_seleccion = SeleccionDeProducto(
            usuario=self.usuario,
            lotes=lotes,
            obtener_conexion=self._obtener_conexion,
            app_ventana=self,
            fecha_produccion=fecha_produccion,
            especie=especie,
            numEspecie=numEspecie,
            tpo_pza=tpo_pza,
            empresa=empresa,
        )
        self.stack_principal.addWidget(self.pantalla_seleccion)
        self.stack_principal.setCurrentWidget(self.pantalla_seleccion)

    def mostrar_seleccion_sin_recargar(self):
        self.stack_principal.setCurrentWidget(self.pantalla_seleccion)

    def mostrar_ficha(
        self,
        *,
        producto,
        fecha_produccion,
        especie,
        numEspecie,
        lote,
        tpo_pza=None,
        nombre_tipo_pieza=None,
        peso_neto_kg,
        fecha_sacrificio,
        nom_impr_etiq=None,
        empresa = 0,
        fecha_vencimiento_str,
    ):
        if self.pantalla_ficha is not None:
            self.stack_principal.removeWidget(self.pantalla_ficha)
            self.pantalla_ficha.deleteLater()

        self.pantalla_ficha = FichaTecnica(
            self.usuario,
            producto,
            fecha_produccion,
            especie,
            numEspecie,
            lote,
            self._obtener_conexion,
            self,
            tpo_pza=tpo_pza,
            nombre_tipo_pieza=nombre_tipo_pieza,
            peso_neto_kg = peso_neto_kg,
            fecha_sacrificio=fecha_sacrificio,
            nom_impr_etiq=nom_impr_etiq,
            empresa=empresa,
            fecha_vencimiento_str=fecha_vencimiento_str
        )
        self.stack_principal.addWidget(self.pantalla_ficha)
        self.stack_principal.setCurrentWidget(self.pantalla_ficha)