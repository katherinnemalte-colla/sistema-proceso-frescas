"""
Motor de impresión de etiquetas para Zebra (ZPL) y utilidades de dibujo.

Camino recomendado (independiente del driver de Windows):
    1. Dibujar la etiqueta en un QImage (ver imprimir_etiqueta_frescas).
    2. Convertirla a ZPL con imagen_a_zpl().
    3. Enviarla en modo RAW con enviar_zpl().

En modo RAW el spooler pasa los bytes tal cual a la impresora, así que el
tamaño de papel, los márgenes y el escalado configurados en Windows YA NO
influyen. Por eso la etiqueta sale igual en todos los computadores.

Velocidad, oscuridad, método de impresión y modo (rasgar/cortar) NO los
manda el programa: se configuran en la impresora (Zebra Setup Utilities o
panel) y se conservan. El programa solo manda tamaño, desplazamiento y
contenido de la etiqueta.
"""

import io
from functools import lru_cache

import qrcode
from PySide6.QtCore import QMarginsF, QRectF, QSizeF
from PySide6.QtGui import QImage, QPageLayout, QPageSize, QPainter
from PySide6.QtPrintSupport import QPrinter
import json
import socket
from datetime import datetime
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# ======================================================================
# ENVÍO DIRECTO A LA ZEBRA (ZPL / RAW)
# ======================================================================

# Por debajo de este nivel de gris (0-255) un punto se imprime en negro.
UMBRAL_NEGRO = 145

# Sensor de papel que manda el programa ("" = NO enviar ^MN y respetar lo
# configurado en la impresora). Valores: "Y" gap, "M" marca negra, "N" continuo.
MEDIO_ZEBRA = ""        # Zebra con etiquetas troqueladas: sensor de separación
MEDIO_GODEX = ""         # Godex continua: no se toca lo configurado

# Largo de la etiqueta de la Zebra para ^LL, en mm (admite decimales).
# OJO: es la distancia de una etiqueta a la siguiente (etiqueta + separación),
# NO solo los 50 mm de la etiqueta. Se lee de la etiqueta de configuración
# (imprimir_etiqueta_configuracion): "LABEL LENGTH" en puntos, dividido entre 8.
# 0 = NO enviar ^LL: la Zebra usa el largo que midió al calibrar.
ALTO_PAPEL_ZEBRA_MM = 0


def parametros_medio(nombre_impresora: str):
    """
    (medio, alto_papel_dots) según la marca de la impresora.

    Godex (papel continuo): sin ^MN y ^LL = alto de la imagen (None).
    Cualquier otra (Zebra troquelada): medio de MEDIO_ZEBRA y, si
    ALTO_PAPEL_ZEBRA_MM > 0, ese largo físico en ^LL; con 0 no se envía ^LL.
    """
    if "godex" in nombre_impresora.lower():
        return MEDIO_GODEX, None
    return MEDIO_ZEBRA, int(round(ALTO_PAPEL_ZEBRA_MM * 8))      # 8 puntos por mm


# Calidad de impresión que puede mandar el programa SOLO a la Zebra.
# None = no enviar nada (la impresora usa lo que tenga guardado; se
# configura una vez con Zebra Setup Utilities). Si se pone un número, se
# manda antes de CADA etiqueta y pisa lo configurado en la impresora.
OSCURIDAD_ZEBRA = None    # 0-30 (~SD). Ej. 15
VELOCIDAD_ZEBRA = None    # pulgadas/seg (^PR). Ej. 4 (la ZD230 llega hasta 6)


def _prefijo_calidad(nombre_impresora: str) -> str:
    """
    Comandos de oscuridad/velocidad para anteponer al ZPL. Cadena vacía si
    las constantes están en None o si la impresora es Godex. No usa ^JUS:
    no escribe en la memoria permanente de la impresora.
    """
    if "godex" in nombre_impresora.lower():
        return ""

    partes = []
    if OSCURIDAD_ZEBRA is not None:
        try:
            oscuridad = max(0, min(30, int(OSCURIDAD_ZEBRA)))
            partes.append(f"~SD{oscuridad:02d}")
        except (TypeError, ValueError):
            logger.warning("OSCURIDAD_ZEBRA=%r no es válido; no se envía",
                           OSCURIDAD_ZEBRA)
    if VELOCIDAD_ZEBRA is not None:
        try:
            velocidad = max(2, min(12, int(VELOCIDAD_ZEBRA)))
            partes.append(f"^XA^PR{velocidad}^XZ")
        except (TypeError, ValueError):
            logger.warning("VELOCIDAD_ZEBRA=%r no es válido; no se envía",
                           VELOCIDAD_ZEBRA)
    return "".join(partes)


def imagen_a_zpl(img, medio="", desplaz_x=0, desplaz_y=0, alto_papel_dots=None):
    """
    Convierte una imagen a un comando ZPL (^GFA) en blanco y negro.

    medio: tipo de sensor de la impresora.
        ""  -> no se envía ^MN (se respeta la configuración de la impresora)
        "Y" -> etiquetas con separación (gap)   [^MNY]
        "M" -> etiquetas con marca negra         [^MNM]
        "N" -> papel continuo                    [^MNN]

    alto_papel_dots: largo de la etiqueta para ^LL, en puntos.
        None -> se usa el alto de la imagen (papel continuo).
        > 0  -> largo físico (nunca menor que la imagen).
        0    -> no se envía ^LL: la impresora usa el largo calibrado.

    Comandos de la cabecera (todos son de ESTA etiqueta, no de la impresora):
        ^PW  ancho de impresión en puntos
        ^LL  largo de la etiqueta en puntos
        ^LH  origen de la etiqueta (0,0)
        ^LT  desplazamiento superior (0)
        ^PON orientación normal
    """
    ancho_total, alto_total = img.width(), img.height()   # para ^PW y ^LL
    rec_x, rec_y = max(0, -desplaz_x), max(0, -desplaz_y)
    if rec_x or rec_y:
        img = img.copy(rec_x, rec_y, ancho_total - rec_x, alto_total - rec_y)
    fo_x, fo_y = max(0, desplaz_x), max(0, desplaz_y)

    mn = f"^MN{medio}" if medio else ""
    if alto_papel_dots == 0:
        ll = ""                                    # usar el largo calibrado
    else:
        ll = f"^LL{max(alto_papel_dots or 0, alto_total)}"

    img = img.convertToFormat(QImage.Format.Format_Grayscale8)
    ancho, alto = img.width(), img.height()
    bytes_fila = (ancho + 7) // 8          # 8 puntos por byte
    stride = img.bytesPerLine()            # puede incluir relleno al final
    pixeles = bytes(img.constBits())

    datos = bytearray()
    for fila_idx in range(alto):
        inicio = fila_idx * stride
        fila = pixeles[inicio:inicio + ancho]

        # Un bit por punto (1 = negro), el punto más a la izquierda es el
        # bit más significativo. Se rellena con ceros (blanco) hasta
        # completar el último byte de la fila.
        valor = 0
        for gris in fila:
            valor = (valor << 1) | (gris < UMBRAL_NEGRO)
        valor <<= bytes_fila * 8 - ancho
        datos += valor.to_bytes(bytes_fila, "big")

    total = len(datos)
    return (
        f"^XA{mn}^PW{ancho_total}{ll}"
        f"^LH0,0^LT0^LS0^PON^PMN"
        f"^FO{fo_x},{fo_y}^GFA,{total},{total},{bytes_fila},{datos.hex().upper()}^FS"
        f"^XZ"
    )
    
def zpl_marco_prueba(ancho_dots, alto_dots, medio="Y", desplaz_x=0, desplaz_y=0):
    mn = f"^MN{medio}" if medio else ""
    return (
        f"^XA{mn}^PW{ancho_dots}^LL{alto_dots}^LH0,0"
        f"^LT{desplaz_y}^LS{desplaz_x}"
        f"^FO0,0^GB{ancho_dots},{alto_dots},4^FS^XZ"
    )

def zpl_regla_prueba(ancho_dots: int, alto_dots: int, medio: str = "Y") -> str:
    """Marcas cada 10 mm (80 puntos) arriba y a la izquierda, más el marco."""
    mn = f"^MN{medio}" if medio else ""
    marcas = ""
    for x in range(0, ancho_dots, 80):
        marcas += f"^FO{x},0^GB3,40,3^FS"       # marca vertical arriba
    for y in range(0, alto_dots, 80):
        marcas += f"^FO0,{y}^GB40,3,3^FS"       # marca horizontal a la izquierda
    return (
        f"^XA{mn}^PW{ancho_dots}^LL{alto_dots}^LH0,0^LT0"
        f"{marcas}^FO0,0^GB{ancho_dots},{alto_dots},4^FS^XZ"
    )
def enviar_zpl(nombre_impresora: str, zpl: str) -> None:
    import win32print

    prefijo = _prefijo_calidad(nombre_impresora) if zpl.lstrip().startswith("^XA") else ""
    if prefijo:
        logger.info("Calidad enviada a %r: %s", nombre_impresora, prefijo)
    datos = (prefijo + zpl).encode("ascii")
    logger.info("ENVIO ZPL impresora=%r bytes=%d", nombre_impresora, len(datos))
    logger.debug("ZPL inicio: %s", zpl[:120])

    handle = win32print.OpenPrinter(nombre_impresora)
    try:
        job = win32print.StartDocPrinter(handle, 1, ("Etiqueta", None, "RAW"))
        logger.info("StartDocPrinter OK job_id=%s", job)
        win32print.StartPagePrinter(handle)

        escritos = win32print.WritePrinter(handle, datos)
        logger.info("WritePrinter escritos=%d de %d", escritos, len(datos))
        if escritos != len(datos):
            logger.error("Se escribieron MENOS bytes de los esperados")

        win32print.EndPagePrinter(handle)
        win32print.EndDocPrinter(handle)
        logger.info("EndDocPrinter OK")

        # Estado del trabajo en la cola de Windows
        try:
            for j in win32print.EnumJobs(handle, 0, -1, 1):
                logger.info("Cola: id=%s estado=%s datatype=%s",
                            j["JobId"], j["Status"], j.get("pDatatype"))
        except Exception as exc:
            logger.warning("No se pudo leer la cola: %s", exc)
    except Exception:
        logger.exception("Fallo enviando ZPL")
        raise
    finally:
        win32print.ClosePrinter(handle)


def imprimir_etiqueta_configuracion(nombre_impresora: str) -> None:
    """
    Imprime la etiqueta de configuración de la Zebra (~WC). Sirve para leer
    el largo de etiqueta que midió la calibración ("LABEL LENGTH", en puntos)
    y confirmar tipo de medio, ajuste de rasgado, oscuridad y velocidad.
    """
    enviar_zpl(nombre_impresora, "~WC")


# ======================================================================
# IMPRESIÓN POR DRIVER (QPrinter) - CAMINO ANTERIOR
# ======================================================================
# Se conserva por si otra etiqueta del proyecto todavía lo usa. Depende
# de la configuración del driver de Windows en cada equipo (papel,
# márgenes, escalado), por eso puede salir distinto entre computadores.
# Si ningún módulo llama a crear_impresora/crear_painter, se pueden borrar.

def crear_impresora(
    nombre_impresora: str,
    ancho_mm: float,
    alto_mm: float,
    margen_mm: float = 0,
) -> QPrinter:
    """QPrinter a 203 DPI, página ancho x alto mm, en modo página completa."""
    impresora = QPrinter(QPrinter.PrinterMode.ScreenResolution)
    impresora.setPrinterName(nombre_impresora)
    impresora.setResolution(203)

    tamano_pagina = QPageSize(
        QSizeF(ancho_mm, alto_mm),
        QPageSize.Unit.Millimeter,
        "EtiquetaPersonalizada",
        QPageSize.SizeMatchPolicy.FuzzyMatch,
    )

    # Layout completo (un QPageLayout() vacío puede ser rechazado por Qt).
    diseno = QPageLayout(
        tamano_pagina,
        QPageLayout.Orientation.Portrait,
        QMarginsF(margen_mm, margen_mm, margen_mm, margen_mm),
        QPageLayout.Unit.Millimeter,
    )
    diseno.setMode(QPageLayout.Mode.FullPageMode)

    impresora.setPageLayout(diseno)
    impresora.setFullPage(True)
    return impresora


def crear_painter(impresora: QPrinter) -> QPainter:
    return QPainter(impresora)


# ======================================================================
# CÓDIGOS QR
# ======================================================================

@lru_cache(maxsize=32)
def generar_qr_bytes(
    contenido: str,
    box_size: int = 6,
    border: int = 2,
    error_correction: int = qrcode.constants.ERROR_CORRECT_M,
) -> bytes:
    """
    Genera el QR en memoria (PNG) y devuelve los bytes.

    Usa caché: la etiqueta dibuja el MISMO QR a izquierda y derecha, así
    solo se genera una vez.

    - box_size: tamaño de cada "punto" del QR en píxeles
    - border:   margen blanco alrededor (recomendado 4; acá 2 por espacio)
    - error_correction: L/M/Q/H; más alto = más tolerante pero más denso
    """
    qr = qrcode.QRCode(
        version=None,  # se ajusta automáticamente al contenido
        error_correction=error_correction,
        box_size=box_size,
        border=border,
    )
    qr.add_data(contenido)
    qr.make(fit=True)

    imagen = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    imagen.save(buffer, format="PNG")
    return buffer.getvalue()


def generar_qr_imagen(contenido: str, **kwargs) -> QImage:
    """Igual que generar_qr_bytes, pero ya como QImage lista para dibujar."""
    imagen = QImage()
    imagen.loadFromData(generar_qr_bytes(contenido, **kwargs))
    return imagen


def dibujar_qr(painter: QPainter, contenido: str, rect: QRectF, **kwargs):
    """
    Dibuja el QR dentro de `rect`.

    Se desactiva el suavizado al escalar para que los módulos del QR
    queden con bordes nítidos (un QR borroso se lee peor).
    """
    painter.save()
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, False)
    painter.drawImage(rect, generar_qr_imagen(contenido, **kwargs))
    painter.restore()


# ======================================================================
# HELPERS DE TEXTO (equivalentes a las funciones xBase del .frx original)
# ======================================================================

def texto_o_vacio(valor) -> str:
    """Equivalente a alltrim(x) cuando x puede venir None/blank."""
    if valor is None:
        return ""
    return str(valor).strip()


def linea_condicional(etiqueta: str, valor) -> str:
    """
    Equivalente a: iif(isblank(campo), "", etiqueta + alltrim(campo)).
    Si no hay valor, la línea completa desaparece.
    """
    texto = texto_o_vacio(valor)
    if not texto:
        return ""
    return f"{etiqueta}{texto}"

# ======================================================================
# DIAGNÓSTICO DE IMPRESORA (para comparar entre computadores)
# ======================================================================



RUTA_LOG_DIAGNOSTICO = Path("logs") / "diagnostico_impresoras.log"


def diagnosticar_impresora_raw(nombre_impresora: str) -> dict:
    """
    Para impresoras RAW/ZPL (Zebra, Godex): consulta la configuración que
    Windows tiene guardada de esa impresora específica, para comparar
    entre computadores si la impresora/driver está configurada distinto.
    """
    import win32print

    diagnostico = {
        "fecha": datetime.now().isoformat(timespec="seconds"),
        "computador": socket.gethostname(),
        "impresora": nombre_impresora,
    }

    try:
        handle = win32print.OpenPrinter(nombre_impresora)
        try:
            info = win32print.GetPrinter(handle, 2)
        finally:
            win32print.ClosePrinter(handle)

        devmode = info.get("pDevMode")

        diagnostico.update({
            "driver_name": info.get("pDriverName"),
            "port_name": info.get("pPortName"),
            "print_processor": info.get("pPrintProcessor"),
            "datatype": info.get("pDatatype"),
            "status": info.get("Status"),
        })

        if devmode is not None:
            diagnostico["devmode"] = {
                "paper_width_decimm": devmode.PaperWidth,    # décimas de mm
                "paper_length_decimm": devmode.PaperLength,  # décimas de mm
                "print_quality_dpi": devmode.PrintQuality,   # DPI real, si es positivo
                "orientation": devmode.Orientation,
                "scale": devmode.Scale,
            }
    except Exception as exc:
        diagnostico["error"] = str(exc)

    _guardar_diagnostico(diagnostico)
    return diagnostico

def imprimir_log_diagnostico_raw(diagnostico: dict) -> None:
    logger.info("=" * 60)
    logger.info(f"Computador raw:  {diagnostico['computador']}")
    logger.info(f"Impresora raw:   {diagnostico['impresora']}")
    if "error" in diagnostico:
        logger.info(f"ERROR raw:       {diagnostico['error']}")
    else:
        logger.info(f"Driver raw:      {diagnostico.get('driver_name')}")
        logger.info(f"Puerto raw:      {diagnostico.get('port_name')}")
        logger.info(f"Datatype rw:    {diagnostico.get('datatype')}")
        logger.info(f"DevMode rw:     {diagnostico.get('devmode')}")
    logger.info("=" * 60)

def diagnosticar_impresora(
    nombre_impresora: str,
    ancho_mm: float,
    alto_mm: float,
    margen_mm: float = 0,
) -> dict:
    """
    Crea el QPrinter con crear_impresora() y extrae todos los valores
    relevantes (tamaño de hoja, área imprimible, márgenes, DPI) para
    poder comparar la configuración real entre distintos computadores.

    Registra el resultado en logs/diagnostico_impresoras.log (una línea
    JSON por cada ejecución) y también lo retorna por si quieres
    mostrarlo en pantalla o en una ventana de debug.
    """
    impresora = crear_impresora(nombre_impresora, ancho_mm, alto_mm, margen_mm)
    layout = impresora.pageLayout()
    dpi = impresora.resolution()

    hoja = layout.fullRect(QPageLayout.Unit.Millimeter)
    imprimible = layout.paintRect(QPageLayout.Unit.Millimeter)
    margenes_min = layout.minimumMargins()

    diagnostico = {
        "fecha": datetime.now().isoformat(timespec="seconds"),
        "computador": socket.gethostname(),
        "impresora": nombre_impresora,
        "solicitado_mm": {"ancho": ancho_mm, "alto": alto_mm, "margen": margen_mm},
        "dpi": dpi,
        "orientacion": layout.orientation().name,
        "hoja_mm": {
            "x": round(hoja.x(), 3), "y": round(hoja.y(), 3),
            "ancho": round(hoja.width(), 3), "alto": round(hoja.height(), 3),
        },
        "imprimible_mm": {
            "x": round(imprimible.x(), 3), "y": round(imprimible.y(), 3),
            "ancho": round(imprimible.width(), 3), "alto": round(imprimible.height(), 3),
        },
        "margenes_minimos_mm": {
            "izq": margenes_min.left(), "der": margenes_min.right(),
            "arriba": margenes_min.top(), "abajo": margenes_min.bottom(),
        },
        "fullPage": impresora.fullPage(),
    }

    _guardar_diagnostico(diagnostico)
    return diagnostico


def _guardar_diagnostico(diagnostico: dict) -> None:
    RUTA_LOG_DIAGNOSTICO.parent.mkdir(parents=True, exist_ok=True)
    with open(RUTA_LOG_DIAGNOSTICO, "a", encoding="utf-8") as archivo:
        archivo.write(json.dumps(diagnostico, ensure_ascii=False) + "\n")


def imprimir_log_diagnostico(diagnostico: dict) -> None:
    """Imprime el diagnóstico en consola de forma legible (para debug rápido)."""
    logger.info("=" * 60)
    logger.info(f"Computador:  {diagnostico['computador']}")
    logger.info(f"Impresora:   {diagnostico['impresora']}")
    logger.info(f"Fecha:       {diagnostico['fecha']}")
    logger.info(f"DPI:         {diagnostico['dpi']}")
    logger.info(f"Solicitado:  {diagnostico['solicitado_mm']}")
    logger.info(f"Hoja real:   {diagnostico['hoja_mm']}")
    logger.info(f"Imprimible:  {diagnostico['imprimible_mm']}")
    logger.info(f"Márgenes min:{diagnostico['margenes_minimos_mm']}")
    logger.info("=" * 60)