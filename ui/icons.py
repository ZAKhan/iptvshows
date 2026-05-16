import os
import sys
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtCore import QByteArray

_BASE = getattr(sys, "_MEIPASS", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_ICONS_DIR = os.path.join(_BASE, "assets", "icons")


def _svg_bytes(name: str, color: str) -> bytes:
    path = os.path.join(_ICONS_DIR, f"{name}.svg")
    if not os.path.exists(path):
        return b""
    with open(path, "rb") as f:
        data = f.read()
    return data.replace(b"currentColor", color.encode())


def icon(name: str, color: str = "#a8a59c", size: int = 18) -> QIcon:
    svg_data = _svg_bytes(name, color)
    if not svg_data:
        return QIcon()
    renderer = QSvgRenderer(QByteArray(svg_data))
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    return QIcon(pixmap)


def icon_accent(name: str, size: int = 18) -> QIcon:
    return icon(name, "#ffb547", size)


def icon_text(name: str, size: int = 18) -> QIcon:
    return icon(name, "#f1efe9", size)


def icon_muted(name: str, size: int = 18) -> QIcon:
    return icon(name, "#6b6960", size)
