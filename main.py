#from models.database import probar_conexion
import sys
from PySide6.QtWidgets import QApplication
from views.productos_view import ProductosView
from controllers.productos_controller import ProductosController

if __name__ == "__main__":
    app = QApplication(sys.argv)

    vista = ProductosView()
    controlador = ProductosController(vista)  # conecta la vista con la lógica

    vista.show()
    sys.exit(app.exec())