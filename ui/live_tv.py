from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QListWidget, QListWidgetItem, QLineEdit, QMenu, QPushButton,
)
from PyQt6.QtCore import Qt, pyqtSignal

from ui.workers import ApiWorker, PosterPrefetcher
from ui.widgets import ChannelListView, LoadingLabel
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
        self._load_from_db()

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

        # Right panel
        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(0)

        # Top bar
        top = QWidget()
        top.setFixedHeight(48)
        top.setStyleSheet("background:#111;border-bottom:1px solid #222;")
        tl = QHBoxLayout(top)
        tl.setContentsMargins(12, 8, 12, 8)
        self._search = QLineEdit()
        self._search.setPlaceholderText("🔍  Search channels…")
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

        # Channel list (fast delegate-based)
        self._ch_list = ChannelListView()
        self._ch_list.play_requested.connect(self._play)
        self._ch_list.itemClicked.connect(self._on_ch_click)
        self._ch_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._ch_list.customContextMenuRequested.connect(self._context_menu)
        rl.addWidget(self._ch_list)

        # EPG bar
        epg = QWidget()
        epg.setFixedHeight(44)
        epg.setStyleSheet("background:#111;border-top:1px solid #222;")
        el = QHBoxLayout(epg)
        el.setContentsMargins(12, 4, 12, 4)
        self._epg_now  = QLabel("Select a channel")
        self._epg_now.setObjectName("EpgCurrent")
        self._epg_next = QLabel("")
        self._epg_next.setObjectName("EpgNext")
        el.addWidget(QLabel("NOW:"))
        el.addWidget(self._epg_now, stretch=1)
        el.addWidget(QLabel("NEXT:"))
        el.addWidget(self._epg_next, stretch=1)
        rl.addWidget(epg)

        root.addWidget(right, stretch=1)
        self._loading = LoadingLabel(self)

    # ── Load from DB ──────────────────────────────────────────────────────────

    def _load_from_db(self):
        cats = db.get_live_categories_cached()
        if cats:
            self._populate_categories(cats)
        else:
            self._count_lbl.setText("No data — click Sync")
            self.status_message.emit("No live TV data. Click 🔄 Sync.")

    # ── Sync ─────────────────────────────────────────────────────────────────

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
        self._populate_categories(db.get_live_categories_cached())
        self._load_channels_from_db(self._active_cat)
        n = stats.get('live', 0)
        self.status_message.emit(f"Synced {n} channels — caching logos…")
        self._start_prefetch(stats.get('live_icons', []))

    def _on_sync_error(self, msg):
        self._syncing = False
        self._sync_btn.setText("🔄  Sync")
        self._sync_btn.setEnabled(True)
        self.status_message.emit(f"Sync error: {msg}")

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
        self._render_categories(cats)

    def _render_categories(self, cats):
        current = self._cat_list.currentRow()
        self._cat_list.blockSignals(True)
        self._cat_list.clear()
        all_item = QListWidgetItem("All Channels")
        all_item.setData(Qt.ItemDataRole.UserRole, None)
        self._cat_list.addItem(all_item)
        for cat in cats:
            item = QListWidgetItem(cat.get('category_name', ''))
            item.setData(Qt.ItemDataRole.UserRole, cat.get('category_id'))
            self._cat_list.addItem(item)
        self._cat_list.blockSignals(False)
        self._cat_list.setCurrentRow(max(current, 0))
        if current < 0:
            self._on_cat_changed(0)

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
            self._active_cat = item.data(Qt.ItemDataRole.UserRole)
            self._load_channels_from_db(self._active_cat)

    # ── Channels ──────────────────────────────────────────────────────────────

    def _load_channels_from_db(self, category_id):
        self._all_channels = db.get_live_streams_cached(category_id)
        q = self._search.text().strip().lower()
        channels = [c for c in self._all_channels if q in c.get('name','').lower()] if q else self._all_channels
        self._ch_list.load(channels)
        self._count_lbl.setText(f"{len(self._all_channels)} channels")
        self.status_message.emit(f"{len(self._all_channels)} channels")

    def _filter(self, text):
        q = text.strip()
        if q:
            filtered = db.search_live_streams(q)
        else:
            filtered = self._all_channels
        self._ch_list.load(filtered)
        self._count_lbl.setText(f"{len(filtered)} channels")

    # ── Playback ──────────────────────────────────────────────────────────────

    def _play(self, ch: dict):
        sid  = str(ch.get('stream_id', ''))
        url  = self.api.live_url(sid, ch.get('container_extension', 'ts'))
        name = ch.get('name', '')
        try:
            player.play(url, name)
            db.add_history(sid, 'live', name, ch.get('stream_icon', ''))
            self.status_message.emit(f"Playing: {name}")
        except FileNotFoundError as e:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "mpv not found", str(e))

    def _on_ch_click(self, list_item):
        ch = list_item.data(Qt.ItemDataRole.UserRole)
        if not ch:
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
        sid = str(ch.get('stream_id',''))
        lbl = "★  Remove Favorite" if db.is_favorite(sid,'live') else "☆  Add to Favorites"
        menu.addAction(lbl).triggered.connect(lambda: self._toggle_fav(ch))
        menu.exec(self._ch_list.mapToGlobal(pos))

    def _toggle_fav(self, ch):
        sid = str(ch.get('stream_id',''))
        if db.is_favorite(sid,'live'):
            db.remove_favorite(sid,'live')
        else:
            db.add_favorite(sid,'live',ch.get('name',''),ch.get('stream_icon',''))

    # ── Helpers ───────────────────────────────────────────────────────────────

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._loading.resize(self.size())
