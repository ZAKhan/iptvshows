from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QPushButton, QLabel, QStackedWidget, QStatusBar,
    QMessageBox, QSizePolicy,
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont, QIcon

from ui.styles import DARK_THEME
from ui.login_dialog import LoginDialog
import core.database as db
from api.xtream import XtreamAPI


NAV_ITEMS = [
    ("▶", "Live TV"),
    ("◼", "Movies"),
    ("⊞", "Series"),
    ("⌕", "Search"),
    ("♡", "Favorites"),
    ("⚙", "Settings"),
]


class SidebarButton(QPushButton):
    def __init__(self, icon: str, label: str, parent=None):
        super().__init__(parent)
        self.setObjectName("NavBtn")
        self._icon = icon
        self._label = label
        self._expanded = True   # sidebar starts expanded
        self._set_text()
        self.setCheckable(False)
        self.setFixedHeight(44)

    def set_expanded(self, expanded: bool):
        self._expanded = expanded
        self._set_text()

    def _set_text(self):
        if self._expanded:
            self.setText(f"  {self._icon}  {self._label}")
        else:
            self.setText(f"  {self._icon}")

    def set_active(self, active: bool):
        self.setProperty('active', 'true' if active else 'false')
        self.style().unpolish(self)
        self.style().polish(self)


class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.api: XtreamAPI | None = None
        self._sidebar_expanded = True

        self.setWindowTitle("IPTV Player")
        self.setMinimumSize(1024, 680)
        self.setStyleSheet(DARK_THEME)
        self._restore_geometry()

        self._build_ui()
        self._load_server()

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Sidebar
        self._sidebar = QWidget()
        self._sidebar.setObjectName("Sidebar")
        self._sidebar.setProperty("expanded", "true")
        sb_layout = QVBoxLayout(self._sidebar)
        sb_layout.setContentsMargins(0, 0, 0, 0)
        sb_layout.setSpacing(0)

        # Logo / toggle
        logo_btn = QPushButton("  ▶  IPTV Player")
        logo_btn.setObjectName("NavBtn")
        logo_btn.setFixedHeight(56)
        logo_btn.setStyleSheet(
            "font-size:15px; font-weight:700; color:#c4bbfc; letter-spacing:-0.3px;"
            "border-bottom:1px solid #1e1e2e; border-radius:0; margin:0; padding-left:14px;"
        )
        logo_btn.clicked.connect(self._toggle_sidebar)
        sb_layout.addWidget(logo_btn)

        # Spacer below logo
        spacer_top = QWidget()
        spacer_top.setFixedHeight(8)
        spacer_top.setStyleSheet("background:transparent;")
        sb_layout.addWidget(spacer_top)

        self._nav_btns: list[SidebarButton] = []
        for icon, label in NAV_ITEMS:
            btn = SidebarButton(icon, label)
            btn.clicked.connect(lambda checked, l=label: self._nav_to(l))
            sb_layout.addWidget(btn)
            self._nav_btns.append(btn)

        sb_layout.addStretch()

        # Server info at bottom
        self._srv_lbl = QLabel("  No server")
        self._srv_lbl.setStyleSheet("color:#3a3a58; font-size:11px; padding:8px 16px;")
        self._srv_lbl.setWordWrap(True)
        sb_layout.addWidget(self._srv_lbl)

        root.addWidget(self._sidebar)

        # Main content stack
        self._stack = QStackedWidget()
        root.addWidget(self._stack, stretch=1)

        # Placeholder pages (replaced after server connects)
        self._pages: dict = {}
        for _, label in NAV_ITEMS:
            placeholder = QLabel(f"Connect to a server to use {label}")
            placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            placeholder.setStyleSheet("color:#2a2a40; font-size:16px;")
            self._pages[label] = placeholder
            self._stack.addWidget(placeholder)

        # Status bar
        self._status = QStatusBar()
        self.setStatusBar(self._status)
        self._status.showMessage("Ready")

        self._nav_to("Live TV")

    # ── Server / connection ───────────────────────────────────────────────────

    def _load_server(self):
        server = db.get_active_server()
        if server:
            self._init_from_server(server)
        else:
            self._prompt_login()

    def _prompt_login(self):
        dlg = LoginDialog(self)
        if dlg.exec():
            server = db.get_active_server()
            if server:
                self._init_from_server(server)
        else:
            self._status.showMessage("No server configured — go to Settings to add one.")

    def _init_from_server(self, server: dict):
        """Build the API object from stored credentials and start immediately — no network call."""
        self.api = XtreamAPI(server['url'], server['username'], server['password'])
        self._srv_lbl.setText(f"  {server.get('name', '')}")
        self._status.showMessage(f"Ready  —  {server.get('name', '')}")
        self._init_pages()

    def _init_pages(self):
        """Replace placeholder pages with real widgets once connected."""
        from ui.live_tv import LiveTvWidget
        from ui.movies import MoviesWidget
        from ui.series import SeriesWidget
        from ui.search import SearchWidget
        from ui.favorites import FavoritesWidget
        from ui.settings import SettingsWidget

        pages_map = {
            "Live TV":   LiveTvWidget(self.api),
            "Movies":    MoviesWidget(self.api),
            "Series":    SeriesWidget(self.api),
            "Search":    SearchWidget(self.api),
            "Favorites": FavoritesWidget(self.api),
            "Settings":  SettingsWidget(),
        }

        for label, widget in pages_map.items():
            old = self._pages[label]
            idx = self._stack.indexOf(old)
            self._stack.insertWidget(idx, widget)
            self._stack.removeWidget(old)
            old.deleteLater()
            self._pages[label] = widget

            if hasattr(widget, 'status_message'):
                widget.status_message.connect(self._status.showMessage)
            if hasattr(widget, 'server_changed'):
                widget.server_changed.connect(self._on_server_changed)
            if hasattr(widget, 'navigate_to'):
                widget.navigate_to.connect(self._on_fav_navigate)

        self._nav_to("Live TV")

    def _on_fav_navigate(self, stream_type: str, data: dict):
        if stream_type == 'vod':
            self._nav_to("Movies")
            self._pages["Movies"].open_detail(data)
        elif stream_type == 'series':
            self._nav_to("Series")
            self._pages["Series"].open_detail(data)

    def _on_server_changed(self):
        server = db.get_active_server()
        if server:
            self._init_from_server(server)

    # ── Navigation ────────────────────────────────────────────────────────────

    def _nav_to(self, label: str):
        self._current_page = label
        page = self._pages.get(label)
        if page:
            self._stack.setCurrentWidget(page)
        for i, btn in enumerate(self._nav_btns):
            _, lbl = NAV_ITEMS[i]
            btn.set_active(lbl == label)

    def _restore_geometry(self):
        geom = db.get_setting("window_geometry")
        if geom:
            try:
                x, y, w, h = (int(v) for v in geom.split(","))
                self.setGeometry(x, y, w, h)
                return
            except (ValueError, TypeError):
                pass
        self.resize(1280, 800)

    def _save_geometry(self):
        g = self.geometry()
        db.set_setting("window_geometry", f"{g.x()},{g.y()},{g.width()},{g.height()}")

    def closeEvent(self, event):
        self._save_geometry()
        from ui.workers import shutdown_pools
        shutdown_pools()
        event.accept()

    def _toggle_sidebar(self):
        self._sidebar_expanded = not self._sidebar_expanded
        w = 200 if self._sidebar_expanded else 56
        self._sidebar.setFixedWidth(w)
        self._sidebar.setProperty("expanded", "true" if self._sidebar_expanded else "false")
        for btn in self._nav_btns:
            btn.set_expanded(self._sidebar_expanded)
