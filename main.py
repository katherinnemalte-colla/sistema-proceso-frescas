import logging
import os
import shutil
import subprocess
import sys
import tempfile

import win32api
from PySide6.QtCore import QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QDialog
from config.settings import DB_SERVER
from models.database import obtener_conexion
from models.usuarios import Usuario
from ui.app_ventana import VentanaApp
from ui.ventana_fondo import VentanaFondo
from ui.ventana_login import VentanaLogin
from utils.logs import configurar_logging
import threading
import time

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QProgressBar, QVBoxLayout, QWidget

EXE_RED = r"\\200.150.50.134\publico\Analista\etiquetasMk\etiquetas_v2.exe"

def _obtener_directorio_base() -> str:
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


class ControladorApp:

    def __init__(self):
        self.ventana_fondo = VentanaFondo()
        self.ventana_app = None

        self.ventana_fondo.show()
        QApplication.processEvents()
        self._mostrar_login()

    def _mostrar_login(self):
        login = VentanaLogin(self.ventana_fondo)
        resultado = login.exec()

        if resultado == QDialog.Accepted:
            self.abrir_ventana_principal(login.usuario_autenticado)
        else:
            sys.exit(0)
            
    def abrir_ventana_principal(self, usuario: Usuario):
        self.ventana_fondo.close()
        
        nombre_usuario = usuario.nombre_usuario

        self.ventana_app = VentanaApp(usuario, obtener_conexion)

        # Título de la ventana con el nombre del usuario.
        self.ventana_app.setWindowTitle(
            f"Etiquetas 2 en 1"+ f"  Usuario: {nombre_usuario}"+f" Entorno : {DB_SERVER}" 
        )

        self.ventana_app.show()
        QTimer.singleShot(0, self.ventana_app.showMaximized)


def version_exe(ruta):
    """Versión del archivo como tupla, ej. (1, 0, 4, 0)."""
    try:
        info = win32api.GetFileVersionInfo(str(ruta), "\\")
        ms, ls = info["FileVersionMS"], info["FileVersionLS"]
        return (ms >> 16, ms & 0xFFFF, ls >> 16, ls & 0xFFFF)
    except Exception:
        return (0, 0, 0, 0)  # exe sin versión: se considera el más viejo

def _mostrar_aviso(texto: str) -> QWidget:
    """Ventana pequeña con barra animada para avisar que se está actualizando."""
    ventana = QWidget()
    ventana.setWindowTitle("Actualizando")
    ventana.setWindowFlags(
        Qt.WindowStaysOnTopHint | Qt.CustomizeWindowHint | Qt.WindowTitleHint
    )
    ventana.setFixedSize(380, 100)

    etiqueta = QLabel(texto)
    etiqueta.setAlignment(Qt.AlignCenter)
    barra = QProgressBar()
    barra.setRange(0, 0)
    barra.setTextVisible(False)

    layout = QVBoxLayout(ventana)
    layout.addWidget(etiqueta)
    layout.addWidget(barra)

    ventana.show()
    QApplication.processEvents()
    return ventana

def _copiar_con_aviso(origen: str, destino: str) -> None:
    """Copia en un hilo para que la ventana no se congele."""
    errores = []

    def tarea():
        try:
            shutil.copy2(origen, destino)
        except Exception as e:
            errores.append(e)

    hilo = threading.Thread(target=tarea, daemon=True)
    hilo.start()
    while hilo.is_alive():
        QApplication.processEvents()
        time.sleep(0.05)
    if errores:
        raise errores[0]
    
def buscar_actualizacion():
    """Si la versión de la red es diferente, cierra el programa y se actualiza."""
    if not getattr(sys, "frozen", False):
        return
    ventana = None
    try:
        exe_actual = sys.executable
        if not os.path.exists(EXE_RED):
            return
        if version_exe(EXE_RED) == version_exe(exe_actual):
            return

        ventana = _mostrar_aviso(
            "Hay una nueva versión disponible.\n"
            "Actualizando, la aplicación se abrirá sola..."
        )

        exe_nuevo = os.path.join(tempfile.gettempdir(), "generar_ticket_nuevo.exe")
        _copiar_con_aviso(EXE_RED, exe_nuevo)

        bat = os.path.join(tempfile.gettempdir(), "actualizar_ticket.bat")
        with open(bat, "w") as f:
            f.write(f"""@echo off
:esperar
ping 127.0.0.1 -n 2 >nul
move /y "{exe_nuevo}" "{exe_actual}" >nul 2>&1
if errorlevel 1 goto esperar
start "" "{exe_actual}"
del "%~f0"
""")

        entorno = os.environ.copy()
        entorno["PYINSTALLER_RESET_ENVIRONMENT"] = "1"
        subprocess.Popen(
            ["cmd", "/c", bat],
            creationflags=subprocess.CREATE_NO_WINDOW,
            env=entorno,
        )
        ventana.close()
        QApplication.processEvents()
        sys.exit(0)
    except SystemExit:
        raise
    except Exception:
        logging.exception("Error al buscar actualización")
        if ventana is not None:
            ventana.close()  # si falló, quita el aviso y sigue con la versión actual

def main(app: QApplication):
    app.setApplicationDisplayName("Etiquetas")

    # Icono global de la aplicación.
    base_dir = _obtener_directorio_base()
    icon_path = os.path.join(
        base_dir, "assets", "icons", "icons", "cialtaicono.ico"
    )
    app.setWindowIcon(QIcon(icon_path))

    controlador = ControladorApp()

    sys.exit(app.exec())
 
    
if __name__ == "__main__":
    configurar_logging()
    app = QApplication(sys.argv)   # se crea una sola vez y se mantiene viva
    buscar_actualizacion()
    main(app)