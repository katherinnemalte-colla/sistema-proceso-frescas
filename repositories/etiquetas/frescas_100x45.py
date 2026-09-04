import os
import socket
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QFont, QFontDatabase, QPixmap
from repositories.empresa_repository import (
    obtener_ciudad_empresa_db,
    obtener_fabricado_empresa_db,
    obtener_telefono_empresa_db,
)
from repositories.consecutivo_repository import (
    ConsecutivoParametros,
    ConsecutivoRepository,
)
from utils import fechas
from services.bascula_service import bascula_service
from .motor_impresion import (
    crear_impresora,
    crear_painter,
    dibujar_qr,
)


# ======================================================================
# CONFIGURACIÓN GENERAL
# ======================================================================

ANCHO_MM = 100
ALTO_MM = 45

# Coordenadas lógicas de impresión.
ANCHO = 1000
ALTO = 450

# Margen general de la etiqueta.
MARGEN = 34

QR_SIZE = 169
SEPARACION_QR = 18
GROSOR_LINEA = 5

FABRICANTE_DIRECCION = "Cra. 126A #17-90 Int. 10"

TEMPERATURA_MINIMA_C = 0
TEMPERATURA_MAXIMA_C = 4
RECOMENDACION_CONSERVACION = "Mantengase Refrigerado entre 0°C y 4°C"
RECOMENDACION_USO = "consumase bien cocido a temperatura superior de 70°C"

NOMBRE_MARCA_DEFAULT = "Cialtis."
CODIGO_PROCESO_DEFAULT = socket.gethostname()

RUTA_ICONOS = os.path.join("assets", "icons")

_consecutivo_repository = ConsecutivoRepository()


# ======================================================================
# RECURSOS
# ======================================================================

def _ruta_icono(nombre_archivo: str) -> str:
    return os.path.join(RUTA_ICONOS, nombre_archivo)


def _ruta_fuente(nombre_archivo: str) -> Path:
    raiz_proyecto = Path(__file__).resolve().parent.parent.parent
    return raiz_proyecto / "assets" / "icons" / "fuentes" / nombre_archivo


def _cargar_pixmap(nombre_archivo: str) -> Optional[QPixmap]:
    """
    Carga una imagen sin escalarla.
    El escalado se hace únicamente al momento de imprimir para conservar
    la mejor calidad posible.
    """
    ruta = _ruta_icono(nombre_archivo)

    if not os.path.isfile(ruta):
        return None

    pixmap = QPixmap(ruta)

    if pixmap.isNull():
        return None

    return pixmap


def obtener_nombre_empresa() -> str:
    """
    Devuelve el nombre de la marca con la fuente Recoleta como respaldo.
    """
    ruta_fuente = _ruta_fuente("Recoleta.otf")

    font_id = QFontDatabase.addApplicationFont(str(ruta_fuente))
    familias = QFontDatabase.applicationFontFamilies(font_id)

    nombre_familia = next(
        (f for f in familias if "demo" not in f.lower()),
        familias[0] if familias else "Arial",
    )

    return (
        f'<span style="font-family:\'{nombre_familia}\'; font-size:20px;">'
        f"{NOMBRE_MARCA_DEFAULT}"
        f"</span>"
    )


def crear_etiqueta_marca() -> Optional[QPixmap]:
    """
    Carga únicamente la imagen de la marca.

    No devuelve QLabel porque la etiqueta se genera directamente con
    QPainter. El QPixmap se escala al tamaño adecuado al imprimir.
    """
    return _cargar_pixmap("logo_marca.png")


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
    peso_neto_kg: Optional[float] = None,
) -> str:
    lote_fmt = str(lote).zfill(7)[-7:]

    nivel_fmt = str(
        nivel_limpieza if nivel_limpieza is not None else 0
    ).zfill(2)

    plu_fmt = str(cdgo_plu).zfill(4)[-4:]

    if peso_neto_kg is not None:
        peso_redondeado = round(peso_neto_kg, 2)
        peso_fmt = f"{peso_redondeado:05.2f}".replace(".", "0")
    else:
        peso_fmt = "0" * 5

    piezas_fmt = str(piezas).zfill(2)

    fecha_fmt = (
        fecha_vencimiento_str.strftime("%d%m%Y")
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
    cod_empresa: int,
    tipo_limpieza_seleccionado: Optional[int] = None,
    peso_bascula: Optional[float] = None,
    numero_ticket: Optional[int] = None,
    fecha_sacrificio: Optional[date] = None,
    nom_impr_etiq: Optional[str] = None,
    numEspecie: Optional[int] = None,
) -> DatosEtiquetaFrescas:

    fecha_produccion = fechas._asegurar_date(fecha_produccion)
    fecha_sacrificio = fechas._asegurar_date(fecha_sacrificio)
    fecha_vencimiento_str = fechas._asegurar_date(fecha_vencimiento_str)

    descripcion = f"{producto.cdgo_plu}-{producto.nom_prog}".strip()

    fecha_sacrificio_str = (
        fecha_sacrificio.strftime("%d/%m/%Y")
        if fecha_sacrificio
        else ""
    )

    # Obtener el peso una sola vez para usar exactamente el mismo valor
    # tanto en el contenido del QR como en los datos de la etiqueta.
    peso_neto_kg = bascula_service.obtener_ultimo_peso()
    #peso_neto_kg = obtener_peso_neto(peso_bascula)
    print(f"'numero de PESO NETO': {peso_neto_kg}")
    contenido_qr = _generar_contenido_qr(
        lote=lote,
        cdgo_plu=producto.cdgo_plu,
        nivel_limpieza=tipo_limpieza_seleccionado,
        peso_neto_kg = peso_neto_kg,
        piezas=1,
        fecha_vencimiento_str=fecha_vencimiento_str,
    )

    return DatosEtiquetaFrescas(
        cdgo_plu=str(producto.cdgo_plu),
        nom_prog=producto.nom_prog,
        descripcion=descripcion,
        lote=str(lote),
        nivel_limpieza=tipo_limpieza_seleccionado,
        peso_neto_kg=peso_neto_kg,

        fecha_fabricacion=fecha_produccion,
        fecha_sacrificio=fecha_sacrificio_str,
        nom_impr_etiq=nom_impr_etiq or "",
        fecha_vencimiento_str=fecha_vencimiento_str,
        numEspecie=numEspecie,

        fabricante_nombre=obtener_fabricado_empresa_db(),
        fabricante_direccion=FABRICANTE_DIRECCION,
        fabricante_ciudad=obtener_ciudad_empresa_db(),
        fabricante_telefono=obtener_telefono_empresa_db(),

        temperatura_minima_c=TEMPERATURA_MINIMA_C,
        temperatura_maxima_c=TEMPERATURA_MAXIMA_C,
        recomendacion_conservacion=RECOMENDACION_CONSERVACION,
        recomendacion_uso=RECOMENDACION_USO,

        marca=crear_etiqueta_marca(),

        categoria=nom_impr_etiq or "",
        codigo=construir_codigo(nombre_usuario, numero_ticket),

        qr_izquierda=contenido_qr,
        qr_derecha=contenido_qr,
    )


# ======================================================================
# IMPRESIÓN
# ======================================================================

def imprimir_etiqueta_frescas(
    datos: DatosEtiquetaFrescas,
    nombre_impresora: str,
):
    impresora = crear_impresora(
        nombre_impresora,
        ANCHO_MM,
        ALTO_MM,
    )

    painter = crear_painter(impresora)

    # Mantiene la orientación utilizada por la impresora actual.
    painter.setWindow(0, 0, 450, 1000)
    painter.translate(450, 0)
    painter.rotate(90)

    # ==================================================================
    # ÁREAS
    # ==================================================================

    x_full = MARGEN
    ancho_full = ANCHO - (MARGEN * 2)

    x_entre_qr = MARGEN + QR_SIZE + SEPARACION_QR
    ancho_entre_qr = ANCHO - (
        2 * (MARGEN + QR_SIZE + SEPARACION_QR)
    )

    # ==================================================================
    # FUNCIONES DE DIBUJO
    # ==================================================================

    def fuente(tamano: int, negrita: bool = False) -> QFont:
        font = QFont("Arial")
        font.setWeight(
            QFont.Weight.Bold if negrita else QFont.Weight.Normal
        )
        font.setPixelSize(tamano)
        return font

    def texto(
        x,
        y,
        ancho,
        alto,
        contenido,
        tamano=20,
        negrita=False,
        alineacion=Qt.AlignmentFlag.AlignLeft,
    ):
        painter.setFont(fuente(tamano, negrita))
        painter.drawText(
            QRectF(x, y, ancho, alto),
            alineacion,
            str(contenido),
        )

    def fila_dos_columnas(
        y,
        alto,
        izquierda,
        derecha,
        tamano=27,
        negrita_izq=False,
        negrita_der=False,
        prop_izq=0.5,
    ):
        ancho_izq = ancho_full * prop_izq

        texto(
            x_full,
            y,
            ancho_izq,
            alto,
            izquierda,
            tamano=tamano,
            negrita=negrita_izq,
        )

        texto(
            x_full + ancho_izq,
            y,
            ancho_full - ancho_izq,
            alto,
            derecha,
            tamano=tamano,
            negrita=negrita_der,
            alineacion=Qt.AlignmentFlag.AlignRight,
        )

    def dibujar_logo_centrado(
        pixmap: Optional[QPixmap],
        x,
        y,
        ancho,
        alto,
    ):
        """
        Dibuja el logo manteniendo su proporción y aprovechando el espacio
        disponible entre los dos QR.
        """
        if pixmap is None or pixmap.isNull():
            return

        logo = pixmap.scaled(
            int(ancho),
            int(alto),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

        x_destino = x + (ancho - logo.width()) / 2
        y_destino = y + (alto - logo.height()) / 2

        painter.drawPixmap(
            int(x_destino),
            int(y_destino),
            logo,
        )

    # ==================================================================
    # QR
    # ==================================================================

    qr_y = ALTO - QR_SIZE - 20

    if datos.qr_izquierda:
        dibujar_qr(
            painter,
            datos.qr_izquierda,
            QRectF(MARGEN, qr_y, QR_SIZE, QR_SIZE),
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
                QR_SIZE,
            ),
        )

    # ==================================================================
    # PARTE SUPERIOR
    # ==================================================================

    # Descripción del producto.
    y = 14

    texto(
        x_full,
        y,
        ancho_full,
        38,
        datos.descripcion,
        tamano=31,
        negrita=True,
    )

    y += 42

    # Fecha de empaque | Peso / lote / nivel.
    nivel_texto = (
        f"   Nv:{datos.nivel_limpieza}"
        if datos.nivel_limpieza is not None
        else ""
    )

    fecha_empaque = (
        datos.fecha_fabricacion.strftime("%d/%m/%Y")
        if datos.fecha_fabricacion
        else ""
    )

    fila_dos_columnas(
        y,
        34,
        f"Fecha Empaque: {fecha_empaque}",
        (
            f"Peso Neto:{datos.peso_neto_kg:.2f}kg   "
            f"Lote:{datos.lote}{nivel_texto}"
        ),
        tamano=28,
        negrita_der=True,
        prop_izq=0.42,
    )
    print(f"Peso Neto:{datos.peso_neto_kg:.2f}kg   ")
    y += 36

    # Fecha beneficio | Fecha de vencimiento.
    fecha_vencimiento = (
        datos.fecha_vencimiento_str.strftime("%d/%m/%Y")
        if datos.fecha_vencimiento_str
        else ""
    )

    fila_dos_columnas(
        y,
        34,
        f"Fecha Beneficio: {datos.fecha_sacrificio}",
        f"F.Vto.Refrigeracion: {fecha_vencimiento}",
        tamano=28,
    )

    y += 40

    # ==================================================================
    # FABRICANTE
    # ==================================================================

    texto(
        x_full,
        y,
        ancho_full,
        30,
        f"{datos.fabricante_nombre}",
        tamano=25,
        negrita=True,
    )

    y += 29

    direccion = (
        f"{datos.fabricante_direccion} "
        f"Tel.{datos.fabricante_telefono} "
        f"{datos.fabricante_ciudad}, "
        f"{datos.fabricante_telefono}"
    )

    texto(
        x_full,
        y,
        ancho_full,
        28,
        direccion,
        tamano=24,
    )

    y += 30

    # ==================================================================
    # CONSERVACIÓN
    # ==================================================================

    texto(
        x_full,
        y,
        ancho_full,
        27,
        datos.recomendacion_conservacion,
        tamano=24,
    )

    y += 27

    texto(
        x_full,
        y,
        ancho_full,
        27,
        f"Recomendación de Uso: {datos.recomendacion_uso}",
        tamano=24,
    )

    y += 32

    # ==================================================================
    # LÍNEA DIVISORIA
    # ==================================================================

    pluma = painter.pen()
    pluma.setWidth(GROSOR_LINEA)
    painter.setPen(pluma)

    painter.drawLine(
        int(x_full),
        int(y),
        int(x_full + ancho_full),
        int(y),
    )

    painter.setPen(Qt.GlobalColor.black)

    y += 10

    alto_bloque_marca = ALTO - y - 20

    # Subimos el bloque completo
    y_marca = y + (alto_bloque_marca * 0.05)

    # ================================================================
    # LOGO GRANDE
    # ================================================================

    dibujar_logo_centrado(
        datos.marca,
        x_entre_qr,
        y_marca,
        ancho_entre_qr,
        175,
    )

    # ================================================================
    # CATEGORÍA DEBAJO DEL LOGO
    # ================================================================

    texto(
        x_entre_qr,
        y_marca + 125,
        ancho_entre_qr,
        35,
        datos.categoria,
        tamano=27,
        negrita=True,
        alineacion=Qt.AlignmentFlag.AlignCenter,
    )

    # ================================================================
    # CÓDIGO DEBAJO DE LA CATEGORÍA
    # ================================================================

    texto(
        x_entre_qr,
        y_marca + 163,
        ancho_entre_qr,
        22,
        datos.codigo,
        tamano=18,
        alineacion=Qt.AlignmentFlag.AlignCenter,
    )