from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QPushButton, QLabel, QStackedWidget, QStatusBar,
    QSizePolicy, QFrame, QScrollArea, QProgressBar,
)
from ui.widgets import SearchField
from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtGui import QFont, QKeySequence, QShortcut

from ui.styles import DARK_THEME
import core.database as db
from api.xtream import XtreamAPI

NAV_ITEMS = [
    ("home",      "Home",      "Home"),
    ("tv",        "Live TV",   "Live TV"),
    ("film",      "Movies",    "Movies"),
    ("list-video","Series",    "Series"),
    ("search",    "Search",    "Search"),
    ("heart",     "Favorites", "Favorites"),
    ("settings",  "Settings",  "Settings"),
]


class NavButton(QPushButton):
    def __init__(self, label: str, parent=None):
        super().__init__(label, parent)
        self.setObjectName("NavItem")
        self.setFixedHeight(40)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setCheckable(False)

    def set_active(self, active: bool):
        self.setProperty("active", "true" if active else "false")
        self.style().unpolish(self)
        self.style().polish(self)


class ServerCard(QFrame):
    add_server_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("SettingCard")
        self.setFixedHeight(72)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(8)

        self._dot = QLabel("●")
        self._dot.setFixedWidth(14)
        self._dot.setStyleSheet("color: #6b6960; font-size: 10px;")

        info = QVBoxLayout()
        info.setSpacing(2)
        self._name_lbl = QLabel("No server connected")
        self._name_lbl.setStyleSheet("color: #6b6960; font-size: 12px; font-weight: 500;")
        self._sub_lbl = QLabel("Tap to add")
        self._sub_lbl.setStyleSheet("color: #6b6960; font-size: 11px;")
        info.addWidget(self._name_lbl)
        info.addWidget(self._sub_lbl)

        self._add_btn = QPushButton("+ Add")
        self._add_btn.setObjectName("BtnPrimaryGlow")
        self._add_btn.setFixedSize(60, 28)
        self._add_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #ffb547,stop:1 #ff7a1a);
                color: #1a1004; border: none; border-radius: 7px;
                font-size: 11px; font-weight: 600;
            }
            QPushButton:hover { background: #ffc060; }
        """)
        self._add_btn.clicked.connect(self.add_server_requested)
        self._add_btn.hide()

        layout.addWidget(self._dot)
        layout.addLayout(info, stretch=1)
        layout.addWidget(self._add_btn)

    def set_server(self, name: str):
        self._dot.setStyleSheet("color: #6cd97e; font-size: 10px;")
        self._name_lbl.setText(name)
        self._name_lbl.setStyleSheet("color: #f1efe9; font-size: 12px; font-weight: 500;")
        self._sub_lbl.setText("Connected")
        self._sub_lbl.setStyleSheet("color: #6cd97e; font-size: 11px;")
        self._add_btn.hide()

    def set_empty(self):
        self._dot.setStyleSheet("color: #6b6960; font-size: 10px;")
        self._name_lbl.setText("No server")
        self._name_lbl.setStyleSheet("color: #6b6960; font-size: 12px; font-weight: 500;")
        self._sub_lbl.setText("Tap to add")
        self._sub_lbl.setStyleSheet("color: #6b6960; font-size: 11px;")
        self._add_btn.show()


class TopBar(QFrame):
    search_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("TopBar")
        self.setFixedHeight(60)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(24, 0, 24, 0)
        layout.setSpacing(12)

        self._search = SearchField("Search movies, series, channels…")
        self._search.setMaximumWidth(520)
        self._search.textChanged.connect(self.search_changed)

        layout.addWidget(self._search)
        layout.addStretch()

        self._bell_btn = QPushButton("🔔")
        self._bell_btn.setObjectName("IconBtn")
        self._bell_btn.setToolTip("Notifications")

        self._avatar = QLabel("Z")
        self._avatar.setFixedSize(38, 38)
        self._avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._avatar.setStyleSheet("""
            background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #ffb547,stop:1 #ff7a1a);
            border-radius: 19px; color: #fff; font-size: 14px; font-weight: 700;
        """)

        layout.addWidget(self._bell_btn)
        layout.addWidget(self._avatar)

    def set_search_text(self, text: str):
        self._search.setText(text)


class BottomBar(QFrame):
    """Custom bottom bar replacing QStatusBar.
    Left: server status label. Center: progress bar (visible during sync). Right: status message."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("BottomBar")
        self.setFixedHeight(30)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 0, 14, 0)
        layout.setSpacing(12)

        self.server_lbl = QLabel("●  No server")
        self.server_lbl.setObjectName("ServerStatus")
        self.server_lbl.setCursor(Qt.CursorShape.PointingHandCursor)
        self.server_lbl.setToolTip("Click to manage servers")
        layout.addWidget(self.server_lbl)

        layout.addStretch()

        self.progress = QProgressBar()
        self.progress.setObjectName("BottomProgress")
        self.progress.setFixedSize(220, 6)
        self.progress.setTextVisible(False)
        self.progress.setRange(0, 100)
        self.progress.hide()
        layout.addWidget(self.progress)

        self.msg_lbl = QLabel("")
        self.msg_lbl.setObjectName("StatusMsg")
        layout.addWidget(self.msg_lbl)

    def showMessage(self, text: str, _timeout: int = 0):
        self.msg_lbl.setText(text or "")

    def show_busy(self):
        """Indeterminate (sweeping) progress."""
        self.progress.setRange(0, 0)
        self.progress.show()

    def set_progress(self, done: int, total: int):
        if total <= 0:
            self.show_busy()
            return
        self.progress.setRange(0, total)
        self.progress.setValue(done)
        self.progress.show()

    def hide_progress(self):
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.hide()


class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.api: XtreamAPI | None = None

        self.setWindowTitle("IPTV Player")
        self.setMinimumSize(1100, 720)
        self.setStyleSheet(DARK_THEME)
        self._restore_geometry()

        self._build_ui()
        self._load_server()
        self._install_shortcuts()

    def _install_shortcuts(self):
        # `/` and Ctrl+L focus search
        for seq in ("/", "Ctrl+L"):
            sc = QShortcut(QKeySequence(seq), self)
            sc.activated.connect(lambda: self._topbar._search.setFocus())
        # Force quit
        sc = QShortcut(QKeySequence("Ctrl+Q"), self)
        sc.activated.connect(lambda: __import__('os')._exit(0))
        # Ctrl+1..7 → nav items
        for i, (_icon, _label, page_key) in enumerate(NAV_ITEMS, start=1):
            sc = QShortcut(QKeySequence(f"Ctrl+{i}"), self)
            sc.activated.connect(lambda k=page_key: self._nav_to(k))
        # Ctrl+R → trigger sync on current page if available
        sc = QShortcut(QKeySequence("Ctrl+R"), self)
        sc.activated.connect(self._trigger_sync_current)
        # Ctrl+F also focuses search
        sc = QShortcut(QKeySequence("Ctrl+F"), self)
        sc.activated.connect(lambda: self._topbar._search.setFocus())

    def _trigger_sync_current(self):
        page = self._pages.get(getattr(self, '_current_page', None))
        if page and hasattr(page, 'sync'):
            page.sync()

    def _on_synced(self, sid: int):
        """Settings finished syncing a server. Refresh content tabs if it's the active one."""
        try:
            current = int(db.get_setting('current_server', '0'))
        except Exception:
            current = 0
        # Match against in-memory current id via db module
        active = db.get_active_server()
        if not active or int(active.get('id', 0)) != int(sid):
            return
        for key in ("Live TV", "Movies", "Series"):
            page = self._pages.get(key)
            if page and hasattr(page, 'reload_after_sync'):
                page.reload_after_sync()

    def _on_topbar_search(self, text: str):
        if not text.strip():
            return
        page = self._pages.get("Search")
        if not page or not hasattr(page, '_search'):
            return
        if self._current_page != "Search":
            self._nav_to("Search")
        if page._search.text() != text:
            page._search.blockSignals(True)
            page._search.setText(text)
            page._search.blockSignals(False)
            page._on_text(text)

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Sidebar ──────────────────────────────────────────────────────────
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(180)
        sb = QVBoxLayout(sidebar)
        sb.setContentsMargins(0, 0, 0, 0)
        sb.setSpacing(0)

        # Brand
        brand_row = QWidget()
        brand_row.setFixedHeight(64)
        brand_row.setStyleSheet("background: transparent;")
        br = QHBoxLayout(brand_row)
        br.setContentsMargins(16, 0, 16, 0)
        br.setSpacing(10)
        mark = QPushButton("▶")
        mark.setObjectName("BrandMark")
        mark.setEnabled(False)
        name_lbl = QLabel("IPTV Player")
        name_lbl.setObjectName("BrandName")
        br.addWidget(mark)
        br.addWidget(name_lbl)
        br.addStretch()
        sb.addWidget(brand_row)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("background: #232329; max-height: 1px; border: none;")
        sb.addWidget(sep)

        sb.addSpacing(8)

        # Nav items
        self._nav_btns: dict[str, NavButton] = {}
        for _icon, label, page_key in NAV_ITEMS:
            btn = NavButton(f"  {label}")
            btn.clicked.connect(lambda checked, k=page_key: self._nav_to(k))
            sb.addWidget(btn)
            self._nav_btns[page_key] = btn

        sb.addStretch()
        root.addWidget(sidebar)

        # ── Right column: topbar + page stack ────────────────────────────────
        right = QWidget()
        right.setStyleSheet("background: #0b0b0d;")
        rv = QVBoxLayout(right)
        rv.setContentsMargins(0, 0, 0, 0)
        rv.setSpacing(0)

        self._topbar = TopBar()
        self._topbar.search_changed.connect(self._on_topbar_search)
        rv.addWidget(self._topbar)

        self._stack = QStackedWidget()
        self._stack.setStyleSheet("background: #0b0b0d;")
        rv.addWidget(self._stack, stretch=1)

        root.addWidget(right, stretch=1)

        # Custom bottom bar (server label always visible on left, message on right area)
        self._status = BottomBar()
        self._status.server_lbl.mousePressEvent = lambda _e: self._nav_to("Settings")
        self._server_lbl = self._status.server_lbl
        rv.addWidget(self._status)
        self._status.showMessage("Ready")

        # Placeholder pages (replaced after _init_pages)
        self._pages: dict[str, QWidget] = {}
        for _icon, _label, page_key in NAV_ITEMS:
            ph = self._make_empty_state()
            self._pages[page_key] = ph
            self._stack.addWidget(ph)

        self._nav_to("Home")

    def _make_empty_state(self) -> QWidget:
        w = QWidget()
        w.setStyleSheet("background: #0b0b0d;")
        v = QVBoxLayout(w)
        v.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v.setSpacing(16)

        title = QLabel("Welcome to Stream")
        title.setObjectName("PageTitleSerif")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(
            'font-family: "Instrument Serif", Georgia, serif; font-size: 48px; color: #f1efe9;'
        )

        sub = QLabel(
            "Connect an IPTV server to start streaming.\n"
            "You can add Xtream-compatible servers or local M3U playlists."
        )
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub.setStyleSheet("color: #6b6960; font-size: 14px;")
        sub.setWordWrap(True)

        add_btn = QPushButton("Add your first server")
        add_btn.setObjectName("BtnPrimaryGlow")
        add_btn.setFixedSize(200, 44)
        add_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #ffb547,stop:1 #ff7a1a);
                color: #1a1004; border: none; border-radius: 10px;
                font-size: 14px; font-weight: 600;
            }
            QPushButton:hover { background: #ffc060; }
        """)
        add_btn.clicked.connect(self._go_to_settings_add_server)

        settings_link = QPushButton("Or browse Settings →")
        settings_link.setFlat(True)
        settings_link.setStyleSheet("color: #6b6960; font-size: 13px; border: none; background: transparent;")
        settings_link.clicked.connect(lambda: self._nav_to("Settings"))

        v.addWidget(title)
        v.addWidget(sub)
        v.addSpacing(8)
        v.addWidget(add_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        v.addWidget(settings_link, alignment=Qt.AlignmentFlag.AlignCenter)
        return w

    # ── Server / connection ───────────────────────────────────────────────────

    def _load_server(self):
        server = db.get_active_server()
        if server:
            self._init_from_server(server)
        else:
            db.set_current_server(0)
            self.api = None
            self._set_server_label(None)
            self._init_pages()

    def _init_from_server(self, server: dict):
        db.set_current_server(server.get('id', 0))
        self.api = XtreamAPI(server['url'], server['username'], server['password'])
        self._set_server_label(server.get('name', 'Server'))
        self._status.showMessage("Ready")
        self._init_pages()
        self._maybe_auto_sync()

    def _set_server_label(self, name):
        if name:
            self._server_lbl.setText(f"●  {name}  ·  Connected")
            self._server_lbl.setStyleSheet(
                "color:#6cd97e; font-size:12px; padding:0 10px;"
            )
        else:
            self._server_lbl.setText("●  No server  ·  Click to add")
            self._server_lbl.setStyleSheet(
                "color:#6b6960; font-size:12px; padding:0 10px;"
            )

    def _maybe_auto_sync(self):
        if not self.api:
            return
        from PyQt6.QtCore import QTimer
        stale = (db.is_stale('live_streams') or db.is_stale('vod_streams')
                 or db.is_stale('series_list'))
        if stale:
            active = db.get_active_server()
            settings = self._pages.get("Settings")
            if active and settings and hasattr(settings, '_sync_server'):
                QTimer.singleShot(800, lambda s=settings, srv=active: s._sync_server(srv))
                self._status.showMessage("Auto-sync queued (cache stale)…")
        else:
            # Cache fresh — resume any interrupted poster prefetch queue.
            QTimer.singleShot(2000, self._resume_poster_prefetch)

    def _resume_poster_prefetch(self):
        """Silently top up the on-disk logo cache. Runs in background; no status
        messages so it doesn't fight with sync output if user later triggers a sync."""
        from ui.workers import PosterPrefetcher, is_cached
        icons = [r.get('stream_icon', '') for r in db.list_live_streams()]
        pending = [u for u in icons if u and not is_cached(u)]
        if not pending:
            return
        self._resume_prefetcher = PosterPrefetcher(pending, parent=self)
        self._resume_prefetcher.start()

    def _init_pages(self):
        from ui.home import HomeWidget
        from ui.live_tv import LiveTvWidget
        from ui.movies import MoviesWidget
        from ui.series import SeriesWidget
        from ui.search import SearchWidget
        from ui.favorites import FavoritesWidget
        from ui.settings import SettingsWidget

        pages_map = {
            "Home":      HomeWidget(self.api),
            "Live TV":   LiveTvWidget(self.api),
            "Movies":    MoviesWidget(self.api),
            "Series":    SeriesWidget(self.api),
            "Search":    SearchWidget(self.api),
            "Favorites": FavoritesWidget(self.api),
            "Settings":  SettingsWidget(),
        }

        for page_key, widget in pages_map.items():
            old = self._pages.get(page_key)
            if old is not None:
                idx = self._stack.indexOf(old)
                self._stack.insertWidget(idx, widget)
                self._stack.removeWidget(old)
                old.deleteLater()
            else:
                self._stack.addWidget(widget)
            self._pages[page_key] = widget

            if hasattr(widget, 'status_message'):
                widget.status_message.connect(self._status.showMessage)
            if hasattr(widget, 'server_changed'):
                widget.server_changed.connect(self._on_server_changed)
            if hasattr(widget, 'navigate_to'):
                widget.navigate_to.connect(self._on_fav_navigate)
            if hasattr(widget, 'synced'):
                widget.synced.connect(self._on_synced)
            if hasattr(widget, 'sync_progress'):
                widget.sync_progress.connect(self._status.set_progress)
            if hasattr(widget, 'sync_finished'):
                widget.sync_finished.connect(self._status.hide_progress)

        current = self._current_page if hasattr(self, '_current_page') else "Home"
        self._nav_to(current)

    def _on_fav_navigate(self, stream_type: str, data: dict):
        if stream_type == 'vod':
            self._nav_to("Movies")
            if hasattr(self._pages["Movies"], 'open_detail'):
                self._pages["Movies"].open_detail(data)
        elif stream_type == 'series':
            self._nav_to("Series")
            if hasattr(self._pages["Series"], 'open_detail'):
                self._pages["Series"].open_detail(data)

    def _on_server_changed(self):
        server = db.get_active_server()
        if server:
            self._init_from_server(server)
        else:
            self.api = None
            self._set_server_label(None)

    def _go_to_settings_add_server(self):
        self._nav_to("Settings")
        settings = self._pages.get("Settings")
        if settings and hasattr(settings, 'open_add_server'):
            settings.open_add_server()

    # ── Navigation ────────────────────────────────────────────────────────────

    def _nav_to(self, page_key: str):
        self._current_page = page_key
        page = self._pages.get(page_key)
        if page:
            self._stack.setCurrentWidget(page)
        for key, btn in self._nav_btns.items():
            btn.set_active(key == page_key)

    # ── Geometry ──────────────────────────────────────────────────────────────

    def _restore_geometry(self):
        geom = db.get_setting("window_geometry")
        if geom:
            try:
                x, y, w, h = (int(v) for v in geom.split(","))
                self.setGeometry(x, y, w, h)
                return
            except (ValueError, TypeError):
                pass
        self.resize(1400, 860)

    def _save_geometry(self):
        g = self.geometry()
        db.set_setting("window_geometry", f"{g.x()},{g.y()},{g.width()},{g.height()}")

    def closeEvent(self, event):
        # Save geometry first (fast sqlite WAL write), then exit immediately.
        # We intentionally skip Qt teardown / pool drains — in-flight HTTP reads
        # can stall closes by tens of seconds. os._exit is OS-level and instant.
        try:
            self._save_geometry()
        except Exception:
            pass
        event.accept()
        import os
        os._exit(0)
