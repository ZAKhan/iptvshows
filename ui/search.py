from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QTabWidget, QMessageBox,
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer

from ui.widgets import MediaListView
import core.database as db
import core.player as player


class SearchWidget(QWidget):
    status_message = pyqtSignal(str)

    def __init__(self, api, parent=None):
        super().__init__(parent)
        self.api = api
        self._build_ui()
        self._debounce = QTimer()
        self._debounce.setSingleShot(True)
        self._debounce.timeout.connect(self._do_search)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        top = QWidget()
        top.setFixedHeight(60)
        top.setStyleSheet("background:#111; border-bottom:1px solid #222;")
        tl = QHBoxLayout(top)
        tl.setContentsMargins(20, 10, 20, 10)

        self._search = QLineEdit()
        self._search.setPlaceholderText("🔍  Search live TV, movies, series…")
        self._search.setFixedHeight(36)
        self._search.textChanged.connect(self._on_text)
        tl.addWidget(self._search)

        layout.addWidget(top)

        self._tabs = QTabWidget()
        self._tabs.setVisible(False)

        self._live_grid = MediaListView()
        self._live_grid.card_play.connect(lambda i: self._play(i, 'live'))

        self._movie_grid = MediaListView()
        self._movie_grid.card_clicked.connect(lambda i: self._play(i, 'vod'))
        self._movie_grid.card_play.connect(lambda i: self._play(i, 'vod'))

        self._series_grid = MediaListView()
        self._series_grid.card_clicked.connect(self._show_series)
        self._series_grid.card_play.connect(self._show_series)

        self._tabs.addTab(self._live_grid, "Live TV")
        self._tabs.addTab(self._movie_grid, "Movies")
        self._tabs.addTab(self._series_grid, "Series")

        layout.addWidget(self._tabs, stretch=1)

        self._hint = QLabel("Start typing to search…")
        self._hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._hint.setStyleSheet("color:#444; font-size:16px;")
        layout.addWidget(self._hint)

    def _on_text(self, text: str):
        if len(text) < 2:
            self._hint.setVisible(True)
            self._tabs.setVisible(False)
            return
        self._hint.setVisible(False)
        self._tabs.setVisible(True)
        # Fix 3: stop before restart so rapid typing resets the timer correctly
        self._debounce.stop()
        self._debounce.start(300)

    def _do_search(self):
        q = self._search.text().strip()
        if len(q) < 2:
            return
        fl = db.search_live_streams(q)
        fm = db.search_vod_streams(q)
        fs = db.search_series(q)

        vod_ids = [str(m.get('stream_id', '')) for m in fm]
        vod_st  = db.bulk_get_watch_statuses(vod_ids, 'vod')
        for m in fm:
            m['_watch_status'] = vod_st.get(str(m.get('stream_id', '')))

        s_ids = [str(s.get('series_id', '')) for s in fs]
        s_st  = db.bulk_get_watch_statuses(s_ids, 'series')
        for s in fs:
            s['_watch_status'] = s_st.get(str(s.get('series_id', '')))

        self._live_grid.load(fl)
        self._movie_grid.load(fm)
        self._series_grid.load(fs)

        live_suffix   = " ⚠ not synced" if not db.has_live_data()   else f" ({len(fl)})"
        movies_suffix = " ⚠ not synced" if not db.has_vod_data()    else f" ({len(fm)})"
        series_suffix = " ⚠ not synced" if not db.has_series_data() else f" ({len(fs)})"
        self._tabs.setTabText(0, f"Live TV{live_suffix}")
        self._tabs.setTabText(1, f"Movies{movies_suffix}")
        self._tabs.setTabText(2, f"Series{series_suffix}")
        self.status_message.emit(f"Found {len(fl)+len(fm)+len(fs)} results")

    def _play(self, item: dict, stream_type: str):
        if stream_type == 'live':
            sid = str(item.get('stream_id', ''))
            ext = item.get('container_extension', 'ts')
            url = self.api.live_url(sid, ext)
        else:
            sid = str(item.get('stream_id', ''))
            ext = item.get('container_extension', 'mp4')
            url = self.api.vod_url(sid, ext)
        title = item.get('name', '')
        try:
            player.play(url, title)
            db.add_history(sid, stream_type, title, item.get('stream_icon', ''))
            if stream_type != 'live' and db.get_watch_status(sid, stream_type) != 'watched':
                db.set_watch_status(sid, stream_type, 'in_progress')
        except FileNotFoundError as e:
            QMessageBox.critical(self, "mpv not found", str(e))

    def _show_series(self, item: dict):
        from ui.series import SeriesDetailDialog
        dlg = SeriesDetailDialog(item, self.api, self)
        dlg.exec()
