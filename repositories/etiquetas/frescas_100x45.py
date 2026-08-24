import random
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QFont

from .motor_impresion import (
    crear_impresora,
    crear_painter,
    dibujar_qr,
)

# --------------------------------------------------------------------
# TAMAÑO FÍSICO DE LA ETIQUETA (mm)
# --------------------------------------------------------------------
ANCHO_MM = 100
ALTO_MM = 45


# ======================================================================
# ⚠️ CONSTANTES QUEMADAS — sin fuente confirmada todavía
# ======================================================================

# fabricante: en el JSON viene fijo (no ligado a ninguna tabla que me
# hayas mostrado). Si más adelante hay una tabla de "sede"/"planta",
# se reemplaza esto por una consulta.
FABRICANTE_NOMBRE = "UNA EMPRESA SAS"
FABRICANTE_DIRECCION = "Cra. 126A #17-90 Int. 10"
FABRICANTE_CIUDAD = "Bogotá"
FABRICANTE_PAIS = "COL"
FABRICANTE_TELEFONO = "601-4187884"

# conservación: valores estándar del rótulo, no dependen del producto.
TEMPERATURA_MINIMA_C = 0
TEMPERATURA_MAXIMA_C = 4
RECOMENDACION_CONSERVACION = "Mantengase Refrigerado entre 0°C y 4°C"
RECOMENDACION_USO = "consumase bien cocido a temperatura superior de 70°C"

# categoría: el JSON la trae fija en "PREMIUM". Si en el futuro depende
# del producto/tipo de pieza, se vuelve parámetro en vez de constante.
CATEGORIA_DEFAULT = "PREMIUM"

CODIGO_PROCESO_DEFAULT = "produccion-p307"


def obtener_nombre_empresa(id_empresa=None) -> str:
    """
    ⚠️ QUEMADO por ahora.

    La tabla `emprsas` tiene múltiples registros (multi-empresa/sede),
    así que antes de armar un ObtenerEmpresaRepository real hace falta
    definir CUÁL empresa aplica para este lote/usuario (¿por planta?
    ¿por usuario logueado? ¿parámetro de configuración?). Mientras
    tanto, devuelve un nombre fijo.
    """
    return "UNA EMPRESA SAS"


def obtener_peso_neto(peso_bascula: Optional[float] = None) -> float:
    """
    Si se conecta la báscula real, pásale su lectura en peso_bascula.
    Mientras tanto (pruebas), genera un peso aleatorio creíble.
    """
    if peso_bascula is not None:
        return round(float(peso_bascula), 3)
    return round(random.uniform(0.5, 8.0), 3)


def construir_codigo(nombre_usuario: str, numero_ticket: Optional[int] = None) -> str:
    """
    Formato observado: "<usuario> produccion-p307 #<numero>"
    ⚠️ El número (#16831764 en tu ejemplo) no sabemos de dónde sale
    todavía -> aleatorio de 8 dígitos si no se pasa uno real.
    """
    if numero_ticket is None:
        numero_ticket = random.randint(10_000_000, 99_999_999)
    return f"{nombre_usuario} {CODIGO_PROCESO_DEFAULT} #{numero_ticket}"


def _generar_contenido_qr(
    id_registro,
    lote,
    otros_numeros: str = "",
    fecha: Optional[datetime] = None,
) -> str:
    """
    Formato que describiste al escanear:
        <id> - <lote> - <otros números aún no definidos> - <ddmmaaaa actual>
    ⚠️ "otros_numeros" queda vacío hasta que definas qué representan.
    """
    fecha = fecha or datetime.now()
    partes = [str(id_registro), str(lote)]
    if otros_numeros:
        partes.append(str(otros_numeros))
    partes.append(fecha.strftime("%d%m%Y"))
    return "-".join(partes)


# ======================================================================
# DATOS DE LA ETIQUETA
# ======================================================================

@dataclass
class DatosEtiquetaFrescas:
    # producto
    cdgo_plu: str
    nom_prog: str
    descripcion: str
    lote: str
    nivel_limpieza: Optional[int]
    peso_neto_kg: float

    # fechas
    fecha_fabricacion: str
    fecha_sacrificio: str
    fecha_vencimiento_refrigeracion: str

    # fabricante
    fabricante_nombre: str
    fabricante_direccion: str
    fabricante_ciudad: str
    fabricante_pais: str
    fabricante_telefono: str

    # conservación
    temperatura_minima_c: float
    temperatura_maxima_c: float
    recomendacion_conservacion: str
    recomendacion_uso: str

    marca: str
    categoria: str
    codigo: str

    # contenido de cada QR (izquierda/derecha); None = no se dibuja ese QR
    qr_izquierda: Optional[str]
    qr_derecha: Optional[str]


def construir_datos_etiqueta(
    producto,                       # objeto con .cdgo_plu / .nom_prog (Producto o ProductoConImagenes)
    lote: str,
    fecha_produccion: str,
    nombre_usuario: str,
    tipo_limpieza_seleccionado: Optional[int] = None,
    peso_bascula: Optional[float] = None,
    numero_ticket: Optional[int] = None,
    fecha_sacrificio: str = "24/06/2026",                # ⚠️ QUEMADO
    fecha_vencimiento_refrigeracion: str = "19/08/2026",  # ⚠️ QUEMADO
) -> DatosEtiquetaFrescas:
    """
    Arma DatosEtiquetaFrescas combinando lo que sí viene de tus
    repositorios (producto, lote, fecha_produccion, tipo de limpieza
    seleccionado, usuario) con los valores quemados de arriba.
    """

    descripcion = f"{producto.cdgo_plu} {producto.nom_prog}".strip()

    contenido_qr = _generar_contenido_qr(
        id_registro=producto.cdgo_plu,
        lote=lote,
    )

    return DatosEtiquetaFrescas(
        cdgo_plu=str(producto.cdgo_plu),
        nom_prog=producto.nom_prog,
        descripcion=descripcion,
        lote=str(lote),
        nivel_limpieza=tipo_limpieza_seleccionado,
        peso_neto_kg=obtener_peso_neto(peso_bascula),

        fecha_fabricacion=fecha_produccion,  # este sí viene de datos reales
        fecha_sacrificio=fecha_sacrificio,
        fecha_vencimiento_refrigeracion=fecha_vencimiento_refrigeracion,

        fabricante_nombre=FABRICANTE_NOMBRE,
        fabricante_direccion=FABRICANTE_DIRECCION,
        fabricante_ciudad=FABRICANTE_CIUDAD,
        fabricante_pais=FABRICANTE_PAIS,
        fabricante_telefono=FABRICANTE_TELEFONO,

        temperatura_minima_c=TEMPERATURA_MINIMA_C,
        temperatura_maxima_c=TEMPERATURA_MAXIMA_C,
        recomendacion_conservacion=RECOMENDACION_CONSERVACION,
        recomendacion_uso=RECOMENDACION_USO,

        marca=obtener_nombre_empresa(),
        categoria=CATEGORIA_DEFAULT,
        codigo=construir_codigo(nombre_usuario, numero_ticket),

        # Mismo contenido en ambos por ahora — si cada QR debe llevar
        # algo distinto (ej. uno de trazabilidad, otro de la empresa),
        # avísame y separo la lógica.
        qr_izquierda=contenido_qr,
        qr_derecha=contenido_qr,
    )


# ======================================================================
# DIBUJO / IMPRESIÓN
# ======================================================================

# ======================================================================
# DIBUJO / IMPRESIÓN (SISTEMA DE COORDENADAS LOGICAS 1000x450)
# ======================================================================

def imprimir_etiqueta_frescas(
    datos: DatosEtiquetaFrescas,
    nombre_impresora: str
):
    impresora = crear_impresora(
        nombre_impresora,
        ANCHO_MM,
        ALTO_MM
    )

    painter = crear_painter(impresora)
    # ================================================================
    # LIENZO
    # ================================================================
    # Se conserva la orientación que ya utilizaba tu impresión:
    # etiqueta física de 100 x 45 mm.
    #
    # Trabajamos con coordenadas lógicas 1000 x 450 para tener
    # suficiente control sobre la distribución.
    # ================================================================

    painter.setWindow(0, 0, 450, 1000)

    painter.translate(450, 0)
    painter.rotate(90)

    # ================================================================
    # CONFIGURACIÓN GENERAL
    # ================================================================

    ANCHO = 1000
    ALTO = 450

    MARGEN = 30

    # QR más pequeños para liberar espacio para el texto
    QR_SIZE = 225

    # Separación entre QR y contenido
    SEPARACION_QR = 15

    # ================================================================
    # ÁREA DE LOS QR
    # ================================================================

    qr_y = ALTO - QR_SIZE - 20

    if datos.qr_izquierda:
        dibujar_qr(
            painter,
            datos.qr_izquierda,
            QRectF(
                MARGEN,
                qr_y,
                QR_SIZE,
                QR_SIZE
            )
        )

    if datos.qr_derecha:
        x_qr_derecha = ANCHO - MARGEN - QR_SIZE

        dibujar_qr(
            painter,
            datos.qr_derecha,
            QRectF(
                x_qr_derecha,
                qr_y,
                QR_SIZE,
                QR_SIZE
            )
        )

    # ================================================================
    # ÁREA CENTRAL DEL TEXTO
    # ================================================================

    x_texto = (
        MARGEN +
        (QR_SIZE + SEPARACION_QR if datos.qr_izquierda else 0)
    )

    x_final = (
        ANCHO -
        MARGEN -
        (QR_SIZE + SEPARACION_QR if datos.qr_derecha else 0)
    )

    ancho_texto = x_final - x_texto

    # ================================================================
    # FUNCIONES AUXILIARES
    # ================================================================

    def fuente(tamano, negrita=False):
        """
        Fuente controlada por píxeles para evitar que la impresora
        escale exageradamente el texto.
        """
        font = QFont("Arial")

        if negrita:
            font.setWeight(QFont.Weight.Bold)
        else:
            font.setWeight(QFont.Weight.Normal)

        font.setPixelSize(tamano)

        return font

    def texto(
        y,
        alto,
        contenido,
        tamano=18,
        negrita=False,
        alineacion=Qt.AlignmentFlag.AlignLeft
    ):
        """
        Dibuja una línea de texto dentro de un rectángulo controlado.
        """
        painter.setFont(fuente(tamano, negrita))

        painter.drawText(
            QRectF(
                x_texto,
                y,
                ancho_texto,
                alto
            ),
            alineacion,
            str(contenido)
        )

    # ================================================================
    # POSICIÓN INICIAL
    # ================================================================

    y = 22

    # ================================================================
    # PRODUCTO
    # ================================================================

    # Primera línea: PLU + nombre del producto
    texto(
        y,
        32,
        datos.descripcion,
        tamano=22,
        negrita=True,
        alineacion=Qt.AlignmentFlag.AlignCenter
    )

    y += 38

    # ================================================================
    # PESO + LOTE
    # ================================================================

    # Peso
    painter.setFont(fuente(19, True))

    painter.drawText(
        QRectF(
            x_texto,
            y,
            ancho_texto / 2,
            30
        ),
        Qt.AlignmentFlag.AlignLeft,
        f"Peso: {datos.peso_neto_kg:.3f} kg"
    )

    # Lote
    painter.setFont(fuente(17, True))

    nivel_texto = ""

    if datos.nivel_limpieza is not None:
        nivel_texto = f"  |  Nivel: {datos.nivel_limpieza}"

    painter.drawText(
        QRectF(
            x_texto + ancho_texto / 2,
            y,
            ancho_texto / 2,
            30
        ),
        Qt.AlignmentFlag.AlignRight,
        f"Lote: {datos.lote}{nivel_texto}"
    )

    y += 35

    # ================================================================
    # LÍNEA DIVISORIA
    # ================================================================

    painter.drawLine(
        int(x_texto),
        int(y),
        int(x_texto + ancho_texto),
        int(y)
    )

    y += 12

    # ================================================================
    # FECHAS
    # ================================================================

    # Fabricación
    painter.setFont(fuente(14, False))

    painter.drawText(
        QRectF(
            x_texto,
            y,
            ancho_texto / 3,
            25
        ),
        Qt.AlignmentFlag.AlignLeft,
        f"Fabricación: {datos.fecha_fabricacion}"
    )

    # Sacrificio
    painter.drawText(
        QRectF(
            x_texto + ancho_texto / 3,
            y,
            ancho_texto / 3,
            25
        ),
        Qt.AlignmentFlag.AlignCenter,
        f"Sacrificio: {datos.fecha_sacrificio}"
    )

    # Vencimiento
    painter.drawText(
        QRectF(
            x_texto + (ancho_texto * 2 / 3),
            y,
            ancho_texto / 3,
            25
        ),
        Qt.AlignmentFlag.AlignRight,
        f"Vence: {datos.fecha_vencimiento_refrigeracion}"
    )

    y += 32

    # ================================================================
    # FABRICANTE
    # ================================================================

    painter.setFont(fuente(13, True))

    painter.drawText(
        QRectF(
            x_texto,
            y,
            ancho_texto,
            22
        ),
        Qt.AlignmentFlag.AlignCenter,
        datos.fabricante_nombre
    )

    y += 21

    painter.setFont(fuente(11))

    direccion = (
        f"{datos.fabricante_direccion}  |  "
        f"{datos.fabricante_ciudad}, {datos.fabricante_pais}  |  "
        f"Tel: {datos.fabricante_telefono}"
    )

    painter.drawText(
        QRectF(
            x_texto,
            y,
            ancho_texto,
            20
        ),
        Qt.AlignmentFlag.AlignCenter,
        direccion
    )

    y += 27

    # ================================================================
    # CONSERVACIÓN
    # ================================================================

    painter.setFont(fuente(12, True))

    painter.drawText(
        QRectF(
            x_texto,
            y,
            ancho_texto,
            22
        ),
        Qt.AlignmentFlag.AlignCenter,
        datos.recomendacion_conservacion
    )

    y += 22

    # ================================================================
    # RECOMENDACIÓN DE USO
    # ================================================================

    painter.setFont(fuente(10))

    painter.drawText(
        QRectF(
            x_texto,
            y,
            ancho_texto,
            20
        ),
        Qt.AlignmentFlag.AlignCenter,
        datos.recomendacion_uso
    )

    y += 27

    # ================================================================
    # MARCA + CATEGORÍA
    # ================================================================

    painter.setFont(fuente(16, True))

    painter.drawText(
        QRectF(
            x_texto,
            y,
            ancho_texto,
            25
        ),
        Qt.AlignmentFlag.AlignCenter,
        f"{datos.marca}  |  {datos.categoria}"
    )

    y += 28

    # ================================================================
    # CÓDIGO DE TRAZABILIDAD
    # ================================================================

    painter.setFont(fuente(9))

    painter.drawText(
        QRectF(
            x_texto,
            y,
            ancho_texto,
            18
        ),
        Qt.AlignmentFlag.AlignCenter,
        datos.codigo
    )

    painter.end()
