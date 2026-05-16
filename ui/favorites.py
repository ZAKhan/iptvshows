from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTabWidget,
    QListWidget, QListWidgetItem, QPushButton, QMenu,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QAction

import core.database as db
import core.player as player
from ui.workers import ApiWorker


class FavoritesWidget(QWidget):
    status_message = pyqtSignal(str)
    navigate_to    = pyqtSignal(str, dict)   # (stream_type, full_data_dict)

    def __init__(self, api, parent=None):
        super().__init__(parent)
        self.api = api
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QWidget()
        header.setObjectName("PageHeader")
        header.setFixedHeight(56)
        hl = QHBoxLayout(header)
        hl.setContentsMargins(24, 0, 24, 0)
        title = QLabel("Favorites & History")
        title.setObjectName("FavHeading")
        hl.addWidget(title)
        layout.addWidget(header)

        self._tabs = QTabWidget()
        self._tabs.setObjectName("SubTabs")

        self._fav_live = self._make_list('live')
        self._fav_vod = self._make_list('vod')
        self._fav_series = self._make_list('series')
        self._history_list = self._make_list(None, history=True)

        self._tabs.addTab(self._fav_live, "Live TV")
        self._tabs.addTab(self._fav_vod, "Movies")
        self._tabs.addTab(self._fav_series, "Series")
        self._tabs.addTab(self._history_list, "History")

        self._tabs.currentChanged.connect(self._refresh)
        layout.addWidget(self._tabs, stretch=1)

    def _make_list(self, stream_type, history=False) -> QListWidget:
        lst = QListWidget()
        lst.setObjectName("PlainList")
        lst.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        lst.customContextMenuRequested.connect(
            lambda pos, l=lst, t=stream_type, h=history: self._context(pos, l, t, h)
        )
        lst.itemDoubleClicked.connect(
            lambda item, t=stream_type, h=history: self._play_item(item, t, h)
        )
        lst.setProperty('stream_type', stream_type)
        lst.setProperty('history', history)
        return lst

    def showEvent(self, event):
        super().showEvent(event)
        self._refresh()

    def _refresh(self, _=None):
        tab = self._tabs.currentIndex()
        if tab == 0:
            self._dispatch(self._fav_live, db.get_favorites, 'live')
        elif tab == 1:
            self._dispatch(self._fav_vod, db.get_favorites, 'vod')
        elif tab == 2:
            self._dispatch(self._fav_series, db.get_favorites, 'series')
        elif tab == 3:
            self._dispatch(self._history_list, db.get_history, 100)

    def _dispatch(self, lst, fn, *args):
        w = ApiWorker(fn, *args)
        w.result.connect(lambda rows, l=lst: self._populate(l, rows))
        w.start()
        self._w = w

    def _populate(self, lst: QListWidget, rows: list):
        lst.clear()
        for row in rows:
            name = row.get('name', '')
            watched = row.get('watched', '') or row.get('added', '')
            display = f"{name}  —  {watched[:16]}" if watched else name
            item = QListWidgetItem(display)
            item.setData(Qt.ItemDataRole.UserRole, row)
            lst.addItem(item)

    def _play_item(self, list_item, stream_type, history):
        row = list_item.data(Qt.ItemDataRole.UserRole)
        if not row:
            return
        t   = row.get('stream_type') or stream_type
        sid = str(row.get('stream_id', ''))

        if t == 'live':
            data = db.get_live_stream_data(sid) or row
            url  = self.api.live_url(sid, data.get('container_extension', 'ts'))
            name = data.get('name', row.get('name', ''))
            icon = data.get('stream_icon', row.get('stream_icon', ''))
            try:
                player.play(url, name)
                db.add_history(sid, t, name, icon)
                self.status_message.emit(f"Playing: {name}")
            except FileNotFoundError as e:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.critical(self, "mpv not found", str(e))

        elif t == 'vod':
            data = db.get_vod_stream_data(sid)
            if data:
                self.navigate_to.emit('vod', data)
            else:
                # fallback: play directly with defaults
                url  = self.api.vod_url(sid)
                name = row.get('name', '')
                try:
                    player.play(url, name)
                    db.add_history(sid, t, name, row.get('stream_icon', ''))
                    self.status_message.emit(f"Playing: {name}")
                except FileNotFoundError as e:
                    from PyQt6.QtWidgets import QMessageBox
                    QMessageBox.critical(self, "mpv not found", str(e))

        elif t == 'series':
            data = db.get_series_data(sid)
            if data:
                self.navigate_to.emit('series', data)
            else:
                self.status_message.emit(f"Series not found in library — sync first")

    def _context(self, pos, lst: QListWidget, stream_type, history: bool):
        item = lst.itemAt(pos)
        if not item:
            return
        row = item.data(Qt.ItemDataRole.UserRole)
        menu = QMenu(self)

        play_act = QAction("▶  Play", self)
        play_act.triggered.connect(lambda: self._play_item(item, stream_type, history))
        menu.addAction(play_act)

        if not history:
            rm_act = QAction("🗑  Remove from Favorites", self)
            rm_act.triggered.connect(lambda: self._remove_fav(row, lst))
            menu.addAction(rm_act)

        menu.exec(lst.mapToGlobal(pos))

    def _remove_fav(self, row: dict, lst: QListWidget):
        sid = str(row.get('stream_id', ''))
        t = row.get('stream_type', '')
        db.remove_favorite(sid, t)
        self._refresh()
