"""
Mensajes reutilizables de la aplicación (errores, confirmaciones, avisos).
Centralizarlos aquí evita repetir el mismo texto en varias ventanas
y facilita cambiar la redacción o traducir el sistema más adelante.
"""


class MensajesLogin:
    USUARIO_O_CLAVE_INCORRECTA = "Usuario o contraseña incorrectos."
    USUARIO_INACTIVO = "Este usuario está inactivo. Contacte al administrador."
    CAMPOS_VACIOS = "Debe ingresar usuario y contraseña."
    ERROR_CONEXION = "No se pudo conectar con la base de datos. Intente nuevamente."


class MensajesGenerales:
    ERROR_INESPERADO = "Ocurrió un error inesperado. Intente nuevamente."
    OPERACION_EXITOSA = "Operación realizada con éxito."
    CONFIRMAR_SALIR = "¿Está seguro que desea salir?"

class MensajeVentanaFlujo:
    ERROR_SELECCION = "Primero debes seleccionar el lote a trabajar."

# Función auxiliar opcional, para no repetir el patrón de QMessageBox en cada ventana
def mostrar_error(parent, titulo: str, mensaje: str):
    from PySide6.QtWidgets import QMessageBox
    QMessageBox.warning(parent, titulo, mensaje)


def mostrar_info(parent, titulo: str, mensaje: str):
    from PySide6.QtWidgets import QMessageBox
    QMessageBox.information(parent, titulo, mensaje)