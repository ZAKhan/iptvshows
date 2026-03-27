import sys
import os
import resource

# ensure project root is on the path
sys.path.insert(0, os.path.dirname(__file__))

# Silence noisy dbus errors from Qt's GNOME theme plugin when the
# Freedesktop portal is unavailable in the current environment
os.environ["QT_LOGGING_RULES"] = "qt.qpa.theme.gnome=false"

# Raise open-file limit to the hard cap so Qt + threads don't exhaust it
try:
    soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
    resource.setrlimit(resource.RLIMIT_NOFILE, (hard, hard))
except Exception:
    pass

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

import core.database as db
from ui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("IPTV Player")
    app.setOrganizationName("iptvshows")

    db.initialize()

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == '__main__':
    main()
