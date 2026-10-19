"""
Ventana de ajuste de la etiqueta de frescas para UNA impresora.

- Se abre desde un botón junto al combo de impresoras (ver ficha técnica).
- Edita: alto de la etiqueta y lo que se CORTA en cada borde (izq., arriba,
  der., abajo). Cualquier usuario puede usarla; los valores se guardan por
  impresora en un JSON local del computador.
- Vista previa en vivo con la MISMA imagen que se manda a la impresora.
  Las franjas rojas son la parte que se corta.
- "Imprimir reglas" y "Imprimir etiqueta de ejemplo" usan datos fijos: no
  consumen consecutivos, no leen la báscula ni cambian la vista previa de
  la ficha técnica.
- No toca ningún ajuste de la impresora (medio, oscuridad, velocidad...).

Uso:
    dialogo = DialogoAjusteEtiqueta(nombre_impresora, parent=self)
    if dialogo.exec() == QDialog.DialogCode.Accepted:
        ...  # se guardó un ajuste nuevo: refresca lo que necesites
"""

import logging
from dataclasses import asdict
from typing import Callable, Optional

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QColor, QImage, QPainter, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QDoubleSpinBox,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from repositories.etiquetas import frescas_100x45 as frescas
from repositories.etiquetas.perfil_impresora import (
    ALTO_MM_MAX,
    ALTO_MM_MIN,
    ANCHO_MM,
    DOTS_POR_MM,
    DPI_ESPERADO,
    ESCALA_AVISO,
    ESCALA_MINIMA,
    PASO_MM,
    PERDIDA_MM_MAX,
    PerfilImpresora,
    cargar_perfil,
    detectar_dpi,
    dpi_es_esperado,
    guardar_perfil,
    nivel_escala,
)

logger = logging.getLogger(__name__)

_COLORES = {
    "ok": "#1b7f3b",
    "aviso": "#b26a00",
    "error": "#b00020",
    "info": "#555555",
}


def _estilo(color: str, negrita: bool = False) -> str:
    peso = "font-weight:bold;" if negrita else ""
    return f"color:{_COLORES[color]};{peso}"


class DialogoAjusteEtiqueta(QDialog):

    ANCHO_PANEL = 330        # columna de controles
    ANCHO_VISTA = 540        # vista previa
    ALTO_VISTA = 300

    def __init__(
        self,
        nombre_impresora: str,
        datos=None,
        parent: Optional[QWidget] = None,
    ):
        """
        nombre_impresora : nombre exacto de la impresora (el del combo).
        datos            : DatosEtiquetaFrescas para la vista previa. Si es
                           None se usan datos de ejemplo (no gasta nada).
        """
        super().__init__(parent)
        self._nombre = nombre_impresora
        self._datos = datos
        self._datos_ejemplo = None
        self._centrado = False
        self._ocupado = False

        guardado = cargar_perfil(nombre_impresora)
        self._tenia_perfil = guardado is not None
        self._inicial = guardado or PerfilImpresora(alto_mm=frescas.ALTO_MM)
        self._dpi = detectar_dpi(nombre_impresora)

        logger.info(
            "Ventana de ajuste abierta: impresora=%r perfil_guardado=%s dpi=%s",
            nombre_impresora, self._tenia_perfil, self._dpi,
        )
        if self._dpi is not None and not dpi_es_esperado(self._dpi):
            logger.warning(
                "La impresora %r parece ser de %s DPI (se esperan %s)",
                nombre_impresora, self._dpi, DPI_ESPERADO,
            )

        self.setWindowTitle(f"Ajuste de etiqueta - {nombre_impresora}")
        self.setModal(True)

        self._construir_interfaz()
        self._cargar_en_campos(self._inicial)

        # La vista previa se redibuja 150 ms después del último cambio.
        self._temporizador = QTimer(self)
        self._temporizador.setSingleShot(True)
        self._temporizador.setInterval(150)
        self._temporizador.timeout.connect(self._actualizar_vista_previa)

        self._conectar_cambios()
        self._actualizar_vista_previa()
        self._ajustar_tamano_a_pantalla()

    # ------------------------------------------------------------------
    # Construcción de la interfaz
    # ------------------------------------------------------------------

    def _spin_borde(self) -> QDoubleSpinBox:
        spin = QDoubleSpinBox()
        spin.setRange(0.0, PERDIDA_MM_MAX)
        spin.setSingleStep(PASO_MM)
        spin.setDecimals(1)
        spin.setSuffix(" mm")
        spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
        spin.setFixedWidth(90)
        return spin

    @staticmethod
    def _campo(titulo: str, spin: QWidget) -> QWidget:
        caja = QWidget()
        lay = QVBoxLayout(caja)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(2)
        etiqueta = QLabel(titulo)
        etiqueta.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(etiqueta)
        lay.addWidget(spin, alignment=Qt.AlignmentFlag.AlignCenter)
        return caja

    def _construir_interfaz(self) -> None:
        raiz = QVBoxLayout(self)

        cuerpo = QHBoxLayout()
        raiz.addLayout(cuerpo)

        # ---------------- Columna izquierda: controles ----------------
        # Ancho fijo: sin esto, los textos largos ensanchan toda la ventana.
        panel_izquierdo = QWidget()
        panel_izquierdo.setFixedWidth(self.ANCHO_PANEL)
        izquierda = QVBoxLayout(panel_izquierdo)
        izquierda.setContentsMargins(0, 0, 0, 0)
        cuerpo.addWidget(panel_izquierdo, 0, Qt.AlignmentFlag.AlignTop)

        izquierda.addWidget(QLabel(f"<b>Etiqueta de {ANCHO_MM} mm de ancho</b> (fijo)"))

        fila_alto = QHBoxLayout()
        fila_alto.addWidget(QLabel("Alto de la etiqueta:"))
        self._spin_alto = QSpinBox()
        self._spin_alto.setRange(ALTO_MM_MIN, ALTO_MM_MAX)
        self._spin_alto.setSuffix(" mm")
        self._spin_alto.setFixedWidth(90)
        fila_alto.addWidget(self._spin_alto)
        fila_alto.addStretch()
        izquierda.addLayout(fila_alto)

        grupo = QGroupBox("Lo que se corta en cada borde")
        rejilla = QGridLayout(grupo)
        self._spin_arr = self._spin_borde()
        self._spin_izq = self._spin_borde()
        self._spin_der = self._spin_borde()
        self._spin_aba = self._spin_borde()
        centro = QLabel("etiqueta")
        centro.setAlignment(Qt.AlignmentFlag.AlignCenter)
        centro.setFrameShape(QFrame.Shape.Box)
        centro.setMinimumSize(70, 40)
        rejilla.addWidget(self._campo("Arriba", self._spin_arr), 0, 1)
        rejilla.addWidget(self._campo("Izquierda", self._spin_izq), 1, 0)
        rejilla.addWidget(centro, 1, 1)
        rejilla.addWidget(self._campo("Derecha", self._spin_der), 1, 2)
        rejilla.addWidget(self._campo("Abajo", self._spin_aba), 2, 1)
        izquierda.addWidget(grupo)

        ayuda = QLabel(
            "1) Pulse «Imprimir reglas».\n"
            "2) En cada borde lea el primer número visible y escríbalo "
            "en ese lado (0 si el borde no se corta).\n"
            "3) Compruebe con «Imprimir etiqueta de ejemplo» y guarde."
        )
        ayuda.setWordWrap(True)
        ayuda.setStyleSheet(_estilo("info"))
        izquierda.addWidget(ayuda)

        self._lbl_estado = QLabel()
        self._lbl_estado.setWordWrap(True)
        izquierda.addWidget(self._lbl_estado)

        self._lbl_dpi = QLabel()
        self._lbl_dpi.setWordWrap(True)
        izquierda.addWidget(self._lbl_dpi)
        self._mostrar_dpi()

        self._btn_reglas = QPushButton("Imprimir reglas")
        self._btn_reglas.clicked.connect(self._imprimir_reglas)
        self._btn_ejemplo = QPushButton("Imprimir etiqueta de ejemplo")
        self._btn_ejemplo.clicked.connect(self._imprimir_ejemplo)
        izquierda.addWidget(self._btn_reglas)
        izquierda.addWidget(self._btn_ejemplo)
        izquierda.addStretch()

        # ---------------- Columna derecha: vista previa ----------------
        derecha = QVBoxLayout()
        cuerpo.addLayout(derecha)

        self._lbl_vista = QLabel()
        self._lbl_vista.setFixedSize(self.ANCHO_VISTA, self.ALTO_VISTA)
        self._lbl_vista.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._lbl_vista.setFrameShape(QFrame.Shape.StyledPanel)
        self._lbl_vista.setStyleSheet("background:#e4e4e4;")
        derecha.addWidget(self._lbl_vista)

        nota = QLabel(
            "Vista previa tal como se imprime (blanco y negro). "
            "Las franjas rojas son lo que se corta."
        )
        nota.setWordWrap(True)
        nota.setStyleSheet(_estilo("info"))
        derecha.addWidget(nota)
        derecha.addStretch()

        # ---------------- Botones inferiores ----------------
        inferior = QHBoxLayout()
        raiz.addLayout(inferior)
        self._btn_restaurar = QPushButton("Restaurar valores")
        self._btn_restaurar.clicked.connect(self._restaurar)
        self._btn_cancelar = QPushButton("Cancelar")
        self._btn_cancelar.clicked.connect(self.reject)
        self._btn_guardar = QPushButton("Guardar")
        self._btn_guardar.setDefault(True)
        self._btn_guardar.clicked.connect(self._guardar)
        inferior.addWidget(self._btn_restaurar)
        inferior.addStretch()
        inferior.addWidget(self._btn_cancelar)
        inferior.addWidget(self._btn_guardar)

    def _conectar_cambios(self) -> None:
        for spin in (self._spin_alto, self._spin_izq, self._spin_arr,
                     self._spin_der, self._spin_aba):
            spin.valueChanged.connect(self._programar_vista_previa)

    # ------------------------------------------------------------------
    # Valores <-> campos
    # ------------------------------------------------------------------

    def _perfil_actual(self) -> PerfilImpresora:
        return PerfilImpresora(
            alto_mm=self._spin_alto.value(),
            perdida_izq_mm=self._spin_izq.value(),
            perdida_arr_mm=self._spin_arr.value(),
            perdida_der_mm=self._spin_der.value(),
            perdida_aba_mm=self._spin_aba.value(),
        ).validado()

    def _cargar_en_campos(self, perfil: PerfilImpresora) -> None:
        perfil = perfil.validado()
        campos = (
            (self._spin_alto, perfil.alto_mm),
            (self._spin_izq, perfil.perdida_izq_mm),
            (self._spin_arr, perfil.perdida_arr_mm),
            (self._spin_der, perfil.perdida_der_mm),
            (self._spin_aba, perfil.perdida_aba_mm),
        )
        for spin, valor in campos:
            spin.blockSignals(True)
            spin.setValue(valor)
            spin.blockSignals(False)

    def _hay_cambios(self) -> bool:
        return self._perfil_actual() != self._inicial.validado()

    # ------------------------------------------------------------------
    # Vista previa
    # ------------------------------------------------------------------

    def _programar_vista_previa(self) -> None:
        self._temporizador.start()

    def _datos_para_vista(self):
        if self._datos is not None:
            return self._datos
        if self._datos_ejemplo is None:
            self._datos_ejemplo = frescas.crear_datos_ejemplo()
        return self._datos_ejemplo

    def _actualizar_vista_previa(self) -> None:
        perfil = self._perfil_actual()
        self._actualizar_estado(perfil)
        try:
            img = frescas.renderizar_para_zebra(self._datos_para_vista(), perfil)
            self._mostrar(img, perfil)
        except Exception:
            logger.exception("No se pudo generar la vista previa del ajuste")
            self._lbl_vista.setPixmap(QPixmap())
            self._lbl_vista.setText(
                "No se pudo generar la vista previa.\nRevise el archivo de log."
            )

    def _mostrar(self, img: QImage, perfil: PerfilImpresora) -> None:
        pixmap = QPixmap.fromImage(img)
        pintor = QPainter(pixmap)
        rojo = QColor(255, 0, 0, 80)
        w, h = pixmap.width(), pixmap.height()
        izq = round(perfil.perdida_izq_mm * DOTS_POR_MM)
        arr = round(perfil.perdida_arr_mm * DOTS_POR_MM)
        der = round(perfil.perdida_der_mm * DOTS_POR_MM)
        aba = round(perfil.perdida_aba_mm * DOTS_POR_MM)
        pintor.fillRect(0, 0, izq, h, rojo)
        pintor.fillRect(w - der, 0, der, h, rojo)
        pintor.fillRect(0, 0, w, arr, rojo)
        pintor.fillRect(0, h - aba, w, aba, rojo)
        pintor.end()

        self._lbl_vista.setText("")
        self._lbl_vista.setPixmap(
            pixmap.scaled(
                self.ANCHO_VISTA - 4, self.ALTO_VISTA - 4,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )

    # ------------------------------------------------------------------
    # Mensajes de estado
    # ------------------------------------------------------------------

    def _actualizar_estado(self, perfil: PerfilImpresora) -> None:
        escala = perfil.escala()
        porcentaje = round(escala * 100)
        nivel = nivel_escala(escala)

        if nivel == "ok":
            self._lbl_estado.setText(f"Contenido al {porcentaje} % del tamaño original.")
            self._lbl_estado.setStyleSheet(_estilo("ok"))
        elif nivel == "aviso":
            self._lbl_estado.setText(
                f"Atención: el contenido se reduce al {porcentaje} % y las "
                f"letras quedarán más pequeñas (conviene no bajar de "
                f"{round(ESCALA_AVISO * 100)} %)."
            )
            self._lbl_estado.setStyleSheet(_estilo("aviso", True))
        else:
            self._lbl_estado.setText(
                f"Valores no permitidos: el contenido quedaría al "
                f"{porcentaje} % (mínimo {round(ESCALA_MINIMA * 100)} %). "
                f"Reduzca lo que se corta o revise el alto."
            )
            self._lbl_estado.setStyleSheet(_estilo("error", True))

        permitido = nivel != "bloqueado" and not self._ocupado
        self._btn_guardar.setEnabled(permitido)
        self._btn_ejemplo.setEnabled(permitido)

    def _mostrar_dpi(self) -> None:
        dpi = self._dpi
        if dpi is None:
            self._lbl_dpi.setText(
                f"No se pudo detectar la resolución de la impresora; "
                f"se asumen {DPI_ESPERADO} DPI."
            )
            self._lbl_dpi.setStyleSheet(_estilo("info"))
        elif dpi_es_esperado(dpi):
            self._lbl_dpi.setText(f"Resolución detectada: {dpi} DPI.")
            self._lbl_dpi.setStyleSheet(_estilo("ok"))
        else:
            relacion = round(DPI_ESPERADO / dpi * 100)
            self._lbl_dpi.setText(
                f"ADVERTENCIA: la impresora parece ser de {dpi} DPI y el "
                f"programa está calibrado para {DPI_ESPERADO} DPI. La etiqueta "
                f"saldría de aprox. {relacion} % de su tamaño. Consulte a "
                f"soporte antes de usarla."
            )
            self._lbl_dpi.setStyleSheet(_estilo("error", True))

    # ------------------------------------------------------------------
    # Acciones
    # ------------------------------------------------------------------

    def _confirmar_dpi(self) -> bool:
        if self._dpi is None or dpi_es_esperado(self._dpi):
            return True
        respuesta = QMessageBox.question(
            self,
            "Resolución distinta",
            f"La impresora parece ser de {self._dpi} DPI y el programa está "
            f"calibrado para {DPI_ESPERADO} DPI: la etiqueta saldrá con otro "
            f"tamaño.\n\n¿Imprimir de todos modos?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return respuesta == QMessageBox.StandardButton.Yes

    def _imprimir_reglas(self) -> None:
        alto = self._spin_alto.value()
        self._ejecutar_impresion(
            "reglas", lambda: frescas.imprimir_prueba_reglas(self._nombre, alto)
        )

    def _imprimir_ejemplo(self) -> None:
        perfil = self._perfil_actual()
        self._ejecutar_impresion(
            "etiqueta de ejemplo",
            lambda: frescas.imprimir_prueba_etiqueta(self._nombre, perfil),
        )

    def _ejecutar_impresion(self, descripcion: str, accion: Callable[[], None]) -> None:
        if self._ocupado or not self._confirmar_dpi():
            return

        self._ocupado = True
        for boton in (self._btn_reglas, self._btn_ejemplo, self._btn_guardar):
            boton.setEnabled(False)
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        QApplication.processEvents()

        try:
            accion()
            logger.info("Impresión de prueba (%s) enviada a %r", descripcion, self._nombre)
        except ValueError as exc:
            QMessageBox.warning(self, "Imprimir prueba", str(exc))
        except Exception as exc:
            logger.exception(
                "Falló la impresión de prueba (%s) en %r", descripcion, self._nombre
            )
            QMessageBox.critical(
                self,
                "Imprimir prueba",
                f"No se pudo imprimir la prueba:\n{exc}\n\n"
                f"Revise que la impresora esté encendida, con papel y no "
                f"en pausa. El detalle quedó en el archivo de log.",
            )
        finally:
            QApplication.restoreOverrideCursor()
            self._ocupado = False
            self._btn_reglas.setEnabled(True)
            self._actualizar_estado(self._perfil_actual())   # reactiva los demás

    def _restaurar(self) -> None:
        self._cargar_en_campos(PerfilImpresora(alto_mm=frescas.ALTO_MM))
        self._actualizar_vista_previa()
        logger.info("Ajuste restaurado a valores por defecto (sin guardar) en %r", self._nombre)

    def _guardar(self) -> None:
        perfil = self._perfil_actual()
        if nivel_escala(perfil.escala()) == "bloqueado":
            QMessageBox.warning(
                self, "Guardar ajuste",
                "Los valores dejan el contenido demasiado pequeño. Corríjalos "
                "antes de guardar.",
            )
            return

        try:
            guardar_perfil(self._nombre, perfil)
        except OSError as exc:
            logger.exception("No se pudo guardar el ajuste de %r", self._nombre)
            QMessageBox.critical(
                self, "Guardar ajuste",
                f"No se pudo guardar el ajuste:\n{exc}",
            )
            return

        logger.info(
            "Ajuste CAMBIADO en %r: antes=%s ahora=%s",
            self._nombre,
            asdict(self._inicial.validado()) if self._tenia_perfil else "sin perfil",
            asdict(perfil),
        )
        self._inicial = perfil
        self._tenia_perfil = True
        self.accept()

    def reject(self) -> None:
        """Cancelar / Esc / cerrar: avisa si hay cambios sin guardar."""
        if self._ocupado:
            return
        if self._hay_cambios():
            respuesta = QMessageBox.question(
                self,
                "Cambios sin guardar",
                "Hay cambios sin guardar. ¿Salir sin guardarlos?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if respuesta != QMessageBox.StandardButton.Yes:
                return
        super().reject()

    # ------------------------------------------------------------------
    # Tamaño y posición
    # ------------------------------------------------------------------

    def _pantalla_disponible(self):
        padre = self.parentWidget()
        pantalla = padre.window().screen() if padre is not None else self.screen()
        return pantalla.availableGeometry()

    def _ajustar_tamano_a_pantalla(self) -> None:
        """Nunca más grande que la pantalla (útil en monitores pequeños)."""
        disponible = self._pantalla_disponible()
        sugerido = self.sizeHint()
        self.resize(
            min(sugerido.width(), int(disponible.width() * 0.95)),
            min(sugerido.height(), int(disponible.height() * 0.95)),
        )

    def _centrar(self) -> None:
        """Centra la ventana sobre la ventana padre (o la pantalla) sin salirse."""
        disponible = self._pantalla_disponible()
        padre = self.parentWidget()
        ventana_padre = padre.window() if padre is not None else None

        if ventana_padre is not None and ventana_padre.isVisible() \
                and not ventana_padre.isMinimized():
            referencia = ventana_padre.frameGeometry()
        else:
            referencia = disponible

        geo = self.frameGeometry()
        geo.moveCenter(referencia.center())
        x = max(disponible.left(), min(geo.left(), disponible.right() - geo.width() + 1))
        y = max(disponible.top(), min(geo.top(), disponible.bottom() - geo.height() + 1))
        self.move(x, y)

    def showEvent(self, evento) -> None:
        super().showEvent(evento)
        if not self._centrado:
            self._centrado = True
            self._centrar()