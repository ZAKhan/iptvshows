from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListWidget,
    QListWidgetItem, QLineEdit, QPushButton, QTextEdit,
    QStackedWidget, QMessageBox, QScrollArea, QSizePolicy, QMenu,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap, QKeySequence, QShortcut

from ui.workers import ApiWorker, ImageWorker, PosterPrefetcher
from ui.widgets import MediaListView, LoadingLabel, _placeholder
import core.database as db
import core.player as player
import api.m3u as m3u


class MoviesWidget(QWidget):
    status_message = pyqtSignal(str)

    def __init__(self, api, parent=None):
        super().__init__(parent)
        self.api = api
        self._all_movies: list = []
        self._syncing = False

        self._build_ui()
        self._initial_load()   # DB only — no network

    # ── Layout ────────────────────────────────────────────────────────────────

    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Category sidebar (always visible)
        left = QWidget()
        left.setFixedWidth(200)
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 0, 0)
        ll.setSpacing(0)

        hdr = QLabel("  Categories")
        hdr.setFixedHeight(36)
        hdr.setStyleSheet(
            "background:#111;color:#888;font-size:11px;"
            "text-transform:uppercase;letter-spacing:1px;border-bottom:1px solid #222;"
        )
        ll.addWidget(hdr)

        # Fix 12: category search
        self._cat_search = QLineEdit()
        self._cat_search.setPlaceholderText("Filter categories…")
        self._cat_search.setFixedHeight(28)
        self._cat_search.setStyleSheet(
            "background:#1a1a1a;border:none;border-bottom:1px solid #222;"
            "color:#ccc;padding:0 8px;font-size:11px;"
        )
        self._cat_search.textChanged.connect(self._filter_categories)
        ll.addWidget(self._cat_search)

        self._cat_list = QListWidget()
        self._cat_list.setObjectName("CategoryList")
        self._cat_list.currentRowChanged.connect(self._on_cat_changed)
        ll.addWidget(self._cat_list)
        self._all_cats: list = []
        root.addWidget(left)

        # Right side: stacked (grid ↔ detail)
        self._stack = QStackedWidget()
        self._stack.addWidget(self._build_grid_page())   # index 0
        self._stack.addWidget(self._build_detail_page()) # index 1
        root.addWidget(self._stack, stretch=1)

        self._loading = LoadingLabel(self)

    def _build_grid_page(self) -> QWidget:
        page = QWidget()
        rl = QVBoxLayout(page)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(0)

        top = QWidget()
        top.setFixedHeight(48)
        top.setStyleSheet("background:#111;border-bottom:1px solid #222;")
        tl = QHBoxLayout(top)
        tl.setContentsMargins(12, 8, 12, 8)
        self._search = QLineEdit()
        self._search.setPlaceholderText("🔍  Search movies…")
        self._search.textChanged.connect(self._filter)
        tl.addWidget(self._search)
        self._count_lbl = QLabel("")
        self._count_lbl.setStyleSheet("color:#555;font-size:11px;margin-right:8px;")
        tl.addWidget(self._count_lbl)
        self._sync_btn = QPushButton("🔄  Sync")
        self._sync_btn.setFixedWidth(80)
        self._sync_btn.clicked.connect(self.sync)
        tl.addWidget(self._sync_btn)
        rl.addWidget(top)

        self._grid = MediaListView()
        self._grid.card_clicked.connect(self._show_detail)
        self._grid.card_play.connect(self._play)
        self._grid.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._grid.customContextMenuRequested.connect(self._grid_context_menu)
        rl.addWidget(self._grid)
        return page

    def _build_detail_page(self) -> QWidget:
        page = QWidget()
        root = QVBoxLayout(page)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Top bar with back button
        bar = QWidget()
        bar.setFixedHeight(48)
        bar.setStyleSheet("background:#111;border-bottom:1px solid #222;")
        bl = QHBoxLayout(bar)
        bl.setContentsMargins(12, 8, 12, 8)
        back_btn = QPushButton("← Back  [Esc]")
        back_btn.clicked.connect(lambda: self._stack.setCurrentIndex(0))
        back_btn.setFixedWidth(110)
        bl.addWidget(back_btn)

        # Fix 8/9: Esc to go back
        esc = QShortcut(QKeySequence(Qt.Key.Key_Escape), page)
        esc.activated.connect(lambda: self._stack.setCurrentIndex(0))

        self._detail_title_bar = QLabel()
        self._detail_title_bar.setStyleSheet("font-size:14px;font-weight:bold;color:#e0e0e0;padding-left:12px;")
        self._detail_title_bar.setMaximumWidth(700)  # fix 11
        bl.addWidget(self._detail_title_bar, stretch=1)
        root.addWidget(bar)

        # Content area
        content = QScrollArea()
        content.setWidgetResizable(True)
        content.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        inner = QWidget()
        cl = QHBoxLayout(inner)
        cl.setContentsMargins(24, 24, 24, 24)
        cl.setSpacing(24)
        cl.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Poster
        self._d_poster = QLabel()
        self._d_poster.setFixedSize(220, 330)
        self._d_poster.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        self._d_poster.setPixmap(_placeholder(220, 330, "🎬"))
        cl.addWidget(self._d_poster, 0, Qt.AlignmentFlag.AlignTop)

        # Info column
        info_col = QVBoxLayout()
        info_col.setSpacing(10)
        info_col.setAlignment(Qt.AlignmentFlag.AlignTop)

        self._d_title = QLabel()
        self._d_title.setWordWrap(True)
        self._d_title.setStyleSheet("font-size:22px;font-weight:bold;color:#e0e0e0;")
        info_col.addWidget(self._d_title)

        self._d_meta = QLabel()
        self._d_meta.setStyleSheet("color:#888;font-size:12px;")
        info_col.addWidget(self._d_meta)

        self._d_rating = QLabel()
        self._d_rating.setObjectName("RatingLabel")
        info_col.addWidget(self._d_rating)

        self._d_desc = QTextEdit()
        self._d_desc.setReadOnly(True)
        self._d_desc.setMinimumHeight(140)
        self._d_desc.setMaximumHeight(260)
        self._d_desc.setStyleSheet("background:#1a1a1a;border:1px solid #222;border-radius:6px;color:#bbb;padding:8px;")
        info_col.addWidget(self._d_desc)

        btn_row = QHBoxLayout()
        self._d_play_btn = QPushButton("▶  Play")
        self._d_play_btn.setObjectName("PlayBtn")
        self._d_play_btn.setFixedHeight(38)
        btn_row.addWidget(self._d_play_btn)

        self._d_fav_btn = QPushButton("☆  Add to Favorites")
        self._d_fav_btn.setObjectName("FavBtn")
        self._d_fav_btn.setFixedHeight(38)
        btn_row.addWidget(self._d_fav_btn)

        self._d_watched_btn = QPushButton("✓  Mark as Watched")
        self._d_watched_btn.setFixedHeight(38)
        btn_row.addWidget(self._d_watched_btn)
        btn_row.addStretch()
        info_col.addLayout(btn_row)
        info_col.addStretch()

        cl.addLayout(info_col, stretch=1)
        content.setWidget(inner)
        root.addWidget(content, stretch=1)
        return page

    # ── Sync (user-triggered only) ────────────────────────────────────────────

    def sync(self):
        if self._syncing:
            return
        self._syncing = True
        self._sync_btn.setText("Syncing…")
        self._sync_btn.setEnabled(False)
        self.status_message.emit("Downloading M3U playlist…")

        self._w = ApiWorker(
            m3u.sync_all,
            self.api.server_url, self.api.username, self.api.password
        )
        self._w.result.connect(self._on_sync_done)
        self._w.error.connect(self._on_sync_error)
        self._w.start()

    def _on_sync_done(self, stats: dict):
        self._syncing = False
        self._sync_btn.setText("🔄  Sync")
        self._sync_btn.setEnabled(True)
        self._populate_categories(db.get_vod_categories_cached())
        self._load_from_db(self._active_cat_id())
        n = stats.get('vod', 0)
        self.status_message.emit(f"Synced {n} movies — fetching posters…")
        self._start_prefetch(stats.get('vod_icons', []))

    def _start_prefetch(self, urls: list):
        self._prefetcher = PosterPrefetcher(urls, parent=self)
        self._prefetcher.progress.connect(
            lambda done, total: self.status_message.emit(f"Caching posters: {done}/{total}…")
        )
        self._prefetcher.finished.connect(
            lambda: self.status_message.emit("All posters cached.")
        )
        self._prefetcher.start()

    def _on_sync_error(self, msg):
        self._syncing = False
        self._sync_btn.setText("🔄  Sync")
        self._sync_btn.setEnabled(True)
        self.status_message.emit(f"Sync error: {msg}")

    # ── Categories ────────────────────────────────────────────────────────────

    def _populate_categories(self, cats):
        self._all_cats = cats
        self._render_categories(cats)

    def _render_categories(self, cats):
        current = self._cat_list.currentRow()
        self._cat_list.blockSignals(True)
        self._cat_list.clear()
        all_item = QListWidgetItem("All Movies")
        all_item.setData(Qt.ItemDataRole.UserRole, None)
        self._cat_list.addItem(all_item)
        for cat in cats:
            item = QListWidgetItem(cat.get('category_name', ''))
            item.setData(Qt.ItemDataRole.UserRole, cat.get('category_id'))
            self._cat_list.addItem(item)
        self._cat_list.blockSignals(False)
        self._cat_list.setCurrentRow(max(current, 0))
        if current < 0:
            self._load_from_db(None)

    def _filter_categories(self, text: str):
        if not text:
            self._render_categories(self._all_cats)
        else:
            q = text.lower()
            filtered = [c for c in self._all_cats
                        if q in c.get('category_name', '').lower()]
            self._render_categories(filtered)

    def _on_cat_changed(self, row):
        item = self._cat_list.item(row)
        if item:
            self._load_from_db(item.data(Qt.ItemDataRole.UserRole))
            self._stack.setCurrentIndex(0)

    def _initial_load(self):
        cats = db.get_vod_categories_cached()
        if cats:
            self._populate_categories(cats)
        else:
            self._count_lbl.setText("No data — click Sync")

    def _active_cat_id(self):
        item = self._cat_list.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    # ── Grid ──────────────────────────────────────────────────────────────────

    def _load_from_db(self, cat_id):
        movies = db.get_vod_streams_cached(cat_id)
        self._all_movies = movies
        self._show_loading(False)
        q = self._search.text().strip().lower()
        display = [m for m in movies if q in m.get('name','').lower()] if q else movies
        self._attach_statuses(display, 'vod', 'stream_id')
        self._grid.load(display)
        self._count_lbl.setText(f"{len(self._all_movies)} movies")

    def _filter(self, text):
        q = text.strip()
        if q:
            filtered = db.search_vod_streams(q)
        else:
            filtered = self._all_movies
        self._attach_statuses(filtered, 'vod', 'stream_id')
        self._grid.load(filtered)
        self._count_lbl.setText(f"{len(filtered)} movies")

    def _attach_statuses(self, items: list, stream_type: str, id_key: str):
        ids = [str(m.get(id_key, '')) for m in items]
        statuses = db.bulk_get_watch_statuses(ids, stream_type)
        for m in items:
            m['_watch_status'] = statuses.get(str(m.get(id_key, '')))

    # ── Detail panel ──────────────────────────────────────────────────────────

    def _show_detail(self, item: dict):
        self._current_item = item
        sid = str(item.get('stream_id', ''))

        self._detail_title_bar.setText(item.get('name', ''))
        self._d_title.setText(item.get('name', ''))

        r = item.get('rating') or item.get('rating_5based', '')
        self._d_rating.setText(f"⭐ {r}" if r else "")

        meta_parts = []
        if item.get('year'):       meta_parts.append(str(item['year']))
        if item.get('genre'):      meta_parts.append(item['genre'])
        if item.get('duration'):   meta_parts.append(item['duration'])
        self._d_meta.setText("  ·  ".join(meta_parts))

        self._d_desc.setPlainText("Loading…")
        self._d_poster.setPixmap(_placeholder(220, 330, "🎬"))

        # Fix 2: safe disconnect before reconnecting
        try:
            self._d_play_btn.clicked.disconnect()
        except TypeError:
            pass
        self._d_play_btn.clicked.connect(lambda: self._play(item))

        try:
            self._d_fav_btn.clicked.disconnect()
        except TypeError:
            pass
        self._update_fav_btn(sid)
        self._d_fav_btn.clicked.connect(lambda: self._toggle_fav(item))

        try:
            self._d_watched_btn.clicked.disconnect()
        except TypeError:
            pass
        self._update_watched_btn(sid)
        self._d_watched_btn.clicked.connect(lambda: self._cycle_watched(item))

        self._stack.setCurrentIndex(1)

        # Async: poster + info
        url = item.get('stream_icon') or item.get('cover', '')
        if url:
            w = ImageWorker(url, size=(220, 330))
            w.ready.connect(lambda pix, _: self._d_poster.setPixmap(pix) if not pix.isNull() else None)
            w.start()
            self._pw = w

        w2 = ApiWorker(self.api.get_vod_info, sid)
        w2.result.connect(self._on_detail_info)
        w2.error.connect(lambda _: self._d_desc.setPlainText("No description available."))
        w2.start()
        self._iw = w2

    def _on_detail_info(self, data: dict):
        info = data.get('info', {})
        self._d_desc.setPlainText(info.get('description') or info.get('plot', '') or "No description available.")
        cover = info.get('movie_image') or info.get('cover_big', '')
        if cover:
            w = ImageWorker(cover, size=(220, 330))
            w.ready.connect(lambda pix, _: self._d_poster.setPixmap(pix) if not pix.isNull() else None)
            w.start()
            self._pw2 = w

    # ── Playback / favorites ──────────────────────────────────────────────────

    def _play(self, item: dict):
        sid  = str(item.get('stream_id', ''))
        ext  = item.get('container_extension', 'mp4')
        url  = self.api.vod_url(sid, ext)
        name = item.get('name', 'Movie')
        try:
            player.play(url, name)
            db.add_history(sid, 'vod', name, item.get('stream_icon', ''))
            if db.get_watch_status(sid, 'vod') != 'watched':
                db.set_watch_status(sid, 'vod', 'in_progress')
                self._refresh_grid_badge(sid)
                self._update_watched_btn(sid)
            self.status_message.emit(f"Playing: {name}")
        except FileNotFoundError as e:
            QMessageBox.critical(self, "mpv not found", str(e))

    def _grid_context_menu(self, pos):
        it = self._grid.itemAt(pos)
        if not it:
            return
        data = it.data(Qt.ItemDataRole.UserRole)
        sid = str(data.get('stream_id', ''))
        menu = QMenu(self)
        menu.addAction("Mark Watched").triggered.connect(
            lambda: self._set_grid_status(sid, 'watched', it))
        menu.addAction("Mark In Progress").triggered.connect(
            lambda: self._set_grid_status(sid, 'in_progress', it))
        menu.addAction("Clear Status").triggered.connect(
            lambda: self._set_grid_status(sid, None, it))
        menu.exec(self._grid.mapToGlobal(pos))

    def _set_grid_status(self, sid: str, status, list_item):
        db.set_watch_status(sid, 'vod', status)
        list_item.setData(Qt.ItemDataRole.UserRole + 2, status)
        self._grid.update(self._grid.indexFromItem(list_item))

    def _refresh_grid_badge(self, sid: str):
        status = db.get_watch_status(sid, 'vod')
        for i in range(self._grid.count()):
            it = self._grid.item(i)
            if str(it.data(Qt.ItemDataRole.UserRole).get('stream_id', '')) == sid:
                it.setData(Qt.ItemDataRole.UserRole + 2, status)
                self._grid.update(self._grid.indexFromItem(it))
                break

    def _cycle_watched(self, item: dict):
        sid = str(item.get('stream_id', ''))
        current = db.get_watch_status(sid, 'vod')
        new_status = None if current == 'watched' else 'watched'
        db.set_watch_status(sid, 'vod', new_status)
        self._update_watched_btn(sid)
        self._refresh_grid_badge(sid)

    def _update_watched_btn(self, sid: str):
        status = db.get_watch_status(sid, 'vod')
        if status == 'watched':
            self._d_watched_btn.setText("✓  Watched")
        elif status == 'in_progress':
            self._d_watched_btn.setText("…  In Progress  ·  Mark Watched")
        else:
            self._d_watched_btn.setText("✓  Mark as Watched")

    def _toggle_fav(self, item: dict):
        sid = str(item.get('stream_id', ''))
        if db.is_favorite(sid, 'vod'):
            db.remove_favorite(sid, 'vod')
        else:
            db.add_favorite(sid, 'vod', item.get('name', ''), item.get('stream_icon', ''))
        self._update_fav_btn(sid)

    def _update_fav_btn(self, sid: str):
        if db.is_favorite(sid, 'vod'):
            self._d_fav_btn.setText("★  Remove Favorite")
            self._d_fav_btn.setProperty('favorited', 'true')
        else:
            self._d_fav_btn.setText("☆  Add to Favorites")
            self._d_fav_btn.setProperty('favorited', 'false')
        self._d_fav_btn.style().unpolish(self._d_fav_btn)
        self._d_fav_btn.style().polish(self._d_fav_btn)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def open_detail(self, item: dict):
        """Navigate directly to the detail page for a given movie dict (called from Favorites)."""
        self._show_detail(item)

    def _show_loading(self, show):
        self._loading.setVisible(show)
        if show:
            self._loading.resize(self.size())
            self._loading.raise_()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._loading.resize(self.size())
