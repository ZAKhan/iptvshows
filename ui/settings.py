from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QFormLayout, QMessageBox, QCheckBox,
    QScrollArea, QFrame, QSizePolicy, QStackedWidget,
    QComboBox,
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal

import time
import core.database as db
from ui.login_dialog import LoginDialog
from ui.anim import apply_card_shadow


def _relative_time(server_id) -> str:
    """Return human 'Xd ago' / 'Xh ago' / 'Just now' / 'Never synced'."""
    if not server_id:
        return "Never synced"
    try:
        ts = float(db.get_setting(f'last_sync_{int(server_id)}', '0') or 0)
    except (TypeError, ValueError):
        ts = 0.0
    if ts <= 0:
        return "Never synced"
    delta = max(0, time.time() - ts)
    days = int(delta // 86400)
    if days >= 1:
        return f"{days} day ago" if days == 1 else f"{days} days ago"
    hours = int(delta // 3600)
    if hours >= 1:
        return f"{hours}h ago"
    mins = int(delta // 60)
    if mins >= 1:
        return f"{mins}m ago"
    return "Just now"


class SectionLabel(QLabel):
    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setStyleSheet(
            "color: #6b6960; font-size: 11px; font-weight: 600; "
            "letter-spacing: 0.1em; text-transform: uppercase; "
            "padding: 0; margin-bottom: 4px;"
        )


class SettingRow(QFrame):
    def __init__(self, title: str, subtitle: str = "", parent=None):
        super().__init__(parent)
        self.setObjectName("SettingRow")
        self.setFixedHeight(60)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(16)

        text_col = QVBoxLayout()
        text_col.setSpacing(2)
        name_lbl = QLabel(title)
        name_lbl.setStyleSheet("color: #f1efe9; font-size: 13px; font-weight: 500;")
        text_col.addWidget(name_lbl)
        if subtitle:
            sub_lbl = QLabel(subtitle)
            sub_lbl.setStyleSheet("color: #6b6960; font-size: 12px;")
            text_col.addWidget(sub_lbl)

        layout.addLayout(text_col, stretch=1)
        self._control_slot = layout

    def set_control(self, widget: QWidget):
        self._control_slot.addWidget(widget)


class ServerCard(QFrame):
    edit_clicked = pyqtSignal(dict)
    delete_clicked = pyqtSignal(dict)
    activate_clicked = pyqtSignal(dict)
    sync_clicked = pyqtSignal(dict)

    def __init__(self, server: dict, parent=None):
        super().__init__(parent)
        self._server = server
        is_active = bool(server.get('active'))
        obj = "ServerCardActive" if is_active else "ServerCard"
        self.setObjectName(obj)
        self.setFixedHeight(80)
        apply_card_shadow(self)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)

        # Icon with initials
        icon_lbl = QLabel(server.get('name', '?')[:2].upper())
        icon_lbl.setFixedSize(44, 44)
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_lbl.setStyleSheet(
            "background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #ffb547,stop:1 #ff7a1a);"
            "border-radius: 10px; color: #1a1004; font-size: 14px; font-weight: 700;"
        )

        info = QVBoxLayout()
        info.setSpacing(2)

        name_row = QHBoxLayout()
        name_lbl = QLabel(server.get('name', 'Server'))
        name_lbl.setStyleSheet("color: #f1efe9; font-size: 13px; font-weight: 600;")
        name_row.addWidget(name_lbl)
        if is_active:
            active_pill = QLabel("● ACTIVE")
            active_pill.setStyleSheet(
                "background: rgba(108,217,126,0.15); color: #6cd97e; "
                "font-size: 10px; font-weight: 700; letter-spacing: 0.06em; "
                "padding: 2px 8px; border-radius: 4px;"
            )
            name_row.addWidget(active_pill)
        name_row.addStretch()
        info.addLayout(name_row)

        url_lbl = QLabel(server.get('url', ''))
        url_lbl.setStyleSheet(
            "color: #6b6960; font-size: 11px; "
            "font-family: 'JetBrains Mono', 'Menlo', monospace;"
        )
        url_lbl.setMaximumWidth(500)
        info.addWidget(url_lbl)

        last_sync_lbl = QLabel(f"Last synced: {_relative_time(server.get('id'))}")
        last_sync_lbl.setStyleSheet("color: #6b6960; font-size: 11px;")
        info.addWidget(last_sync_lbl)

        actions = QHBoxLayout()
        actions.setSpacing(6)

        edit_btn = QPushButton("Edit")
        edit_btn.setObjectName("BtnSecondary")
        edit_btn.setFixedSize(72, 32)
        edit_btn.setStyleSheet("""
            QPushButton { background: rgba(255,255,255,0.06); border: 1px solid #2e2e36;
                color: #a8a59c; border-radius: 7px; padding: 0 8px; font-size: 12px; font-weight: 600; }
            QPushButton:hover { color: #f1efe9; border-color: #ffb547; }
        """)
        edit_btn.clicked.connect(lambda: self.edit_clicked.emit(self._server))

        del_btn = QPushButton("Remove")
        del_btn.setObjectName("BtnDanger")
        del_btn.setFixedSize(88, 32)
        del_btn.setStyleSheet("""
            QPushButton { background: transparent; border: 1px solid #ff6b6b;
                color: #ff6b6b; border-radius: 7px; padding: 0 8px; font-size: 12px; font-weight: 600; }
            QPushButton:hover { background: #ff6b6b; color: #fff; }
        """)
        del_btn.clicked.connect(lambda: self.delete_clicked.emit(self._server))

        self._sync_btn = QPushButton("↻  Sync")
        self._sync_btn.setFixedSize(88, 32)
        self._sync_btn.setStyleSheet("""
            QPushButton { background: rgba(255,181,71,0.12); border: 1px solid #ffb547;
                color: #ffb547; border-radius: 7px; padding: 0 8px; font-size: 12px; font-weight: 600; }
            QPushButton:hover { background: #ffb547; color: #1a1004; }
            QPushButton:disabled { color: #6b6960; border-color: #2e2e36; background: transparent; }
        """)
        self._sync_btn.clicked.connect(lambda: self.sync_clicked.emit(self._server))
        actions.addWidget(self._sync_btn)

        if not is_active:
            act_btn = QPushButton("Set Active")
            act_btn.setFixedSize(96, 32)
            act_btn.setStyleSheet("""
                QPushButton { background: rgba(255,181,71,0.12); border: 1px solid #ffb547;
                    color: #ffb547; border-radius: 7px; padding: 0 8px; font-size: 12px; font-weight: 600; }
                QPushButton:hover { background: #ffb547; color: #1a1004; }
            """)
            act_btn.clicked.connect(lambda: self.activate_clicked.emit(self._server))
            actions.addWidget(act_btn)

        actions.addWidget(edit_btn)
        actions.addWidget(del_btn)

        layout.addWidget(icon_lbl)
        layout.addLayout(info, stretch=1)
        layout.addLayout(actions)


class SettingsWidget(QWidget):
    server_changed = pyqtSignal()
    status_message = pyqtSignal(str)
    synced         = pyqtSignal(int)               # server id
    sync_progress  = pyqtSignal(int, int)          # (done, total) 0..100
    sync_finished  = pyqtSignal()                  # hide bar

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tmdb_worker = None
        self._sync_worker = None
        self._servers: list = []
        self._build_ui()

    def _build_ui(self):
        # Scroll container
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

        content = QWidget()
        scroll.setWidget(content)

        root = QVBoxLayout(content)
        root.setContentsMargins(40, 36, 40, 36)
        root.setSpacing(0)
        root.setAlignment(Qt.AlignmentFlag.AlignTop)

        # ── Page header ───────────────────────────────────────────────────────
        title = QLabel("Settings")
        title.setStyleSheet(
            'font-family: "Instrument Serif", Georgia, serif; '
            'font-size: 44px; color: #f1efe9; font-weight: 400;'
        )
        sub = QLabel("Configure your IPTV servers, playback preferences, and app behaviour.")
        sub.setStyleSheet("color: #6b6960; font-size: 14px; margin-top: 4px;")
        root.addWidget(title)
        root.addWidget(sub)
        root.addSpacing(28)

        # ── Tab bar ───────────────────────────────────────────────────────────
        tab_bar = QHBoxLayout()
        tab_bar.setSpacing(0)
        tab_bar.setContentsMargins(0, 0, 0, 0)

        self._tab_btns: dict[str, QPushButton] = {}
        for tab in ["Servers", "Playback", "About"]:
            btn = QPushButton(tab)
            btn.setObjectName("NavTab")
            btn.setFixedHeight(40)
            btn.clicked.connect(lambda checked, t=tab: self._switch_tab(t))
            tab_bar.addWidget(btn)
        tab_bar.addStretch()

        sep_line = QFrame()
        sep_line.setFrameShape(QFrame.Shape.HLine)
        sep_line.setStyleSheet("background: #232329; max-height: 1px; border: none;")

        root.addLayout(tab_bar)
        root.addWidget(sep_line)
        root.addSpacing(24)

        # Collect tab button refs
        for btn in content.findChildren(QPushButton):
            if btn.objectName() == "NavTab":
                self._tab_btns[btn.text()] = btn

        # ── Tab pages stack ───────────────────────────────────────────────────
        self._tab_stack = QStackedWidget()
        self._tab_stack.addWidget(self._build_servers_tab())
        self._tab_stack.addWidget(self._build_playback_tab())
        self._tab_stack.addWidget(self._build_about_tab())
        root.addWidget(self._tab_stack, stretch=1)

        self._switch_tab("Servers")
        self._refresh_server_cards()

    def _build_servers_tab(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(16)

        v.addWidget(SectionLabel("Your Servers"))

        self._srv_cards_container = QWidget()
        self._srv_cards_layout = QVBoxLayout(self._srv_cards_container)
        self._srv_cards_layout.setContentsMargins(0, 0, 0, 0)
        self._srv_cards_layout.setSpacing(8)
        v.addWidget(self._srv_cards_container)

        # Add server dashed button
        add_frame = QFrame()
        add_frame.setObjectName("Card")
        add_frame.setFixedHeight(64)
        add_frame.setCursor(Qt.CursorShape.PointingHandCursor)
        add_frame.setStyleSheet(
            "QFrame { background: transparent; border: 1.5px dashed #2e2e36; "
            "border-radius: 12px; } QFrame:hover { border-color: #ffb547; }"
        )
        af_layout = QHBoxLayout(add_frame)
        add_lbl = QLabel("+ Add new server")
        add_lbl.setStyleSheet("color: #6b6960; font-size: 13px;")
        add_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        af_layout.addWidget(add_lbl)
        add_frame.mousePressEvent = lambda e: self._add_server()
        v.addWidget(add_frame)

        v.addSpacing(28)

        # ── Danger zone ───────────────────────────────────────────────────────
        danger = QFrame()
        danger.setObjectName("DangerZone")
        dv = QVBoxLayout(danger)
        dv.setContentsMargins(20, 16, 20, 16)
        dv.setSpacing(12)

        danger_title = QLabel("Danger Zone")
        danger_title.setStyleSheet("color: #ff6b6b; font-size: 14px; font-weight: 700;")
        dv.addWidget(danger_title)

        for label, action in [
            ("Clear watch history", self._clear_history),
            ("Reset library cache", self._clear_cache),
        ]:
            row = QHBoxLayout()
            row.addWidget(QLabel(label))
            btn = QPushButton(label.split()[0] + " " + label.split()[1])
            btn.setObjectName("BtnDanger")
            btn.setFixedWidth(120)
            btn.clicked.connect(action)
            row.addStretch()
            row.addWidget(btn)
            dv.addLayout(row)

        v.addWidget(danger)
        v.addStretch()
        return w

    def _build_playback_tab(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(16)

        # MPV card
        card = QFrame()
        card.setObjectName("SettingCard")
        apply_card_shadow(card)
        cv = QVBoxLayout(card)
        cv.setContentsMargins(0, 0, 0, 0)
        cv.setSpacing(0)

        title_row = QWidget()
        title_row.setFixedHeight(52)
        tr = QHBoxLayout(title_row)
        tr.setContentsMargins(16, 0, 16, 0)
        tr.addWidget(QLabel("Playback"))
        cv.addWidget(title_row)

        form = QFormLayout()
        form.setContentsMargins(16, 8, 16, 16)
        form.setSpacing(12)

        self._mpv_args = QLineEdit()
        self._mpv_args.setPlaceholderText("e.g. --hwdec=auto --vo=gpu")
        self._mpv_args.setText(db.get_setting('mpv_extra_args', ''))
        form.addRow("MPV extra args:", self._mpv_args)

        self._fullscreen = QCheckBox("Start in fullscreen")
        self._fullscreen.setChecked(db.get_setting('mpv_fullscreen', '0') == '1')
        form.addRow("", self._fullscreen)

        cv.addLayout(form)
        v.addWidget(card)

        # TMDB card
        card2 = QFrame()
        card2.setObjectName("SettingCard")
        apply_card_shadow(card2)
        cv2 = QVBoxLayout(card2)
        cv2.setContentsMargins(0, 0, 0, 0)

        title2 = QWidget()
        title2.setFixedHeight(52)
        tr2 = QHBoxLayout(title2)
        tr2.setContentsMargins(16, 0, 16, 0)
        tr2.addWidget(QLabel("TMDB Poster Fetching"))
        cv2.addWidget(title2)

        form2 = QFormLayout()
        form2.setContentsMargins(16, 8, 16, 16)
        form2.setSpacing(12)

        self._tmdb_key = QLineEdit()
        self._tmdb_key.setPlaceholderText("Paste your TMDB v3 API key")
        self._tmdb_key.setText(db.get_setting('tmdb_api_key', ''))
        self._tmdb_key.setEchoMode(QLineEdit.EchoMode.Password)
        form2.addRow("API Key:", self._tmdb_key)

        # Status pill
        self._tmdb_status_lbl = QLabel("TMDB: Idle")
        self._tmdb_status_lbl.setStyleSheet(
            "color:#a8a59c; font-size:12px; padding:6px 12px;"
            "background:#18181d; border:1px solid #232329; border-radius:6px;"
        )
        form2.addRow("Status:", self._tmdb_status_lbl)

        btn_row = QHBoxLayout()
        gradient_qss = """
            QPushButton { background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #ffb547,stop:1 #ff7a1a);
                color: #1a1004; border: none; border-radius: 8px; padding: 8px 16px; font-weight: 600; font-size:12px; }
            QPushButton:hover { background: #ffc060; }
            QPushButton:disabled { background: #2e2e36; color: #6b6960; }
        """
        outline_qss = """
            QPushButton { background: transparent; border: 1px solid #2e2e36;
                color: #a8a59c; border-radius: 8px; padding: 8px 16px; font-size:12px; font-weight:600; }
            QPushButton:hover { border-color: #ffb547; color: #ffb547; }
        """

        self._tmdb_fetch_btn = QPushButton("Fetch Series")
        self._tmdb_fetch_btn.setStyleSheet(gradient_qss)
        self._tmdb_fetch_btn.clicked.connect(lambda: self._fetch_tmdb_posters('tv'))

        self._tmdb_movie_btn = QPushButton("Fetch Movies")
        self._tmdb_movie_btn.setStyleSheet(gradient_qss)
        self._tmdb_movie_btn.clicked.connect(lambda: self._fetch_tmdb_posters('movies'))

        self._tmdb_all_btn = QPushButton("Fetch All")
        self._tmdb_all_btn.setStyleSheet(gradient_qss)
        self._tmdb_all_btn.clicked.connect(lambda: self._fetch_tmdb_posters('all'))

        self._tmdb_pause_btn = QPushButton("Pause")
        self._tmdb_pause_btn.setStyleSheet(outline_qss)
        self._tmdb_pause_btn.clicked.connect(self._toggle_tmdb_pause)

        self._tmdb_stop_btn = QPushButton("Stop")
        self._tmdb_stop_btn.setStyleSheet(outline_qss)
        self._tmdb_stop_btn.clicked.connect(self._stop_tmdb)

        btn_row.addWidget(self._tmdb_fetch_btn)
        btn_row.addWidget(self._tmdb_movie_btn)
        btn_row.addWidget(self._tmdb_all_btn)
        btn_row.addWidget(self._tmdb_pause_btn)
        btn_row.addWidget(self._tmdb_stop_btn)
        btn_row.addStretch()
        form2.addRow("", btn_row)

        cv2.addLayout(form2)
        v.addWidget(card2)

        # Status polling timer
        self._tmdb_status_timer = QTimer(self)
        self._tmdb_status_timer.setInterval(800)
        self._tmdb_status_timer.timeout.connect(self._update_tmdb_status)
        self._tmdb_status_timer.start()
        self._update_tmdb_status()

        save_btn = QPushButton("Save Settings")
        save_btn.setFixedWidth(160)
        save_btn.setFixedHeight(40)
        save_btn.setStyleSheet("""
            QPushButton { background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #ffb547,stop:1 #ff7a1a);
                color: #1a1004; border: none; border-radius: 10px; font-weight: 600; font-size: 13px; }
            QPushButton:hover { background: #ffc060; }
        """)
        save_btn.clicked.connect(self._save)
        v.addWidget(save_btn, alignment=Qt.AlignmentFlag.AlignLeft)
        v.addStretch()
        return w

    def _build_about_tab(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)
        v.setAlignment(Qt.AlignmentFlag.AlignTop)

        card = QFrame()
        card.setObjectName("SettingCard")
        cv = QVBoxLayout(card)
        cv.setContentsMargins(20, 16, 20, 16)
        cv.setSpacing(8)

        try:
            from version import __version__
        except ImportError:
            __version__ = "dev"

        cv.addWidget(QLabel(f"<b>IPTV Player</b> v{__version__}"))
        cv.addWidget(QLabel("PyQt6 · Python · mpv · Xtream Codes API"))
        v.addWidget(card)
        v.addStretch()
        return w

    def _switch_tab(self, tab: str):
        tabs = ["Servers", "Playback", "About"]
        if tab in tabs:
            self._tab_stack.setCurrentIndex(tabs.index(tab))
        # Update button active states via style
        for name, btn in self._tab_btns.items():
            btn.setProperty("active", "true" if name == tab else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def showEvent(self, event):
        super().showEvent(event)
        self._refresh_server_cards()

    def _refresh_server_cards(self):
        self._servers = db.get_servers()
        # Clear old cards
        for i in reversed(range(self._srv_cards_layout.count())):
            item = self._srv_cards_layout.itemAt(i)
            if item and item.widget():
                item.widget().deleteLater()

        for srv in self._servers:
            card = ServerCard(srv)
            card.edit_clicked.connect(self._edit_server)
            card.delete_clicked.connect(self._del_server)
            card.activate_clicked.connect(self._activate_server)
            card.sync_clicked.connect(self._sync_server)
            self._srv_cards_layout.addWidget(card)

    def open_add_server(self):
        self._switch_tab("Servers")
        self._add_server()

    def _add_server(self):
        dlg = LoginDialog(self)
        if dlg.exec():
            self._refresh_server_cards()
            self.server_changed.emit()

    def _edit_server(self, srv: dict):
        dlg = LoginDialog(self, server=srv)
        if dlg.exec():
            self._refresh_server_cards()
            self.server_changed.emit()

    def _del_server(self, srv: dict):
        reply = QMessageBox.question(
            self, "Delete Server",
            f"Delete server '{srv.get('name', '')}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            db.delete_server(srv['id'])
            self._refresh_server_cards()
            self.server_changed.emit()

    def _activate_server(self, srv: dict):
        db.set_active_server(srv['id'])
        self._refresh_server_cards()
        self.server_changed.emit()
        self.status_message.emit(f"Active server: {srv.get('name', '')}")

    def _sync_server(self, srv: dict):
        try:
            running = self._sync_worker is not None and self._sync_worker.isRunning()
        except RuntimeError:
            running = False
        if running:
            self.status_message.emit("Sync already running…")
            return
        from ui.workers import SyncWorker, set_tmdb_paused
        set_tmdb_paused(True)                              # pause TMDB poster fetcher
        url, user, pw = srv['url'], srv['username'], srv['password']
        self.status_message.emit(f"Syncing {srv.get('name', '')}…")
        self.sync_progress.emit(0, 100)
        self._sync_worker = SyncWorker(url, user, pw, parent=self)
        # Explicit slot — PyQt6 signal-to-signal sometimes drops cross-thread.
        self._sync_worker.progress.connect(self._forward_sync_progress)
        self._sync_worker.result.connect(lambda stats, s=srv: self._on_sync_done(s, stats))
        self._sync_worker.error.connect(
            lambda e, s=srv: self._on_sync_error(s, e)
        )
        self._sync_worker.start()

    def _forward_sync_progress(self, done: int, total: int):
        self.sync_progress.emit(done, total)

    def _on_sync_error(self, srv: dict, err: str):
        from ui.workers import set_tmdb_paused
        set_tmdb_paused(False)
        self.sync_finished.emit()
        self.status_message.emit(f"Sync error ({srv.get('name','')}): {err}")

    def _on_sync_done(self, srv: dict, stats: dict):
        import time
        db.set_setting(f'last_sync_{int(srv.get("id", 0))}', str(time.time()))
        live_a, vod_a, ser_a = (
            stats.get('live_added', 0),
            stats.get('vod_added', 0),
            stats.get('series_added', 0),
        )
        summary = (
            f"{srv.get('name', '')} synced — "
            f"{stats.get('live', 0)} live ({live_a} new), "
            f"{stats.get('vod', 0)} movies ({vod_a} new), "
            f"{stats.get('series', 0)} series ({ser_a} new)"
        )
        self.synced.emit(int(srv.get('id', 0)))
        self._refresh_server_cards()
        urls = stats.get('live_icons', [])
        if urls:
            from ui.workers import PosterPrefetcher
            self.status_message.emit(f"{summary} — caching logos…")
            self._poster_prefetcher = PosterPrefetcher(urls, parent=self)
            self._poster_prefetcher.progress.connect(self._on_prefetch_progress)
            self._poster_prefetcher.finished.connect(lambda s=summary: self._on_prefetch_done(s))
            self._poster_prefetcher.start()
        else:
            self._on_prefetch_done(summary)

    def _on_prefetch_progress(self, done: int, total: int):
        # Map prefetch progress into 90..100 range.
        if total <= 0:
            return
        pct = 90 + int(10 * done / max(total, 1))
        self.sync_progress.emit(min(pct, 100), 100)

    def _on_prefetch_done(self, summary: str):
        from ui.workers import set_tmdb_paused
        set_tmdb_paused(False)
        self.sync_finished.emit()
        self.status_message.emit(summary)

    def _save(self):
        db.set_setting('mpv_extra_args', self._mpv_args.text().strip())
        db.set_setting('mpv_fullscreen', '1' if self._fullscreen.isChecked() else '0')
        db.set_setting('tmdb_api_key', self._tmdb_key.text().strip())
        self.status_message.emit("Settings saved.")

    def _fetch_tmdb_posters(self, mode: str = 'all'):
        if self._is_tmdb_running():
            self.status_message.emit("TMDB fetch already running.")
            return
        api_key = self._tmdb_key.text().strip()
        if not api_key:
            QMessageBox.warning(self, "No API Key", "Enter your TMDB API key first, then save.")
            return
        db.set_setting('tmdb_api_key', api_key)

        from ui.workers import TMDBFetcher, set_tmdb_paused
        set_tmdb_paused(False)
        self._tmdb_worker = TMDBFetcher(api_key, mode=mode, parent=self)
        self._tmdb_worker.progress.connect(
            lambda done, total: self.status_message.emit(f"TMDB posters: {done}/{total}…")
        )
        self._tmdb_worker.finished.connect(self._on_tmdb_finished)
        self._tmdb_worker.start()
        self._update_tmdb_status()

    def _is_tmdb_running(self) -> bool:
        try:
            return bool(self._tmdb_worker) and self._tmdb_worker.isRunning()
        except RuntimeError:
            return False

    def _toggle_tmdb_pause(self):
        from ui.workers import set_tmdb_paused, is_tmdb_paused
        set_tmdb_paused(not is_tmdb_paused())
        self._update_tmdb_status()

    def _stop_tmdb(self):
        if not self._is_tmdb_running():
            return
        try:
            self._tmdb_worker.requestInterruption()
        except Exception:
            pass
        self.status_message.emit("TMDB fetch stop requested.")

    def _on_tmdb_finished(self):
        self.status_message.emit("TMDB poster fetch complete.")
        self.synced.emit(int(db.get_active_server().get('id', 0)) if db.get_active_server() else 0)
        self._update_tmdb_status()

    def _update_tmdb_status(self):
        from ui.workers import is_tmdb_paused
        running = self._is_tmdb_running()
        if running and is_tmdb_paused():
            text = "Paused (Xtream sync running or manual pause)"
            color = "#ffb547"
        elif running:
            text = "Running"
            color = "#6cd97e"
        else:
            text = "Idle"
            color = "#a8a59c"
        self._tmdb_status_lbl.setText(f"TMDB: {text}")
        self._tmdb_status_lbl.setStyleSheet(
            f"color:{color}; font-size:12px; padding:6px 12px;"
            "background:#18181d; border:1px solid #232329; border-radius:6px;"
        )
        # Toggle button state
        if hasattr(self, '_tmdb_pause_btn'):
            self._tmdb_pause_btn.setText("Resume" if is_tmdb_paused() else "Pause")
            self._tmdb_pause_btn.setEnabled(running)
            self._tmdb_stop_btn.setEnabled(running)
            for btn in (self._tmdb_fetch_btn, self._tmdb_movie_btn, self._tmdb_all_btn):
                btn.setEnabled(not running)

    def _clear_cache(self):
        import os, shutil
        cache_dir = os.path.expanduser("~/.config/iptvshows/images")
        if os.path.exists(cache_dir):
            shutil.rmtree(cache_dir)
        self.status_message.emit("Image cache cleared.")

    def _clear_history(self):
        reply = QMessageBox.question(
            self, "Clear History",
            "Clear all watch history? This cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            with db._get_conn() as conn:
                conn.execute("DELETE FROM history")
                conn.execute("DELETE FROM watch_status")
                conn.execute("DELETE FROM series_progress")
            self.status_message.emit("Watch history cleared.")
