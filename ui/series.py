from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, QApplication,
    QListWidgetItem, QLineEdit, QPushButton, QTextEdit,
    QStackedWidget, QSplitter, QMessageBox, QScrollArea, QMenu,
    QFrame,
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QKeySequence, QShortcut

from ui.workers import ApiWorker, ImageWorker, PosterPrefetcher, TMDBFetcher
from ui.widgets import MediaListView, LoadingLabel, _placeholder, SearchField
from ui.anim import apply_card_shadow
import core.database as db
import core.player as player
import api.m3u as m3u
import api.tmdb as tmdb


class SeriesWidget(QWidget):
    status_message = pyqtSignal(str)

    def __init__(self, api, parent=None):
        super().__init__(parent)
        self.api = api
        self._all_series: list = []
        self._seasons_data: dict = {}
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
            empty = QLabel("No server connected")
            empty.setObjectName("PlayerInfo")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            root.addWidget(empty)
            return

        # ── Category sidebar ──────────────────────────────────────────────────
        left = QFrame()
        left.setObjectName("SidebarPanel")
        left.setFixedWidth(220)
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 0, 0)
        ll.setSpacing(0)

        cat_hdr = QWidget()
        cat_hdr.setObjectName("PageHeader")
        cat_hdr.setFixedHeight(48)
        chl = QHBoxLayout(cat_hdr)
        chl.setContentsMargins(14, 0, 14, 0)
        lbl = QLabel("CATEGORIES")
        lbl.setObjectName("SectionLbl")
        chl.addWidget(lbl)
        ll.addWidget(cat_hdr)

        self._cat_search = SearchField("Filter categories…")
        self._cat_search.textChanged.connect(self._filter_categories)
        ll.addWidget(self._cat_search)

        self._cat_list = QListWidget()
        self._cat_list.setObjectName("CategoryList")
        self._cat_list.currentRowChanged.connect(self._on_cat_changed)
        ll.addWidget(self._cat_list)
        self._all_cats: list = []
        root.addWidget(left)

        # ── Right stack (grid ↔ detail) ───────────────────────────────────────
        self._stack = QStackedWidget()
        self._stack.addWidget(self._build_grid_page())
        self._stack.addWidget(self._build_detail_page())
        root.addWidget(self._stack, stretch=1)

        self._loading = LoadingLabel(self)

    def _build_grid_page(self) -> QWidget:
        page = QWidget()
        v = QVBoxLayout(page)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)

        top = QWidget()
        top.setObjectName("TabHeader")
        top.setFixedHeight(56)
        tl = QHBoxLayout(top)
        tl.setContentsMargins(20, 8, 20, 8)
        tl.setSpacing(12)

        title_lbl = QLabel("Series")
        title_lbl.setObjectName("TabHeading")
        tl.addWidget(title_lbl)

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

        self._search = SearchField("Search series…")
        self._search.setMinimumWidth(160)
        self._search.setMaximumWidth(260)
        self._search.textChanged.connect(self._filter)
        tl.addWidget(self._search, stretch=1)

        v.addWidget(top)

        self._grid = MediaListView()
        self._grid.card_clicked.connect(self._show_detail)
        self._grid.card_play.connect(self._show_detail)
        v.addWidget(self._grid)
        return page

    def _build_detail_page(self) -> QWidget:
        page = QWidget()
        root = QVBoxLayout(page)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Top bar
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
        self._d_title_bar = QLabel()
        self._d_title_bar.setObjectName("DetailBarTitle")
        bl.addWidget(back_btn)
        bl.addWidget(self._d_title_bar, stretch=1)
        root.addWidget(bar)

        # Hero info strip
        info_strip = QFrame()
        info_strip.setObjectName("DetailInfoStrip")
        info_strip.setFixedHeight(200)
        isl = QHBoxLayout(info_strip)
        isl.setContentsMargins(24, 16, 24, 16)
        isl.setSpacing(20)

        self._d_poster = QLabel()
        self._d_poster.setFixedSize(113, 170)
        self._d_poster.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._d_poster.setPixmap(_placeholder(113, 170, "🎞"))
        self._d_poster.setStyleSheet("border-radius: 10px;")
        apply_card_shadow(self._d_poster)
        isl.addWidget(self._d_poster)

        meta_col = QVBoxLayout()
        meta_col.setSpacing(4)

        self._d_title = QLabel()
        self._d_title.setObjectName("PanelHeading")
        meta_col.addWidget(self._d_title)

        self._d_meta = QLabel()
        self._d_meta.setObjectName("CountLbl")
        meta_col.addWidget(self._d_meta)

        self._d_genres = QLabel()
        self._d_genres.setObjectName("MutedDesc")
        meta_col.addWidget(self._d_genres)

        self._d_network = QLabel()
        self._d_network.setObjectName("NetworkLbl")
        meta_col.addWidget(self._d_network)

        self._d_desc = QLabel()
        self._d_desc.setWordWrap(True)
        self._d_desc.setObjectName("MutedDesc")
        self._d_desc.setMaximumHeight(60)
        self._d_desc.setAlignment(Qt.AlignmentFlag.AlignTop)
        meta_col.addWidget(self._d_desc)
        meta_col.addStretch()
        isl.addLayout(meta_col, stretch=1)
        root.addWidget(info_strip)

        # Action bar
        btn_bar = QWidget()
        btn_bar.setObjectName("TabHeader")
        btn_bar.setFixedHeight(52)
        bbl = QHBoxLayout(btn_bar)
        bbl.setContentsMargins(20, 8, 20, 8)
        bbl.setSpacing(10)

        self._d_continue_btn = QPushButton("▶  Continue")
        self._d_continue_btn.setObjectName("PrimaryGradBtn")
        self._d_continue_btn.setFixedHeight(36)
        self._d_continue_btn.setVisible(False)
        bbl.addWidget(self._d_continue_btn)

        self._d_fav_btn = QPushButton("♡  Favorite")
        self._d_fav_btn.setObjectName("FavBtn")
        self._d_fav_btn.setFixedHeight(36)
        bbl.addWidget(self._d_fav_btn)
        bbl.addStretch()
        root.addWidget(btn_bar)

        # Season | Episode splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(1)

        self._season_list = QListWidget()
        self._season_list.setObjectName("SeasonList")
        self._season_list.setMaximumWidth(180)
        self._season_list.currentRowChanged.connect(self._on_season_changed)
        splitter.addWidget(self._season_list)

        self._ep_list = QListWidget()
        self._ep_list.setObjectName("EpisodeList")
        self._ep_list.itemDoubleClicked.connect(self._play_episode)
        self._ep_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._ep_list.customContextMenuRequested.connect(self._ep_context_menu)
        splitter.addWidget(self._ep_list)
        splitter.setSizes([180, 9999])
        root.addWidget(splitter, stretch=1)

        self._ep_status = QLabel("Double-click an episode to play")
        self._ep_status.setObjectName("EpStatus")
        self._ep_status.setFixedHeight(24)
        root.addWidget(self._ep_status)

        return page

    # ── Sync ──────────────────────────────────────────────────────────────────

    def sync(self):
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
        self._populate_categories(db.get_series_categories_cached())
        self._load_from_db(self._active_cat_id())
        n = stats.get('series', 0)
        added = stats.get('series_added', 0)
        removed = stats.get('series_removed', 0)
        self.status_message.emit(
            f"Synced {n} series — {added} new, {removed} removed"
        )
        self._start_prefetch(stats.get('series_icons', []))

    def _start_prefetch(self, urls: list):
        self._prefetcher = PosterPrefetcher(urls, parent=self)
        self._prefetcher.progress.connect(
            lambda done, total: self.status_message.emit(f"Caching posters: {done}/{total}…")
        )
        self._prefetcher.finished.connect(lambda: self.status_message.emit("All posters cached."))
        self._prefetcher.start()

    def _on_sync_error(self, msg):
        self._syncing = False
        self.status_message.emit(f"Sync error: {msg}")

    def reload_after_sync(self):
        if not self.api:
            return
        self._initial_load()

    # ── Categories ────────────────────────────────────────────────────────────

    def _initial_load(self):
        if self.api is None:
            return
        w = ApiWorker(db.get_series_categories_cached)
        w.result.connect(self._on_categories_loaded)
        w.start()
        self._w_cats = w

    def _on_categories_loaded(self, cats):
        if cats:
            self._populate_categories(cats)
        else:
            self._count_lbl.setText("No data — click Sync")

    def _populate_categories(self, cats):
        self._all_cats = cats
        self._render_categories(cats)

    def _render_categories(self, cats):
        current = self._cat_list.currentRow()
        self._cat_list.blockSignals(True)
        self._cat_list.clear()
        all_item = QListWidgetItem("All Series")
        all_item.setData(Qt.ItemDataRole.UserRole, None)
        self._cat_list.addItem(all_item)
        for cat in cats:
            item = QListWidgetItem(cat.get('category_name', ''))
            item.setData(Qt.ItemDataRole.UserRole, cat.get('category_id'))
            self._cat_list.addItem(item)
        self._cat_list.blockSignals(False)
        if current < 0:
            saved = db.get_setting('last_cat_series', '')
            target = 0
            if saved:
                for i in range(self._cat_list.count()):
                    if str(self._cat_list.item(i).data(Qt.ItemDataRole.UserRole) or '') == saved:
                        target = i
                        break
            self._cat_list.setCurrentRow(target)
            if target == 0:
                self._load_from_db(None)
        else:
            self._cat_list.setCurrentRow(current)

    def _filter_categories(self, text: str):
        if not text:
            self._render_categories(self._all_cats)
        else:
            q = text.lower()
            self._render_categories(
                [c for c in self._all_cats if q in c.get('category_name', '').lower()]
            )

    def _on_cat_changed(self, row):
        item = self._cat_list.item(row)
        if item:
            cid = item.data(Qt.ItemDataRole.UserRole)
            db.set_setting('last_cat_series', str(cid) if cid else '')
            self._load_from_db(cid)
            self._stack.setCurrentIndex(0)

    def _active_cat_id(self):
        item = self._cat_list.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    # ── Grid ──────────────────────────────────────────────────────────────────

    def _load_from_db(self, cat_id):
        self._count_lbl.setText("Loading…")
        if self._view_mode == 'new':
            w = ApiWorker(db.list_new_series, '')
        else:
            w = ApiWorker(db.list_series, cat_id)
        w.result.connect(self._on_series_loaded)
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
            self._load_from_db(self._active_cat_id())

    def _on_series_loaded(self, series):
        self._all_series = series
        self._show_loading(False)
        q = self._search.text().strip().lower()
        display = [s for s in series if q in s.get('name', '').lower()] if q else series
        self._attach_statuses(display)
        self._grid.load(display)
        self._count_lbl.setText(f"{len(self._all_series):,} series")
        # TMDB poster fetching is triggered from Settings → Playback.

    def _start_tmdb_fetch(self):
        key = db.get_setting('tmdb_api_key', '')
        if not key or self._tmdb_worker is not None:
            return
        self._tmdb_worker = TMDBFetcher(key, mode='tv', parent=self)
        self._tmdb_worker.poster_updated.connect(self._on_tmdb_poster)
        self._tmdb_worker.finished.connect(self._on_tmdb_done)
        self._tmdb_worker.progress.connect(
            lambda d, t: self.status_message.emit(f"TMDB posters: {d}/{t}…")
        )
        self._tmdb_worker.start()

    def _on_tmdb_poster(self, _kind: str, series_id: str, url: str):
        self._grid.refresh_poster(series_id, url)

    def _on_tmdb_done(self):
        self._tmdb_worker = None
        self.status_message.emit("TMDB poster fetch complete.")

    def _filter(self, _text):
        if not hasattr(self, '_search_timer'):
            self._search_timer = QTimer(self)
            self._search_timer.setSingleShot(True)
            self._search_timer.setInterval(220)
            self._search_timer.timeout.connect(self._do_search)
        self._search_timer.start()

    def _do_search(self):
        q = self._search.text().strip()
        if not q:
            self._on_search_result(self._all_series)
            return
        if self._view_mode == 'new':
            w = ApiWorker(db.list_new_series, q)
        else:
            w = ApiWorker(db.search_series_lite, q)
        w.result.connect(self._on_search_result)
        w.start()
        self._w_search = w

    def _on_search_result(self, rows):
        self._attach_statuses(rows)
        self._grid.load(rows)
        self._count_lbl.setText(f"{len(rows):,} series")

    def _attach_statuses(self, items: list):
        ids = [str(s.get('series_id', '')) for s in items]
        statuses = db.bulk_get_watch_statuses(ids, 'series')
        for s in items:
            s['_watch_status'] = statuses.get(str(s.get('series_id', '')))

    # ── Detail panel ──────────────────────────────────────────────────────────

    def _show_detail(self, item: dict):
        sid = str(item.get('series_id', ''))
        full = db.get_series_data(sid)
        if full:
            full['_watch_status'] = item.get('_watch_status')
            item = full
        self._current_series = item
        name = item.get('name', '')

        self._d_title_bar.setText(name)
        self._d_title.setText(name)

        r = item.get('rating') or item.get('rating_5based', '')
        parts = []
        if item.get('releaseDate'):
            parts.append(str(item['releaseDate'])[:4])
        if r:
            parts.append(f"★ {r}")
        self._d_meta.setText("  ·  ".join(parts))
        self._d_genres.setText("")
        self._d_network.setText("")
        self._d_desc.setText("Loading…")
        self._d_poster.setPixmap(_placeholder(113, 170, "🎞"))
        self._season_list.clear()
        self._ep_list.clear()
        self._ep_status.setText("Loading episodes…")
        self._seasons_data = {}

        self._update_fav_btn(sid)
        try: self._d_fav_btn.clicked.disconnect()
        except TypeError: pass
        self._d_fav_btn.clicked.connect(lambda: self._toggle_fav(item))

        try: self._d_continue_btn.clicked.disconnect()
        except TypeError: pass
        progress = db.get_series_progress(sid)
        if progress:
            label = f"▶  Continue: S{progress['season_num']} · E{progress['ep_num']} — {progress['ep_title']}"
            self._d_continue_btn.setText(label)
            self._d_continue_btn.setVisible(True)
            self._d_continue_btn.clicked.connect(
                lambda: self._jump_to_episode(progress['season_num'], progress['episode_id'], play=True)
            )
        else:
            self._d_continue_btn.setVisible(False)

        self._stack.setCurrentIndex(1)

        url = item.get('cover') or item.get('stream_icon', '')
        if url:
            w = ImageWorker(url, size=(113, 170))
            w.ready.connect(lambda pix, _: self._d_poster.setPixmap(pix) if not pix.isNull() else None)
            w.start()
            self._pw = w

        api_key = db.get_setting('tmdb_api_key', '')
        if api_key and name:
            tw = ApiWorker(tmdb.get_tv_details, api_key, name)
            tw.result.connect(self._on_tmdb_details)
            tw.start()
            self._tmdb_w = tw

        m3u_eps = item.get('_m3u_episodes')
        if m3u_eps:
            self._on_series_info({'info': {}, 'seasons': m3u_eps['seasons'],
                                  'episodes': m3u_eps['episodes']})
        elif self.api:
            w2 = ApiWorker(self.api.get_series_info, sid)
            w2.result.connect(self._on_series_info)
            w2.error.connect(lambda e: self._ep_status.setText(f"Error: {e}"))
            w2.start()
            self._iw = w2

    def _on_series_info(self, data: dict):
        info = data.get('info', {})
        desc = info.get('plot') or info.get('description', '') or "No description."
        self._d_desc.setText(desc)

        cover = info.get('cover_big') or info.get('backdrop_path', [''])
        if isinstance(cover, list):
            cover = cover[0] if cover else ''
        if cover:
            w = ImageWorker(cover, size=(113, 170))
            w.ready.connect(lambda pix, _: self._d_poster.setPixmap(pix) if not pix.isNull() else None)
            w.start()
            self._pw2 = w

        seasons = data.get('seasons', [])
        self._seasons_data = data.get('episodes', {})

        self._season_list.clear()
        if seasons:
            for s in seasons:
                item = QListWidgetItem(f"Season {s.get('season_number', '?')}")
                item.setData(Qt.ItemDataRole.UserRole, str(s.get('season_number', '1')))
                self._season_list.addItem(item)
        elif self._seasons_data:
            for snum in sorted(self._seasons_data.keys(),
                               key=lambda x: int(x) if str(x).isdigit() else 0):
                item = QListWidgetItem(f"Season {snum}")
                item.setData(Qt.ItemDataRole.UserRole, snum)
                self._season_list.addItem(item)

        total = sum(len(v) for v in self._seasons_data.values())
        self._ep_status.setText(
            f"{self._season_list.count()} seasons · {total} episodes  —  double-click to play"
        )

        sid = str(self._current_series.get('series_id', ''))
        progress = db.get_series_progress(sid)
        if progress and self._season_list.count():
            self._jump_to_episode(progress['season_num'], progress['episode_id'])
        elif self._season_list.count():
            self._season_list.setCurrentRow(0)

    def _on_tmdb_details(self, data: dict):
        if not data:
            return
        parts = []
        if data.get('year'):             parts.append(data['year'])
        if data.get('vote_average'):     parts.append(f"TMDB ★ {data['vote_average']}")
        if data.get('number_of_seasons'): parts.append(f"{data['number_of_seasons']} seasons")
        if data.get('number_of_episodes'): parts.append(f"{data['number_of_episodes']} eps")
        if parts:
            self._d_meta.setText("  ·  ".join(parts))

        genres = data.get('genres', [])
        if genres:
            self._d_genres.setText("  ·  ".join(genres[:4]))

        network_parts = []
        if data.get('networks'):         network_parts.append(data['networks'][0])
        if data.get('status'):           network_parts.append(data['status'])
        if data.get('created_by'):       network_parts.append("by " + ", ".join(data['created_by'][:2]))
        if network_parts:
            self._d_network.setText("  ·  ".join(network_parts))

        overview = data.get('overview', '')
        if overview and len(overview) > len(self._d_desc.text()):
            self._d_desc.setText(overview)

        poster_url = data.get('poster_url')
        if poster_url:
            w = ImageWorker(poster_url, size=(113, 170))
            w.ready.connect(lambda pix, _: self._d_poster.setPixmap(pix) if not pix.isNull() else None)
            w.start()
            self._tmdb_poster_w = w

    def _on_season_changed(self, row):
        item = self._season_list.item(row)
        if not item:
            return
        snum = item.data(Qt.ItemDataRole.UserRole)
        eps = self._seasons_data.get(snum, [])

        ep_ids = [str(ep.get('id', '')) for ep in eps]
        ep_statuses = db.bulk_get_watch_statuses(ep_ids, 'series_ep')

        self._ep_list.clear()
        for ep in eps:
            ep_id    = str(ep.get('id', ''))
            ep_num   = ep.get('episode_num', '?')
            ep_title = ep.get('title', f"Episode {ep_num}")
            status   = ep_statuses.get(ep_id)
            prefix   = "✓  " if status == 'watched' else ("…  " if status == 'in_progress' else "    ")
            label    = (f"{prefix}{ep_num:>3}.  {ep_title}"
                       if isinstance(ep_num, int) else f"{prefix}{ep_title}")
            litem = QListWidgetItem(label)
            litem.setData(Qt.ItemDataRole.UserRole,     ep)
            litem.setData(Qt.ItemDataRole.UserRole + 1, status)
            self._ep_list.addItem(litem)

    def _play_episode(self, list_item):
        ep = list_item.data(Qt.ItemDataRole.UserRole)
        if not ep or not self.api:
            return
        ep_id    = str(ep.get('id', ''))
        ep_num   = ep.get('episode_num', '?')
        ep_title = ep.get('title', f"Episode {ep_num}")
        ext      = ep.get('container_extension', 'mp4')
        url      = ep.get('stream_url') or self.api.series_url(ep_id, ext)
        series_name = self._current_series.get('name', '')
        title    = f"{series_name} — {ep_title}"

        season_item = self._season_list.currentItem()
        season_num  = season_item.data(Qt.ItemDataRole.UserRole) if season_item else '1'

        try:
            player.play(url, title)
            series_id = str(self._current_series.get('series_id', ''))
            db.add_history(ep_id, 'series', title, self._current_series.get('cover', ''))
            db.save_series_progress(series_id, ep_id, season_num, ep_num, ep_title)

            if db.get_watch_status(ep_id, 'series_ep') != 'watched':
                self._set_ep_status(ep_id, 'in_progress', list_item)
            if db.get_watch_status(series_id, 'series') != 'watched':
                db.set_watch_status(series_id, 'series', 'in_progress')

            label = f"▶  Continue: S{season_num} · E{ep_num} — {ep_title}"
            self._d_continue_btn.setText(label)
            self._d_continue_btn.setVisible(True)
            self.status_message.emit(f"Playing: {title}")
        except FileNotFoundError as e:
            QMessageBox.critical(self, "mpv not found", str(e))

    def _jump_to_episode(self, season_num: str, episode_id: str, play: bool = False):
        target_row = 0
        for i in range(self._season_list.count()):
            if str(self._season_list.item(i).data(Qt.ItemDataRole.UserRole)) == str(season_num):
                target_row = i
                break
        self._season_list.setCurrentRow(target_row)
        for i in range(self._ep_list.count()):
            it = self._ep_list.item(i)
            ep = it.data(Qt.ItemDataRole.UserRole)
            if str(ep.get('id', '')) == str(episode_id):
                self._ep_list.setCurrentRow(i)
                self._ep_list.scrollToItem(it)
                if play:
                    self._play_episode(it)
                break

    def _ep_context_menu(self, pos):
        litem = self._ep_list.itemAt(pos)
        if not litem:
            return
        ep    = litem.data(Qt.ItemDataRole.UserRole)
        ep_id = str(ep.get('id', ''))
        menu  = QMenu(self)
        menu.addAction("▶  Play").triggered.connect(lambda: self._play_episode(litem))
        menu.addAction("📋  Copy URL").triggered.connect(lambda: self._copy_ep_url(ep))
        menu.addSeparator()
        menu.addAction("Mark Watched").triggered.connect(
            lambda: self._set_ep_status(ep_id, 'watched', litem))
        menu.addAction("Mark In Progress").triggered.connect(
            lambda: self._set_ep_status(ep_id, 'in_progress', litem))
        menu.addAction("Clear Status").triggered.connect(
            lambda: self._set_ep_status(ep_id, None, litem))
        menu.exec(self._ep_list.mapToGlobal(pos))

    def _copy_ep_url(self, ep: dict):
        if not self.api:
            return
        ep_id = str(ep.get('id', ''))
        ext   = ep.get('container_extension', 'mp4')
        url   = ep.get('stream_url') or self.api.series_url(ep_id, ext)
        QApplication.clipboard().setText(f"'{url}'")
        self.status_message.emit(f"Copied URL for {ep.get('title', 'episode')}")

    def _set_ep_status(self, ep_id: str, status, litem):
        db.set_watch_status(ep_id, 'series_ep', status)
        ep       = litem.data(Qt.ItemDataRole.UserRole)
        ep_num   = ep.get('episode_num', '?')
        ep_title = ep.get('title', f"Episode {ep_num}")
        prefix   = "✓  " if status == 'watched' else ("…  " if status == 'in_progress' else "    ")
        label    = (f"{prefix}{ep_num:>3}.  {ep_title}"
                   if isinstance(ep_num, int) else f"{prefix}{ep_title}")
        litem.setText(label)
        litem.setData(Qt.ItemDataRole.UserRole + 1, status)

    def _toggle_fav(self, item: dict):
        sid = str(item.get('series_id', ''))
        if db.is_favorite(sid, 'series'):
            db.remove_favorite(sid, 'series')
        else:
            db.add_favorite(sid, 'series', item.get('name', ''), item.get('cover', ''))
        self._update_fav_btn(sid)

    def _update_fav_btn(self, sid: str):
        if db.is_favorite(sid, 'series'):
            self._d_fav_btn.setText("♥  Favorited")
            self._d_fav_btn.setProperty('favorited', 'true')
        else:
            self._d_fav_btn.setText("♡  Favorite")
            self._d_fav_btn.setProperty('favorited', 'false')
        self._d_fav_btn.style().unpolish(self._d_fav_btn)
        self._d_fav_btn.style().polish(self._d_fav_btn)

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
