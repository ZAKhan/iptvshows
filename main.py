import sys
import os
import logging
import resource
import traceback
from logging.handlers import RotatingFileHandler

sys.path.insert(0, os.path.dirname(__file__))

os.environ["QT_LOGGING_RULES"] = "qt.qpa.theme.gnome=false;qt.text.font.db=false"


def _setup_logging():
    log_dir = os.path.expanduser("~/.config/iptvshows")
    os.makedirs(log_dir, exist_ok=True)
    handler = RotatingFileHandler(
        os.path.join(log_dir, "iptvshows.log"),
        maxBytes=512 * 1024, backupCount=3, encoding="utf-8",
    )
    handler.setFormatter(logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(handler)

    def _excepthook(exc_type, exc, tb):
        root.error("Uncaught: %s", "".join(traceback.format_exception(exc_type, exc, tb)))
        sys.__excepthook__(exc_type, exc, tb)
    sys.excepthook = _excepthook


_setup_logging()

try:
    soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
    resource.setrlimit(resource.RLIMIT_NOFILE, (hard, hard))
except Exception:
    pass

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QFontDatabase

import core.database as db


def _base_dir() -> str:
    return getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))


def _load_fonts():
    fonts_dir = os.path.join(_base_dir(), "assets", "fonts")
    font_files = [
        "InterTight-Regular.ttf",
        "InterTight-Medium.ttf",
        "InterTight-SemiBold.ttf",
        "InterTight-Bold.ttf",
        "InterTight-Italic.ttf",
        "InstrumentSerif-Regular.ttf",
        "InstrumentSerif-Italic.ttf",
    ]
    for fname in font_files:
        path = os.path.join(fonts_dir, fname)
        if os.path.exists(path):
            QFontDatabase.addApplicationFont(path)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("IPTV Player")
    app.setOrganizationName("iptvshows")
    app.setQuitOnLastWindowClosed(True)
    # Bypass Qt teardown waits on QThread destructors when the app quits.
    app.aboutToQuit.connect(lambda: os._exit(0))

    _load_fonts()

    default_font = QFont("Inter Tight", 13)
    default_font.setWeight(QFont.Weight.Normal)
    app.setFont(default_font)

    db.initialize()
    logging.info("Starting IPTV Player")

    from ui.main_window import MainWindow
    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == '__main__':
    main()
