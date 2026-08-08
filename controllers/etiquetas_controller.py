from PySide6.QtWidgets import QMessageBox

from views.main_windows import EtiquetasWindow
from models.producto_model import ProductoModel


class EtiquetasController:

    def __init__(self):

        self.view = EtiquetasWindow()
        self.model = ProductoModel()

        # Evento Enter del campo PLU
        self.view.txtPlu.returnPressed.connect(self.buscar_producto)

    def mostrar(self):
        self.view.show()

    def buscar_producto(self):

        plu = self.view.txtPlu.text().strip()

        if not plu:
            QMessageBox.warning(
                self.view,
                "Advertencia",
                "Debe ingresar un PLU."
            )
            return

        producto = self.model.buscar_producto(plu)

        if producto is None:
            QMessageBox.information(
                self.view,
                "Información",
                "Producto no encontrado."
            )
            self.limpiar_campos()
            return

        # producto[0] = cdgo_plu
        # producto[1] = nmbre_prdcto
        # producto[2] = cdgo_espcie
        # producto[3] = estdo

        if producto[3] == 1:
            QMessageBox.warning(
                self.view,
                "Advertencia",
                "Producto Inactivo."
            )
            self.limpiar_campos()
            return

        self.view.txtEspecie.setText(str(producto[2]))
        self.view.txtNombre.setText(producto[1])

    def limpiar_campos(self):
        self.view.txtEspecie.clear()
        self.view.txtNombre.clear()