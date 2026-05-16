"""
IPTV Player - Image loading utilities for poster/thumbnails.
Version: 0.1
"""

import os
import hashlib
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import QSize, Qt

IMAGE_CACHE_DIR = os.path.expanduser("~/.config/iptvshows/images")

def _ensure_cache_dir():
    os.makedirs(IMAGE_CACHE_DIR, exist_ok=True)


def _url_to_filename(url: str) -> str:
    if not url:
        return ""
    return hashlib.md5(url.encode()).hexdigest() + ".jpg"


def get_poster_path(url: str) -> str:
    if not url:
        return ""
    _ensure_cache_dir()
    return os.path.join(IMAGE_CACHE_DIR, _url_to_filename(url))


def load_poster(url: str, size: QSize = None) -> QPixmap:
    path = get_poster_path(url)
    if path and os.path.exists(path):
        pix = QPixmap(path)
        if size and not pix.isNull():
            return pix.scaled(size, Qt.AspectRatioMode.KeepAspectRatio,
                             Qt.TransformationMode.SmoothTransformation)
        return pix
    return QPixmap()


def poster_exists(url: str) -> bool:
    if not url:
        return False
    path = get_poster_path(url)
    return path and os.path.exists(path)