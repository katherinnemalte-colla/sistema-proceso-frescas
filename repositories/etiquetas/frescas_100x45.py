"""
Etiqueta de frescas: 100 mm de ancho fijo y alto variable de 30 a 50 mm.

- El ALTO se pasa como parámetro (alto_mm) o sale del perfil de la impresora.
- Cada impresora puede tener un PERFIL (perfil_impresora.py) con lo que se
  corta en cada borde. El contenido se reduce y se centra dentro de la zona
  que sí sale. No se cambia nada de la configuración de la impresora.
- Si una impresora todavía no tiene perfil, se usan DESPLAZ_X y DESPLAZ_Y
  como hasta ahora. Al guardar el primer perfil dejan de usarse.

Logs: este módulo solo usa logging.getLogger(__name__). La configuración
(archivo, formato, nivel) se hace UNA vez en main.py; aquí nunca se llama
a logging.basicConfig().
"""

import logging
import os
import socket
from dataclasses import dataclass, replace
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QMarginsF, QRectF, QSizeF, Qt
from PySide6.QtGui import (
    QFont,
    QImage,
    QPageLayout,
    QPageSize,
    QPainter,
    QPdfWriter,
    QPen,
    QPixmap,
    QFontMetricsF,
)
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
from .motor_impresion import (
    crear_impresora,
    crear_painter,
    dibujar_qr,
    enviar_zpl,
    imagen_a_zpl,
    zpl_marco_prueba,
    zpl_regla_prueba,
    diagnosticar_impresora,
    imprimir_log_diagnostico,
    diagnosticar_impresora_raw,
    imprimir_log_diagnostico_raw,
)
from repositories.etiquetas.perfil_impresora import (
    ALTO_MM_DEFECTO,
    ALTO_MM_MAX,
    ALTO_MM_MIN,
    ANCHO_MM,
    DOTS_POR_MM,
    PerfilImpresora,
    cargar_perfil,
    detectar_dpi,
    dpi_es_esperado,
)

logger = logging.getLogger(__name__)


# ======================================================================
# CONFIGURACIÓN GENERAL
# ======================================================================

# El ANCHO (100 mm), el rango del ALTO (30 a 50 mm) y los puntos por mm
# están en perfil_impresora.py. ALTO_MM es solo el valor por defecto.
ALTO_MM = ALTO_MM_DEFECTO

MODO_PRUEBA_MARCO = False
PRUEBA_ZPL = "C"   # "A", "B" o "C"

ANCHO_DOTS = ANCHO_MM * DOTS_POR_MM   # 800 (el alto en puntos se calcula aparte)

# Tipo de sensor de la Zebra: "Y" = etiquetas con separación (gap),
# "M" = marca negra, "N" = continuo.
MEDIO_ZEBRA = ""

# Coordenadas lógicas de dibujo: 1 unidad = 0,1 mm.
# El ancho es fijo (1000 unidades); el alto = alto_mm * 10 (300 a 500).
ANCHO = ANCHO_MM * 10

# Margen igual en los CUATRO lados, en unidades lógicas (25 = 2,5 mm).
MARGEN = 45

QR_SIZE = 170             # tamaño MÁXIMO del QR (se achica en etiquetas bajas)
SEPARACION_QR = 7
SEPARACION_BLOQUES = 5   # espacio entre el texto superior y la franja inferior
GROSOR_LINEA = 5

# Solo se usan si la impresora NO tiene perfil guardado (compatibilidad).
DESPLAZ_X = 0
DESPLAZ_Y = 0

# ---- Adaptación al alto ----
QR_MIN = 110              # el QR no baja de 11 mm (si no, se lee mal)
ALTO_REF = 450            # 45 mm: altura para la que se eligieron las letras
# Espacio que tenían las 7 filas de texto en el diseño original (= 220).
ALTO_TEXTO_REF = (ALTO_REF - QR_SIZE - MARGEN - SEPARACION_BLOQUES) - MARGEN
# Si la escala de letra baja de este valor se escribe un aviso en el log.
ESCALA_MIN_AVISO = 0.5

# Espacio mínimo (unidades lógicas) entre columnas de una misma fila.
# Si no caben, la fila reduce la letra hasta que quepan.
SEPARACION_MIN_COLUMNAS = 14
TAMANO_MIN_COLUMNAS = 12

# Dibuja un marco en el borde de la etiqueta (vista previa e impresión).
# Útil para comprobar qué borde se corta; dejar en False en producción.
MARCO_DE_PRUEBA = False

# Guarda debug_etiqueta.png y ultimo_envio.zpl en la carpeta de logs cada
# vez que se imprime por ZPL. Útil para probar; poner False en producción.
GUARDAR_ARCHIVOS_DEBUG = True

TEMPERATURA_MINIMA_C = 0
TEMPERATURA_MAXIMA_C = 4

RECOMENDACION_CONSERVACION = "Mantengase Refrigerado entre 0°C y 4°C"
RECOMENDACION_USO = "consumase bien cocido a temperatura superior de 70°C"

CODIGO_PROCESO_DEFAULT = socket.gethostname()

RUTA_ICONOS = ruta_recurso(os.path.join("assets", "icons"))
ETIQUETA_VENCIMIENTO = {
    "refrigerado": "F.Vto.Refrigeracion:",
    "congelado": "F.Vto.Congelacion:",
}

_consecutivo_repository = ConsecutivoRepository()


# ======================================================================
# MEDIDAS SEGÚN EL ALTO
# ======================================================================

def normalizar_alto_mm(alto_mm=None) -> int:
    """
    Devuelve un alto válido (entero entre ALTO_MM_MIN y ALTO_MM_MAX).

    - None            -> ALTO_MM (valor por defecto)
    - no es número    -> ALTO_MM y se avisa en el log
    - fuera de rango  -> se ajusta al límite más cercano y se avisa
    """
    if alto_mm is None:
        alto_mm = ALTO_MM

    try:
        alto = int(round(float(alto_mm)))
    except (TypeError, ValueError):
        logger.warning(
            "alto_mm=%r no es un número; se usa el valor por defecto %s mm",
            alto_mm, ALTO_MM,
        )
        alto = ALTO_MM

    limitado = max(ALTO_MM_MIN, min(ALTO_MM_MAX, alto))
    if limitado != alto:
        logger.warning(
            "alto_mm=%s fuera del rango %s-%s mm; se usa %s mm",
            alto, ALTO_MM_MIN, ALTO_MM_MAX, limitado,
        )
    return limitado


def medidas_alto(alto_mm=None) -> tuple:
    """
    (alto_mm, alto en unidades lógicas, alto en puntos de impresora)

    Ej.: 30 mm -> (30, 300, 240)      50 mm -> (50, 500, 400)
    """
    alto_mm = normalizar_alto_mm(alto_mm)
    return alto_mm, alto_mm * 10, alto_mm * DOTS_POR_MM


def _dir_diagnostico() -> Path:
    """
    Carpeta LOCAL de cada computador para archivos de depuración
    (la misma que usa el log: ...\\AppData\\Local\\etiquetasMk\\logs).
    """
    base = os.environ.get("LOCALAPPDATA") or str(Path.home())
    carpeta = Path(base) / "etiquetasMk" / "logs"
    carpeta.mkdir(parents=True, exist_ok=True)
    return carpeta


def _guardar_debug(img: Optional[QImage], zpl: str) -> None:
    """Guarda la imagen y el ZPL enviados. Nunca debe tumbar la impresión."""
    if not GUARDAR_ARCHIVOS_DEBUG:
        return
    try:
        carpeta = _dir_diagnostico()
        if img is not None:
            img.save(str(carpeta / "debug_etiqueta.png"))
        (carpeta / "ultimo_envio.zpl").write_text(zpl, encoding="ascii")
        logger.debug("Archivos de depuración guardados en %s", carpeta)
    except OSError:
        logger.warning(
            "No se pudieron guardar los archivos de depuración", exc_info=True
        )


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
        logger.warning("No se encontró la imagen %s", ruta)
        return None

    pixmap = QPixmap(ruta)
    if pixmap.isNull():
        logger.warning("La imagen %s está dañada o no se pudo leer", ruta)
        return None
    return pixmap


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
    consecutivo = _consecutivo_repository.obtener_consecutivo(params)
    logger.debug("Consecutivo de etiqueta obtenido: %s", consecutivo)
    return consecutivo


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

    # Aviso: [-7:] y [-4:] cortan en silencio si el dato es más largo.
    if len(str(lote)) > 7:
        logger.warning("Lote %r tiene más de 7 caracteres; el QR usa %r", lote, lote_fmt)
    if len(str(cdgo_plu)) > 4:
        logger.warning("PLU %r tiene más de 4 caracteres; el QR usa %r", cdgo_plu, plu_fmt)

    if peso_neto_kg is not None:
        # Ej.: 3.25 kg -> "03025" (el punto decimal se reemplaza por 0)
        peso_fmt = f"{round(peso_neto_kg, 2):05.2f}".replace(".", "0")
    else:
        logger.warning("Peso None: el QR queda con peso 00000")
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

    # Tipo de conservación del vencimiento: "refrigerado" | "congelado"
    tipo_conservacion: str = "refrigerado"


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
    tipo_conservacion: str = "refrigerado",      # NUEVO
) -> DatosEtiquetaFrescas:

    fecha_produccion = fechas._asegurar_date(fecha_produccion)
    fecha_sacrificio = fechas._asegurar_date(fecha_sacrificio)
    fecha_vencimiento_str = fechas._asegurar_date(fecha_vencimiento_str)

    # Valor inválido o vacío -> refrigerado
    if tipo_conservacion not in ETIQUETA_VENCIMIENTO:
        tipo_conservacion = "refrigerado"

    # El peso se obtiene UNA sola vez para que el QR y el texto de la
    # etiqueta muestren exactamente el mismo valor.
    peso_neto_kg = (
        peso_bascula
        if peso_bascula is not None
        else bascula_service.obtener_ultimo_peso()
    )

    logger.info(
        "Construyendo etiqueta: plu=%s lote=%s peso=%s conservacion=%s",
        producto.cdgo_plu, lote, peso_neto_kg, tipo_conservacion,
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
        tipo_conservacion=tipo_conservacion,
    )


def crear_datos_ejemplo() -> DatosEtiquetaFrescas:
    """
    Datos FIJOS para la ventana de ajuste y las impresiones de prueba.
    No usa base de datos, báscula ni consecutivos: se puede llamar las
    veces que se quiera sin gastar números de etiqueta.
    """
    hoy = date.today()
    vencimiento = hoy + timedelta(days=7)
    contenido_qr = _generar_contenido_qr(
        lote="0001234", nivel_limpieza=1, cdgo_plu="1234", piezas=1,
        fecha_vencimiento_str=vencimiento, peso_neto_kg=1.0,
    )
    return DatosEtiquetaFrescas(
        cdgo_plu="1234",
        nom_prog="PRODUCTO DE PRUEBA",
        descripcion="1234-PRODUCTO DE PRUEBA",
        lote="0001234",
        nivel_limpieza=1,
        peso_neto_kg=1.0,

        fecha_fabricacion=hoy,
        fecha_sacrificio=_formatear_fecha(hoy),
        nom_impr_etiq="PRUEBA",
        numEspecie=None,
        fecha_vencimiento_str=vencimiento,

        fabricante_nombre="EMPRESA DE EJEMPLO S.A.S. NIT 000.000.000-0",
        fabricante_direccion="Calle de ejemplo 123 Zona Industrial",
        fabricante_ciudad="Ciudad",
        fabricante_telefono="0000000",

        temperatura_minima_c=TEMPERATURA_MINIMA_C,
        temperatura_maxima_c=TEMPERATURA_MAXIMA_C,
        recomendacion_conservacion=RECOMENDACION_CONSERVACION,
        recomendacion_uso=RECOMENDACION_USO,

        marca=crear_etiqueta_marca(),
        categoria="PRUEBA",
        codigo="PRUEBA #000000",

        qr_izquierda=contenido_qr,
        qr_derecha=contenido_qr,

    )


# ======================================================================
# DIBUJO (compartido entre impresión y vista previa)
# ======================================================================

def _dibujar_contenido_etiqueta(
    painter: QPainter,
    datos: DatosEtiquetaFrescas,
    alto_mm=None,
) -> None:
    """
    Dibuja la etiqueta completa (QR, textos, logo) sobre un QPainter cuyo
    sistema de coordenadas es ANCHO x alto (1 unidad = 0,1 mm).
    El diseño se adapta al alto: en etiquetas bajas el QR y las letras se
    achican; nunca crecen más que en el diseño original de 45 mm.
    """
    alto_mm, alto, _ = medidas_alto(alto_mm)

    # ---------------- Medidas derivadas (se adaptan al alto) ----------------
    # El QR se achica en etiquetas bajas (nunca por debajo de QR_MIN).
    qr_size = max(QR_MIN, min(QR_SIZE, round(QR_SIZE * alto / ALTO_REF)))
    alto_bloque_inferior = qr_size + SEPARACION_BLOQUES

    x_full = MARGEN
    ancho_full = ANCHO - (MARGEN * 2)

    # Zona central (entre los dos QR) para logo / categoría / código.
    x_entre_qr = MARGEN + qr_size + SEPARACION_QR
    ancho_entre_qr = ANCHO - (2 * x_entre_qr)

    # El QR respeta el mismo MARGEN que los demás lados.
    qr_y = alto - qr_size - MARGEN

    # El alto disponible entre el margen superior y la franja del QR se
    # reparte proporcionalmente entre las filas (según sus "pesos").
    pesos_filas = [42, 36, 40, 29, 30, 27, 32]
    alto_disponible = (qr_y - SEPARACION_BLOQUES) - MARGEN
    factor = alto_disponible / sum(pesos_filas)
    saltos = [round(peso * factor) for peso in pesos_filas]

    # Escala de letra y cajas: 1.0 con 45 mm o más; menor en etiquetas bajas.
    esc = min(1.0, alto_disponible / ALTO_TEXTO_REF)

    logger.debug(
        "Dibujo %dx%d mm: qr=%d alto_texto=%d escala_letra=%.2f",
        ANCHO_MM, alto_mm, qr_size, alto_disponible, esc,
    )
    if esc < ESCALA_MIN_AVISO:
        logger.warning(
            "Letra muy pequeña (escala %.2f) para %d mm de alto; "
            "revisa MARGEN y QR_SIZE", esc, alto_mm,
        )

    # ---------------- Funciones auxiliares ----------------

    def fuente(tamano: int, negrita: bool = False) -> QFont:
        font = QFont("Arial")
        font.setWeight(QFont.Weight.Bold if negrita else QFont.Weight.Normal)
        font.setPixelSize(max(1, round(tamano * esc)))
        return font

    def segmentos(contenido, negrita=False) -> list:
        """
        Convierte el contenido en una lista de segmentos (texto, negrita).

        - "texto"                     -> [("texto", negrita)]
        - ("Titulo:", "valor")        -> [("Titulo:", True), ("valor", False)]
        - [("a", True), ("b", False)] -> se usa tal cual
        """
        if isinstance(contenido, list):
            return [(str(t), bool(b)) for t, b in contenido]
        if isinstance(contenido, tuple):
            titulo, valor = contenido
            return [(str(titulo), True), (str(valor), False)]
        return [(str(contenido), negrita)]

    def ancho_texto(contenido, tamano, negrita=False) -> float:
        """Ancho real (unidades lógicas) que ocupa el contenido."""
        return sum(
            QFontMetricsF(fuente(tamano, b)).horizontalAdvance(t)
            for t, b in segmentos(contenido, negrita)
        )

    def texto(
        x, y, ancho, alto_caja, contenido,
        tamano=20,
        negrita=False,
        alineacion=Qt.AlignmentFlag.AlignLeft,
    ):
        # tamano y alto_caja son valores de DISEÑO: aquí se escalan.
        alto_px = alto_caja * esc
        segs = segmentos(contenido, negrita)

        # Un solo segmento: se deja que Qt alinee dentro de la caja.
        if len(segs) == 1:
            t, b = segs[0]
            painter.setFont(fuente(tamano, b))
            painter.drawText(QRectF(x, y, ancho, alto_px), alineacion, t)
            return

        # Varios segmentos: se dibujan uno a continuación del otro.
        medidos = [
            (t, fuente(tamano, b), QFontMetricsF(fuente(tamano, b)))
            for t, b in segs
        ]
        total = sum(m.horizontalAdvance(t) for t, _, m in medidos)

        if alineacion & Qt.AlignmentFlag.AlignRight:
            cursor = x + ancho - total
        elif alineacion & Qt.AlignmentFlag.AlignHCenter:
            cursor = x + (ancho - total) / 2
        else:
            cursor = x

        izq = Qt.AlignmentFlag.AlignLeft
        for t, f, m in medidos:
            w = m.horizontalAdvance(t)
            painter.setFont(f)
            painter.drawText(QRectF(cursor, y, w + 4, alto_px), izq, t)
            cursor += w

    def fila_dos_columnas(
        y, alto_fila, izquierda, derecha,
        tamano=27,
        negrita_der=False,
        prop_izq=0.5,
    ):
        ancho_izq = ancho_full * prop_izq
        texto(x_full, y, ancho_izq, alto_fila, izquierda, tamano=tamano)
        texto(
            x_full + ancho_izq, y, ancho_full - ancho_izq, alto_fila, derecha,
            tamano=tamano,
            negrita=negrita_der,
            alineacion=Qt.AlignmentFlag.AlignRight,
        )

    def fila_columnas(y, alto_fila, columnas, tamano=24):
        """
        Reparte N textos en una fila SIN que se monten:
        el primero queda pegado a la izquierda, el último a la derecha y el
        espacio sobrante se reparte en partes iguales entre ellos.
        Si no caben con una separación mínima, la letra de la fila se
        reduce hasta que quepan.
        """
        n = len(columnas)
        if n == 0:
            return

        t = tamano
        while True:
            anchos = [ancho_texto(c, t) for c in columnas]
            libre = ancho_full - sum(anchos)
            separacion = libre / (n - 1) if n > 1 else 0
            if separacion >= SEPARACION_MIN_COLUMNAS or t <= TAMANO_MIN_COLUMNAS:
                break
            t -= 1

        if t != tamano:
            logger.debug("Fila de columnas: letra reducida de %d a %d", tamano, t)
        if separacion < 0:
            logger.warning(
                "La fila no cabe ni con letra %d (faltan %.0f unidades)",
                t, -separacion,
            )

        x = x_full
        for contenido, w in zip(columnas, anchos):
            texto(x, y, w + 4, alto_fila, contenido, tamano=t)
            x += w + separacion

    def dibujar_logo_centrado(pixmap: Optional[QPixmap], x, y, ancho, alto_area):
        """
        Dibuja el logo conservando su proporción, centrado en el área dada.
        Se dibuja desde la imagen ORIGINAL (no pre-escalada) para evitar
        escalar dos veces y perder nitidez.
        """
        if pixmap is None or pixmap.isNull():
            return

        tam = pixmap.size().scaled(
            int(ancho), int(alto_area), Qt.AspectRatioMode.KeepAspectRatio
        )
        destino = QRectF(
            x + (ancho - tam.width()) / 2,
            y + (alto_area - tam.height()) / 2,
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
            QRectF(MARGEN, qr_y, qr_size, qr_size),
        )

    if datos.qr_derecha:
        dibujar_qr(
            painter, datos.qr_derecha,
            QRectF(ANCHO - MARGEN - qr_size, qr_y, qr_size, qr_size),
        )

    # ---------------- Parte superior (textos) ----------------

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
        ("Fecha Empacado:", f" {fecha_empaque}"),
        ("Contenido Neto:", peso_texto),
        tamano=24,
        prop_izq=0.42,
    )
    y += saltos[1]

    # Fecha beneficio | Lote | Nivel (si existe) | Fecha de vencimiento.
    columnas = [
        ("Fecha Beneficio:", f" {datos.fecha_sacrificio}"),
        ("Lote:", f" {datos.lote}"),
    ]
    if datos.nivel_limpieza is not None:
        columnas.append(("Nv:", f" {datos.nivel_limpieza}"))
        
    columnas.append(
        (
            ETIQUETA_VENCIMIENTO.get(datos.tipo_conservacion, "F.Vto:"),
            f" {_formatear_fecha(datos.fecha_vencimiento_str)}",
            #"F.Vto.Refrigeracion:",
            #f" {_formatear_fecha(datos.fecha_vencimiento_str)}",
        )
    )
    fila_columnas(y, 34, columnas, tamano=23)
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

    painter.setPen(QPen(Qt.GlobalColor.black, max(2, GROSOR_LINEA * esc)))
    painter.drawLine(
        int(x_full), int(y), int(x_full + ancho_full), int(y)
    )
    painter.setPen(Qt.GlobalColor.black)

    # ---------------- Bloque inferior: logo + categoría + código ----------------
    # Ocupa la franja entre los dos QR: empieza en la línea divisoria y
    # termina en el margen inferior.

    alto_categoria = 30     # valores de diseño: texto() los escala
    alto_codigo = 22
    espacio = 2

    alto_logo = (
        alto_bloque_inferior
        - (alto_categoria + alto_codigo) * esc
        - (espacio * 2)
    )
    y_logo = alto - MARGEN - alto_bloque_inferior
    y_categoria = y_logo + alto_logo + espacio
    y_codigo = y_categoria + alto_categoria * esc + espacio

    dibujar_logo_centrado(datos.marca, x_entre_qr, y_logo, ancho_entre_qr, alto_logo)

    texto(
        x_entre_qr, y_categoria, ancho_entre_qr, alto_categoria,
        datos.categoria,
        tamano=37, negrita=True,
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
        painter.drawRect(0, 0, ANCHO - 1, alto - 1)


# ======================================================================
# VISTA PREVIA (en memoria, no toca la impresora)
# ======================================================================

def generar_vista_previa_pixmap(
    datos: DatosEtiquetaFrescas,
    alto_mm=None,
) -> QPixmap:
    """
    Genera una imagen con el MISMO diseño que se imprime,
    para mostrarla en la interfaz.

    No toca la impresora física ni el perfil de la impresora.
    """
    alto_mm, alto, _ = medidas_alto(alto_mm)
    logger.debug("Vista previa %dx%d mm", ANCHO_MM, alto_mm)

    pixmap = QPixmap(ANCHO, alto)
    pixmap.fill(Qt.GlobalColor.white)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

    _dibujar_contenido_etiqueta(painter, datos, alto_mm)

    painter.end()
    return pixmap


# ======================================================================
# IMPRESIÓN (ZPL RAW directo a la Zebra)
# ======================================================================

def renderizar_para_zebra(datos: DatosEtiquetaFrescas, perfil=None) -> QImage:
    """
    Dibuja la etiqueta en una imagen de ANCHO_DOTS x alto_dots (800 x 240
    a 800 x 400), es decir, 1 píxel = 1 punto de la impresora.

    perfil (PerfilImpresora): alto y bordes que se cortan. El contenido se
    reduce y se centra dentro de la zona que sí sale. Sin perfil, ocupa
    toda la etiqueta. Esta es la MISMA imagen que se manda a imprimir.
    """
    if perfil is None:
        perfil = PerfilImpresora(alto_mm=ALTO_MM)
    elif not isinstance(perfil, PerfilImpresora):
        perfil = PerfilImpresora(alto_mm=perfil)   # compatibilidad: alto_mm suelto
    perfil = perfil.validado()

    alto_mm, alto, alto_dots = medidas_alto(perfil.alto_mm)
    x, y, escala = perfil.colocacion()
    logger.debug(
        "Renderizando para Zebra: %dx%d puntos, origen=(%.1f,%.1f), escala=%.3f",
        ANCHO_DOTS, alto_dots, x, y, escala,
    )

    img = QImage(ANCHO_DOTS, alto_dots, QImage.Format.Format_RGB32)
    img.fill(Qt.GlobalColor.white)

    painter = QPainter(img)
    # Sin suavizado: la impresora es solo blanco/negro, el suavizado
    # generaría grises que luego se pierden o engruesan al binarizar.
    painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, False)
    # Zona que sí sale + coordenadas lógicas -> puntos de la impresora.
    painter.translate(x, y)
    painter.scale((ANCHO_DOTS / ANCHO) * escala, (alto_dots / alto) * escala)

    _dibujar_contenido_etiqueta(painter, datos, alto_mm)

    painter.end()
    return img


_renderizar_para_zebra = renderizar_para_zebra   # nombre anterior


def generar_pdf_etiqueta(
    datos: DatosEtiquetaFrescas,
    ruta_pdf: str,
    alto_mm=None,
) -> None:
    """
    Genera un PDF de 100 mm x alto_mm con el MISMO diseño de la etiqueta.
    No usa impresora ni driver: escribe el archivo directamente.
    """
    alto_mm, alto, _ = medidas_alto(alto_mm)
    logger.info("Generando PDF %dx%d mm en %s", ANCHO_MM, alto_mm, ruta_pdf)

    writer = QPdfWriter(ruta_pdf)
    writer.setResolution(300)
    writer.setPageSize(
        QPageSize(QSizeF(ANCHO_MM, alto_mm), QPageSize.Unit.Millimeter)
    )
    writer.setPageMargins(QMarginsF(0, 0, 0, 0), QPageLayout.Unit.Millimeter)

    painter = QPainter(writer)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

    # Coordenadas lógicas -> toda la página del PDF.
    painter.setWindow(0, 0, ANCHO, alto)
    painter.setViewport(0, 0, writer.width(), writer.height())

    _dibujar_contenido_etiqueta(painter, datos, alto_mm)
    painter.end()


def _imprimir_con_driver(
    datos: DatosEtiquetaFrescas,
    nombre_impresora: str,
    alto_mm=None,
) -> None:
    """
    Camino por driver de Windows (QPrinter). Se adapta a cualquier tamaño
    de página que el driver reporte (muchos ignoran el tamaño personalizado
    y usan el más parecido de su catálogo), sin deformar ni recortar el
    diseño: se escala manteniendo la proporción y se centra.
    """
    alto_mm, alto, _ = medidas_alto(alto_mm)

    diagnostico = diagnosticar_impresora(nombre_impresora, ANCHO_MM, alto_mm)
    imprimir_log_diagnostico(diagnostico)

    impresora = crear_impresora(nombre_impresora, ANCHO_MM, alto_mm, margen_mm=0)
    painter = crear_painter(impresora)

    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

    # Área real imprimible que reporta el driver, en píxeles de dispositivo.
    layout = impresora.pageLayout()
    area = layout.paintRectPixels(impresora.resolution())

    # Escala máxima que cabe SIN deformar: la menor entre ancho y alto.
    escala = min(area.width() / ANCHO, area.height() / alto)
    ancho_dibujo = ANCHO * escala
    alto_dibujo = alto * escala

    # Centrado dentro del área real.
    x = area.x() + (area.width() - ancho_dibujo) / 2
    y = area.y() + (area.height() - alto_dibujo) / 2

    logger.info(
        "Driver: area=%dx%d px, escala=%.3f, origen=(%.0f,%.0f)",
        area.width(), area.height(), escala, x, y,
    )

    painter.setWindow(0, 0, ANCHO, alto)
    painter.setViewport(int(x), int(y), int(ancho_dibujo), int(alto_dibujo))

    _dibujar_contenido_etiqueta(painter, datos, alto_mm)
    painter.end()


# ----------------------------------------------------------------------
# Envío a la Zebra (compartido por la impresión normal y las pruebas)
# ----------------------------------------------------------------------

def _es_destino_pdf(nombre_impresora: str) -> bool:
    destino = nombre_impresora.lower()
    return destino.endswith(".pdf") or "pdf" in destino


def _advertir_dpi(nombre_impresora: str) -> None:
    """Escribe una advertencia en el log si la impresora no es de 203 DPI."""
    dpi = detectar_dpi(nombre_impresora)
    if dpi is None:
        logger.info("DPI de %r: no se pudo detectar (se asume 203)", nombre_impresora)
    elif not dpi_es_esperado(dpi):
        logger.warning(
            "La impresora %r parece ser de %s DPI; el programa está calibrado "
            "para 203 DPI y la etiqueta saldrá más pequeña",
            nombre_impresora, dpi,
        )
    else:
        logger.info("DPI de %r: %s", nombre_impresora, dpi)


def _registrar_diagnostico_raw(nombre_impresora: str) -> None:
    diagnostico = diagnosticar_impresora_raw(nombre_impresora)
    imprimir_log_diagnostico_raw(diagnostico)


def _enviar_zpl_con_log(
    nombre_impresora: str,
    zpl: str,
    img: Optional[QImage] = None,
) -> None:
    logger.info("ZPL generado: %d caracteres", len(zpl))
    _guardar_debug(img, zpl)

    try:
        enviar_zpl(nombre_impresora, zpl)
    except Exception:
        logger.exception("Falló el envío del ZPL a %r", nombre_impresora)
        raise

    logger.info("ZPL enviado a %r sin errores", nombre_impresora)


def _enviar_imagen(
    nombre_impresora: str,
    img: QImage,
    desplaz_x: int = 0,
    desplaz_y: int = 0,
) -> None:
    zpl = imagen_a_zpl(
        img, MEDIO_ZEBRA, desplaz_x=desplaz_x, desplaz_y=desplaz_y,
    )
    _enviar_zpl_con_log(nombre_impresora, zpl, img)


def _resolver_perfil(nombre_impresora: str, alto_mm, perfil):
    """
    (perfil efectivo, sin_perfil_guardado)
    Prioridad: perfil recibido > perfil guardado de la impresora > por
    defecto. Un alto_mm explícito reemplaza el alto del perfil.
    """
    if perfil is not None:
        efectivo, sin_perfil = perfil.validado(), False
    else:
        guardado = cargar_perfil(nombre_impresora)
        sin_perfil = guardado is None
        efectivo = guardado if guardado is not None else PerfilImpresora(alto_mm=ALTO_MM)

    if alto_mm is not None:
        efectivo = replace(efectivo, alto_mm=normalizar_alto_mm(alto_mm))
    return efectivo, sin_perfil


def imprimir_etiqueta_frescas(
    datos: DatosEtiquetaFrescas,
    nombre_impresora: str,
    alto_mm=None,
    perfil=None,
) -> None:
    """
    Decide cómo imprimir según el destino:
      - ruta que termina en .pdf        -> archivo PDF directo
      - impresora virtual con 'pdf'     -> driver de Windows (QPrinter)
      - cualquier otra (Godex/Zebra)    -> ZPL RAW

    alto_mm y perfil son opcionales. Sin ellos se usa el perfil guardado de
    la impresora (o, si no tiene, ALTO_MM y DESPLAZ_X/Y), así el código que
    ya llamaba con dos argumentos sigue funcionando.
    """
    perfil, sin_perfil = _resolver_perfil(nombre_impresora, alto_mm, perfil)
    alto_mm, _, alto_dots = medidas_alto(perfil.alto_mm)

    logger.info(
        "IMPRIMIR impresora=%r etiqueta=%dx%d mm (%dx%d puntos) %s",
        nombre_impresora, ANCHO_MM, alto_mm, ANCHO_DOTS, alto_dots,
        "SIN perfil guardado" if sin_perfil else perfil,
    )

    if nombre_impresora.lower().endswith(".pdf"):
        generar_pdf_etiqueta(datos, nombre_impresora, alto_mm)
        return

    if "pdf" in nombre_impresora.lower():
        logger.info("Destino: driver de Windows (QPrinter)")
        _imprimir_con_driver(datos, nombre_impresora, alto_mm)
        return

    logger.info(
        "Destino: ZPL RAW | prueba=%s medio=%s", PRUEBA_ZPL, MEDIO_ZEBRA,
    )

    _advertir_dpi(nombre_impresora)
    _registrar_diagnostico_raw(nombre_impresora)

    img = None
    if PRUEBA_ZPL == "A":
        zpl = zpl_regla_prueba(ANCHO_DOTS, alto_dots, MEDIO_ZEBRA)

    elif PRUEBA_ZPL == "B":
        zpl = zpl_marco_prueba(
            ANCHO_DOTS, alto_dots, MEDIO_ZEBRA, desplaz_x=0, desplaz_y=0
        )

    elif PRUEBA_ZPL == "C":
        img = renderizar_para_zebra(datos, perfil)   # se renderiza UNA vez
        # Con perfil, el ajuste ya está aplicado dentro de la imagen.
        desplaz_x, desplaz_y = (DESPLAZ_X, DESPLAZ_Y) if sin_perfil else (0, 0)
        logger.info("Desplazamiento heredado: (%s,%s)", desplaz_x, desplaz_y)
        zpl = imagen_a_zpl(
            img, MEDIO_ZEBRA, desplaz_x=desplaz_x, desplaz_y=desplaz_y,
        )

    else:
        raise ValueError("PRUEBA_ZPL debe ser 'A', 'B' o 'C'")

    _enviar_zpl_con_log(nombre_impresora, zpl, img)


# ======================================================================
# PRUEBAS DE IMPRESIÓN (no tocan consecutivos, base de datos ni báscula)
# ======================================================================

def _renderizar_reglas(alto_mm=None) -> QImage:
    """
    Etiqueta de prueba para MEDIR qué se corta en cada borde: marco pegado
    al borde y, en cada lado, una regla que cuenta hacia adentro (mm).
    Se imprime completa, sin aplicar ningún perfil.
    """
    alto_mm, _, alto_dots = medidas_alto(alto_mm)
    w, h = ANCHO_DOTS, alto_dots

    img = QImage(w, h, QImage.Format.Format_RGB32)
    img.fill(Qt.GlobalColor.white)

    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, False)
    p.setRenderHint(QPainter.RenderHint.TextAntialiasing, False)
    negro = Qt.GlobalColor.black

    paso = DOTS_POR_MM          # una marca por mm
    alcance = 10                # mm que cubre cada regla
    cx, cy = w // 2, h // 2

    # Marco pegado al borde: si un lado del marco no se ve, ese lado se corta.
    p.setPen(QPen(negro, 2))
    p.drawRect(1, 1, w - 2, h - 2)

    p.setPen(QPen(negro, 1))
    fuente = QFont("Arial")
    fuente.setPixelSize(12)
    p.setFont(fuente)

    # Líneas base de las cuatro reglas.
    p.drawLine(0, cy, alcance * paso, cy)                   # izquierda
    p.drawLine(w - alcance * paso, cy, w, cy)               # derecha
    p.drawLine(cx, 0, cx, alcance * paso)                   # arriba
    p.drawLine(cx, h - alcance * paso, cx, h)               # abajo

    centro_h = Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop
    izq_v = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter

    for mm in range(alcance + 1):
        d = mm * paso
        largo = 16 if mm % 2 == 0 else 8
        p.drawLine(d, cy - largo, d, cy)                    # izquierda
        p.drawLine(w - d, cy - largo, w - d, cy)            # derecha
        p.drawLine(cx, d, cx + largo, d)                    # arriba
        p.drawLine(cx, h - d, cx + largo, h - d)            # abajo

        if mm and mm % 2 == 0:                              # número cada 2 mm
            p.drawText(QRectF(d - 12, cy + 3, 24, 14), centro_h, str(mm))
            p.drawText(QRectF(w - d - 12, cy + 3, 24, 14), centro_h, str(mm))
            p.drawText(QRectF(cx + largo + 3, d - 7, 24, 14), izq_v, str(mm))
            p.drawText(QRectF(cx + largo + 3, h - d - 7, 24, 14), izq_v, str(mm))

    # Instrucciones en el centro.
    centro = Qt.AlignmentFlag.AlignCenter
    titulo = QFont("Arial")
    titulo.setPixelSize(18)
    titulo.setBold(True)
    p.setFont(titulo)
    p.drawText(QRectF(100, cy - 30, w - 200, 24), centro,
               f"PRUEBA DE BORDES  {ANCHO_MM} x {alto_mm} mm")
    fuente.setPixelSize(14)
    p.setFont(fuente)
    p.drawText(QRectF(100, cy, w - 200, 20), centro,
               "Anote el primer número visible en cada borde")

    p.end()
    return img


def imprimir_prueba_reglas(nombre_impresora: str, alto_mm=None) -> None:
    """
    Imprime la etiqueta de bordes (marco + reglas) para medir qué se corta.
    Solo para impresoras de etiquetas (ZPL); lanza ValueError con un
    mensaje claro si el destino es un PDF.
    """
    if _es_destino_pdf(nombre_impresora):
        raise ValueError(
            "La prueba de bordes solo se imprime en impresoras de etiquetas, "
            "no en una impresora o archivo PDF."
        )

    alto_mm, _, alto_dots = medidas_alto(alto_mm)
    logger.info(
        "PRUEBA DE BORDES impresora=%r etiqueta=%dx%d mm",
        nombre_impresora, ANCHO_MM, alto_mm,
    )
    _advertir_dpi(nombre_impresora)
    _registrar_diagnostico_raw(nombre_impresora)
    _enviar_imagen(nombre_impresora, _renderizar_reglas(alto_mm))


def imprimir_prueba_etiqueta(nombre_impresora: str, perfil) -> None:
    """
    Imprime una etiqueta de EJEMPLO con el perfil indicado (aunque todavía
    no esté guardado), para comprobar que no se corta. No consume
    consecutivos ni lee la báscula.
    """
    perfil = perfil.validado()
    logger.info("PRUEBA DE ETIQUETA impresora=%r %s", nombre_impresora, perfil)
    datos = crear_datos_ejemplo()

    if _es_destino_pdf(nombre_impresora):
        imprimir_etiqueta_frescas(datos, nombre_impresora, perfil=perfil)
        return

    _advertir_dpi(nombre_impresora)
    _registrar_diagnostico_raw(nombre_impresora)
    _enviar_imagen(nombre_impresora, renderizar_para_zebra(datos, perfil))