from PySide6.QtCore import QObject, QEvent, QTimer, Signal
from PySide6.QtWidgets import QApplication

class InactivityWatcher(QObject):
    timeout = Signal()

    # Eventos que cuentan como "actividad"
    _ACTIVITY = {
        QEvent.MouseMove, QEvent.MouseButtonPress, QEvent.MouseButtonRelease,
        QEvent.KeyPress, QEvent.Wheel, QEvent.TouchBegin,
    }

    def __init__(self, minutes=15, parent=None):
        super().__init__(parent)
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(minutes * 60 * 1000)
        self._timer.timeout.connect(self.timeout)

    def start(self):
        QApplication.instance().installEventFilter(self)
        self._timer.start()

    def stop(self):
        QApplication.instance().removeEventFilter(self)
        self._timer.stop()

    def eventFilter(self, obj, event):
        if event.type() in self._ACTIVITY:
            self._timer.start()  # reinicia la cuenta
        return False  # nunca consumir el evento