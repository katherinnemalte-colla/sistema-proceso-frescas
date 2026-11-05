import logging
import os
import shutil
import subprocess
import sys
import tempfile
from utils.inactividad import InactivityWatcher
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
from utils.rutas import ruta_recurso
import threading
import time
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QProgressBar, QVBoxLayout, QWidget

EXE_RED = r"\\200.150.50.134\publico\Analista\etiquetasMk\etiquetas_v2.exe"
RUTA_ICONOS = ruta_recurso(os.path.join("assets", "icons"))

def _obtener_directorio_base() -> str:
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


class ControladorApp:

    def __init__(self):
        self.ventana_fondo = None
        self.ventana_app = None
        self.usuario = None

        self.watcher = InactivityWatcher(minutes=15)
        self.watcher.timeout.connect(self._cerrar_sesion)

        self._mostrar_fondo_y_login()

    def _mostrar_fondo_y_login(self):
        self.ventana_fondo = VentanaFondo()
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
        self.usuario = usuario
        self.ventana_fondo.close()

        self.ventana_app = VentanaApp(usuario, obtener_conexion)
        self.ventana_app.setWindowTitle(
            f"Etiquetas 2 en 1  Usuario: {usuario.nombre_usuario}  Entorno : {DB_SERVER}" +""
        )
        self.ventana_app.show()
        QTimer.singleShot(0, self.ventana_app.showMaximized)

        self.watcher.start()   # empieza a contar inactividad

    def _cerrar_sesion(self):
        self.watcher.stop()
        self.usuario = None

        # Cerrar diálogos abiertos y la ventana principal
        for w in QApplication.topLevelWidgets():
            if w is not self.ventana_app and w.isVisible():
                w.close()
        if self.ventana_app is not None:
            self.ventana_app.close()
            self.ventana_app.deleteLater()
            self.ventana_app = None

        self._mostrar_fondo_y_login()

def version_exe(ruta):
    """Versión del archivo como tupla, ej. (1, 0, 4, 0)."""
    try:
        info = win32api.GetFileVersionInfo(str(ruta), "\\")
        ms, ls = info["FileVersionMS"], info["FileVersionLS"]
        return (ms >> 16, ms & 0xFFFF, ls >> 16, ls & 0xFFFF)
    except Exception:
        return (0, 0, 0, 0)  # exe sin versión: se considera el más viejo
def _mostrar_progreso(texto: str = "Actualizando Etiquetas...") -> tuple[QWidget, QProgressBar]:
    """Ventana con título y una barra verde gruesa."""
    ventana = QWidget()
    ventana.setWindowTitle("Actualizando Etiquetas")
    ventana.setWindowFlags(
        Qt.Window
        | Qt.CustomizeWindowHint
        | Qt.WindowTitleHint        # con título, sin botón de cerrar
        | Qt.WindowStaysOnTopHint
    )
    ventana.setFixedSize(440, 130)

    etiqueta = QLabel(texto)
    etiqueta.setAlignment(Qt.AlignCenter)
    etiqueta.setStyleSheet("font-size: 15px;")

    barra = QProgressBar()
    barra.setRange(0, 100)
    barra.setFixedHeight(30)        # más gruesa
    barra.setAlignment(Qt.AlignCenter)
    barra.setStyleSheet("""
        QProgressBar {
            border: 1px solid #A8D5A8;
            border-radius: 8px;
            background: #EEF7EE;
            color: #2E5E2E;
            font-weight: bold;
        }
        QProgressBar::chunk {
            background-color: #8FD18F;   /* verde claro */
            border-radius: 7px;
        }
    """)

    layout = QVBoxLayout(ventana)
    layout.setContentsMargins(20, 20, 20, 20)
    layout.addWidget(etiqueta)
    layout.addWidget(barra)

    # Centrar en la pantalla
    centro = QApplication.primaryScreen().availableGeometry().center()
    marco = ventana.frameGeometry()
    marco.moveCenter(centro)
    ventana.move(marco.topLeft())

    ventana.show()
    QApplication.processEvents()
    return ventana, barra

def _copiar_con_progreso(origen: str, destino: str, barra: QProgressBar) -> None:
    """Copia por bloques en un hilo y mueve la barra según lo copiado."""
    total = os.path.getsize(origen)
    estado = {"copiado": 0, "error": None}

    def tarea():
        try:
            with open(origen, "rb") as src, open(destino, "wb") as dst:
                while True:
                    bloque = src.read(1024 * 1024)   # 1 MB por vez
                    if not bloque:
                        break
                    dst.write(bloque)
                    estado["copiado"] += len(bloque)
        except Exception as e:
            estado["error"] = e

    hilo = threading.Thread(target=tarea, daemon=True)
    hilo.start()
    while hilo.is_alive():
        barra.setValue(int(estado["copiado"] * 100 / total))
        QApplication.processEvents()
        time.sleep(0.03)

    if estado["error"]:
        raise estado["error"]
    barra.setValue(100)
    QApplication.processEvents()

    
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
        ventana, barra = _mostrar_progreso(
            "Hay una nueva versión. Actualizando, el programa se abrirá solo..."
        )

        exe_nuevo = os.path.join(tempfile.gettempdir(), "generar_ticket_nuevo.exe")
        _copiar_con_progreso(EXE_RED, exe_nuevo, barra)

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
            ventana.close()

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