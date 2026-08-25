"""
motor_impresion.py

Piezas GENÉRICAS de impresión de etiquetas, reutilizables sin importar
el diseño/tamaño específico: configuración de QPrinter, generación de
códigos QR, y helpers de texto (equivalentes a alltrim/isblank del
reporte FoxPro original).

Cada plantilla de etiqueta concreta (frescas_100x45.py, y las que
vengan después) importa de acá en vez de reimplementar esto.

Requiere: pip install qrcode --break-system-packages
"""

import io
from typing import Optional

import qrcode
from PySide6.QtCore import QMarginsF, QRectF, QSizeF
from PySide6.QtGui import QImage, QPainter,QPageLayout, QPageSize
from PySide6.QtPrintSupport import QPrinter


# ======================================================================
# CONFIGURACIÓN DE IMPRESORA
# ======================================================================

def crear_impresora(
    nombre_impresora: str,
    ancho_mm: float,
    alto_mm: float,
    margen_mm: float = 2,
) -> QPrinter:
    """
    Arma un QPrinter apuntando a la impresora Zebra con resolución nativa
    de 203 DPI para evitar saturar la memoria del equipo térmico.
    """
    # 1. Inicializar usando un modo válido de Qt6 (ScreenResolution es el estándar)
    impresora = QPrinter(QPrinter.PrinterMode.ScreenResolution)
    impresora.setPrinterName(nombre_impresora)
    
    # 2. Forzar explícitamente los 203 DPI nativos de la Zebra ZD230
    impresora.setResolution(203)
    
    # 3. Configurar el tamaño de la página física
    tamano_pagina = QPageSize(
        QSizeF(ancho_mm, alto_mm),
        QPageSize.Unit.Millimeter,
        "EtiquetaPersonalizada",
        QPageSize.SizeMatchPolicy.ExactMatch
    )
    
    diseno = QPageLayout()
    diseno.setPageSize(tamano_pagina)
    diseno.setOrientation(QPageLayout.Orientation.Portrait)
    
    margenes = QMarginsF(margen_mm, margen_mm, margen_mm, margen_mm)
    diseno.setMargins(margenes)
    diseno.setUnits(QPageLayout.Unit.Millimeter)
    
    impresora.setPageLayout(diseno)
    impresora.setFullPage(True)
    
    return impresora



def crear_painter(impresora: QPrinter) -> QPainter:
    return QPainter(impresora)


# ======================================================================
# CÓDIGOS QR
# ======================================================================

def generar_qr_bytes(
    contenido: str,
    box_size: int = 6,
    border: int = 2,
    error_correction=qrcode.constants.ERROR_CORRECT_M,
) -> bytes:
    """
    Genera el QR en memoria (PNG) y lo devuelve como bytes.

    - box_size: tamaño de cada "punto" del QR en píxeles -> tamaño final
    - border:   margen blanco alrededor (mínimo recomendado: 4, acá 2
      porque el espacio en la etiqueta es angosto)
    - error_correction: L/M/Q/H -> a más alto, más tolerante a daño,
      pero el QR queda más denso (peor para etiquetas chicas)
    """
    qr = qrcode.QRCode(
        version=None,  # se ajusta automático al contenido
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
    """Genera y dibuja un QR directamente dentro de `rect`."""
    painter.drawImage(rect, generar_qr_imagen(contenido, **kwargs))


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
    Equivalente a:
        iif(isblank(campo), "", etiqueta + alltrim(campo))
    Si no hay valor, la línea completa desaparece (no deja etiqueta vacía).
    """
    texto = texto_o_vacio(valor)
    if not texto:
        return ""
    return f"{etiqueta}{texto}"