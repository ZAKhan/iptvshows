import os
from PyQt6.QtWidgets import (
    QListWidget, QListView, QStyledItemDelegate,
    QLabel, QSizePolicy, QApplication, QStyle,
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QRect, QTimer
from PyQt6.QtGui import (
    QPixmap, QIcon, QColor, QPainter, QFont, QPen, QFontMetrics,
)
from ui.workers import ImageWorker, cached_path, is_cached

# ── Sizes ─────────────────────────────────────────────────────────────────────
CARD_W, CARD_H   = 150, 225   # poster dimensions
CARD_ITEM_H      = CARD_H + 40  # poster + title row
CH_ITEM_H        = 32           # channel row height
LOGO_SIZE        = 24


# ── Shared placeholder icons (created once, reused) ───────────────────────────
_PLACEHOLDER_CACHE: dict = {}

def _placeholder_icon(w: int, h: int, text: str = "") -> QIcon:
    key = (w, h, text)
    if key not in _PLACEHOLDER_CACHE:
        pix = QPixmap(w, h)
        pix.fill(QColor("#12121e"))
        if text:
            p = QPainter(pix)
            p.setPen(QColor("#2a2a40"))
            f = QFont(); f.setPointSize(18)
            p.setFont(f)
            p.drawText(pix.rect(), Qt.AlignmentFlag.AlignCenter, text)
            p.end()
        _PLACEHOLDER_CACHE[key] = QIcon(pix)
    return _PLACEHOLDER_CACHE[key]

def _placeholder(w: int, h: int, text: str = "") -> QPixmap:
    """Return a plain QPixmap placeholder (used in detail panels)."""
    pix = QPixmap(w, h)
    pix.fill(QColor("#12121e"))
    if text:
        p = QPainter(pix)
        p.setPen(QColor("#2a2a40"))
        f = QFont(); f.setPointSize(18)
        p.setFont(f)
        p.drawText(pix.rect(), Qt.AlignmentFlag.AlignCenter, text)
        p.end()
    return pix


# ── Media item delegate (poster grid) ────────────────────────────────────────

class MediaDelegate(QStyledItemDelegate):
    def paint(self, painter: QPainter, option, index):
        painter.save()
        r = option.rect.adjusted(4, 4, -4, -4)

        # Card background
        hover    = bool(option.state & QStyle.StateFlag.State_MouseOver)
        selected = bool(option.state & QStyle.StateFlag.State_Selected)
        bg = QColor("#1e1a40") if selected else (QColor("#18182a") if hover else QColor("#12121e"))
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
        painter.fillRect(title_rect, QColor("#0e0e1a"))

        title = index.data(Qt.ItemDataRole.DisplayRole) or ""
        painter.setPen(QColor("#ddddf0"))
        f = QFont(); f.setPointSize(9)
        painter.setFont(f)
        elided = QFontMetrics(f).elidedText(title, Qt.TextElideMode.ElideRight, title_rect.width() - 8)
        painter.drawText(title_rect.adjusted(4, 2, -4, -2),
                         Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft, elided)

        # Rating
        rating = index.data(Qt.ItemDataRole.UserRole + 1)
        if rating:
            painter.setPen(QColor("#fb923c"))
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
                painter.setBrush(QColor("#f97316"))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawEllipse(bx, by, bsz, bsz)
                painter.setPen(QPen(QColor("#ffffff"), 2))
                painter.drawLine(bx + 9, by + 4, bx + 9, by + 9)
                painter.drawLine(bx + 9, by + 11, bx + 9, by + 14)

        # Hover / selected border
        if selected:
            painter.setPen(QPen(QColor("#7c6af5"), 2))
            painter.drawRoundedRect(r.adjusted(1, 1, -1, -1), 6, 6)
        elif hover:
            painter.setPen(QPen(QColor("#4a4a6a"), 1))
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
        self.setStyleSheet("QListWidget { background:#0d0d14; border:none; outline:none; }"
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

    def load(self, items: list):
        self.clear()
        self._loaded.clear()
        self._workers.clear()

        ph = _placeholder_icon(CARD_W, CARD_H, "🎬")
        for item_data in items:
            it = self._make_item(item_data, ph)
            self.addItem(it)

        # Layout visible items first, then lazy-load their images
        QTimer.singleShot(20, self._load_visible)

    def _make_item(self, data: dict, ph: QIcon) -> "QListWidgetItem":
        from PyQt6.QtWidgets import QListWidgetItem
        it = QListWidgetItem()
        it.setData(Qt.ItemDataRole.UserRole, data)
        it.setData(Qt.ItemDataRole.UserRole + 1,
                   str(data.get('rating') or data.get('rating_5based') or ''))
        it.setData(Qt.ItemDataRole.UserRole + 2, data.get('_watch_status'))
        it.setText(data.get('name', ''))
        it.setSizeHint(QSize(CARD_W + 8, CARD_ITEM_H))
        it.setIcon(ph)
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
        if not url:
            return
        if is_cached(url):
            pix = QPixmap(cached_path(url))
            if not pix.isNull():
                it.setIcon(QIcon(pix.scaled(CARD_W, CARD_H,
                                            Qt.AspectRatioMode.KeepAspectRatio,
                                            Qt.TransformationMode.SmoothTransformation)))
        else:
            w = ImageWorker(url, tag=idx, size=(CARD_W, CARD_H))
            w.ready.connect(self._on_image)
            w.start()
            self._workers[idx] = w

    def _on_image(self, pix: QPixmap, idx):
        it = self.item(idx)
        if it and not pix.isNull():
            it.setIcon(QIcon(pix))
        self._workers.pop(idx, None)   # fix 5: release worker ref


# ── Channel delegate ──────────────────────────────────────────────────────────

class ChannelDelegate(QStyledItemDelegate):
    def paint(self, painter: QPainter, option, index):
        painter.save()
        r = option.rect

        selected = bool(option.state & QStyle.StateFlag.State_Selected)
        hover    = bool(option.state & QStyle.StateFlag.State_MouseOver)
        bg = QColor("#1a1830") if selected else (QColor("#14141f") if hover else QColor("#0d0d14"))
        painter.fillRect(r, bg)

        # Separator
        painter.setPen(QColor("#1a1a28"))
        painter.drawLine(r.bottomLeft(), r.bottomRight())

        # Logo
        icon = index.data(Qt.ItemDataRole.DecorationRole)
        lx = r.left() + 6
        ly = r.top() + (r.height() - LOGO_SIZE) // 2
        if icon and not icon.isNull():
            painter.drawPixmap(lx, ly, icon.pixmap(LOGO_SIZE, LOGO_SIZE))
        else:
            painter.fillRect(QRect(lx, ly, LOGO_SIZE, LOGO_SIZE), QColor("#1e1e30"))

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
            painter.setPen(QColor("#c4bbfc") if selected else QColor("#ddddf0"))
            painter.drawText(QRect(tx, r.top(), avail_w, r.height()),
                             Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, elided)
        else:
            elided = fm.elidedText(name, Qt.TextElideMode.ElideRight, avail_w)
            painter.setPen(QColor("#c4bbfc") if selected else QColor("#ddddf0"))
            painter.drawText(QRect(tx, r.top(), avail_w, r.height()),
                             Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, elided)

        # Channel number (right)
        if num:
            fn2 = QFont(); fn2.setPointSize(9)
            painter.setFont(fn2)
            painter.setPen(QColor("#2e2e48"))
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
        self.setStyleSheet("QListWidget { background:#0d0d14; border:none; outline:none; }"
                           "QListWidget::item { border:none; }")
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

        ph = _placeholder_icon(LOGO_SIZE, LOGO_SIZE, "📺")
        for ch in channels:
            it = self._make_item(ch, ph)
            self.addItem(it)

        QTimer.singleShot(20, self._load_visible)

    def _make_item(self, ch: dict, ph: QIcon):
        from PyQt6.QtWidgets import QListWidgetItem
        it = QListWidgetItem()
        it.setData(Qt.ItemDataRole.UserRole,     ch)
        it.setData(Qt.ItemDataRole.UserRole + 1, "")       # EPG (filled later)
        it.setData(Qt.ItemDataRole.UserRole + 2, ch.get('num', ''))
        it.setText(ch.get('name', ''))
        it.setSizeHint(QSize(0, CH_ITEM_H))
        it.setIcon(ph)
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
        if not url:
            return
        if is_cached(url):
            pix = QPixmap(cached_path(url))
            if not pix.isNull():
                it.setIcon(QIcon(pix.scaled(LOGO_SIZE, LOGO_SIZE,
                                            Qt.AspectRatioMode.KeepAspectRatio,
                                            Qt.TransformationMode.SmoothTransformation)))
        else:
            w = ImageWorker(url, tag=idx, size=(LOGO_SIZE, LOGO_SIZE))
            w.ready.connect(self._on_logo)
            w.start()
            self._workers[idx] = w

    def _on_logo(self, pix: QPixmap, idx):
        it = self.item(idx)
        if it and not pix.isNull():
            it.setIcon(QIcon(pix))
        self._workers.pop(idx, None)   # fix 5: release worker ref


# ── Loading label ─────────────────────────────────────────────────────────────

class LoadingLabel(QLabel):
    def __init__(self, parent=None):
        super().__init__("Loading…", parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("color:#3a3a58; font-size:15px; background:#0d0d14;")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.hide()
