from PyQt6.QtCore import QPropertyAnimation, QEasingCurve, QTimer, pyqtProperty
from PyQt6.QtWidgets import QGraphicsDropShadowEffect, QWidget
from PyQt6.QtGui import QColor


def apply_drop_shadow(widget: QWidget, blur: int = 16, y: int = 4,
                      color: tuple = (0, 0, 0, 128)) -> QGraphicsDropShadowEffect:
    effect = QGraphicsDropShadowEffect(widget)
    effect.setBlurRadius(blur)
    effect.setOffset(0, y)
    effect.setColor(QColor(*color))
    widget.setGraphicsEffect(effect)
    return effect


def apply_card_shadow(widget: QWidget):
    return apply_drop_shadow(widget, blur=16, y=4, color=(0, 0, 0, 100))


def apply_hover_shadow(widget: QWidget):
    return apply_drop_shadow(widget, blur=32, y=12, color=(0, 0, 0, 130))


class PulseTimer:
    """Alternates a label or widget opacity via stylesheet at a given interval."""

    def __init__(self, widget: QWidget, period_ms: int = 1600,
                 on_style: str = "opacity: 1;", off_style: str = "opacity: 0.4;"):
        self._widget = widget
        self._on = True
        self._on_style = on_style
        self._off_style = off_style
        self._timer = QTimer(widget)
        self._timer.setInterval(period_ms // 2)
        self._timer.timeout.connect(self._tick)

    def start(self):
        self._timer.start()

    def stop(self):
        self._timer.stop()

    def _tick(self):
        self._on = not self._on
        # toggle via color — stylesheet opacity isn't well supported, use color alpha
        if hasattr(self._widget, 'setStyleSheet'):
            pass  # subclasses can override _apply
        self._apply(self._on)

    def _apply(self, visible: bool):
        pass


class LiveDotPulse:
    """Pulses a QLabel dot between bright and dim by swapping text color."""

    def __init__(self, label, period_ms: int = 1600,
                 bright: str = "#ff4d4d", dim: str = "rgba(255,77,77,0.3)"):
        self._label = label
        self._bright = bright
        self._dim = dim
        self._on = True
        self._timer = QTimer(label)
        self._timer.setInterval(period_ms // 2)
        self._timer.timeout.connect(self._tick)

    def start(self):
        self._timer.start()

    def stop(self):
        self._timer.stop()

    def _tick(self):
        self._on = not self._on
        color = self._bright if self._on else self._dim
        base = self._label.styleSheet()
        # inject color override — works if the label has a simple style
        self._label.setStyleSheet(f"color: {color};")
