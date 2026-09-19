import logging
import random
import re
import socket
from typing import Callable, Optional
import os
from PySide6.QtCore import QObject, QThread, QTimer, Signal
from repositories.configuracion_repository import obtener_puerto_com
from models.database import obtener_conexion
try:
    import serial
    from serial.tools import list_ports

except ImportError:
    serial = None
    list_ports = None


logger = logging.getLogger(__name__)


# ======================================================================
# CONFIGURACIÓN
# ======================================================================
BAUDIOS = 9600

# Puerto fijo de producción. Confirma este valor en el Administrador de dispositivos.
COM_BASCULA_FALLBACK = "COM5"

# Consulta de configuración del puerto por equipo.
CODIGO_PROCESO_DEFAULT = socket.gethostname()

# En producción debe permanecer en False para nunca imprimir pesos aleatorios.
MODO_PRUEBA = False

INTERVALO_MODO_PRUEBA_MS = 2000

# La báscula NO transmite sola: hay que pedirle el peso enviando este
# comando (confirmado con HyperTerminal: se escribe "P" + Enter y ella
# responde con la línea del peso). Si en algún momento deja de
# responder, probar con b"P\r" o b"P\n" en vez de b"P\r\n".
COMANDO_SOLICITUD_PESO = b"P\r\n"

# Pausa entre cada solicitud de peso durante la lectura continua.
# Más bajo = más "tiempo real", pero satura más la báscula/puerto.
INTERVALO_POLL_MS = 400

# Cuántas líneas se leen de cada puerto candidato antes de descartarlo
# durante la búsqueda automática.
INTENTOS_LECTURA_BUSQUEDA = 5

# Timeout (segundos) usado solo durante la búsqueda automática, para no
# quedarse esperando indefinidamente en un puerto que no es la báscula.
TIMEOUT_BUSQUEDA_S = 2

INTERVALO_RECONEXION_MS = 5000
# ======================================================================
# PARSEO DE LA TRAMA
# ======================================================================

_PATRON_PESO = re.compile(
    r"([-+]?\d+(?:\.\d+)?)\s*kg",
    re.IGNORECASE,
)


def _extraer_peso(linea: str) -> Optional[float]:
    """
    Extrae el peso de una línea recibida desde la báscula.

    Retorna:
        float: peso encontrado.
        None: si la línea no contiene un peso válido.
    """

    if not linea:
        return None

    coincidencia = _PATRON_PESO.search(linea)

    if not coincidencia:
        return None

    try:
        return float(coincidencia.group(1))

    except (TypeError, ValueError):
        return None


# ======================================================================
# BÚSQUEDA AUTOMÁTICA DE LA BÁSCULA
# ======================================================================

def _buscar_puerto_bascula() -> Optional[str]:
    """
    Recorre TODOS los puertos serie disponibles en el sistema y prueba
    cada uno, leyendo unas líneas para ver si responde con una trama de
    peso reconocible (número + "kg"). Devuelve el primer puerto donde
    se detecte una báscula, o None si no se encuentra ninguna.

    Al no depender de un nombre de puerto fijo, esto sigue funcionando
    aunque Windows le asigne un número de COM distinto (como pasó antes
    de COM4 a COM6).
    """

    if serial is None or list_ports is None:
        logger.error("PySerial no está instalado.")
        return None

    puertos_disponibles = list_ports.comports()

    if not puertos_disponibles:
        logger.warning("No se detectó ningún puerto serie disponible.")
        return None

    for info_puerto in puertos_disponibles:
        nombre_puerto = info_puerto.device

        logger.info(
            "Probando báscula en %s (%s)...",
            nombre_puerto,
            info_puerto.description,
        )

        try:
            with serial.Serial(
                port=nombre_puerto,
                baudrate=BAUDIOS,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=TIMEOUT_BUSQUEDA_S,
            ) as puerto:

                logger.info(
                    "Puerto %s abierto correctamente.",
                    nombre_puerto,
                )

                for numero in range(INTENTOS_LECTURA_BUSQUEDA):

                    try:
                        puerto.reset_input_buffer()
                        puerto.write(COMANDO_SOLICITUD_PESO)
                        puerto.flush()
                    except Exception as exc:
                        logger.debug(
                            "No se pudo enviar el comando a %s: %s",
                            nombre_puerto,
                            exc,
                        )
                        break

                    bruto = puerto.readline()

                    logger.debug(
                        "Lectura #%d desde %s: %r",
                        numero + 1,
                        nombre_puerto,
                        bruto,
                    )

                    if not bruto:
                        continue

                    linea = bruto.decode(
                        "ascii",
                        errors="ignore",
                    ).strip()

                    if not linea:
                        continue

                    peso = _extraer_peso(linea)

                    if peso is not None:
                        logger.info(
                            "Báscula encontrada en %s: %.3f kg",
                            nombre_puerto,
                            peso,
                        )
                        return nombre_puerto

        except Exception as exc:
            # No es la báscula, o el puerto está ocupado por otra cosa
            # (mouse serial, módem virtual, etc.) — seguimos probando
            # con el siguiente puerto de la lista.
            logger.debug(
                "Descartado %s: %s",
                nombre_puerto,
                exc,
            )
            continue

    logger.warning(
        "No fue posible detectar la báscula en ningún puerto disponible."
    )

    return None


# ======================================================================
# ERROR PERSONALIZADO
# ======================================================================

class BasculaConexionError(Exception):
    """
    Error relacionado con la conexión de la báscula.
    """

    pass


# ======================================================================
# HILO DE LECTURA DEL PUERTO SERIE
# ======================================================================

class _HiloLecturaBascula(QThread):
    """
    Hilo encargado de leer continuamente la báscula real.

    Se ejecuta separado de la interfaz para evitar congelamientos.
    """

    peso_leido = Signal(float)

    error_conexion = Signal(str)

    def __init__(
        self,
        puerto: str,
        baudios: int = BAUDIOS,
        parent: Optional[QObject] = None,
    ):
        super().__init__(parent)

        self._puerto_nombre = puerto
        self._baudios = baudios

        self._detener = False

        self._puerto = None

    # ------------------------------------------------------------------
    # EJECUCIÓN DEL HILO
    # ------------------------------------------------------------------

    def run(self) -> None:

        if serial is None:

            self.error_conexion.emit(
                "PySerial no está instalado."
            )

            return

        try:

            self._puerto = serial.Serial(
                port=self._puerto_nombre,
                baudrate=self._baudios,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,

                # Usamos timeout para que el hilo pueda comprobar
                # periódicamente si debe detenerse.
                timeout=1,
            )

            logger.info(
                "Puerto de báscula abierto correctamente: %s",
                self._puerto_nombre,
            )

        except (
            serial.SerialException,
            PermissionError,
            OSError,
        ) as exc:

            self.error_conexion.emit(
                str(exc)
            )

            return

        try:

            while not self._detener:

                try:
                    self._puerto.reset_input_buffer()
                    self._puerto.write(COMANDO_SOLICITUD_PESO)
                    self._puerto.flush()

                    bruto = self._puerto.readline()

                except (
                    serial.SerialException,
                    OSError,
                ) as exc:

                    if not self._detener:

                        self.error_conexion.emit(
                            str(exc)
                        )

                    break

                if self._detener:
                    break

                if bruto:

                    linea = bruto.decode(
                        "ascii",
                        errors="ignore",
                    ).strip()

                    if linea:

                        logger.debug(
                            "Lectura báscula [%s]: %r",
                            self._puerto_nombre,
                            linea,
                        )

                        peso = _extraer_peso(linea)

                        if peso is not None:
                            self.peso_leido.emit(
                                peso
                            )

                # Pausa breve antes de la siguiente solicitud, para no
                # saturar la báscula con comandos seguidos.
                self.msleep(INTERVALO_POLL_MS)

        finally:

            self._cerrar_puerto()

            logger.info(
                "Hilo de báscula detenido: %s",
                self._puerto_nombre,
            )

    # ------------------------------------------------------------------
    # CERRAR PUERTO
    # ------------------------------------------------------------------

    def _cerrar_puerto(self) -> None:

        if self._puerto is None:
            return

        try:

            if self._puerto.is_open:
                self._puerto.close()

        except Exception as exc:

            logger.debug(
                "Error cerrando puerto de báscula: %s",
                exc,
            )

        finally:

            self._puerto = None

    # ------------------------------------------------------------------
    # DETENER
    # ------------------------------------------------------------------

    def detener(self) -> None:
        """
        Solicita la detención del hilo y espera a que termine.
        """

        self._detener = True

        # Cerrar el puerto ayuda a desbloquear readline().
        self._cerrar_puerto()

        if self.isRunning():

            self.wait(2000)


# ======================================================================
# SERVICIO PRINCIPAL
# ======================================================================

class BasculaService(QObject):
    """
    Servicio central de la báscula.

    Estados (self.modo):

        None
            Servicio detenido.

        "real"
            Conectado a una báscula real.

        "prueba"
            Generando pesos aleatorios mediante QTimer.
    """

    # ------------------------------------------------------------------
    # SEÑALES
    # ------------------------------------------------------------------

    peso_actualizado = Signal(float)

    error_bascula = Signal(str)

    # ------------------------------------------------------------------
    # CONSTRUCTOR
    # ------------------------------------------------------------------

    def __init__(self, obtener_conexion: Optional[Callable] = None):
        super().__init__()

        # Función inyectada desde la aplicación para obtener la conexión SQL.
        # Ejemplo: BasculaService(obtener_conexion=_crear_conexion)
        self._obtener_conexion = obtener_conexion

        self._ultimo_peso: Optional[float] = None

        self._modo: Optional[str] = None
        
        self._timer_prueba: Optional[QTimer] = None

        self._hilo: Optional[_HiloLecturaBascula] = None

        self._timer_prueba: Optional[QTimer] = None
        
         # Nuevo: control de reconexión automática.
        self._timer_reconexion: Optional[QTimer] = None
        self._desconexion_manual = False

    # ==================================================================
    # PROPIEDADES
    # ==================================================================

    @property
    def modo(self) -> Optional[str]:
        """
        Retorna el modo actual:

            "real"
            "prueba"
            None
        """

        return self._modo

    @property
    def esta_activo(self) -> bool:
        """
        Indica si el servicio está activo.
        """

        return self._modo is not None

    # ==================================================================
    # INICIAR
    # ==================================================================
    def _obtener_puerto_configurado(self) -> str:
        """
        Obtiene el puerto configurado en BASICAS para este equipo,
        delegando la consulta al repositorio.

        Si la consulta falla o no devuelve información, se utiliza
        COM_BASCULA_FALLBACK como respaldo controlado.
        """

        puerto = obtener_puerto_com(
            obtener_conexion=self._obtener_conexion,
            codigo_proceso=CODIGO_PROCESO_DEFAULT,
        )

        print(f"[BASCULA] Equipo: {CODIGO_PROCESO_DEFAULT} -> puerto obtenido de BASICAS: {puerto}")

        if puerto is None:
            mensaje = (
                f"No se pudo consultar el puerto configurado en BASICAS. "
                f"Se intentará {COM_BASCULA_FALLBACK}."
            )
            logger.warning(mensaje)
            print(f"[BASCULA] {mensaje}")
            self.error_bascula.emit(mensaje)
            return COM_BASCULA_FALLBACK

        return puerto

    def iniciar(self) -> None:
        if self._modo is not None:
            logger.debug("La báscula ya está activa en modo: %s", self._modo)
            return

        # Estamos intentando activamente: no es una desconexión "dejada así".
        self._desconexion_manual = False
        self._detener_timer_reconexion()

        if MODO_PRUEBA:
            mensaje = "Modo de prueba activado por configuración."
            logger.warning(mensaje)
            self.error_bascula.emit(mensaje)
            self._activar_modo_prueba()
            return

        if serial is None:
            mensaje = "PySerial no está instalado. No se iniciará la báscula."
            logger.error(mensaje)
            self.error_bascula.emit(mensaje)
            return

        puerto_bascula = self._obtener_puerto_configurado()

        self._hilo = _HiloLecturaBascula(
            puerto=puerto_bascula,
            baudios=BAUDIOS,
            parent=self,
        )

        self._hilo.peso_leido.connect(self._on_peso_leido)
        self._hilo.error_conexion.connect(self._on_error_conexion)
        self._hilo.finished.connect(self._on_hilo_finalizado)

        self._modo = "real"
        self._hilo.start()

        logger.info("Intentando iniciar báscula real en puerto fijo: %s", puerto_bascula)
        
    def _programar_reconexion(self) -> None:
        if self._timer_reconexion is None:
            self._timer_reconexion = QTimer(self)
            self._timer_reconexion.setInterval(INTERVALO_RECONEXION_MS)
            self._timer_reconexion.timeout.connect(self._intentar_reconectar)

        if not self._timer_reconexion.isActive():
            self._timer_reconexion.start()
            logger.info(
                "Reintentando conexión con la báscula cada %d ms.",
                INTERVALO_RECONEXION_MS,
            )


    def _intentar_reconectar(self) -> None:
        if self._desconexion_manual or self._modo is not None:
            self._detener_timer_reconexion()
            return

        logger.info("Intentando reconectar la báscula...")
        self.iniciar()


    def _detener_timer_reconexion(self) -> None:
        if self._timer_reconexion is not None and self._timer_reconexion.isActive():
            self._timer_reconexion.stop()

    # ==================================================================
    # LECTURA REAL
    # ==================================================================

    def _on_peso_leido(
        self,
        peso:Optional[float],
    ) -> None:
        """
        Recibe una lectura proveniente de la báscula real.
        """

        # Protección adicional.
        if self._modo != "real":
            return

        self._ultimo_peso = round(
            peso,
            3,
        )

        logger.debug(
            "Peso real recibido: %.3f kg",
            self._ultimo_peso,
        )

        self.peso_actualizado.emit(
            self._ultimo_peso
        )

    # ==================================================================
    # ERROR DE CONEXIÓN
    # ==================================================================

    def _on_error_conexion(self, mensaje: str) -> None:
        logger.error("No se pudo conectar con la báscula: %s", mensaje)

        mensaje_usuario = f"Báscula desconectada: {mensaje}"
        self.error_bascula.emit(mensaje_usuario)

        self._modo = None
        self._ultimo_peso = None

        # Refleja la desconexión en la UI: el peso deja de ser válido.
        self.peso_actualizado.emit(0.0)

        if MODO_PRUEBA:
            self._activar_modo_prueba()
            return

        # Reintenta solo si nadie salió intencionalmente de la pantalla.
        if not self._desconexion_manual:
            self._programar_reconexion()

    # ==================================================================
    # FINALIZACIÓN DEL HILO
    # ==================================================================

    def _on_hilo_finalizado(self) -> None:
        """
        Limpia la referencia al hilo cuando termina.
        """

        logger.debug(
            "Hilo de báscula finalizado."
        )

        self._hilo = None

    # ==================================================================
    # MODO PRUEBA
    # ==================================================================

    def _activar_modo_prueba(self) -> None:
        """
        Activa el modo de prueba.

        El QTimer permanece activo mientras la pantalla utilice
        el servicio.
        """

        self._modo = "prueba"

        # Crear timer solamente una vez.
        if self._timer_prueba is None:

            self._timer_prueba = QTimer(
                self
            )

            self._timer_prueba.setInterval(
                INTERVALO_MODO_PRUEBA_MS
            )

            self._timer_prueba.timeout.connect(
                self._generar_peso_prueba
            )

        # Evitar iniciar dos veces el mismo timer.
        if not self._timer_prueba.isActive():

            self._timer_prueba.start()

        # Generar inmediatamente el primer peso.
        self._generar_peso_prueba()

        logger.warning(
            "MODO PRUEBA activado. "
            "Intervalo: %d ms",
            INTERVALO_MODO_PRUEBA_MS,
        )

    def _generar_peso_prueba(self) -> None:
        """
        Genera un peso aleatorio.

        IMPORTANTE:
        Si el servicio ya fue detenido, no genera nada.
        """

        # Esta condición evita que un timeout pendiente genere
        # pesos después de salir de Ficha Técnica.
        if self._modo != "prueba":
            return

        self._ultimo_peso = round(
            random.uniform(
                0.5,
                8.0,
            ),
            3,
        )

        logger.warning(
            "MODO PRUEBA: peso generado = %.3f kg",
            self._ultimo_peso,
        )

        self.peso_actualizado.emit(
            self._ultimo_peso
        )

    # ==================================================================
    # API PÚBLICA
    # ==================================================================

    def obtener_peso_neto(
        self,
        forzar_nuevo: bool = False,
    ) -> float:
        """
        Devuelve el peso neto actual.

        Si el servicio no está iniciado, se inicia automáticamente.

        `forzar_nuevo` se mantiene para compatibilidad con el código
        existente.

        En modo prueba, si se solicita explícitamente un nuevo valor,
        se genera inmediatamente uno.
        """

        if self._modo is None:

            self.iniciar()

        if (
            forzar_nuevo
            and self._modo == "prueba"
        ):

            self._generar_peso_prueba()

        if self._ultimo_peso is None:

            return 0.0

        return self._ultimo_peso

    # ------------------------------------------------------------------

    def obtener_ultimo_peso(self) -> Optional[float]:
        """
        Devuelve el último peso disponible.

        A diferencia de obtener_peso_neto(), NO inicia la báscula
        y NO genera un nuevo peso.

        Puede devolver None.
        """

        return self._ultimo_peso

    # ------------------------------------------------------------------

    def reiniciar(self) -> None:
        """
        Limpia únicamente el peso almacenado.

        No detiene la báscula ni el QTimer.
        """

        self._ultimo_peso = None

        logger.debug(
            "Último peso reiniciado."
        )

    # ==================================================================
    # DETENER COMPLETAMENTE
    # ==================================================================

    def detener(self) -> None:
        logger.info("Deteniendo servicio de báscula...")

        self._desconexion_manual = True
        self._detener_timer_reconexion()

        if self._timer_prueba is not None:
            if self._timer_prueba.isActive():
                self._timer_prueba.stop()
                logger.info("QTimer de modo prueba detenido.")

        if self._hilo is not None:
            hilo = self._hilo
            self._hilo = None
            hilo.detener()
            logger.info("Hilo de báscula real detenido.")

        self._modo = None

        self._ultimo_peso = None

        logger.info(
            "Servicio de báscula detenido completamente."
        )


# ======================================================================
# INSTANCIA ÚNICA
# ======================================================================

bascula_service = BasculaService(obtener_conexion=obtener_conexion)