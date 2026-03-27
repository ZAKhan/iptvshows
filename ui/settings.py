from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QGroupBox,
    QLineEdit, QFormLayout, QMessageBox, QCheckBox,
)
from PyQt6.QtCore import Qt, pyqtSignal

import core.database as db
from ui.login_dialog import LoginDialog


class SettingsWidget(QWidget):
    server_changed = pyqtSignal()
    status_message = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tmdb_worker = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        header = QLabel("Settings")
        header.setObjectName("SectionTitle")
        layout.addWidget(header)

        # ── Servers group ─────────────────────────────────────────────────────
        srv_group = QGroupBox("IPTV Servers")
        srv_layout = QVBoxLayout(srv_group)

        self._srv_table = QTableWidget(0, 4)
        self._srv_table.setHorizontalHeaderLabels(["Name", "URL", "Username", "Active"])
        self._srv_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._srv_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self._srv_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self._srv_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self._srv_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._srv_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._srv_table.setFixedHeight(200)
        srv_layout.addWidget(self._srv_table)

        btn_row = QHBoxLayout()
        self._btn_add = QPushButton("+ Add Server")
        self._btn_edit = QPushButton("Edit")
        self._btn_del = QPushButton("Delete")
        self._btn_activate = QPushButton("Set Active")
        self._btn_activate.setObjectName("PlayBtn")
        btn_row.addWidget(self._btn_add)
        btn_row.addWidget(self._btn_edit)
        btn_row.addWidget(self._btn_del)
        btn_row.addStretch()
        btn_row.addWidget(self._btn_activate)
        srv_layout.addLayout(btn_row)

        self._btn_add.clicked.connect(self._add_server)
        self._btn_edit.clicked.connect(self._edit_server)
        self._btn_del.clicked.connect(self._del_server)
        self._btn_activate.clicked.connect(self._activate_server)

        layout.addWidget(srv_group)

        # ── MPV options group ─────────────────────────────────────────────────
        mpv_group = QGroupBox("MPV Options")
        mpv_form = QFormLayout(mpv_group)
        mpv_form.setSpacing(10)

        self._mpv_args = QLineEdit()
        self._mpv_args.setPlaceholderText("e.g. --hwdec=auto --vo=gpu")
        self._mpv_args.setText(db.get_setting('mpv_extra_args', ''))
        mpv_form.addRow("Extra arguments:", self._mpv_args)

        self._fullscreen = QCheckBox("Start in fullscreen")
        self._fullscreen.setChecked(db.get_setting('mpv_fullscreen', '0') == '1')
        mpv_form.addRow("", self._fullscreen)

        layout.addWidget(mpv_group)

        # ── TMDB group ────────────────────────────────────────────────────────
        tmdb_group = QGroupBox("TMDB (TV Show Posters)")
        tmdb_form = QFormLayout(tmdb_group)
        tmdb_form.setSpacing(10)

        self._tmdb_key = QLineEdit()
        self._tmdb_key.setPlaceholderText("Paste your TMDB v3 API key here")
        self._tmdb_key.setText(db.get_setting('tmdb_api_key', ''))
        self._tmdb_key.setEchoMode(QLineEdit.EchoMode.Password)
        tmdb_form.addRow("API Key:", self._tmdb_key)

        btn_row = QHBoxLayout()
        self._tmdb_fetch_btn = QPushButton("Fetch Series Posters")
        self._tmdb_fetch_btn.setObjectName("PlayBtn")
        self._tmdb_fetch_btn.clicked.connect(lambda: self._fetch_tmdb_posters('tv'))
        btn_row.addWidget(self._tmdb_fetch_btn)

        self._tmdb_movie_btn = QPushButton("Fetch Movie Posters")
        self._tmdb_movie_btn.setObjectName("PlayBtn")
        self._tmdb_movie_btn.clicked.connect(lambda: self._fetch_tmdb_posters('movies'))
        btn_row.addWidget(self._tmdb_movie_btn)

        self._tmdb_all_btn = QPushButton("Fetch All Posters")
        self._tmdb_all_btn.clicked.connect(lambda: self._fetch_tmdb_posters('all'))
        btn_row.addWidget(self._tmdb_all_btn)

        tmdb_form.addRow("", btn_row)

        layout.addWidget(tmdb_group)

        # ── Cache group ───────────────────────────────────────────────────────
        cache_group = QGroupBox("Cache")
        cache_layout = QHBoxLayout(cache_group)
        self._clear_cache_btn = QPushButton("Clear Image Cache")
        self._clear_cache_btn.clicked.connect(self._clear_cache)
        cache_layout.addWidget(self._clear_cache_btn)
        cache_layout.addStretch()
        layout.addWidget(cache_group)

        save_btn = QPushButton("Save Settings")
        save_btn.setObjectName("PlayBtn")
        save_btn.clicked.connect(self._save)
        layout.addWidget(save_btn)

        layout.addStretch()

        self._refresh_table()

    def showEvent(self, event):
        super().showEvent(event)
        self._refresh_table()

    def _refresh_table(self):
        servers = db.get_servers()
        self._servers = servers
        self._srv_table.setRowCount(len(servers))
        for i, s in enumerate(servers):
            self._srv_table.setItem(i, 0, QTableWidgetItem(s.get('name', '')))
            self._srv_table.setItem(i, 1, QTableWidgetItem(s.get('url', '')))
            self._srv_table.setItem(i, 2, QTableWidgetItem(s.get('username', '')))
            active = "✔" if s.get('active') else ""
            ai = QTableWidgetItem(active)
            ai.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._srv_table.setItem(i, 3, ai)

    def _selected_server(self):
        row = self._srv_table.currentRow()
        if row < 0 or row >= len(self._servers):
            return None
        return self._servers[row]

    def _add_server(self):
        dlg = LoginDialog(self)
        if dlg.exec():
            self._refresh_table()
            self.server_changed.emit()

    def _edit_server(self):
        srv = self._selected_server()
        if not srv:
            QMessageBox.information(self, "No Selection", "Select a server to edit.")
            return
        dlg = LoginDialog(self, server=srv)
        if dlg.exec():
            self._refresh_table()
            self.server_changed.emit()

    def _del_server(self):
        srv = self._selected_server()
        if not srv:
            return
        reply = QMessageBox.question(
            self, "Delete Server",
            f"Delete server '{srv.get('name', '')}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            db.delete_server(srv['id'])
            self._refresh_table()
            self.server_changed.emit()

    def _activate_server(self):
        srv = self._selected_server()
        if not srv:
            return
        db.set_active_server(srv['id'])
        self._refresh_table()
        self.server_changed.emit()
        self.status_message.emit(f"Active server: {srv.get('name', '')}")

    def _save(self):
        db.set_setting('mpv_extra_args', self._mpv_args.text().strip())
        db.set_setting('mpv_fullscreen', '1' if self._fullscreen.isChecked() else '0')
        db.set_setting('tmdb_api_key', self._tmdb_key.text().strip())
        self.status_message.emit("Settings saved.")

    def _fetch_tmdb_posters(self, mode: str = 'all'):
        if self._tmdb_worker and self._tmdb_worker.isRunning():
            return
        api_key = self._tmdb_key.text().strip()
        if not api_key:
            QMessageBox.warning(self, "No API Key", "Enter your TMDB API key first, then save.")
            return
        db.set_setting('tmdb_api_key', api_key)

        from ui.workers import TMDBFetcher
        self._tmdb_worker = TMDBFetcher(api_key, mode=mode, parent=self)
        self._tmdb_worker.progress.connect(self._on_tmdb_progress)
        self._tmdb_worker.finished.connect(self._on_tmdb_done)
        self._tmdb_worker.start()

        for btn in (self._tmdb_fetch_btn, self._tmdb_movie_btn, self._tmdb_all_btn):
            btn.setEnabled(False)
        self.status_message.emit(f"Fetching {mode} posters from TMDB…")

    def _on_tmdb_progress(self, done: int, total: int):
        self.status_message.emit(f"TMDB posters: {done}/{total}…")

    def _on_tmdb_done(self):
        for btn in (self._tmdb_fetch_btn, self._tmdb_movie_btn, self._tmdb_all_btn):
            btn.setEnabled(True)
        self.status_message.emit("TMDB poster fetch complete.")

    def _clear_cache(self):
        import os, shutil
        cache_dir = os.path.expanduser("~/.config/iptvshows/images")
        if os.path.exists(cache_dir):
            shutil.rmtree(cache_dir)
        self.status_message.emit("Image cache cleared.")
