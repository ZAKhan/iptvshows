from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, QApplication,
    QListWidgetItem, QLineEdit, QPushButton, QTextEdit,
    QStackedWidget, QMessageBox, QScrollArea, QSizePolicy,
    QFrame, QMenu,
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QPixmap, QKeySequence, QShortcut

from ui.workers import ApiWorker, ImageWorker, PosterPrefetcher, TMDBFetcher
from ui.widgets import LoadingLabel, _placeholder, MediaListView, SearchField
from ui.anim import apply_card_shadow
import core.database as db
import core.player as player
import api.m3u as m3u


class FilterSidebar(QWidget):
    filter_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(220)
        self.setObjectName("Surface")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        header = QLabel("FILTERS")
        header.setObjectName("SectionLbl")
        layout.addWidget(header)

        sep = QFrame()
        sep.setObjectName("HDiv")
        sep.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(sep)

        # Category search
        self._cat_search = SearchField("Filter categories…")
        self._cat_search.textChanged.connect(self._on_cat_search)
        layout.addWidget(self._cat_search)

        # Category list
        self._cat_list = QListWidget()
        self._cat_list.setObjectName("CategoryList")
        self._cat_list.currentRowChanged.connect(lambda _: self.filter_changed.emit())
        layout.addWidget(self._cat_list, stretch=1)

        self._all_cats: list = []

    def load_categories(self, cats: list):
        self._all_cats = cats
        self._render_cats(cats)

    def _render_cats(self, cats: list):
        row = self._cat_list.currentRow()
        self._cat_list.blockSignals(True)
        self._cat_list.clear()
        all_item = QListWidgetItem("All Movies")
        all_item.setData(Qt.ItemDataRole.UserRole, None)
        self._cat_list.addItem(all_item)
        for c in cats:
            it = QListWidgetItem(c.get('category_name', ''))
            it.setData(Qt.ItemDataRole.UserRole, c.get('category_id'))
            self._cat_list.addItem(it)
        self._cat_list.blockSignals(False)
        if row < 0:
            saved = db.get_setting('last_cat_vod', '')
            target = 0
            if saved:
                for i in range(self._cat_list.count()):
                    if str(self._cat_list.item(i).data(Qt.ItemDataRole.UserRole) or '') == saved:
                        target = i
                        break
            self._cat_list.setCurrentRow(target)
        else:
            self._cat_list.setCurrentRow(row)

    def _on_cat_search(self, text: str):
        if not text:
            self._render_cats(self._all_cats)
        else:
            q = text.lower()
            self._render_cats([c for c in self._all_cats if q in c.get('category_name','').lower()])

    def active_cat_id(self):
        item = self._cat_list.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item else None


class MoviesWidget(QWidget):
    status_message = pyqtSignal(str)

    def __init__(self, api, parent=None):
        super().__init__(parent)
        self.api = api
        self._all_movies: list = []
        self._syncing = False
        self._tmdb_worker = None
        self._view_mode = 'all'   # 'all' | 'new'
        self._build_ui()
        self._initial_load()

    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        if self.api is None:
            empty = self._make_empty()
            root.addWidget(empty)
            return

        self._filter_sidebar = FilterSidebar()
        self._filter_sidebar.filter_changed.connect(self._on_filter_changed)
        root.addWidget(self._filter_sidebar)

        sep = QFrame()
        sep.setObjectName("VDiv")
        sep.setFrameShape(QFrame.Shape.VLine)
        root.addWidget(sep)

        # Right: stacked grid ↔ detail
        self._stack = QStackedWidget()
        self._stack.addWidget(self._build_grid_page())
        self._stack.addWidget(self._build_detail_page())
        root.addWidget(self._stack, stretch=1)

        self._loading = LoadingLabel(self)

    def _make_empty(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl = QLabel("No server connected")
        lbl.setObjectName("PlayerInfo")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v.addWidget(lbl)
        return w

    def _build_grid_page(self) -> QWidget:
        page = QWidget()
        v = QVBoxLayout(page)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)

        # Top bar
        top = QWidget()
        top.setObjectName("TabHeader")
        top.setFixedHeight(56)
        tl = QHBoxLayout(top)
        tl.setContentsMargins(20, 8, 20, 8)
        tl.setSpacing(12)

        title = QLabel("Movies")
        title.setObjectName("TabHeading")
        tl.addWidget(title)

        self._count_lbl = QLabel("")
        self._count_lbl.setObjectName("CountLbl")
        tl.addWidget(self._count_lbl)

        tl.addSpacing(16)
        self._seg_all = QPushButton("All")
        self._seg_all.setObjectName("Chip")
        self._seg_all.setProperty("active", "true")
        self._seg_all.setFixedHeight(28)
        self._seg_all.clicked.connect(lambda: self._set_view('all'))
        tl.addWidget(self._seg_all)
        self._seg_new = QPushButton("New")
        self._seg_new.setObjectName("Chip")
        self._seg_new.setFixedHeight(28)
        self._seg_new.clicked.connect(lambda: self._set_view('new'))
        tl.addWidget(self._seg_new)

        tl.addStretch()

        self._search = SearchField("Search movies…")
        self._search.setMinimumWidth(160)
        self._search.setMaximumWidth(260)
        self._search.textChanged.connect(self._filter)
        tl.addWidget(self._search, stretch=1)

        v.addWidget(top)

        self._poster_grid = MediaListView()
        self._poster_grid.card_clicked.connect(self._show_detail)
        self._poster_grid.card_play.connect(self._play)
        self._poster_grid.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._poster_grid.customContextMenuRequested.connect(self._grid_context_menu)
        v.addWidget(self._poster_grid, stretch=1)
        return page

    def _grid_context_menu(self, pos):
        item = self._poster_grid.itemAt(pos)
        if not item:
            return
        data = item.data(Qt.ItemDataRole.UserRole)
        menu = QMenu(self)
        menu.addAction("▶  Play").triggered.connect(lambda: self._play(data))
        menu.addAction("📋  Copy URL").triggered.connect(lambda: self._copy_url(data))
        menu.addSeparator()
        sid = str(data.get('stream_id', ''))
        fav = db.is_favorite(sid, 'vod')
        menu.addAction("♥  Unfavorite" if fav else "♡  Favorite").triggered.connect(
            lambda: self._toggle_fav(data)
        )
        menu.exec(self._poster_grid.mapToGlobal(pos))

    def _copy_url(self, item: dict):
        if not self.api:
            return
        sid = str(item.get('stream_id', ''))
        ext = item.get('container_extension') or (db.get_vod_stream_data(sid) or {}).get('container_extension', 'mp4')
        url = self.api.vod_url(sid, ext)
        QApplication.clipboard().setText(f"'{url}'")
        self.status_message.emit(f"Copied URL for {item.get('name', '')}")

    def _build_detail_page(self) -> QWidget:
        page = QWidget()
        root = QVBoxLayout(page)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        bar = QWidget()
        bar.setObjectName("TabHeader")
        bar.setFixedHeight(52)
        bl = QHBoxLayout(bar)
        bl.setContentsMargins(20, 8, 20, 8)
        back_btn = QPushButton("← Back")
        back_btn.setObjectName("BackBtn")
        back_btn.clicked.connect(lambda: self._stack.setCurrentIndex(0))
        esc = QShortcut(QKeySequence(Qt.Key.Key_Escape), page)
        esc.activated.connect(lambda: self._stack.setCurrentIndex(0))
        self._detail_title_bar = QLabel()
        self._detail_title_bar.setObjectName("DetailBarTitle")
        bl.addWidget(back_btn)
        bl.addWidget(self._detail_title_bar, stretch=1)
        root.addWidget(bar)

        content = QScrollArea()
        content.setWidgetResizable(True)
        content.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        inner = QWidget()
        cl = QHBoxLayout(inner)
        cl.setContentsMargins(28, 28, 28, 28)
        cl.setSpacing(28)
        cl.setAlignment(Qt.AlignmentFlag.AlignTop)

        self._d_poster = QLabel()
        self._d_poster.setFixedSize(220, 330)
        self._d_poster.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        self._d_poster.setPixmap(_placeholder(220, 330, "🎬"))
        self._d_poster.setStyleSheet("border-radius: 12px;")
        apply_card_shadow(self._d_poster)
        cl.addWidget(self._d_poster, 0, Qt.AlignmentFlag.AlignTop)

        info_col = QVBoxLayout()
        info_col.setSpacing(12)
        info_col.setAlignment(Qt.AlignmentFlag.AlignTop)

        self._d_title = QLabel()
        self._d_title.setWordWrap(True)
        self._d_title.setObjectName("DetailHeading")
        info_col.addWidget(self._d_title)

        self._d_meta = QLabel()
        self._d_meta.setObjectName("MutedMedium")
        info_col.addWidget(self._d_meta)

        self._d_rating = QLabel()
        self._d_rating.setObjectName("RatingPill")
        self._d_rating.setFixedWidth(80)
        info_col.addWidget(self._d_rating)

        self._d_desc = QTextEdit()
        self._d_desc.setReadOnly(True)
        self._d_desc.setObjectName("DetailDesc")
        self._d_desc.setMinimumHeight(120)
        self._d_desc.setMaximumHeight(220)
        info_col.addWidget(self._d_desc)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        self._d_play_btn = QPushButton("▶  Play")
        self._d_play_btn.setObjectName("PrimaryGradBtn")
        self._d_play_btn.setFixedHeight(42)
        btn_row.addWidget(self._d_play_btn)

        self._d_fav_btn = QPushButton("♡  Favorite")
        self._d_fav_btn.setObjectName("FavBtn")
        self._d_fav_btn.setFixedHeight(42)
        btn_row.addWidget(self._d_fav_btn)

        self._d_watched_btn = QPushButton("✓  Mark Watched")
        self._d_watched_btn.setObjectName("WatchedBtn")
        self._d_watched_btn.setFixedHeight(42)
        btn_row.addWidget(self._d_watched_btn)
        btn_row.addStretch()
        info_col.addLayout(btn_row)
        info_col.addStretch()

        cl.addLayout(info_col, stretch=1)
        content.setWidget(inner)
        root.addWidget(content, stretch=1)
        return page

    # ── Data loading ──────────────────────────────────────────────────────────

    def _initial_load(self):
        if self.api is None:
            return
        w = ApiWorker(db.get_vod_categories_cached)
        w.result.connect(self._on_categories_loaded)
        w.start()
        self._w_cats = w

    def _on_categories_loaded(self, cats):
        if cats:
            self._filter_sidebar.load_categories(cats)
        self._load_from_db(None)

    def _on_filter_changed(self):
        cid = self._filter_sidebar.active_cat_id()
        db.set_setting('last_cat_vod', str(cid) if cid else '')
        self._load_from_db(cid)

    def _load_from_db(self, cat_id):
        if hasattr(self, '_count_lbl'):
            self._count_lbl.setText("Loading…")
        if self._view_mode == 'new':
            w = ApiWorker(db.list_new_vod_streams, '')
        else:
            w = ApiWorker(db.list_vod_streams, cat_id)
        w.result.connect(self._on_movies_loaded)
        w.error.connect(lambda e: self.status_message.emit(f"DB error: {e}"))
        w.start()
        self._w_load = w

    def _set_view(self, mode: str):
        if mode == self._view_mode:
            return
        self._view_mode = mode
        for btn, m in ((self._seg_all, 'all'), (self._seg_new, 'new')):
            btn.setProperty('active', 'true' if m == mode else 'false')
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        q = self._search.text().strip()
        if q:
            self._do_search()
        else:
            cid = self._filter_sidebar.active_cat_id() if hasattr(self, '_filter_sidebar') else None
            self._load_from_db(cid)

    def _on_movies_loaded(self, movies):
        self._all_movies = movies
        q = self._search.text().strip().lower() if hasattr(self, '_search') else ''
        display = [m for m in movies if q in m.get('name', '').lower()] if q else movies
        self._poster_grid.load(display)
        if hasattr(self, '_count_lbl'):
            self._count_lbl.setText(f"{len(display):,} movies")
        # TMDB poster fetching is now triggered manually from Settings → Playback.

    def _start_tmdb_fetch(self):
        key = db.get_setting('tmdb_api_key', '')
        if not key or self._tmdb_worker is not None:
            return
        self._tmdb_worker = TMDBFetcher(key, mode='movies', parent=self)
        self._tmdb_worker.poster_updated.connect(self._on_tmdb_poster)
        self._tmdb_worker.finished.connect(self._on_tmdb_done)
        self._tmdb_worker.progress.connect(
            lambda d, t: self.status_message.emit(f"TMDB posters: {d}/{t}…")
        )
        self._tmdb_worker.start()

    def _on_tmdb_poster(self, _kind: str, stream_id: str, url: str):
        self._poster_grid.refresh_poster(stream_id, url)

    def _on_tmdb_done(self):
        self._tmdb_worker = None
        self.status_message.emit("TMDB poster fetch complete.")

    def _filter(self, _text: str):
        if not hasattr(self, '_search_timer'):
            self._search_timer = QTimer(self)
            self._search_timer.setSingleShot(True)
            self._search_timer.setInterval(220)
            self._search_timer.timeout.connect(self._do_search)
        self._search_timer.start()

    def _do_search(self):
        q = self._search.text().strip()
        if not q:
            self._on_search_result(self._all_movies)
            return
        if self._view_mode == 'new':
            w = ApiWorker(db.list_new_vod_streams, q)
        else:
            w = ApiWorker(db.search_vod_streams_lite, q)
        w.result.connect(self._on_search_result)
        w.start()
        self._w_search = w

    def _on_search_result(self, rows):
        self._poster_grid.load(rows)
        self._count_lbl.setText(f"{len(rows):,} movies")

    # ── Sync ──────────────────────────────────────────────────────────────────

    def sync(self):
        """Kept for Ctrl+R / auto-sync compat — actual sync UI now lives in Settings."""
        if self._syncing or self.api is None:
            return
        self._syncing = True
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
        self._filter_sidebar.load_categories(db.get_vod_categories_cached())
        self._load_from_db(self._filter_sidebar.active_cat_id())
        n = stats.get('vod', 0)
        added = stats.get('vod_added', 0)
        removed = stats.get('vod_removed', 0)
        self.status_message.emit(
            f"Synced {n} movies — {added} new, {removed} removed"
        )
        urls = stats.get('vod_icons', [])
        if urls:
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
        self.status_message.emit(f"Sync error: {msg}")

    def reload_after_sync(self):
        """Called by main_window when a settings-driven sync finishes."""
        if not self.api:
            return
        self._initial_load()

    # ── Detail ────────────────────────────────────────────────────────────────

    def _show_detail(self, item: dict):
        sid = str(item.get('stream_id', ''))
        # Lite list rows lack full metadata — hydrate from JSON blob
        full = db.get_vod_stream_data(sid)
        if full:
            full['_watch_status'] = item.get('_watch_status')
            item = full
        self._current_item = item

        self._detail_title_bar.setText(item.get('name', ''))
        self._d_title.setText(item.get('name', ''))

        r = str(item.get('rating') or item.get('rating_5based', '') or '')
        self._d_rating.setText(f"★ {r}" if r and r not in ('None','0','0.0') else "")

        meta_parts = []
        if item.get('year'):     meta_parts.append(str(item['year']))
        if item.get('genre'):    meta_parts.append(item['genre'])
        if item.get('duration'): meta_parts.append(item['duration'])
        self._d_meta.setText("  ·  ".join(meta_parts))
        self._d_desc.setPlainText("Loading…")
        self._d_poster.setPixmap(_placeholder(220, 330, "🎬"))

        try: self._d_play_btn.clicked.disconnect()
        except TypeError: pass
        self._d_play_btn.clicked.connect(lambda: self._play(item))

        try: self._d_fav_btn.clicked.disconnect()
        except TypeError: pass
        self._update_fav_btn(sid)
        self._d_fav_btn.clicked.connect(lambda: self._toggle_fav(item))

        try: self._d_watched_btn.clicked.disconnect()
        except TypeError: pass
        self._update_watched_btn(sid)
        self._d_watched_btn.clicked.connect(lambda: self._cycle_watched(item))

        self._stack.setCurrentIndex(1)

        url = item.get('stream_icon') or item.get('cover', '')
        if url:
            w = ImageWorker(url, size=(220, 330))
            w.ready.connect(lambda pix, _: self._d_poster.setPixmap(pix) if not pix.isNull() else None)
            w.start()
            self._pw = w

        if self.api:
            w2 = ApiWorker(self.api.get_vod_info, sid)
            w2.result.connect(self._on_detail_info)
            w2.error.connect(lambda _: self._d_desc.setPlainText("No description available."))
            w2.start()
            self._iw = w2

    def _on_detail_info(self, data: dict):
        info = data.get('info', {})
        self._d_desc.setPlainText(
            info.get('description') or info.get('plot', '') or "No description available."
        )
        cover = info.get('movie_image') or info.get('cover_big', '')
        if cover:
            w = ImageWorker(cover, size=(220, 330))
            w.ready.connect(lambda pix, _: self._d_poster.setPixmap(pix) if not pix.isNull() else None)
            w.start()
            self._pw2 = w

    # ── Playback / favorites ──────────────────────────────────────────────────

    def _play(self, item: dict):
        if not self.api:
            return
        sid  = str(item.get('stream_id', ''))
        ext  = item.get('container_extension') or (db.get_vod_stream_data(sid) or {}).get('container_extension', 'mp4')
        url  = self.api.vod_url(sid, ext)
        name = item.get('name', 'Movie')
        try:
            player.play(url, name)
            db.add_history(sid, 'vod', name, item.get('stream_icon', ''))
            if db.get_watch_status(sid, 'vod') != 'watched':
                db.set_watch_status(sid, 'vod', 'in_progress')
                self._update_watched_btn(sid)
            self.status_message.emit(f"Playing: {name}")
        except FileNotFoundError as e:
            QMessageBox.critical(self, "mpv not found", str(e))

    def _toggle_fav(self, item: dict):
        sid = str(item.get('stream_id', ''))
        if db.is_favorite(sid, 'vod'):
            db.remove_favorite(sid, 'vod')
        else:
            db.add_favorite(sid, 'vod', item.get('name', ''), item.get('stream_icon', ''))
        self._update_fav_btn(sid)

    def _update_fav_btn(self, sid: str):
        if db.is_favorite(sid, 'vod'):
            self._d_fav_btn.setText("♥  Favorited")
            self._d_fav_btn.setProperty('favorited', 'true')
        else:
            self._d_fav_btn.setText("♡  Favorite")
            self._d_fav_btn.setProperty('favorited', 'false')
        self._d_fav_btn.style().unpolish(self._d_fav_btn)
        self._d_fav_btn.style().polish(self._d_fav_btn)

    def _cycle_watched(self, item: dict):
        sid = str(item.get('stream_id', ''))
        current = db.get_watch_status(sid, 'vod')
        db.set_watch_status(sid, 'vod', None if current == 'watched' else 'watched')
        self._update_watched_btn(sid)

    def _update_watched_btn(self, sid: str):
        status = db.get_watch_status(sid, 'vod')
        if status == 'watched':
            self._d_watched_btn.setText("✓  Watched")
        elif status == 'in_progress':
            self._d_watched_btn.setText("…  In Progress")
        else:
            self._d_watched_btn.setText("✓  Mark Watched")

    def open_detail(self, item: dict):
        self._show_detail(item)

    def _show_loading(self, show: bool):
        self._loading.setVisible(show)
        if show:
            self._loading.resize(self.size())
            self._loading.raise_()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, '_loading'):
            self._loading.resize(self.size())
