"""
Etiqueta de productos frescos (100 x 45 mm) para Zebra ZD230 (203 DPI).

El diseño se dibuja UNA sola vez (_dibujar_contenido_etiqueta) y se usa
tanto en la vista previa como en la impresión, así ambas son idénticas.

La impresión se hace enviando ZPL en modo RAW (ver motor_impresion.py),
por lo que no depende del papel/márgenes configurados en el driver de
Windows de cada computador.
"""

import os
import socket
from dataclasses import dataclass
from datetime import date
from typing import Optional

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QFont, QImage, QPainter, QPen, QPixmap
from PySide6.QtCore import QMarginsF, QSizeF
from PySide6.QtGui import QImage, QPageLayout, QPageSize, QPainter, QPdfWriter
from repositories.empresa_repository import (
    obtener_ciudad_empresa_db,
    obtener_fabricado_empresa_db,
    obtener_fabricado_empresa_direccion_db,
    obtener_telefono_empresa_db,
)
from repositories.consecutivo_repository import (
    ConsecutivoParametros,
    ConsecutivoRepository,
)
from services.bascula_service import bascula_service
from utils import fechas
from utils.rutas import ruta_recurso
from .motor_impresion import crear_impresora, crear_painter,dibujar_qr, enviar_zpl, imagen_a_zpl,zpl_marco_prueba,zpl_regla_prueba


# ======================================================================
# CONFIGURACIÓN GENERAL
# ======================================================================

# Tamaño físico de la etiqueta.
ANCHO_MM = 100
ALTO_MM = 45
MODO_PRUEBA_MARCO = True
# Resolución de la Zebra ZD230: 203 DPI ≈ 8 puntos por mm.
DOTS_POR_MM = 8
ANCHO_DOTS = ANCHO_MM * DOTS_POR_MM   # 800
ALTO_DOTS = ALTO_MM * DOTS_POR_MM     # 360

# Tipo de sensor de la Zebra: "Y" = etiquetas con separación (gap),
# "M" = marca negra, "N" = continuo.
MEDIO_ZEBRA = "Y"

# Coordenadas lógicas de dibujo: 1 unidad = 0,1 mm (1000 x 450 = 100 x 45 mm).
ANCHO = ANCHO_MM * 10
ALTO = ALTO_MM * 10

# Margen igual en los CUATRO lados, en unidades lógicas (12 = 1,2 mm).
# Las térmicas tienen ~1 mm de tolerancia entre etiqueta y etiqueta: con un
# margen de 0,4 mm lo que queda pegado al borde se corta a veces.
# Súbelo si todavía se corta; bájalo si necesitas más espacio.
MARGEN = 12

QR_SIZE = 160
SEPARACION_QR = 10
SEPARACION_BLOQUES = 10   # espacio entre el texto superior y la franja inferior
GROSOR_LINEA = 5

# La franja inferior (logo + categoría + código) arranca justo debajo de la
# línea divisoria, que queda SEPARACION_BLOQUES por encima del QR.
ALTO_BLOQUE_INFERIOR = QR_SIZE + SEPARACION_BLOQUES

# Dibuja un marco en el borde de la etiqueta (vista previa e impresión).
# Útil para comprobar qué borde se corta; dejar en False en producción.
MARCO_DE_PRUEBA = False

TEMPERATURA_MINIMA_C = 0
TEMPERATURA_MAXIMA_C = 4

RECOMENDACION_CONSERVACION = "Mantengase Refrigerado entre 0°C y 4°C"
RECOMENDACION_USO = "consumase bien cocido a temperatura superior de 70°C"

CODIGO_PROCESO_DEFAULT = socket.gethostname()

RUTA_ICONOS = ruta_recurso(os.path.join("assets", "icons"))

_consecutivo_repository = ConsecutivoRepository()


# ======================================================================
# RECURSOS
# ======================================================================

def _cargar_pixmap(nombre_archivo: str) -> Optional[QPixmap]:
    """
    Carga una imagen sin escalarla (el escalado se hace al dibujar, para
    conservar la mejor calidad). Devuelve None si no existe o está dañada.
    """
    ruta = os.path.join(RUTA_ICONOS, nombre_archivo)

    if not os.path.isfile(ruta):
        return None

    pixmap = QPixmap(ruta)
    return None if pixmap.isNull() else pixmap


def crear_etiqueta_marca() -> Optional[QPixmap]:
    return _cargar_pixmap("logo_marca.png")


def _formatear_fecha(valor: Optional[date], formato: str = "%d/%m/%Y") -> str:
    """Fecha como texto; cadena vacía si no hay fecha."""
    return valor.strftime(formato) if valor else ""


# ======================================================================
# DATOS AUXILIARES
# ======================================================================

def siguiente_consecutivo_etiqueta_canasta() -> int:
    params = ConsecutivoParametros(
        tabla="ETIQUETAS_CANASTAS",
        tabla_eva="invntrio_clta_p",
        campo_eva="nmro_psta",
        proceso=0,
    )
    return _consecutivo_repository.obtener_consecutivo(params)


def construir_codigo(nombre_usuario, numero_ticket=None) -> str:
    if numero_ticket is None:
        numero_ticket = siguiente_consecutivo_etiqueta_canasta()

    return f"{nombre_usuario} {CODIGO_PROCESO_DEFAULT} #{numero_ticket}"

def _generar_contenido_qr(
    lote: str,
    nivel_limpieza: Optional[int],
    cdgo_plu: str,
    piezas: int,
    fecha_vencimiento_str: Optional[date],
    peso_neto_kg: Optional[float],
) -> str:
    """
    Contenido del QR (largo fijo):
    lote(7) + nivel(2) + plu(4) + peso(5) + piezas(2) + fecha DDMMAAAA(8)
    """
    lote_fmt = str(lote).zfill(7)[-7:]
    nivel_fmt = str(nivel_limpieza if nivel_limpieza is not None else 0).zfill(2)
    plu_fmt = str(cdgo_plu).zfill(4)[-4:]

    if peso_neto_kg is not None:
        # Ej.: 3.25 kg -> "03025" (el punto decimal se reemplaza por 0)
        peso_fmt = f"{round(peso_neto_kg, 2):05.2f}".replace(".", "0")
    else:
        peso_fmt = "0" * 5

    piezas_fmt = str(piezas).zfill(2)
    fecha_fmt = (
        _formatear_fecha(fecha_vencimiento_str, "%d%m%Y")
        if fecha_vencimiento_str
        else "0" * 8
    )

    return f"{lote_fmt}{nivel_fmt}{plu_fmt}{peso_fmt}{piezas_fmt}{fecha_fmt}"


# ======================================================================
# DATOS DE LA ETIQUETA
# ======================================================================

@dataclass
class DatosEtiquetaFrescas:
    # Producto
    cdgo_plu: str
    nom_prog: str
    descripcion: str
    lote: str
    nivel_limpieza: Optional[int]
    peso_neto_kg: Optional[float]

    # Fechas
    fecha_fabricacion: Optional[date]
    fecha_sacrificio: str
    nom_impr_etiq: str
    numEspecie: Optional[int]
    fecha_vencimiento_str: Optional[date]

    # Fabricante
    fabricante_nombre: str
    fabricante_direccion: str
    fabricante_ciudad: str
    fabricante_telefono: str

    # Conservación
    temperatura_minima_c: float
    temperatura_maxima_c: float
    recomendacion_conservacion: str
    recomendacion_uso: str

    # Marca / categoría
    marca: Optional[QPixmap]
    categoria: str
    codigo: str

    # QR
    qr_izquierda: Optional[str]
    qr_derecha: Optional[str]


def construir_datos_etiqueta(
    producto,
    lote: str,
    fecha_produccion: date,
    fecha_vencimiento_str: Optional[date],
    nombre_usuario: str,
    cod_empresa: int,          # no se usa; se conserva por compatibilidad
    peso_bascula: Optional[float],
    tipo_limpieza_seleccionado: Optional[int] = None,
    numero_ticket: Optional[int] = None,
    fecha_sacrificio: Optional[date] = None,
    nom_impr_etiq: Optional[str] = None,
    numEspecie: Optional[int] = None,
) -> DatosEtiquetaFrescas:

    fecha_produccion = fechas._asegurar_date(fecha_produccion)
    fecha_sacrificio = fechas._asegurar_date(fecha_sacrificio)
    fecha_vencimiento_str = fechas._asegurar_date(fecha_vencimiento_str)

    # El peso se obtiene UNA sola vez para que el QR y el texto de la
    # etiqueta muestren exactamente el mismo valor.
    peso_neto_kg = (
        peso_bascula
        if peso_bascula is not None
        else bascula_service.obtener_ultimo_peso()
    )

    contenido_qr = _generar_contenido_qr(
        lote=lote,
        cdgo_plu=producto.cdgo_plu,
        peso_neto_kg=peso_neto_kg,
        nivel_limpieza=tipo_limpieza_seleccionado,
        piezas=1,
        fecha_vencimiento_str=fecha_vencimiento_str,
    )

    categoria = nom_impr_etiq or ""

    return DatosEtiquetaFrescas(
        cdgo_plu=str(producto.cdgo_plu),
        nom_prog=producto.nom_prog,
        descripcion=f"{producto.cdgo_plu}-{producto.nom_prog}".strip(),
        lote=str(lote),
        nivel_limpieza=tipo_limpieza_seleccionado,
        peso_neto_kg=peso_neto_kg,

        fecha_fabricacion=fecha_produccion,
        fecha_sacrificio=_formatear_fecha(fecha_sacrificio),
        nom_impr_etiq=categoria,
        fecha_vencimiento_str=fecha_vencimiento_str,
        numEspecie=numEspecie,

        fabricante_nombre=obtener_fabricado_empresa_db(),
        fabricante_direccion=obtener_fabricado_empresa_direccion_db(),
        fabricante_ciudad=obtener_ciudad_empresa_db(),
        fabricante_telefono=obtener_telefono_empresa_db(),

        temperatura_minima_c=TEMPERATURA_MINIMA_C,
        temperatura_maxima_c=TEMPERATURA_MAXIMA_C,
        recomendacion_conservacion=RECOMENDACION_CONSERVACION,
        recomendacion_uso=RECOMENDACION_USO,

        marca=crear_etiqueta_marca(),
        categoria=categoria,
        codigo=construir_codigo(nombre_usuario, numero_ticket),

        qr_izquierda=contenido_qr,
        qr_derecha=contenido_qr,
    )


# ======================================================================
# DIBUJO (compartido entre impresión y vista previa)
# ======================================================================

def _dibujar_contenido_etiqueta(
    painter: QPainter,
    datos: DatosEtiquetaFrescas,
) -> None:
    """
    Dibuja la etiqueta completa (QR, textos, logo) sobre un QPainter cuyo
    sistema de coordenadas es ANCHO x ALTO (1000 x 450, 1 unidad = 0,1 mm).
    """

    # ---------------- Medidas derivadas ----------------
    x_full = MARGEN
    ancho_full = ANCHO - (MARGEN * 2)

    # Zona central (entre los dos QR) para logo / categoría / código.
    x_entre_qr = MARGEN + QR_SIZE + SEPARACION_QR
    ancho_entre_qr = ANCHO - (2 * x_entre_qr)

    # El QR respeta el mismo MARGEN que los demás lados.
    qr_y = ALTO - QR_SIZE - MARGEN

    # ---------------- Funciones auxiliares ----------------

    def fuente(tamano: int, negrita: bool = False) -> QFont:
        font = QFont("Arial")
        font.setWeight(QFont.Weight.Bold if negrita else QFont.Weight.Normal)
        font.setPixelSize(tamano)
        return font

    def texto(
        x, y, ancho, alto, contenido,
        tamano=20,
        negrita=False,
        alineacion=Qt.AlignmentFlag.AlignLeft,
    ):
        painter.setFont(fuente(tamano, negrita))
        painter.drawText(QRectF(x, y, ancho, alto), alineacion, str(contenido))

    def fila_dos_columnas(
        y, alto, izquierda, derecha,
        tamano=27,
        negrita_der=False,
        prop_izq=0.5,
    ):
        ancho_izq = ancho_full * prop_izq
        texto(x_full, y, ancho_izq, alto, izquierda, tamano=tamano)
        texto(
            x_full + ancho_izq, y, ancho_full - ancho_izq, alto, derecha,
            tamano=tamano,
            negrita=negrita_der,
            alineacion=Qt.AlignmentFlag.AlignRight,
        )

    def fila_tres_columnas(y, alto, izquierda, centro, derecha, tamano=24):
        """Tres textos en una fila: izquierda | centro | derecha."""
        ancho_col = ancho_full / 3
        alineaciones = (
            Qt.AlignmentFlag.AlignLeft,
            Qt.AlignmentFlag.AlignCenter,
            Qt.AlignmentFlag.AlignRight,
        )
        for i, (contenido, alineacion) in enumerate(
            zip((izquierda, centro, derecha), alineaciones)
        ):
            texto(
                x_full + ancho_col * i, y, ancho_col, alto, contenido,
                tamano=tamano,
                alineacion=alineacion,
            )

    def dibujar_logo_centrado(pixmap: Optional[QPixmap], x, y, ancho, alto):
        """
        Dibuja el logo conservando su proporción, centrado en el área dada.
        Se dibuja desde la imagen ORIGINAL (no pre-escalada) para evitar
        escalar dos veces y perder nitidez.
        """
        if pixmap is None or pixmap.isNull():
            return

        tam = pixmap.size().scaled(
            int(ancho), int(alto), Qt.AspectRatioMode.KeepAspectRatio
        )
        destino = QRectF(
            x + (ancho - tam.width()) / 2,
            y + (alto - tam.height()) / 2,
            tam.width(),
            tam.height(),
        )

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        painter.drawPixmap(destino, pixmap, QRectF(pixmap.rect()))
        painter.restore()

    # ---------------- QR (izquierda y derecha) ----------------

    if datos.qr_izquierda:
        dibujar_qr(
            painter, datos.qr_izquierda,
            QRectF(MARGEN, qr_y, QR_SIZE, QR_SIZE),
        )

    if datos.qr_derecha:
        dibujar_qr(
            painter, datos.qr_derecha,
            QRectF(ANCHO - MARGEN - QR_SIZE, qr_y, QR_SIZE, QR_SIZE),
        )

    # ---------------- Parte superior (textos) ----------------
    # El alto disponible entre el margen superior y la franja del QR se
    # reparte proporcionalmente entre las filas (según sus "pesos"). Así,
    # si cambia ALTO, MARGEN o QR_SIZE, el texto se adapta solo y nunca
    # se monta sobre el QR.

    pesos_filas = [42, 36, 40, 29, 30, 27, 32]
    alto_disponible = (qr_y - SEPARACION_BLOQUES) - MARGEN
    factor = alto_disponible / sum(pesos_filas)
    saltos = [round(peso * factor) for peso in pesos_filas]

    y = MARGEN

    # Descripción del producto (PLU-nombre).
    texto(x_full, y, ancho_full, 38, datos.descripcion, tamano=31, negrita=True)
    y += saltos[0]

    # Fecha de empaque | Contenido neto.
    fecha_empaque = _formatear_fecha(datos.fecha_fabricacion)
    peso_texto = (
        f"{datos.peso_neto_kg:.2f}kg"
        if datos.peso_neto_kg is not None
        else "--.--kg"
    )
    fila_dos_columnas(
        y, 34,
        f"Fecha Empacado: {fecha_empaque}",
        f"Contenido Neto:{peso_texto}",
        tamano=25,
        negrita_der=True,
        prop_izq=0.42,
    )
    y += saltos[1]

    # Fecha beneficio | Lote (+ nivel) | Fecha de vencimiento.
    nivel_texto = (
        f"   Nv:{datos.nivel_limpieza}"
        if datos.nivel_limpieza is not None
        else ""
    )
    fila_tres_columnas(
        y, 34,
        f"Fecha Beneficio: {datos.fecha_sacrificio}",
        f"Lote:{datos.lote}{nivel_texto}",
        f"F.Vto.Refrigeracion: {_formatear_fecha(datos.fecha_vencimiento_str)}",
        tamano=22,
    )
    y += saltos[2]

    # Fabricante.
    texto(
        x_full, y, ancho_full, 30, datos.fabricante_nombre,
        tamano=25, negrita=True,
    )
    y += saltos[3]

    direccion = (
        f"{datos.fabricante_direccion} "
        f"Tel.{datos.fabricante_telefono} "
        f"{datos.fabricante_ciudad} "
    )
    texto(x_full, y, ancho_full, 28, direccion, tamano=24)
    y += saltos[4]

    # Conservación y uso.
    texto(
        x_full, y, ancho_full, 27,
        datos.recomendacion_conservacion, tamano=24,
    )
    y += saltos[5]

    texto(
        x_full, y, ancho_full, 27,
        f"Recomendación de Uso: {datos.recomendacion_uso}", tamano=24,
    )
    y += saltos[6]

    # ---------------- Línea divisoria ----------------

    painter.setPen(QPen(Qt.GlobalColor.black, GROSOR_LINEA))
    painter.drawLine(
        int(x_full), int(y), int(x_full + ancho_full), int(y)
    )
    painter.setPen(Qt.GlobalColor.black)

    # ---------------- Bloque inferior: logo + categoría + código ----------------
    # Ocupa la franja entre los dos QR: empieza en la línea divisoria y
    # termina en el margen inferior.

    alto_categoria = 30
    alto_codigo = 22
    espacio = 2

    alto_logo = ALTO_BLOQUE_INFERIOR - alto_categoria - alto_codigo - (espacio * 2)
    y_logo = ALTO - MARGEN - ALTO_BLOQUE_INFERIOR
    y_categoria = y_logo + alto_logo + espacio
    y_codigo = y_categoria + alto_categoria + espacio

    dibujar_logo_centrado(datos.marca, x_entre_qr, y_logo, ancho_entre_qr, alto_logo)

    texto(
        x_entre_qr, y_categoria, ancho_entre_qr, alto_categoria,
        datos.categoria,
        tamano=27, negrita=True,
        alineacion=Qt.AlignmentFlag.AlignCenter,
    )

    texto(
        x_entre_qr, y_codigo, ancho_entre_qr, alto_codigo,
        datos.codigo,
        tamano=18,
        alineacion=Qt.AlignmentFlag.AlignCenter,
    )

    # ---------------- Marco de prueba (opcional) ----------------

    if MARCO_DE_PRUEBA:
        painter.setPen(QPen(Qt.GlobalColor.black, 4))
        painter.drawRect(0, 0, ANCHO - 1, ALTO - 1)


# ======================================================================
# VISTA PREVIA (en memoria, no toca la impresora)
# ======================================================================

def generar_vista_previa_pixmap(
    datos: DatosEtiquetaFrescas,
) -> QPixmap:
    """
    Genera una imagen con el MISMO diseño que se imprime,
    para mostrarla en la interfaz.

    No toca la impresora física.
    """

    pixmap = QPixmap(
        ANCHO,
        ALTO,
    )

    pixmap.fill(
        Qt.GlobalColor.white
    )

    painter = QPainter(pixmap)

    painter.setRenderHint(
        QPainter.RenderHint.Antialiasing
    )

    painter.setRenderHint(
        QPainter.RenderHint.TextAntialiasing
    )

    _dibujar_contenido_etiqueta(
        painter,
        datos,
    )

    painter.end()

    return pixmap


# ======================================================================
# IMPRESIÓN (ZPL RAW directo a la Zebra)
# ======================================================================

def _renderizar_para_zebra(datos: DatosEtiquetaFrescas) -> QImage:
    """
    Dibuja la etiqueta en una imagen de ANCHO_DOTS x ALTO_DOTS (800 x 360),
    es decir, 1 píxel = 1 punto de la impresora.
    """
    img = QImage(ANCHO_DOTS, ALTO_DOTS, QImage.Format.Format_RGB32)
    img.fill(Qt.GlobalColor.white)

    painter = QPainter(img)
    # Sin suavizado: la impresora es solo blanco/negro, el suavizado
    # generaría grises que luego se pierden o engruesan al binarizar.
    painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, False)
    # Coordenadas lógicas (1000x450) -> puntos de la impresora (800x360).
    painter.scale(ANCHO_DOTS / ANCHO, ALTO_DOTS / ALTO)

    _dibujar_contenido_etiqueta(painter, datos)

    painter.end()
    return img


def generar_pdf_etiqueta(datos: DatosEtiquetaFrescas, ruta_pdf: str) -> None:
    """
    Genera un PDF de 100 x 45 mm con el MISMO diseño de la etiqueta.
    No usa impresora ni driver: escribe el archivo directamente.
    """
    writer = QPdfWriter(ruta_pdf)
    writer.setResolution(300)
    writer.setPageSize(
        QPageSize(QSizeF(ANCHO_MM, ALTO_MM), QPageSize.Unit.Millimeter)
    )
    writer.setPageMargins(QMarginsF(0, 0, 0, 0), QPageLayout.Unit.Millimeter)

    painter = QPainter(writer)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

    # Coordenadas lógicas (1000x450) -> toda la página del PDF.
    painter.setWindow(0, 0, ANCHO, ALTO)
    painter.setViewport(0, 0, writer.width(), writer.height())

    _dibujar_contenido_etiqueta(painter, datos)
    painter.end()


def _imprimir_con_driver(datos: DatosEtiquetaFrescas, nombre_impresora: str) -> None:
    """
    Camino por driver de Windows (QPrinter). Se usa para impresoras
    virtuales como 'Microsoft Print to PDF', que no entienden ZPL.
    """
    impresora = crear_impresora(nombre_impresora, ANCHO_MM, ALTO_MM, margen_mm=0)
    painter = crear_painter(impresora)

    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
    painter.setWindow(0, 0, ANCHO, ALTO)
    painter.setViewport(0, 0, painter.device().width(), painter.device().height())

    _dibujar_contenido_etiqueta(painter, datos)
    painter.end()


def imprimir_etiqueta_frescas(
    datos: DatosEtiquetaFrescas,
    nombre_impresora: str,
) -> None:
    """
    Decide cómo imprimir según el destino:
      - ruta que termina en .pdf        -> archivo PDF directo
      - impresora virtual con 'pdf'     -> driver de Windows (QPrinter)
      - cualquier otra (Godex/Zebra)    -> ZPL RAW
    """
    destino = nombre_impresora.lower()

    if destino.endswith(".pdf"):
        generar_pdf_etiqueta(datos, nombre_impresora)
        return

    if "pdf" in destino:
        _imprimir_con_driver(datos, nombre_impresora)
        return

    if MODO_PRUEBA_MARCO:
        zpl = zpl_regla_prueba(ANCHO_DOTS, ALTO_DOTS, MEDIO_ZEBRA)
    else:
        zpl = imagen_a_zpl(_renderizar_para_zebra(datos), MEDIO_ZEBRA)

    enviar_zpl(nombre_impresora, zpl)