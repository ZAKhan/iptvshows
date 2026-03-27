from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListWidget,
    QListWidgetItem, QLineEdit, QPushButton, QTextEdit,
    QStackedWidget, QSplitter, QMessageBox, QScrollArea, QMenu,
)
from PyQt6.QtCore import Qt, pyqtSignal, QEvent
from PyQt6.QtGui import QKeySequence, QShortcut

from ui.workers import ApiWorker, ImageWorker, PosterPrefetcher
from ui.widgets import MediaListView, LoadingLabel, _placeholder
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

        self._build_ui()
        self._initial_load()   # DB only — no network

    # ── Layout ────────────────────────────────────────────────────────────────

    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Category sidebar
        left = QWidget()
        left.setFixedWidth(200)
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 0, 0)
        ll.setSpacing(0)
        hdr = QLabel("  Categories")
        hdr.setFixedHeight(26)
        hdr.setStyleSheet(
            "background:#111;color:#666;font-size:10px;"
            "text-transform:uppercase;letter-spacing:1px;border-bottom:1px solid #222;"
        )
        ll.addWidget(hdr)

        self._cat_search = QLineEdit()
        self._cat_search.setPlaceholderText("Filter…")
        self._cat_search.setFixedHeight(24)
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
        self._all_cats: list = []   # full unfiltered list
        root.addWidget(left)

        # Right stacked: grid ↔ detail
        self._stack = QStackedWidget()
        self._stack.addWidget(self._build_grid_page())    # 0
        self._stack.addWidget(self._build_detail_page())  # 1
        root.addWidget(self._stack, stretch=1)

        self._loading = LoadingLabel(self)

    def _build_grid_page(self) -> QWidget:
        page = QWidget()
        rl = QVBoxLayout(page)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(0)

        top = QWidget()
        top.setFixedHeight(34)
        top.setStyleSheet("background:#111;border-bottom:1px solid #222;")
        tl = QHBoxLayout(top)
        tl.setContentsMargins(8, 4, 8, 4)
        self._search = QLineEdit()
        self._search.setPlaceholderText("🔍  Search series…")
        self._search.textChanged.connect(self._filter)
        tl.addWidget(self._search)
        self._count_lbl = QLabel("")   # fix 1: was missing
        self._count_lbl.setStyleSheet("color:#555;font-size:11px;margin-right:8px;")
        tl.addWidget(self._count_lbl)
        self._sync_btn = QPushButton("🔄  Sync")
        self._sync_btn.setFixedWidth(80)
        self._sync_btn.clicked.connect(self.sync)
        tl.addWidget(self._sync_btn)
        rl.addWidget(top)

        self._grid = MediaListView()
        self._grid.card_clicked.connect(self._show_detail)
        self._grid.card_play.connect(self._show_detail)
        rl.addWidget(self._grid)
        return page

    def _build_detail_page(self) -> QWidget:
        page = QWidget()
        root = QVBoxLayout(page)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Top bar
        bar = QWidget()
        bar.setFixedHeight(34)
        bar.setStyleSheet("background:#111;border-bottom:1px solid #1e1e2e;")
        bl = QHBoxLayout(bar)
        bl.setContentsMargins(8, 4, 8, 4)
        back_btn = QPushButton("← Back")
        back_btn.setFixedWidth(80)
        back_btn.clicked.connect(lambda: self._stack.setCurrentIndex(0))
        bl.addWidget(back_btn)

        esc = QShortcut(QKeySequence(Qt.Key.Key_Escape), page)
        esc.activated.connect(lambda: self._stack.setCurrentIndex(0))
        self._d_title_bar = QLabel()
        self._d_title_bar.setStyleSheet("font-size:13px;font-weight:600;color:#c4bbfc;padding-left:10px;")
        self._d_title_bar.setMaximumWidth(800)
        bl.addWidget(self._d_title_bar, stretch=1)
        root.addWidget(bar)

        # Info strip: poster + rich metadata
        info_strip = QWidget()
        info_strip.setFixedHeight(190)
        info_strip.setStyleSheet("background:#0f0f1c;border-bottom:1px solid #1e1e2e;")
        isl = QHBoxLayout(info_strip)
        isl.setContentsMargins(14, 10, 14, 10)
        isl.setSpacing(14)

        self._d_poster = QLabel()
        self._d_poster.setFixedSize(113, 170)
        self._d_poster.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._d_poster.setPixmap(_placeholder(113, 170, "🎞"))
        self._d_poster.setStyleSheet("border-radius:6px;")
        isl.addWidget(self._d_poster)

        meta_col = QVBoxLayout()
        meta_col.setSpacing(3)
        meta_col.setContentsMargins(0, 0, 0, 0)

        self._d_title = QLabel()
        self._d_title.setStyleSheet("font-size:16px;font-weight:700;color:#eeeef8;")
        meta_col.addWidget(self._d_title)

        # Row: year · TMDB score · seasons · episodes
        self._d_meta = QLabel()
        self._d_meta.setStyleSheet("color:#6a6a8a;font-size:11px;")
        meta_col.addWidget(self._d_meta)

        # Genres
        self._d_genres = QLabel()
        self._d_genres.setObjectName("GenresLabel")
        meta_col.addWidget(self._d_genres)

        # Network · Status · Created by
        self._d_network = QLabel()
        self._d_network.setObjectName("NetworkLabel")
        meta_col.addWidget(self._d_network)

        # Description
        self._d_desc = QLabel()
        self._d_desc.setWordWrap(True)
        self._d_desc.setStyleSheet("color:#8888aa;font-size:11px;line-height:1.4;")
        self._d_desc.setMaximumHeight(64)
        self._d_desc.setAlignment(Qt.AlignmentFlag.AlignTop)
        meta_col.addWidget(self._d_desc)

        meta_col.addStretch()
        isl.addLayout(meta_col, stretch=1)
        root.addWidget(info_strip)

        # Button bar
        btn_bar = QWidget()
        btn_bar.setFixedHeight(32)
        btn_bar.setStyleSheet("background:#0a0a12;border-bottom:1px solid #1e1e2e;")
        bbl = QHBoxLayout(btn_bar)
        bbl.setContentsMargins(10, 4, 10, 4)
        bbl.setSpacing(6)

        self._d_continue_btn = QPushButton("▶  Continue")
        self._d_continue_btn.setObjectName("PlayBtn")
        self._d_continue_btn.setVisible(False)
        bbl.addWidget(self._d_continue_btn)

        self._d_fav_btn = QPushButton("☆  Favorite")
        self._d_fav_btn.setObjectName("FavBtn")
        bbl.addWidget(self._d_fav_btn)

        bbl.addStretch()
        root.addWidget(btn_bar)

        # Seasons | Episodes splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(1)

        self._season_list = QListWidget()
        self._season_list.setObjectName("CategoryList")
        self._season_list.setMaximumWidth(160)
        self._season_list.currentRowChanged.connect(self._on_season_changed)
        splitter.addWidget(self._season_list)

        self._ep_list = QListWidget()
        self._ep_list.itemDoubleClicked.connect(self._play_episode)
        self._ep_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._ep_list.customContextMenuRequested.connect(self._ep_context_menu)
        splitter.addWidget(self._ep_list)
        splitter.setSizes([160, 9999])

        root.addWidget(splitter, stretch=1)

        # Status bar at bottom
        self._ep_status = QLabel("Double-click an episode to play")
        self._ep_status.setStyleSheet("color:#444460;font-size:10px;padding:2px 10px;"
                                      "background:#0a0a12;border-top:1px solid #1e1e2e;")
        self._ep_status.setFixedHeight(20)
        root.addWidget(self._ep_status)

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
        self._populate_categories(db.get_series_categories_cached())
        self._load_from_db(self._active_cat_id())
        n = stats.get('series', 0)
        self.status_message.emit(f"Synced {n} series — fetching posters…")
        self._start_prefetch(stats.get('series_icons', []))

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

    def _initial_load(self):
        cats = db.get_series_categories_cached()
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

    def _active_cat_id(self):
        item = self._cat_list.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    # ── Grid ──────────────────────────────────────────────────────────────────

    def _load_from_db(self, cat_id):
        series = db.get_series_cached(cat_id)
        self._all_series = series
        self._show_loading(False)
        q = self._search.text().strip().lower()
        display = [s for s in series if q in s.get('name','').lower()] if q else series
        self._attach_statuses(display)
        self._grid.load(display)
        self._count_lbl.setText(f"{len(self._all_series)} series")

    def _filter(self, text):
        q = text.strip()
        if q:
            filtered = db.search_series(q)
        else:
            filtered = self._all_series
        self._attach_statuses(filtered)
        self._grid.load(filtered)
        self._count_lbl.setText(f"{len(filtered)} series")

    def _attach_statuses(self, items: list):
        ids = [str(s.get('series_id', '')) for s in items]
        statuses = db.bulk_get_watch_statuses(ids, 'series')
        for s in items:
            s['_watch_status'] = statuses.get(str(s.get('series_id', '')))

    # ── Detail panel ──────────────────────────────────────────────────────────

    def _show_detail(self, item: dict):
        self._current_series = item
        sid = str(item.get('series_id', ''))

        name = item.get('name', '')
        self._d_title_bar.setText(name)
        self._d_title.setText(name)

        # Build meta line from available IPTV data
        r = item.get('rating') or item.get('rating_5based', '')
        parts = []
        if item.get('releaseDate'):
            parts.append(str(item['releaseDate'])[:4])
        if r:
            parts.append(f"⭐ {r}")
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
        try:
            self._d_fav_btn.clicked.disconnect()
        except TypeError:
            pass
        self._d_fav_btn.clicked.connect(lambda: self._toggle_fav(item))

        # Continue button
        try:
            self._d_continue_btn.clicked.disconnect()
        except TypeError:
            pass
        progress = db.get_series_progress(sid)
        if progress:
            label = f"▶  Continue: S{progress['season_num']} · E{progress['ep_num']} — {progress['ep_title']}"
            self._d_continue_btn.setText(label)
            self._d_continue_btn.setVisible(True)
            self._d_continue_btn.clicked.connect(lambda: self._jump_to_episode(
                progress['season_num'], progress['episode_id'], play=True))
        else:
            self._d_continue_btn.setVisible(False)

        self._stack.setCurrentIndex(1)

        url = item.get('cover') or item.get('stream_icon', '')
        if url:
            w = ImageWorker(url, size=(113, 170))
            w.ready.connect(lambda pix, _: self._d_poster.setPixmap(pix) if not pix.isNull() else None)
            w.start()
            self._pw = w

        # Fetch rich TMDB metadata in background
        api_key = db.get_setting('tmdb_api_key', '')
        if api_key and name:
            tw = ApiWorker(tmdb.get_tv_details, api_key, name)
            tw.result.connect(self._on_tmdb_details)
            tw.start()
            self._tmdb_w = tw

        m3u_eps = item.get('_m3u_episodes')
        if m3u_eps:
            # Episode data already embedded from M3U parse — no API call needed
            self._on_series_info({'info': {}, 'seasons': m3u_eps['seasons'],
                                  'episodes': m3u_eps['episodes']})
        else:
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

        # Jump to last played episode if progress exists, otherwise go to S1
        sid = str(self._current_series.get('series_id', ''))
        progress = db.get_series_progress(sid)
        if progress and self._season_list.count():
            self._jump_to_episode(progress['season_num'], progress['episode_id'])
        elif self._season_list.count():
            self._season_list.setCurrentRow(0)

    def _on_tmdb_details(self, data: dict):
        if not data:
            return

        # Update meta line with TMDB score + season/episode counts
        parts = []
        if data.get('year'):
            parts.append(data['year'])
        if data.get('vote_average'):
            parts.append(f"TMDB ⭐ {data['vote_average']}")
        if data.get('number_of_seasons'):
            parts.append(f"{data['number_of_seasons']} seasons")
        if data.get('number_of_episodes'):
            parts.append(f"{data['number_of_episodes']} eps")
        if parts:
            self._d_meta.setText("  ·  ".join(parts))

        # Genres
        genres = data.get('genres', [])
        if genres:
            self._d_genres.setText("  ·  ".join(genres[:4]))

        # Network · Status · Created by
        network_parts = []
        networks = data.get('networks', [])
        if networks:
            network_parts.append(networks[0])
        if data.get('status'):
            network_parts.append(data['status'])
        creators = data.get('created_by', [])
        if creators:
            network_parts.append("by " + ", ".join(creators[:2]))
        if network_parts:
            self._d_network.setText("  ·  ".join(network_parts))

        # Override description with TMDB overview if it has meaningful content
        overview = data.get('overview', '')
        if overview and len(overview) > len(self._d_desc.text()):
            self._d_desc.setText(overview)

        # Use TMDB poster if available and no cover already loaded
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
            label    = f"{prefix}{ep_num:>3}.  {ep_title}" if isinstance(ep_num, int) else f"{prefix}{ep_title}"
            litem = QListWidgetItem(label)
            litem.setData(Qt.ItemDataRole.UserRole,     ep)
            litem.setData(Qt.ItemDataRole.UserRole + 1, status)
            self._ep_list.addItem(litem)

    def _play_episode(self, list_item):
        ep = list_item.data(Qt.ItemDataRole.UserRole)
        if not ep:
            return
        ep_id    = str(ep.get('id', ''))
        ep_num   = ep.get('episode_num', '?')
        ep_title = ep.get('title', f"Episode {ep_num}")
        ext      = ep.get('container_extension', 'mp4')
        url      = ep.get('stream_url') or self.api.series_url(ep_id, ext)
        series_name = self._current_series.get('name', '')
        title    = f"{series_name} — {ep_title}"

        # Current season from the season selector
        season_item = self._season_list.currentItem()
        season_num  = season_item.data(Qt.ItemDataRole.UserRole) if season_item else '1'

        try:
            player.play(url, title)
            series_id = str(self._current_series.get('series_id', ''))
            db.add_history(ep_id, 'series', title, self._current_series.get('cover', ''))

            # Save last-played position for this series
            db.save_series_progress(series_id, ep_id, season_num, ep_num, ep_title)

            # Mark episode and series-level status
            if db.get_watch_status(ep_id, 'series_ep') != 'watched':
                self._set_ep_status(ep_id, 'in_progress', list_item)
            if db.get_watch_status(series_id, 'series') != 'watched':
                db.set_watch_status(series_id, 'series', 'in_progress')

            # Refresh the Continue button label
            label = f"▶  Continue: S{season_num} · E{ep_num} — {ep_title}"
            self._d_continue_btn.setText(label)
            self._d_continue_btn.setVisible(True)

            self.status_message.emit(f"Playing: {title}")
        except FileNotFoundError as e:
            QMessageBox.critical(self, "mpv not found", str(e))

    # ── Continue watching ─────────────────────────────────────────────────────

    def _jump_to_episode(self, season_num: str, episode_id: str, play: bool = False):
        """Select the season and scroll to the episode. Optionally play it."""
        # Find and select the matching season row
        target_row = 0
        for i in range(self._season_list.count()):
            if str(self._season_list.item(i).data(Qt.ItemDataRole.UserRole)) == str(season_num):
                target_row = i
                break
        # setCurrentRow triggers _on_season_changed which populates _ep_list
        self._season_list.setCurrentRow(target_row)

        # Find the episode row
        for i in range(self._ep_list.count()):
            it = self._ep_list.item(i)
            ep = it.data(Qt.ItemDataRole.UserRole)
            if str(ep.get('id', '')) == str(episode_id):
                self._ep_list.setCurrentRow(i)
                self._ep_list.scrollToItem(it)
                if play:
                    self._play_episode(it)
                break

    # ── Episode watch status ──────────────────────────────────────────────────

    def _ep_context_menu(self, pos):
        litem = self._ep_list.itemAt(pos)
        if not litem:
            return
        ep    = litem.data(Qt.ItemDataRole.UserRole)
        ep_id = str(ep.get('id', ''))
        menu  = QMenu(self)
        menu.addAction("▶  Play").triggered.connect(lambda: self._play_episode(litem))
        menu.addSeparator()
        menu.addAction("Mark Watched").triggered.connect(
            lambda: self._set_ep_status(ep_id, 'watched', litem))
        menu.addAction("Mark In Progress").triggered.connect(
            lambda: self._set_ep_status(ep_id, 'in_progress', litem))
        menu.addAction("Clear Status").triggered.connect(
            lambda: self._set_ep_status(ep_id, None, litem))
        menu.exec(self._ep_list.mapToGlobal(pos))

    def _set_ep_status(self, ep_id: str, status, litem):
        db.set_watch_status(ep_id, 'series_ep', status)
        ep       = litem.data(Qt.ItemDataRole.UserRole)
        ep_num   = ep.get('episode_num', '?')
        ep_title = ep.get('title', f"Episode {ep_num}")
        prefix   = "✓  " if status == 'watched' else ("…  " if status == 'in_progress' else "    ")
        label    = f"{prefix}{ep_num:>3}.  {ep_title}" if isinstance(ep_num, int) else f"{prefix}{ep_title}"
        litem.setText(label)
        litem.setData(Qt.ItemDataRole.UserRole + 1, status)

    # ── Favorites ─────────────────────────────────────────────────────────────

    def _toggle_fav(self, item: dict):
        sid = str(item.get('series_id', ''))
        if db.is_favorite(sid, 'series'):
            db.remove_favorite(sid, 'series')
        else:
            db.add_favorite(sid, 'series', item.get('name', ''), item.get('cover', ''))
        self._update_fav_btn(sid)

    def _update_fav_btn(self, sid: str):
        if db.is_favorite(sid, 'series'):
            self._d_fav_btn.setText("★  Remove Favorite")
            self._d_fav_btn.setProperty('favorited', 'true')
        else:
            self._d_fav_btn.setText("☆  Favorite")
            self._d_fav_btn.setProperty('favorited', 'false')
        self._d_fav_btn.style().unpolish(self._d_fav_btn)
        self._d_fav_btn.style().polish(self._d_fav_btn)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def open_detail(self, item: dict):
        """Navigate directly to the detail page for a given series dict (called from Favorites)."""
        self._show_detail(item)

    def _show_loading(self, show):
        self._loading.setVisible(show)
        if show:
            self._loading.resize(self.size())
            self._loading.raise_()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._loading.resize(self.size())
