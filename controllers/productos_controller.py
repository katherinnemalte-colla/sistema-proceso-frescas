import math
from models.producto_model import obtener_productos_paginado, contar_productos


class ProductosController:
    def __init__(self, view):
        self.view = view
        self.pagina_actual = 1
        self.tamano_pagina = 20
        self.total_productos = contar_productos()
        self.total_paginas = math.ceil(self.total_productos / self.tamano_pagina)

        # Conecta los botones a las funciones
        self.view.btn_siguiente.clicked.connect(self.siguiente_pagina)
        self.view.btn_anterior.clicked.connect(self.pagina_anterior)

        self.cargar_pagina()

    def cargar_pagina(self):
        productos = obtener_productos_paginado(self.pagina_actual, self.tamano_pagina)
        self.view.mostrar_productos(productos)
        self.view.actualizar_label_pagina(self.pagina_actual, self.total_paginas)

        # Deshabilita botones en los extremos
        self.view.btn_anterior.setEnabled(self.pagina_actual > 1)
        self.view.btn_siguiente.setEnabled(self.pagina_actual < self.total_paginas)

    def siguiente_pagina(self):
        if self.pagina_actual < self.total_paginas:
            self.pagina_actual += 1
            self.cargar_pagina()

    def pagina_anterior(self):
        if self.pagina_actual > 1:
            self.pagina_actual -= 1
            self.cargar_pagina()