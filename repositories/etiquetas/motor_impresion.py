"""
Motor de impresión de etiquetas para Zebra (ZPL) y utilidades de dibujo.

Camino recomendado (independiente del driver de Windows):
    1. Dibujar la etiqueta en un QImage (ver imprimir_etiqueta_frescas).
    2. Convertirla a ZPL con imagen_a_zpl().
    3. Enviarla en modo RAW con enviar_zpl().

En modo RAW el spooler pasa los bytes tal cual a la impresora, así que el
tamaño de papel, los márgenes y el escalado configurados en Windows YA NO
influyen. Por eso la etiqueta sale igual en todos los computadores.
"""

import io
from functools import lru_cache

import qrcode
from PySide6.QtCore import QMarginsF, QRectF, QSizeF
from PySide6.QtGui import QImage, QPageLayout, QPageSize, QPainter
from PySide6.QtPrintSupport import QPrinter


# ======================================================================
# ENVÍO DIRECTO A LA ZEBRA (ZPL / RAW)
# ======================================================================

# Por debajo de este nivel de gris (0-255) un punto se imprime en negro.
UMBRAL_NEGRO = 128


def imagen_a_zpl(img, medio="Y", desplaz_x=0, desplaz_y=0):
    """
    Convierte una imagen a un comando ZPL (^GFA) en blanco y negro.

    medio: tipo de sensor de la Zebra.
        "Y" -> etiquetas con separación (gap)   [^MNY]
        "M" -> etiquetas con marca negra         [^MNM]
        "N" -> papel continuo                    [^MNN]

    Comandos de la cabecera:
        ^PW  ancho de impresión en puntos
        ^LL  largo de la etiqueta en puntos
        ^LH  origen de la etiqueta (0,0)
        ^LT  desplazamiento superior (0)
        ^PON orientación normal
    """
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
        f"^XA^MN{medio}^PW{ancho}^LL{alto}^LH0,0^LT{desplaz_y}^LS{desplaz_x}^PON"
        f"^FO0,0^GFA,{total},{total},{bytes_fila},{datos.hex().upper()}^FS"
        f"^XZ"
    )
    """
    return (
        f"^XA^MN{medio}^PW{ancho}^LL{alto}^LH0,0^LT0^PON"
        f"^FO0,0^GFA,{total},{total},{bytes_fila},{datos.hex().upper()}^FS"
        f"^XZ"
    )
"""
def zpl_marco_prueba(ancho_dots, alto_dots, medio="Y", desplaz_x=0, desplaz_y=0):
    return (
        f"^XA^MN{medio}^PW{ancho_dots}^LL{alto_dots}^LH0,0"
        f"^LT{desplaz_y}^LS{desplaz_x}"
        f"^FO0,0^GB{ancho_dots},{alto_dots},4^FS^XZ"
    )

def zpl_regla_prueba(ancho_dots: int, alto_dots: int, medio: str = "Y") -> str:
    """Marcas cada 10 mm (80 puntos) arriba y a la izquierda, más el marco."""
    marcas = ""
    for x in range(0, ancho_dots, 80):
        marcas += f"^FO{x},0^GB3,40,3^FS"       # marca vertical arriba
    for y in range(0, alto_dots, 80):
        marcas += f"^FO0,{y}^GB40,3,3^FS"       # marca horizontal a la izquierda
    return (
        f"^XA^MN{medio}^PW{ancho_dots}^LL{alto_dots}^LH0,0^LT0"
        f"{marcas}^FO0,0^GB{ancho_dots},{alto_dots},4^FS^XZ"
    )
def enviar_zpl(nombre_impresora: str, zpl: str) -> None:
    """
    Envía el ZPL a la impresora en modo RAW (requiere Windows + pywin32).
    `nombre_impresora` debe ser exactamente el nombre que muestra Windows.
    """
    # Import diferido: así el resto del módulo (vista previa, QR) sigue
    # funcionando aunque pywin32 no esté instalado.
    import win32print

    try:
        handle = win32print.OpenPrinter(nombre_impresora)
    except Exception as exc:
        disponibles = [
            p[2] for p in win32print.EnumPrinters(
                win32print.PRINTER_ENUM_LOCAL
                | win32print.PRINTER_ENUM_CONNECTIONS
            )
        ]
        raise RuntimeError(
            f"No se pudo abrir la impresora '{nombre_impresora}'. "
            f"Impresoras disponibles: {disponibles}"
        ) from exc

    try:
        win32print.StartDocPrinter(handle, 1, ("Etiqueta", None, "RAW"))
        win32print.StartPagePrinter(handle)
        win32print.WritePrinter(handle, zpl.encode("ascii"))
        win32print.EndPagePrinter(handle)
        win32print.EndDocPrinter(handle)
    finally:
        win32print.ClosePrinter(handle)


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