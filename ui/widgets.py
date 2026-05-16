import os
from PyQt6.QtWidgets import (
    QListWidget, QListView, QStyledItemDelegate,
    QLabel, QLineEdit, QSizePolicy, QApplication, QStyle,
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QRect, QTimer
from PyQt6.QtGui import (
    QPixmap, QPixmapCache, QIcon, QColor, QPainter, QFont, QPen, QFontMetrics,
    QImage, QAction,
)
from ui.workers import ImageWorker, cached_path, is_cached, _cache_key


# ── Glyph icons (built once per char+color+size) ──────────────────────────────
_GLYPH_CACHE: dict = {}

def _glyph_icon(ch: str, color: str = "#6b6960", size: int = 18) -> QIcon:
    key = (ch, color, size)
    cached = _GLYPH_CACHE.get(key)
    if cached is not None:
        return cached
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
    p.setPen(QColor(color))
    f = QFont()
    f.setPointSize(max(int(size * 0.62), 10))
    f.setWeight(QFont.Weight.Bold)
    p.setFont(f)
    p.drawText(pix.rect(), Qt.AlignmentFlag.AlignCenter, ch)
    p.end()
    icon = QIcon(pix)
    _GLYPH_CACHE[key] = icon
    return icon


class SearchField(QLineEdit):
    """Pill-shaped search input with leading magnifier and built-in clear button."""

    def __init__(self, placeholder: str = "Search…", parent=None):
        super().__init__(parent)
        self.setObjectName("Search")
        self.setPlaceholderText(placeholder)
        self.setClearButtonEnabled(True)
        self.setMinimumHeight(38)
        self._search_action = QAction(_glyph_icon("⌕", "#a8a59c", 18), "", self)
        self.addAction(self._search_action, QLineEdit.ActionPosition.LeadingPosition)

# ── Sizes ─────────────────────────────────────────────────────────────────────
CARD_W, CARD_H   = 150, 225   # poster dimensions
CARD_ITEM_H      = CARD_H + 40  # poster + title row
CH_ITEM_H        = 32           # channel row height
LOGO_SIZE        = 24


# ── Shared placeholder icons (created once, reused) ───────────────────────────
_PLACEHOLDER_CACHE: dict = {}
_MONOGRAM_CACHE: dict = {}
_MONOGRAM_ICON_CACHE: dict = {}


def _monogram_icon(letter: str, w: int, h: int) -> QIcon:
    """QIcon variant of monogram pixmap; cached per letter+size to avoid
    rebuilding 30k+ QIcon wrappers on main thread during list reloads."""
    key = (letter, w, h)
    cached = _MONOGRAM_ICON_CACHE.get(key)
    if cached is not None:
        return cached
    icon = QIcon(_monogram_pixmap(letter, w, h))
    _MONOGRAM_ICON_CACHE[key] = icon
    return icon

_GRAD_PALETTES = [
    ("#4d3520", "#1f140a"),   # amber
    ("#4d2a1f", "#1f0e0a"),   # burnt orange
    ("#4d2a2a", "#1f0e0e"),   # red
    ("#2e4d2a", "#101e0e"),   # green
    ("#2a4d4a", "#0e1e1c"),   # teal
    ("#1f3a4d", "#0e1d28"),   # blue
    ("#3a3a44", "#16161b"),   # slate
    ("#4d402a", "#1f1a0d"),   # mustard
]


def _palette_for(letter: str) -> tuple:
    idx = (ord(letter.upper()) - ord('A')) % len(_GRAD_PALETTES) if letter else 0
    return _GRAD_PALETTES[idx]


def _monogram_pixmap(letter: str, w: int, h: int) -> QPixmap:
    key = (letter, w, h)
    cached = _MONOGRAM_CACHE.get(key)
    if cached is not None:
        return cached
    from PyQt6.QtGui import QLinearGradient
    pix = QPixmap(w, h)
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    c1, c2 = _palette_for(letter)
    grad = QLinearGradient(0, 0, w, h)
    grad.setColorAt(0.0, QColor(c1))
    grad.setColorAt(1.0, QColor(c2))
    p.setBrush(grad)
    p.setPen(Qt.PenStyle.NoPen)
    p.drawRoundedRect(0, 0, w, h, 6, 6)
    if letter:
        p.setPen(QColor(255, 255, 255, 38))
        f = QFont(); f.setPointSize(max(int(h * 0.32), 16)); f.setWeight(QFont.Weight.Bold)
        p.setFont(f)
        p.drawText(pix.rect(), Qt.AlignmentFlag.AlignCenter, letter.upper())
    p.end()
    _MONOGRAM_CACHE[key] = pix
    return pix


def _placeholder_icon(w: int, h: int, text: str = "") -> QIcon:
    """Neutral placeholder for un-titled cells (still cached)."""
    key = (w, h, text)
    if key not in _PLACEHOLDER_CACHE:
        pix = _monogram_pixmap(text[:1] if text else '', w, h)
        _PLACEHOLDER_CACHE[key] = QIcon(pix)
    return _PLACEHOLDER_CACHE[key]


def _placeholder(w: int, h: int, text: str = "") -> QPixmap:
    """Return a plain QPixmap placeholder (used in detail panels)."""
    return _monogram_pixmap(text[:1] if text else '', w, h)


# ── Media item delegate (poster grid) ────────────────────────────────────────

class MediaDelegate(QStyledItemDelegate):
    def paint(self, painter: QPainter, option, index):
        painter.save()
        r = option.rect.adjusted(4, 4, -4, -4)

        # Card background
        hover    = bool(option.state & QStyle.StateFlag.State_MouseOver)
        selected = bool(option.state & QStyle.StateFlag.State_Selected)
        bg = QColor("#1e1a10") if selected else (QColor("#18181d") if hover else QColor("#121216"))
        painter.fillRect(r, bg)

        # Poster image
        icon = index.data(Qt.ItemDataRole.DecorationRole)
        if icon and not icon.isNull():
            poster_rect = QRect(r.left(), r.top(), r.width(), CARD_H)
            pix = icon.pixmap(r.width(), CARD_H)
            x = poster_rect.left() + (poster_rect.width() - pix.width()) // 2
            painter.drawPixmap(x, poster_rect.top(), pix)

        # Title strip
        title_rect = QRect(r.left(), r.top() + CARD_H, r.width(), r.height() - CARD_H)
        painter.fillRect(title_rect, QColor("#0b0b0d"))

        title = index.data(Qt.ItemDataRole.DisplayRole) or ""
        painter.setPen(QColor("#f1efe9"))
        f = QFont(); f.setPointSize(9)
        painter.setFont(f)
        elided = QFontMetrics(f).elidedText(title, Qt.TextElideMode.ElideRight, title_rect.width() - 8)
        painter.drawText(title_rect.adjusted(4, 2, -4, -2),
                         Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft, elided)

        # Rating
        rating = index.data(Qt.ItemDataRole.UserRole + 1)
        if rating:
            painter.setPen(QColor("#ffb547"))
            fr = QFont(); fr.setPointSize(8)
            painter.setFont(fr)
            painter.drawText(title_rect.adjusted(4, 20, -4, -2),
                             Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft,
                             f"★ {rating}")

        # Watch status badge (top-right corner of poster)
        status = index.data(Qt.ItemDataRole.UserRole + 2)
        if status:
            bsz = 18
            bx = r.right() - bsz - 5
            by = r.top() + 5
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            if status == 'watched':
                painter.setBrush(QColor("#22c55e"))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawEllipse(bx, by, bsz, bsz)
                painter.setPen(QPen(QColor("#ffffff"), 2))
                painter.drawLine(bx + 4, by + 9, bx + 7, by + 13)
                painter.drawLine(bx + 7, by + 13, bx + 14, by + 5)
            elif status == 'in_progress':
                painter.setBrush(QColor("#ffb547"))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawEllipse(bx, by, bsz, bsz)
                painter.setPen(QPen(QColor("#1a1004"), 2))
                painter.drawLine(bx + 9, by + 4, bx + 9, by + 9)
                painter.drawLine(bx + 9, by + 11, bx + 9, by + 14)

        # Hover / selected border
        if selected:
            painter.setPen(QPen(QColor("#ffb547"), 2))
            painter.drawRoundedRect(r.adjusted(1, 1, -1, -1), 6, 6)
        elif hover:
            painter.setPen(QPen(QColor("#2e2e36"), 1))
            painter.drawRoundedRect(r.adjusted(0, 0, -1, -1), 6, 6)

        painter.restore()

    def sizeHint(self, option, index):
        return QSize(CARD_W + 8, CARD_ITEM_H)


# ── Media list view (replaces MediaGrid) ─────────────────────────────────────

class MediaListView(QListWidget):
    card_clicked = pyqtSignal(dict)
    card_play    = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setViewMode(QListView.ViewMode.IconMode)
        self.setResizeMode(QListView.ResizeMode.Adjust)
        self.setMovement(QListView.Movement.Static)
        self.setUniformItemSizes(True)
        self.setIconSize(QSize(CARD_W, CARD_H))
        self.setSpacing(6)
        self.setItemDelegate(MediaDelegate(self))
        self.setStyleSheet("QListWidget { background:#121216; border:none; outline:none; }"
                           "QListWidget::item { border:none; }")
        self.itemClicked.connect(
            lambda it: self.card_clicked.emit(it.data(Qt.ItemDataRole.UserRole))
        )
        self.itemDoubleClicked.connect(
            lambda it: self.card_play.emit(it.data(Qt.ItemDataRole.UserRole))
        )
        self._loaded: set = set()   # indices whose images are loading/loaded
        self._workers: dict = {}    # index -> worker ref

        self._scroll_timer = QTimer(self)
        self._scroll_timer.setSingleShot(True)
        self._scroll_timer.setInterval(80)
        self._scroll_timer.timeout.connect(self._load_visible)

    # ── public ───────────────────────────────────────────────────────────────

    def refresh_poster(self, item_id: str, url: str):
        """Reload the icon for the item whose series_id/stream_id matches item_id."""
        if not url or not url.startswith('http'):
            return
        for i in range(self.count()):
            it = self.item(i)
            data = it.data(Qt.ItemDataRole.UserRole)
            sid = str(data.get('series_id') or data.get('stream_id') or '')
            if sid == str(item_id):
                w = ImageWorker(url, tag=i, size=(CARD_W, CARD_H))
                w.ready.connect(self._on_image)
                w.start()
                self._workers[i] = w
                break

    def load(self, items: list):
        self.clear()
        self._loaded.clear()
        self._workers.clear()

        for item_data in items:
            it = self._make_item(item_data)
            self.addItem(it)

        # Layout visible items first, then lazy-load their images
        QTimer.singleShot(20, self._load_visible)

    def _make_item(self, data: dict, _ph=None) -> "QListWidgetItem":
        from PyQt6.QtWidgets import QListWidgetItem
        it = QListWidgetItem()
        it.setData(Qt.ItemDataRole.UserRole, data)
        it.setData(Qt.ItemDataRole.UserRole + 1,
                   str(data.get('rating') or data.get('rating_5based') or ''))
        it.setData(Qt.ItemDataRole.UserRole + 2, data.get('_watch_status'))
        name = data.get('name', '')
        it.setText(name)
        it.setSizeHint(QSize(CARD_W + 8, CARD_ITEM_H))
        it.setIcon(_monogram_icon(name[:1] if name else '', CARD_W, CARD_H))
        return it

    # ── lazy image loading ────────────────────────────────────────────────────

    def scrollContentsBy(self, dx, dy):
        super().scrollContentsBy(dx, dy)
        self._scroll_timer.start()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._scroll_timer.start()

    def _load_visible(self):
        vp = self.viewport().rect()
        for i in range(self.count()):
            if i in self._loaded:
                continue
            it = self.item(i)
            if vp.intersects(self.visualItemRect(it)):
                self._load_item_image(i, it)

    def _load_item_image(self, idx: int, it):
        self._loaded.add(idx)
        data = it.data(Qt.ItemDataRole.UserRole)
        url  = data.get('stream_icon') or data.get('cover') or ''
        if not url or not url.startswith('http'):
            return
        # In-memory cache hit → no disk I/O, no scale, no decode
        key = _cache_key(url, (CARD_W, CARD_H))
        cached = QPixmapCache.find(key)
        if cached is not None:
            it.setIcon(QIcon(cached))
            return
        # Always go through worker — disk read + scale happens off UI thread
        w = ImageWorker(url, tag=idx, size=(CARD_W, CARD_H))
        w.ready.connect(self._on_image)
        w.start()
        self._workers[idx] = w

    def _on_image(self, pix: QPixmap, idx):
        it = self.item(idx)
        if it and not pix.isNull():
            data = it.data(Qt.ItemDataRole.UserRole)
            url = data.get('stream_icon') or data.get('cover') or ''
            if url:
                QPixmapCache.insert(_cache_key(url, (CARD_W, CARD_H)), pix)
            it.setIcon(QIcon(pix))
        self._workers.pop(idx, None)


# ── Channel delegate ──────────────────────────────────────────────────────────

class ChannelDelegate(QStyledItemDelegate):
    def paint(self, painter: QPainter, option, index):
        painter.save()
        r = option.rect

        selected = bool(option.state & QStyle.StateFlag.State_Selected)
        hover    = bool(option.state & QStyle.StateFlag.State_MouseOver)
        bg = QColor("#1a1a10") if selected else (QColor("#18181d") if hover else QColor("#121216"))
        painter.fillRect(r, bg)

        # Selected: amber left border stripe
        if selected:
            painter.fillRect(QRect(r.left(), r.top(), 2, r.height()), QColor("#ffb547"))

        # Separator
        painter.setPen(QColor("#1a1a1f"))
        painter.drawLine(r.bottomLeft(), r.bottomRight())

        # Logo
        icon = index.data(Qt.ItemDataRole.DecorationRole)
        lx = r.left() + (8 if selected else 6)
        ly = r.top() + (r.height() - LOGO_SIZE) // 2
        if icon and not icon.isNull():
            painter.drawPixmap(lx, ly, icon.pixmap(LOGO_SIZE, LOGO_SIZE))
        else:
            painter.fillRect(QRect(lx, ly, LOGO_SIZE, LOGO_SIZE), QColor("#232329"))

        tx = lx + LOGO_SIZE + 8

        # Channel name (single line, vertically centered)
        name = index.data(Qt.ItemDataRole.DisplayRole) or ""
        epg  = index.data(Qt.ItemDataRole.UserRole + 1) or ""
        num  = str(index.data(Qt.ItemDataRole.UserRole + 2) or "")

        fn = QFont(); fn.setPointSize(10)
        painter.setFont(fn)
        fm = QFontMetrics(fn)

        right_margin = 36 if num else 4
        avail_w = r.width() - tx - right_margin - 4

        if epg:
            # name + dim EPG inline: "Channel Name  ·  Now Playing"
            epg_short = QFontMetrics(fn).elidedText(epg, Qt.TextElideMode.ElideRight, avail_w // 2)
            full = name + "  ·  " + epg_short
            elided = fm.elidedText(full, Qt.TextElideMode.ElideRight, avail_w)
            painter.setPen(QColor("#ffb547") if selected else QColor("#f1efe9"))
            painter.drawText(QRect(tx, r.top(), avail_w, r.height()),
                             Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, elided)
        else:
            elided = fm.elidedText(name, Qt.TextElideMode.ElideRight, avail_w)
            painter.setPen(QColor("#ffb547") if selected else QColor("#f1efe9"))
            painter.drawText(QRect(tx, r.top(), avail_w, r.height()),
                             Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, elided)

        # Channel number (right)
        if num:
            fn2 = QFont(); fn2.setPointSize(9)
            painter.setFont(fn2)
            painter.setPen(QColor("#6b6960"))
            painter.drawText(QRect(r.right() - 36, r.top(), 32, r.height()),
                             Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, num)

        painter.restore()

    def sizeHint(self, option, index):
        return QSize(0, CH_ITEM_H)


# ── Channel list view (replaces scroll area + ChannelRow widgets) ─────────────

class ChannelListView(QListWidget):
    play_requested = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setItemDelegate(ChannelDelegate(self))
        self.setUniformItemSizes(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.itemDoubleClicked.connect(
            lambda it: self.play_requested.emit(it.data(Qt.ItemDataRole.UserRole))
        )
        self._loaded: set = set()
        self._workers: dict = {}

        self._scroll_timer = QTimer(self)
        self._scroll_timer.setSingleShot(True)
        self._scroll_timer.setInterval(60)
        self._scroll_timer.timeout.connect(self._load_visible)

    def load(self, channels: list):
        self.clear()
        self._loaded.clear()
        self._workers.clear()

        for ch in channels:
            it = self._make_item(ch)
            self.addItem(it)

        QTimer.singleShot(20, self._load_visible)

    def _make_item(self, ch: dict, _ph=None):
        from PyQt6.QtWidgets import QListWidgetItem
        it = QListWidgetItem()
        it.setData(Qt.ItemDataRole.UserRole,     ch)
        it.setData(Qt.ItemDataRole.UserRole + 1, "")       # EPG (filled later)
        it.setData(Qt.ItemDataRole.UserRole + 2, ch.get('num', ''))
        name = ch.get('name', '')
        it.setText(name)
        it.setSizeHint(QSize(0, CH_ITEM_H))
        it.setIcon(_monogram_icon(name[:1] if name else '', LOGO_SIZE, LOGO_SIZE))
        return it

    def set_epg(self, stream_id: str, text: str):
        """Update EPG text for a channel by stream_id."""
        for i in range(self.count()):
            it = self.item(i)
            ch = it.data(Qt.ItemDataRole.UserRole)
            if str(ch.get('stream_id', '')) == stream_id:
                it.setData(Qt.ItemDataRole.UserRole + 1, text)
                self.update(self.indexFromItem(it))
                break

    # ── lazy logo loading ─────────────────────────────────────────────────────

    def scrollContentsBy(self, dx, dy):
        super().scrollContentsBy(dx, dy)
        self._scroll_timer.start()

    def _load_visible(self):
        vp = self.viewport().rect()
        for i in range(self.count()):
            if i in self._loaded:
                continue
            it = self.item(i)
            if vp.intersects(self.visualItemRect(it)):
                self._load_logo(i, it)

    def _load_logo(self, idx: int, it):
        self._loaded.add(idx)
        ch  = it.data(Qt.ItemDataRole.UserRole)
        url = ch.get('stream_icon', '')
        if not url or not url.startswith('http'):
            return
        key = _cache_key(url, (LOGO_SIZE, LOGO_SIZE))
        cached = QPixmapCache.find(key)
        if cached is not None:
            it.setIcon(QIcon(cached))
            return
        w = ImageWorker(url, tag=idx, size=(LOGO_SIZE, LOGO_SIZE))
        w.ready.connect(self._on_logo)
        w.start()
        self._workers[idx] = w

    def _on_logo(self, pix: QPixmap, idx):
        it = self.item(idx)
        if it and not pix.isNull():
            ch = it.data(Qt.ItemDataRole.UserRole)
            url = ch.get('stream_icon', '')
            if url:
                QPixmapCache.insert(_cache_key(url, (LOGO_SIZE, LOGO_SIZE)), pix)
            it.setIcon(QIcon(pix))
        self._workers.pop(idx, None)


# ── Loading label ─────────────────────────────────────────────────────────────

class LoadingLabel(QLabel):
    def __init__(self, parent=None):
        super().__init__("Loading…", parent)
        self.setObjectName("LoadingOverlay")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.hide()
