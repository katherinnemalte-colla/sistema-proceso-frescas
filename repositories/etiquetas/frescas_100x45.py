import random
import os
from dataclasses import dataclass
from typing import List, Optional
from datetime import date
import socket
from dataclasses import dataclass
from datetime import datetime, timedelta
from PySide6.QtCore import QRectF, Qt
from PySide6.QtWidgets import QLabel
from PySide6.QtGui import QFont, QFontDatabase
from models.database import obtener_conexion  # el helper que uses para conectar
from repositories.empresa_repository import(
    obtener_fabricado_empresa_db,
    obtener_telefono_empresa_db,
    obtener_ciudad_empresa_db)
from repositories.obtener_tipo_limpieza_repository import(ObtenerTipoLimpiezaRepository)
from .motor_impresion import (
    crear_impresora,
    crear_painter,
    dibujar_qr,
)
from pathlib import Path
# --------------------------------------------------------------------
# TAMAÑO FÍSICO DE LA ETIQUETA (mm)
# --------------------------------------------------------------------
ANCHO_MM = 100
ALTO_MM = 45

FABRICANTE_DIRECCION = "Cra. 126A #17-90 Int. 10"
FABRICANTE_CIUDAD = "Bogotá"
#FABRICANTE_PAIS = "COL"
FABRICANTE_TELEFONO = "601-4187884"

# conservación: valores estándar del rótulo, no dependen del producto.
TEMPERATURA_MINIMA_C = 0
TEMPERATURA_MAXIMA_C = 4
RECOMENDACION_CONSERVACION = "Mantengase Refrigerado entre 0°C y 4°C"
RECOMENDACION_USO = "consumase bien cocido a temperatura superior de 70°C"


#NOMBRE_MARCA_DEFAULT = "Cialta"
CODIGO_PROCESO_DEFAULT = socket.gethostname()

def calcular_fecha_vencimiento(
    fecha_fabricacion: datetime,
    dia_refr: Optional[int],
) -> Optional[datetime]:
    if dia_refr is None:
        return None
    return fecha_fabricacion + timedelta(days=dia_refr)

# Al inicio del archivo o fuera de cualquier clase (columna 0):
def obtener_nombre_empresa() -> str:
    raiz_proyecto = Path(__file__).resolve().parent.parent.parent
    ruta_fuente = raiz_proyecto / "assets" / "icons" / "fuentes" / "OPTITimesRoman-Italic.otf"

    font_id = QFontDatabase.addApplicationFont(str(ruta_fuente))


    return font_id


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
    lote,
    nivel_limpieza,
    cdgo_plu,
    #pso
    piezas,
    fecha_fabricacion=Optional[datetime],
) -> str:
    #fecha = fecha or datetime.now()
    partes = lote,nivel_limpieza,cdgo_plu,piezas,fecha_fabricacion
    #partes.append(fecha_fabricacion.strftime("%d%m%Y"))

    return partes

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
    fecha_sacrificio: Optional[date]
    nom_impr_etiq: str         
    fecha_vencimiento_refrigeracion: str

    # fabricante
    fabricante_nombre: str
    fabricante_direccion: str
    fabricante_ciudad: str
    #fabricante_pais: str
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
    fecha_produccion: datetime,
    nombre_usuario: str,
    cod_empresa: int,
    tipo_limpieza_seleccionado: Optional[int] = None,
    peso_bascula: Optional[float] = None,
    numero_ticket: Optional[int] = None,
    fecha_sacrificio: Optional[str] = None,                # ⚠️ QUEMADO
    nom_impr_etiq: Optional[str] = None,
    fecha_vencimiento_refrigeracion: str = "19/08/2026",  # ⚠️ QUEMADO
) -> DatosEtiquetaFrescas:
 
    descripcion = f"{producto.cdgo_plu}-{producto.nom_prog}".strip()

    repo_limpieza = ObtenerTipoLimpiezaRepository(obtener_conexion)
    ficha_tecnica = repo_limpieza.obtener_ficha_tecnica_producto(
        plu=producto.cdgo_plu, cod_empresa=cod_empresa
    )

    fecha_vencimiento = calcular_fecha_vencimiento(
        fecha_fabricacion=fecha_produccion,
        dia_refr=ficha_tecnica.dia_refr if ficha_tecnica else None,
    )
    fecha_vencimiento_str = (
        fecha_vencimiento.strftime("%d/%m/%Y") if fecha_vencimiento else ""
    )

    peso_neto = obtener_peso_neto(peso_bascula)

    contenido_qr = _generar_contenido_qr(
        lote=lote,
        cdgo_plu = producto.cdgo_plu,
        nivel_limpieza=tipo_limpieza_seleccionado,
        #peso_neto_kg
        #fecha_fabricacion= fecha_produccion,
        peso_neto_kg=peso_neto,
        piezas=1,
        fecha_vencimiento=fecha_vencimiento,
    )
    ##
    repo_limpieza = ObtenerTipoLimpiezaRepository(obtener_conexion)
    resultado_sacrificio = repo_limpieza.obtener_fecha_sacrificio(int(lote))

    fecha_sacrificio_str = (
        resultado_sacrificio.scrfcio.strftime("%d/%m/%Y")
        if resultado_sacrificio and resultado_sacrificio.scrfcio
        else ""
    )
    nom_impr_etiq_valor = resultado_sacrificio.nom_impr_etiq if resultado_sacrificio else ""
    print(f"el valor de categoria es, {nom_impr_etiq_valor}")
    return DatosEtiquetaFrescas(
        cdgo_plu=str(producto.cdgo_plu),
        nom_prog=producto.nom_prog,
        descripcion=descripcion,
        lote=str(lote),
        nivel_limpieza=tipo_limpieza_seleccionado,
        peso_neto_kg=obtener_peso_neto(peso_bascula),   #reviasr cuando este el peso de la bascula real 

        fecha_fabricacion=fecha_produccion.strftime("%d/%m/%Y"),
        #fecha_fabricacion=fecha_produccion,  # este sí viene de datos reales
        fecha_sacrificio= fecha_sacrificio_str or "",
        nom_impr_etiq=nom_impr_etiq or "",
        fecha_vencimiento_refrigeracion=fecha_vencimiento_str,

        fabricante_nombre=obtener_fabricado_empresa_db(),
        fabricante_direccion=FABRICANTE_DIRECCION,
        fabricante_ciudad=obtener_ciudad_empresa_db(),
        #fabricante_pais=FABRICANTE_PAIS,
        fabricante_telefono=obtener_telefono_empresa_db(),

        temperatura_minima_c=TEMPERATURA_MINIMA_C,
        temperatura_maxima_c=TEMPERATURA_MAXIMA_C,
        recomendacion_conservacion=RECOMENDACION_CONSERVACION,
        recomendacion_uso=RECOMENDACION_USO,

        marca=obtener_nombre_empresa(),
        #categoria=CATEGORIA_DEFAULT,
        categoria=nom_impr_etiq_valor or "",
        codigo=construir_codigo(nombre_usuario, numero_ticket),

        qr_izquierda=contenido_qr,
        qr_derecha=contenido_qr,
    )
    

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

    painter.setWindow(0, 0, 450, 1000)
    painter.translate(450, 0)
    painter.rotate(90)
    
    # ================================================================
    # CONFIGURACIÓN GENERAL
    # ================================================================

    ANCHO = 1000
    ALTO = 450

    MARGEN = 39
    QR_SIZE = 169
    SEPARACION_QR = 18
    GROSOR_LINEA = 5

    # ================================================================
    # DOS ZONAS DE TEXTO:
    #
    # - Zona COMPLETA (margen a margen): todo lo que va ARRIBA de la
    #   línea divisoria (descripción, fechas, fabricante, dirección,
    #   conservación). En la etiqueta real este bloque ocupa todo el
    #   ancho, no solo el espacio entre los dos QR.
    # - Zona ANGOSTA (entre los dos QR): solo la fila de abajo
    #   (marca + categoría + código), que sí debe quedar centrada
    #   entre los QR.
    # ================================================================

    x_full = MARGEN
    ancho_full = ANCHO - (MARGEN * 2)

    x_entre_qr = MARGEN + QR_SIZE + SEPARACION_QR
    ancho_entre_qr = ANCHO - (2 * (MARGEN + QR_SIZE + SEPARACION_QR))

    # ================================================================
    # FUNCIONES AUXILIARES
    # ================================================================

    def fuente(tamano, negrita=False):
        font = QFont("Arial")
        font.setWeight(QFont.Weight.Bold if negrita else QFont.Weight.Normal)
        font.setPixelSize(tamano)
        return font

    def texto(x, y, ancho, alto, contenido, tamano=20, negrita=False,
              alineacion=Qt.AlignmentFlag.AlignLeft):
        painter.setFont(fuente(tamano, negrita))
        painter.drawText(QRectF(x, y, ancho, alto), alineacion, str(contenido))

    def fila_dos_columnas(y, alto, izquierda, derecha, tamano=25,
                           negrita_izq=False, negrita_der=False, prop_izq=0.5):
        """
        Dibuja una fila con un texto a la izquierda y otro a la derecha,
        repartiendo el ancho completo — evita repetir el mismo cálculo
        de columnas en cada fila de dos textos.
        """
        ancho_izq = ancho_full * prop_izq
        texto(x_full, y, ancho_izq, alto, izquierda, tamano=tamano, negrita=negrita_izq)
        texto(
            x_full + ancho_izq, y, ancho_full - ancho_izq, alto, derecha,
            tamano=tamano, negrita=negrita_der,
            alineacion=Qt.AlignmentFlag.AlignRight
        )

    # ================================================================
    # ÁREA DE LOS QR (se dibujan primero, quedan fijos en las esquinas)
    # ================================================================

    qr_y = ALTO - QR_SIZE - 20

    if datos.qr_izquierda:
        dibujar_qr(painter, datos.qr_izquierda, QRectF(MARGEN, qr_y, QR_SIZE, QR_SIZE))

    if datos.qr_derecha:
        x_qr_derecha = ANCHO - MARGEN - QR_SIZE
        dibujar_qr(painter, datos.qr_derecha, QRectF(x_qr_derecha, qr_y, QR_SIZE, QR_SIZE))

    # ================================================================
    # FILA 1 — DESCRIPCIÓN DEL PRODUCTO (ancho completo, izquierda)
    # ================================================================

    y = 18

    texto(x_full, y, ancho_full, 32, datos.descripcion, tamano=24, negrita=True)

    y += 38

    # ================================================================
    # FILA 2 — Fecha Fabricación (izq.)  |  Peso / Lote / Nivel (der.)
    # ================================================================

    nivel_texto = f"   Nv:{datos.nivel_limpieza}" if datos.nivel_limpieza is not None else ""
    fila_dos_columnas(
        y, 28,
        f"Fecha Empaque: {datos.fecha_fabricacion}",
        f"Peso Neto:{datos.peso_neto_kg:.2f}kg   Lote:{datos.lote}{nivel_texto}",
        tamano=25, negrita_der=True, prop_izq=0.42
    )

    y += 30

    # ================================================================
    # FILA 3 — Fecha Sacrificio (izq.)  |  F.Vto. Refrigeración (der.)
    # ================================================================

    fila_dos_columnas(
        y, 28,
        f"Fecha Beneficio: {datos.fecha_sacrificio}",
        f"F.Vto. Refrigeracion: {datos.fecha_vencimiento_refrigeracion}",
        tamano=25
    )

    y += 36

    # ================================================================
    # FABRICANTE (ancho completo, izquierda)
    # ================================================================

    texto(x_full, y, ancho_full, 26, f" {datos.fabricante_nombre}",
          tamano=20, negrita=True)

    y += 26

    # ⚠️ En la foto de la etiqueta real el teléfono aparece DOS veces
    # (antes y después de la ciudad). Se deja una sola vez aquí porque
    # todo indica que es un error de la plantilla original; avísame si
    # en realidad debe repetirse.
    direccion = (
        f"{datos.fabricante_direccion} Tel.{datos.fabricante_telefono} "
        f"{datos.fabricante_ciudad}, {datos.fabricante_telefono}"
    )
    texto(x_full, y, ancho_full, 22, direccion, tamano=20)

    y += 26

    # ================================================================
    # CONSERVACIÓN + RECOMENDACIÓN DE USO (ancho completo, izquierda)
    # ================================================================

    texto(x_full, y, ancho_full, 22, datos.recomendacion_conservacion, tamano=20)
    y += 22

    texto(x_full, y, ancho_full, 22, f"Recomendación de Uso: {datos.recomendacion_uso}",
          tamano=20)
    y += 28

    # ================================================================
    # LÍNEA DIVISORIA — ancho completo (margen a margen), más gruesa,
    # justo antes del bloque de QRs
    # ================================================================

    pluma = painter.pen()
    pluma.setWidth(GROSOR_LINEA)
    painter.setPen(pluma)
    painter.drawLine(int(x_full), int(y), int(x_full + ancho_full), int(y))
    painter.setPen(Qt.GlobalColor.black)  # se restaura para el texto que sigue
    y += 12

    # ================================================================
    # BLOQUE ENTRE LOS DOS QR: MARCA + CATEGORÍA + CÓDIGO
    # (esta parte sí va centrada, solo en el espacio entre los QR)
    # ================================================================

    alto_bloque_marca = ALTO - y - 20
    y_marca = y + (alto_bloque_marca * 0.30)

    texto(x_entre_qr, y_marca, ancho_entre_qr, 40, datos.marca,
          tamano=42, negrita=True, alineacion=Qt.AlignmentFlag.AlignCenter)

    texto(x_entre_qr, y_marca + 42, ancho_entre_qr, 32, datos.categoria,
          tamano=26, negrita=True, alineacion=Qt.AlignmentFlag.AlignCenter)

    texto(x_entre_qr, y_marca + 80, ancho_entre_qr, 20, datos.codigo,
          tamano=17, alineacion=Qt.AlignmentFlag.AlignCenter)

    painter.end()