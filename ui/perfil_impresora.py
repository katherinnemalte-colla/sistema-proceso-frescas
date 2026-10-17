"""
Los perfiles se guardan en un JSON LOCAL (por usuario de Windows en cada
computador):  %%\\etiquetasMk\\perfiles_impresoras.json
Todos los errores de lectura/validación se registran en el log y se
reemplazan por valores seguros: un JSON dañado nunca debe tumbar la app.
"""

import json
import logging
import math
import os
import re
import shutil
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

# ----------------------------------------------------------------------
# Geometría fija de la etiqueta
# ----------------------------------------------------------------------
ANCHO_MM = 100            # el ancho es siempre 100 mm
ALTO_MM_MIN = 30          # límites del alto: NO se tocan
ALTO_MM_MAX = 50
ALTO_MM_DEFECTO = 30

DPI_ESPERADO = 203        # el programa está calibrado para 203 DPI
DOTS_POR_MM = 8           # 203 DPI ≈ 8 puntos por mm

# ----------------------------------------------------------------------
# Límites del ajuste
# ----------------------------------------------------------------------
PERDIDA_MM_MAX = 6.0      # máximo que se admite por borde
PASO_MM = 0.5             # los valores se redondean a pasos de 0,5 mm
ESCALA_AVISO = 0.85       # por debajo: advertencia (letras más pequeñas)
ESCALA_MINIMA = 0.65      # por debajo: no se permite guardar ni imprimir


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
    n = _numero(valor, 0.0, 0.0, PERDIDA_MM_MAX, nombre)
    return round(n / PASO_MM) * PASO_MM


@dataclass(frozen=True)
class PerfilImpresora:
    """
    alto_mm        : alto de la etiqueta (30 a 50)
    perdida_*_mm   : lo que se CORTA en ese borde, en mm (0 = no se corta)
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
        (x, y, escala) para dibujar el contenido dentro de la zona que sí
        sale. x e y están en puntos de impresora; la escala (<= 1) es
        relativa a la etiqueta completa y es la misma en ancho y alto.
        """
        p = self.validado()
        ancho_dots = ANCHO_MM * DOTS_POR_MM
        alto_dots = p.alto_mm * DOTS_POR_MM

        izq = round(p.perdida_izq_mm * DOTS_POR_MM)
        arr = round(p.perdida_arr_mm * DOTS_POR_MM)
        der = round(p.perdida_der_mm * DOTS_POR_MM)
        aba = round(p.perdida_aba_mm * DOTS_POR_MM)

        w = ancho_dots - izq - der      # ancho que sí sale
        h = alto_dots - arr - aba       # alto que sí sale
        escala = min(w / ancho_dots, h / alto_dots)

        # Centrado dentro de la zona que sí sale.
        x = izq + (w - ancho_dots * escala) / 2
        y = arr + (h - alto_dots * escala) / 2
        return x, y, escala

    def escala(self) -> float:
        return self.colocacion()[2]


def nivel_escala(escala: float) -> str:
    """'ok', 'aviso' (letras más pequeñas) o 'bloqueado' (demasiado reducido)."""
    if escala < ESCALA_MINIMA:
        return "bloqueado"
    if escala < ESCALA_AVISO:
        return "aviso"
    return "ok"


# ----------------------------------------------------------------------
# Almacenamiento (JSON local)
# ----------------------------------------------------------------------

def ruta_perfiles() -> Path:
    base = os.environ.get("LOCALAPPDATA") or str(Path.home())
    return Path(base) / "etiquetasMk" / "perfiles_impresoras.json"


def _leer_todo() -> dict:
    """Devuelve {nombre_impresora: {...}}; {} si no existe o está dañado."""
    ruta = ruta_perfiles()
    if not ruta.exists():
        return {}

    try:
        with open(ruta, encoding="utf-8") as f:
            contenido = json.load(f)
        impresoras = contenido.get("impresoras", {})
        if not isinstance(impresoras, dict):
            raise ValueError("'impresoras' no es un diccionario")
        return impresoras
    except (OSError, ValueError, AttributeError) as exc:
        logger.error("No se pudo leer %s (%s); se ignoran los perfiles guardados", ruta, exc)
        try:  # copia del archivo dañado, para no perderlo al guardar uno nuevo
            shutil.copy2(ruta, ruta.with_suffix(".json.dañado"))
        except OSError:
            pass
        return {}


def cargar_perfil(nombre_impresora: str) -> Optional[PerfilImpresora]:
    """Perfil guardado de esa impresora, o None si no tiene."""
    crudo = _leer_todo().get(nombre_impresora)
    if crudo is None:
        return None
    if not isinstance(crudo, dict):
        logger.error("Perfil de %r con formato inválido; se ignora", nombre_impresora)
        return None

    return PerfilImpresora(
        alto_mm=crudo.get("alto_mm", ALTO_MM_DEFECTO),
        perdida_izq_mm=crudo.get("perdida_izq_mm", 0.0),
        perdida_arr_mm=crudo.get("perdida_arr_mm", 0.0),
        perdida_der_mm=crudo.get("perdida_der_mm", 0.0),
        perdida_aba_mm=crudo.get("perdida_aba_mm", 0.0),
    ).validado()


def guardar_perfil(nombre_impresora: str, perfil: PerfilImpresora) -> None:
    """
    Guarda el perfil (validado). Escribe a un archivo temporal y lo
    reemplaza al final, así un corte a mitad de escritura no daña el JSON.
    Puede lanzar OSError: quien llama debe capturarlo y avisar al usuario.
    """
    perfil = perfil.validado()
    impresoras = _leer_todo()
    impresoras[nombre_impresora] = asdict(perfil)

    ruta = ruta_perfiles()
    ruta.parent.mkdir(parents=True, exist_ok=True)

    fd, tmp = tempfile.mkstemp(dir=ruta.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump({"version": 1, "impresoras": impresoras}, f,
                      indent=2, ensure_ascii=False)
        os.replace(tmp, ruta)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise

    logger.info("Perfil guardado para %r: %s", nombre_impresora, asdict(perfil))


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