from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QApplication,
    QListWidget, QListWidgetItem, QLineEdit, QMenu, QPushButton,
    QFrame, QComboBox, QCompleter,
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal

from ui.workers import ApiWorker, PosterPrefetcher
from ui.widgets import ChannelListView, LoadingLabel, SearchField
from ui.anim import LiveDotPulse
import core.database as db
import core.player as player
import api.m3u as m3u


class LiveTvWidget(QWidget):
    status_message = pyqtSignal(str)

    def __init__(self, api, parent=None):
        super().__init__(parent)
        self.api = api
        self._all_channels: list = []
        self._active_cat: str | None = None
        self._syncing = False

        self._build_ui()
        if self.api is not None:
            self._load_from_db()

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

        # ── Channel list panel (left) ─────────────────────────────────────────
        left = QFrame()
        left.setObjectName("SidebarPanel")
        left.setFixedWidth(320)
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 0, 0)
        ll.setSpacing(0)

        # Search + Sync header
        top = QWidget()
        top.setObjectName("PageHeader")
        top.setFixedHeight(52)
        tl = QHBoxLayout(top)
        tl.setContentsMargins(12, 8, 12, 8)
        tl.setSpacing(8)

        self._search = SearchField("Search channels…")
        self._search.textChanged.connect(self._filter)
        tl.addWidget(self._search, stretch=1)

        ll.addWidget(top)

        # Category dropdown
        cat_wrap = QWidget()
        cat_wrap.setObjectName("PageHeader")
        cwl = QHBoxLayout(cat_wrap)
        cwl.setContentsMargins(12, 6, 12, 6)
        cwl.setSpacing(0)
        self._cat_combo = QComboBox()
        self._cat_combo.setMinimumHeight(38)
        self._cat_combo.setMaxVisibleItems(20)
        self._cat_combo.setEditable(True)
        self._cat_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self._cat_combo.lineEdit().setPlaceholderText("Search categories…")
        self._cat_combo.completer().setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self._cat_combo.completer().setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self._cat_combo.completer().setFilterMode(Qt.MatchFlag.MatchContains)
        self._cat_combo.setStyleSheet(
            "QComboBox { background:#18181d; border:1px solid #232329; border-radius:8px;"
            " padding:4px 28px 4px 12px; color:#f1efe9; font-size:13px; }"
            "QComboBox:hover { border-color:#2e2e36; }"
            "QComboBox:focus { border-color:#ffb547; }"
            "QComboBox QLineEdit { background:transparent; border:none; color:#f1efe9; padding:0; }"
            "QComboBox::drop-down { subcontrol-origin:padding; subcontrol-position:center right;"
            " width:24px; border:none; }"
            "QComboBox::down-arrow {"
            " image:none;"
            " width:0; height:0;"
            " border-left:5px solid transparent;"
            " border-right:5px solid transparent;"
            " border-top:6px solid #ffb547;"
            " margin-right:8px; }"
            "QComboBox QAbstractItemView { min-height: 480px; }"
        )
        self._cat_combo.currentIndexChanged.connect(self._on_cat_changed)
        cwl.addWidget(self._cat_combo)
        self._all_cats: list = []
        ll.addWidget(cat_wrap)

        self._count_lbl = QLabel("")
        self._count_lbl.setObjectName("MutedSmall")
        self._count_lbl.setFixedHeight(28)
        self._count_lbl.setContentsMargins(14, 0, 14, 0)
        ll.addWidget(self._count_lbl)

        self._ch_list = ChannelListView()
        self._ch_list.setObjectName("ChannelList")
        self._ch_list.play_requested.connect(self._play)
        self._ch_list.itemClicked.connect(self._on_ch_click)
        self._ch_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._ch_list.customContextMenuRequested.connect(self._context_menu)
        ll.addWidget(self._ch_list, stretch=1)
        root.addWidget(left)

        # ── Right panel: player + EPG ─────────────────────────────────────────
        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(0)

        # Player placeholder
        player_frame = QFrame()
        player_frame.setObjectName("PlayerHero")
        player_frame.setMinimumHeight(300)
        pfl = QVBoxLayout(player_frame)
        pfl.setContentsMargins(0, 0, 0, 0)
        pfl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._player_info = QLabel("Select a channel to watch")
        self._player_info.setObjectName("PlayerInfo")
        self._player_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pfl.addWidget(self._player_info)
        rl.addWidget(player_frame, stretch=1)

        # EPG bar
        epg = QFrame()
        epg.setObjectName("EpgStrip")
        epg.setFixedHeight(60)
        el = QHBoxLayout(epg)
        el.setContentsMargins(20, 0, 20, 0)
        el.setSpacing(16)

        # Live dot with pulse
        self._live_dot = QLabel("● LIVE")
        self._live_dot.setObjectName("LivePill")
        self._live_dot.hide()
        self._live_pulse = LiveDotPulse(self._live_dot)
        el.addWidget(self._live_dot)

        now_col = QVBoxLayout()
        now_col.setSpacing(2)
        now_lbl = QLabel("NOW")
        now_lbl.setObjectName("EpgHint")
        self._epg_now = QLabel("Select a channel")
        self._epg_now.setObjectName("EpgNow")
        now_col.addWidget(now_lbl)
        now_col.addWidget(self._epg_now)
        el.addLayout(now_col, stretch=1)

        sep = QFrame()
        sep.setObjectName("VDiv")
        sep.setFrameShape(QFrame.Shape.VLine)
        el.addWidget(sep)

        next_col = QVBoxLayout()
        next_col.setSpacing(2)
        next_lbl = QLabel("NEXT")
        next_lbl.setObjectName("EpgHint")
        self._epg_next = QLabel("")
        self._epg_next.setObjectName("EpgNext")
        next_col.addWidget(next_lbl)
        next_col.addWidget(self._epg_next)
        el.addLayout(next_col, stretch=1)

        rl.addWidget(epg)
        root.addWidget(right, stretch=1)

        self._loading = LoadingLabel(self)

    # ── Load from DB ──────────────────────────────────────────────────────────

    def _load_from_db(self):
        w = ApiWorker(db.get_live_categories_cached)
        w.result.connect(self._on_categories_loaded)
        w.start()
        self._w_cats = w

    def _on_categories_loaded(self, cats):
        if cats:
            self._populate_categories(cats)
        else:
            self._count_lbl.setText("No data — tap ↻ to sync")
            self.status_message.emit("No live TV data. Click Sync.")

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
        cw = ApiWorker(db.get_live_categories_cached)
        cw.result.connect(self._populate_categories)
        cw.start()
        self._w_cats_post_sync = cw
        self._load_channels_from_db(self._active_cat)
        n = stats.get('live', 0)
        added = stats.get('live_added', 0)
        removed = stats.get('live_removed', 0)
        self.status_message.emit(
            f"Synced {n} channels — {added} new, {removed} removed — caching logos…"
        )
        self._start_prefetch(stats.get('live_icons', []))

    def _on_sync_error(self, msg):
        self._syncing = False
        self.status_message.emit(f"Sync error: {msg}")

    def reload_after_sync(self):
        if not self.api:
            return
        self._load_from_db()

    def _start_prefetch(self, urls):
        self._prefetcher = PosterPrefetcher(urls, parent=self)
        self._prefetcher.progress.connect(
            lambda d, t: self.status_message.emit(f"Caching logos: {d}/{t}…")
        )
        self._prefetcher.finished.connect(lambda: self.status_message.emit("Logos cached."))
        self._prefetcher.start()

    # ── Categories ────────────────────────────────────────────────────────────

    def _populate_categories(self, cats):
        self._all_cats = cats
        self._cat_combo.blockSignals(True)
        self._cat_combo.clear()
        self._cat_combo.addItem("All categories", None)
        for cat in cats:
            self._cat_combo.addItem(cat.get('category_name', ''), cat.get('category_id'))
        self._cat_combo.blockSignals(False)
        saved = db.get_setting('last_cat_live', '')
        target = 0
        if saved:
            for i in range(self._cat_combo.count()):
                if str(self._cat_combo.itemData(i) or '') == saved:
                    target = i
                    break
        self._cat_combo.setCurrentIndex(target)
        self._select_cat(self._cat_combo.itemData(target))

    def _on_cat_changed(self, idx):
        cat_id = self._cat_combo.itemData(idx)
        db.set_setting('last_cat_live', str(cat_id) if cat_id else '')
        self._select_cat(cat_id)

    def _select_cat(self, cat_id):
        self._active_cat = cat_id
        self._load_channels_from_db(cat_id)

    # ── Channels ──────────────────────────────────────────────────────────────

    def _load_channels_from_db(self, category_id):
        self._count_lbl.setText("Loading…")
        w = ApiWorker(db.list_live_streams, category_id)
        w.result.connect(self._on_channels_loaded)
        w.error.connect(lambda e: self.status_message.emit(f"DB error: {e}"))
        w.start()
        self._w_load = w

    def _on_channels_loaded(self, channels):
        self._all_channels = channels
        q = self._search.text().strip().lower()
        display = [c for c in channels if q in c.get('name', '').lower()] if q else channels
        self._ch_list.load(display)
        self._count_lbl.setText(f"{len(channels):,} channels")
        self.status_message.emit(f"{len(channels)} channels")

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
            self._on_search_result(self._all_channels)
            return
        w = ApiWorker(db.search_live_streams_lite, q)
        w.result.connect(self._on_search_result)
        w.start()
        self._w_search = w

    def _on_search_result(self, rows):
        self._ch_list.load(rows)
        self._count_lbl.setText(f"{len(rows):,} channels")

    # ── Playback ──────────────────────────────────────────────────────────────

    def _play(self, ch: dict):
        if not self.api:
            return
        sid  = str(ch.get('stream_id', ''))
        ext  = ch.get('container_extension') or (db.get_live_stream_data(sid) or {}).get('container_extension', 'ts')
        url  = self.api.live_url(sid, ext)
        name = ch.get('name', '')
        try:
            player.play(url, name)
            db.add_history(sid, 'live', name, ch.get('stream_icon', ''))
            self._epg_now.setText(name)
            self._live_dot.show()
            self._live_pulse.start()
            if hasattr(self, '_player_info'):
                self._player_info.setText(f"Playing: {name}")
            self.status_message.emit(f"Playing: {name}")
        except FileNotFoundError as e:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "mpv not found", str(e))

    def _on_ch_click(self, list_item):
        ch = list_item.data(Qt.ItemDataRole.UserRole)
        if not ch or not self.api:
            return
        self._epg_now.setText(ch.get('name', ''))
        self._epg_next.setText("")
        sid = str(ch.get('stream_id', ''))
        w = ApiWorker(self.api.get_short_epg, sid, 2)
        w.result.connect(lambda data, c=ch: self._on_epg(data, c))
        w.error.connect(lambda _: None)
        w.start()
        self._epg_worker = w

    def _on_epg(self, data, ch):
        import base64
        listings = data.get('epg_listings', [])
        def decode(s):
            try: return base64.b64decode(s).decode('utf-8')
            except: return s
        self._epg_now.setText(decode(listings[0].get('title','')) if listings else ch.get('name',''))
        self._epg_next.setText(decode(listings[1].get('title','')) if len(listings) > 1 else '')

    # ── Context menu ──────────────────────────────────────────────────────────

    def _context_menu(self, pos):
        item = self._ch_list.itemAt(pos)
        if not item:
            return
        ch = item.data(Qt.ItemDataRole.UserRole)
        menu = QMenu(self)
        menu.addAction("▶  Play").triggered.connect(lambda: self._play(ch))
        menu.addAction("📋  Copy URL").triggered.connect(lambda: self._copy_url(ch))
        menu.addSeparator()
        sid = str(ch.get('stream_id',''))
        lbl = "♥  Remove Favorite" if db.is_favorite(sid,'live') else "♡  Add to Favorites"
        menu.addAction(lbl).triggered.connect(lambda: self._toggle_fav(ch))
        menu.exec(self._ch_list.mapToGlobal(pos))

    def _copy_url(self, ch: dict):
        if not self.api:
            return
        sid = str(ch.get('stream_id', ''))
        ext = ch.get('container_extension') or (db.get_live_stream_data(sid) or {}).get('container_extension', 'ts')
        url = self.api.live_url(sid, ext)
        QApplication.clipboard().setText(f"'{url}'")
        self.status_message.emit(f"Copied URL for {ch.get('name', '')}")

    def _toggle_fav(self, ch):
        sid = str(ch.get('stream_id',''))
        if db.is_favorite(sid,'live'):
            db.remove_favorite(sid,'live')
        else:
            db.add_favorite(sid,'live',ch.get('name',''),ch.get('stream_icon',''))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, '_loading'):
            self._loading.resize(self.size())
