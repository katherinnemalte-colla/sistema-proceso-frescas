"""
Perfiles de impresora (ajuste de la etiqueta por desplazamiento).

Los perfiles se guardan en la BD, tabla dbo.basicas, una fila por
equipo (hostname de Windows) + impresora:

    nombr_grup = GRUPO_PERFIL      eleme_grup = hostname
    codig_elem = nombre impresora  valor1 = alto_mm
    valor2 = izquierda             valor3 = arriba
    valor4c = derecha (texto)      valor5c = abajo (texto)

Ajuste por DESPLAZAMIENTO PURO: el contenido nunca se reduce ni se
deforma (escala siempre 1). Cada valor, en mm, mueve el contenido
desde ese borde:
    positivo -> empuja el contenido hacia adentro (se aleja de ese borde)
    negativo -> lo acerca a ese borde (si se pasa, se corta)
Lados opuestos se compensan: x = izq - der ; y = arr - aba.

Todos los errores de lectura/validación se registran en el log y se
reemplazan por valores seguros: un problema con la BD o con un dato
dañado nunca debe tumbar la app.
"""

import logging
import math
import re
import socket
from dataclasses import dataclass
from typing import Optional, Tuple

from config.settings import DB_DATABASE
from models.database import obtener_conexion

logger = logging.getLogger(__name__)

DB_PRODUCTOS = DB_DATABASE
GRUPO_PERFIL = "PERFIL_IMPRESORA"
DESCRIPCION_PERFIL = "Perfil de impresora (ajuste de etiqueta)"

# ----------------------------------------------------------------------
# Geometría fija de la etiqueta
# ----------------------------------------------------------------------
ANCHO_MM = 100             # el ancho es siempre 100 mm
ALTO_MM_MIN = 52          # límites del alto: NO se tocan
ALTO_MM_MAX = 55
ALTO_MM_DEFECTO = 45

DPI_ESPERADO = 203        # el programa está calibrado para 203 DPI
DOTS_POR_MM = 8           # 203 DPI ≈ 8 puntos por mm

# ----------------------------------------------------------------------
# Límites del ajuste
# ----------------------------------------------------------------------
PERDIDA_MM_MAX = 6.0      # máximo desplazamiento por borde (+ o -)
PASO_MM = 0.5             # los valores se redondean a pasos de 0,5 mm
ESCALA_AVISO = 0.85       # (sin uso con desplazamiento: la escala es 1)
ESCALA_MINIMA = 0.65      # (sin uso con desplazamiento: la escala es 1)


# ----------------------------------------------------------------------
# Validación
# ----------------------------------------------------------------------

def _numero(valor, defecto: float, minimo: float, maximo: float, nombre: str) -> float:
    """Convierte a número dentro de [minimo, maximo]; nunca lanza error."""
    try:
        n = float(valor)
        if math.isnan(n) or math.isinf(n):
            raise ValueError("no es un número finito")
    except (TypeError, ValueError):
        logger.warning("Perfil: %s=%r no es válido; se usa %s", nombre, valor, defecto)
        return float(defecto)

    limitado = max(minimo, min(maximo, n))
    if limitado != n:
        logger.warning(
            "Perfil: %s=%s fuera de rango [%s, %s]; se usa %s",
            nombre, n, minimo, maximo, limitado,
        )
    return limitado


def _borde(valor, nombre: str) -> float:
    """Desplazamiento de un borde: de -PERDIDA_MM_MAX a +PERDIDA_MM_MAX."""
    n = _numero(valor, 0.0, -PERDIDA_MM_MAX, PERDIDA_MM_MAX, nombre)
    return round(n / PASO_MM) * PASO_MM + 0.0       # "+ 0.0" evita -0.0


@dataclass(frozen=True)
class PerfilImpresora:
    """
    alto_mm        : alto de la etiqueta (30 a 50)
    perdida_*_mm   : desplazamiento desde ese borde, en mm
                     (+ aleja el contenido del borde, - lo acerca; 0 = sin ajuste)
    """
    alto_mm: int = ALTO_MM_DEFECTO
    perdida_izq_mm: float = 0.0
    perdida_arr_mm: float = 0.0
    perdida_der_mm: float = 0.0
    perdida_aba_mm: float = 0.0

    def validado(self) -> "PerfilImpresora":
        """Copia con todos los valores dentro de los límites."""
        alto = _numero(self.alto_mm, ALTO_MM_DEFECTO, ALTO_MM_MIN, ALTO_MM_MAX, "alto_mm")
        return PerfilImpresora(
            alto_mm=int(round(alto)),
            perdida_izq_mm=_borde(self.perdida_izq_mm, "perdida_izq_mm"),
            perdida_arr_mm=_borde(self.perdida_arr_mm, "perdida_arr_mm"),
            perdida_der_mm=_borde(self.perdida_der_mm, "perdida_der_mm"),
            perdida_aba_mm=_borde(self.perdida_aba_mm, "perdida_aba_mm"),
        )

    def colocacion(self) -> Tuple[float, float, float]:
        """
        (x, y, escala) para dibujar el contenido. x e y son el
        desplazamiento en puntos de impresora respecto a la etiqueta
        completa (pueden ser negativos); la escala es SIEMPRE 1.0:
        el contenido no se reduce ni se deforma, solo se mueve y, si se
        pasa del borde, se corta.
        """
        p = self.validado()
        izq = round(p.perdida_izq_mm * DOTS_POR_MM)
        arr = round(p.perdida_arr_mm * DOTS_POR_MM)
        der = round(p.perdida_der_mm * DOTS_POR_MM)
        aba = round(p.perdida_aba_mm * DOTS_POR_MM)

        x = float(izq - der)
        y = float(arr - aba)
        return x, y, 1.0

    def escala(self) -> float:
        return self.colocacion()[2]

    def contenido_cortado_mm(self) -> Tuple[float, float, float, float]:
        """
        (izq, arr, der, aba): mm de contenido que se pierden en cada borde
        por el desplazamiento. Útil para avisar en pantalla.
        """
        p = self.validado()
        dx = p.perdida_izq_mm - p.perdida_der_mm
        dy = p.perdida_arr_mm - p.perdida_aba_mm
        return (max(-dx, 0.0) + 0.0, max(-dy, 0.0) + 0.0,
                max(dx, 0.0) + 0.0, max(dy, 0.0) + 0.0)


def nivel_escala(escala: float) -> str:
    """'ok', 'aviso' (letras más pequeñas) o 'bloqueado' (demasiado reducido).
    Con desplazamiento puro la escala es 1, así que siempre devuelve 'ok'."""
    if escala < ESCALA_MINIMA:
        return "bloqueado"
    if escala < ESCALA_AVISO:
        return "aviso"
    return "ok"


# ----------------------------------------------------------------------
# Almacenamiento (BD: dbo.basicas)
# ----------------------------------------------------------------------

def nombre_equipo() -> str:
    return socket.gethostname()


def _texto_a_numero(valor, nombre: str) -> float:
    """valor4c / valor5c vienen como texto; si no sirve, 0.0 (sin ajuste)."""
    try:
        return float(str(valor).strip().replace(",", "."))
    except (TypeError, ValueError):
        logger.warning("Perfil: %s=%r no es numérico; se usa 0", nombre, valor)
        return 0.0


def cargar_perfil(nombre_impresora: str) -> Optional[PerfilImpresora]:
    """Perfil guardado de esta impresora en este equipo, o None si no tiene
    (o si la BD no responde: la app sigue funcionando con valores por defecto)."""
    try:
        with obtener_conexion() as conexion:
            cursor = conexion.cursor()
            cursor.execute(
                f"""
                SELECT valor1, valor2, valor3, valor4c, valor5c
                FROM [{DB_PRODUCTOS}].dbo.basicas
                WHERE nombr_grup = ? AND eleme_grup = ? AND codig_elem = ?
                """,
                GRUPO_PERFIL, nombre_equipo(), nombre_impresora,
            )
            fila = cursor.fetchone()
            cursor.close()
    except Exception:
        logger.error("No se pudo leer el perfil de %r desde la BD",
                     nombre_impresora, exc_info=True)
        return None

    if fila is None:
        return None

    return PerfilImpresora(
        alto_mm=fila.valor1,
        perdida_izq_mm=fila.valor2,
        perdida_arr_mm=fila.valor3,
        perdida_der_mm=_texto_a_numero(fila.valor4c, "perdida_der_mm"),
        perdida_aba_mm=_texto_a_numero(fila.valor5c, "perdida_aba_mm"),
    ).validado()


def guardar_perfil(nombre_impresora: str, perfil: PerfilImpresora) -> None:
    """
    Guarda el perfil (validado) en basicas: UPDATE si ya existe, INSERT si no,
    en una sola transacción. Puede lanzar errores de BD: quien llama debe
    capturarlos (except Exception) y avisar al usuario.
    """
    perfil = perfil.validado()
    equipo = nombre_equipo()
    der = f"{perfil.perdida_der_mm:g}"
    aba = f"{perfil.perdida_aba_mm:g}"

    with obtener_conexion() as conexion:
        cursor = conexion.cursor()
        try:
            cursor.execute(
                f"""
                UPDATE [{DB_PRODUCTOS}].dbo.basicas
                   SET valor1 = ?, valor2 = ?, valor3 = ?,
                       valor4c = ?, valor5c = ?, actlzcion = GETDATE()
                 WHERE nombr_grup = ? AND eleme_grup = ? AND codig_elem = ?
                """,
                perfil.alto_mm, perfil.perdida_izq_mm, perfil.perdida_arr_mm,
                der, aba, GRUPO_PERFIL, equipo, nombre_impresora,
            )
            if cursor.rowcount == 0:
                cursor.execute(
                    f"""
                    INSERT INTO [{DB_PRODUCTOS}].dbo.basicas
                        (nombr_grup, eleme_grup, codig_elem, valor1, valor2, valor3,
                         valor4c, valor5c, dscrpcion, actlzcion,
                         fecha1, fecha2, valor6Text)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, GETDATE(),
                            '1900/01/01', '1900/01/01', '')
                    """,
                    GRUPO_PERFIL, equipo, nombre_impresora,
                    perfil.alto_mm, perfil.perdida_izq_mm, perfil.perdida_arr_mm,
                    der, aba, DESCRIPCION_PERFIL,
                )
            conexion.commit()
        except Exception:
            conexion.rollback()
            raise
        finally:
            cursor.close()

    logger.info("Perfil guardado en BD para %r (%s): %s",
                nombre_impresora, equipo, perfil)


# ----------------------------------------------------------------------
# Resolución (DPI) de la impresora
# ----------------------------------------------------------------------

def detectar_dpi(nombre_impresora: str) -> Optional[int]:
    """
    Mejor esfuerzo para saber los DPI: primero lo que Windows guarda de la
    impresora y, si no sirve, el nombre ("ZDesigner ZD230-203dpi ZPL").
    Devuelve None si no se puede saber. Solo lee, no cambia nada.
    """
    try:
        import win32print

        handle = win32print.OpenPrinter(nombre_impresora)
        try:
            info = win32print.GetPrinter(handle, 2)
        finally:
            win32print.ClosePrinter(handle)

        devmode = info.get("pDevMode")
        if devmode is not None:
            calidad = int(devmode.PrintQuality)
            if 100 <= calidad <= 1200:      # valores negativos no son DPI
                return calidad
    except ImportError:
        pass                                # sin pywin32 (no es Windows)
    except Exception:
        logger.debug("No se pudo leer el DPI de %r en Windows", nombre_impresora,
                     exc_info=True)

    coincidencia = re.search(r"(\d{3})\s*dpi", nombre_impresora, re.IGNORECASE)
    if coincidencia:
        return int(coincidencia.group(1))
    return None


def dpi_es_esperado(dpi: Optional[int]) -> bool:
    """True si coincide con 203 DPI (se tolera de 200 a 208)."""
    return dpi is not None and 200 <= dpi <= 208