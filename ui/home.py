from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QSizePolicy, QGridLayout,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

import core.database as db
from ui.anim import apply_card_shadow, LiveDotPulse


class SectionHeader(QWidget):
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        lbl = QLabel(title)
        lbl.setStyleSheet(
            'font-family: "Instrument Serif", Georgia, serif; font-size: 26px; color: #f1efe9;'
        )
        layout.addWidget(lbl)
        layout.addStretch()


class ContinueCard(QFrame):
    clicked = pyqtSignal(dict)

    def __init__(self, item: dict, parent=None):
        super().__init__(parent)
        self._item = item
        self.setObjectName("Card")
        self.setFixedHeight(180)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        apply_card_shadow(self)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 10)
        layout.setSpacing(6)

        thumb = QFrame()
        thumb.setStyleSheet(
            "background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #3a2a18,stop:1 #1a1004);"
            "border-radius: 8px;"
        )
        thumb.setMinimumHeight(100)
        layout.addWidget(thumb, stretch=1)

        # Progress bar (3px)
        prog_bg = QFrame()
        prog_bg.setFixedHeight(3)
        prog_bg.setStyleSheet("background: #232329; border-radius: 2px;")
        prog_inner = QFrame(prog_bg)
        pct = item.get('pct', 0)
        prog_inner.setFixedHeight(3)
        prog_inner.setStyleSheet(
            "background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #ffb547,stop:1 #ff7a1a);"
            "border-radius: 2px;"
        )
        layout.addWidget(prog_bg)

        title = QLabel(item.get('name', ''))
        title.setStyleSheet("color: #f1efe9; font-size: 13px; font-weight: 600;")
        title.setWordWrap(True)
        layout.addWidget(title)

        sub = QLabel(item.get('sub', ''))
        sub.setStyleSheet("color: #6b6960; font-size: 11px;")
        layout.addWidget(sub)

        def _resize(event=None):
            w = prog_bg.width()
            prog_inner.setFixedWidth(max(6, int(w * pct / 100)))
        prog_bg.resizeEvent = lambda e: _resize()

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        self.clicked.emit(self._item)

    def showEvent(self, event):
        super().showEvent(event)
        # Make all child widgets transparent so the whole card surface is clickable.
        for child in self.findChildren(QWidget):
            child.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)


class LiveCard(QFrame):
    def __init__(self, item: dict, parent=None):
        super().__init__(parent)
        self.setObjectName("Card")
        self.setFixedHeight(100)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        apply_card_shadow(self)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(4)

        top = QHBoxLayout()
        top.setSpacing(8)

        logo = QLabel(item.get('abbr', '???'))
        logo.setFixedSize(40, 40)
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo.setStyleSheet(
            "background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #3d2e1a,stop:1 #1a1004);"
            "border-radius: 8px; color: #a8a59c; font-size: 11px; font-weight: 700;"
        )

        name_col = QVBoxLayout()
        name_col.setSpacing(2)
        name_lbl = QLabel(item.get('name', ''))
        name_lbl.setStyleSheet("color: #f1efe9; font-size: 13px; font-weight: 600;")

        live_lbl = QLabel("● LIVE")
        live_lbl.setStyleSheet(
            "color: #ff4d4d; font-size: 11px; font-weight: 700; letter-spacing: 0.08em;"
        )
        self._pulse = LiveDotPulse(live_lbl)
        self._pulse.start()

        name_col.addWidget(name_lbl)
        name_col.addWidget(live_lbl)
        top.addWidget(logo)
        top.addLayout(name_col, stretch=1)
        layout.addLayout(top)

        show_lbl = QLabel(item.get('show', ''))
        show_lbl.setStyleSheet("color: #6b6960; font-size: 11px;")
        layout.addWidget(show_lbl)

        prog_bg = QFrame()
        prog_bg.setFixedHeight(3)
        prog_bg.setStyleSheet("background: #232329; border-radius: 2px;")
        prog_inner = QFrame(prog_bg)
        prog_inner.setFixedHeight(3)
        prog_inner.setStyleSheet(
            "background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #ffb547,stop:1 #ff7a1a);"
            "border-radius: 2px;"
        )
        layout.addWidget(prog_bg)

        def _resize(event=None):
            prog_inner.setFixedWidth(max(6, int(prog_bg.width() * 0.4)))
        prog_bg.resizeEvent = lambda e: _resize()


class HeroPanel(QFrame):
    play_clicked = pyqtSignal(dict)

    def __init__(self, item: dict, parent=None):
        super().__init__(parent)
        self.setObjectName("Hero")
        self.setMinimumHeight(340)
        self.setMaximumHeight(400)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(36, 36, 36, 36)
        layout.setSpacing(32)

        # Left info
        info = QVBoxLayout()
        info.setSpacing(12)
        info.setAlignment(Qt.AlignmentFlag.AlignBottom)

        badge = QLabel("● Featured tonight")
        badge.setObjectName("HeroBadge")
        badge.setFixedWidth(160)

        title = QLabel(item.get('name', 'Featured'))
        title.setObjectName("HeroTitle")
        title.setStyleSheet(
            'font-family: "Instrument Serif", Georgia, serif; font-size: 46px; '
            'color: #f1efe9; font-weight: 400;'
        )
        title.setWordWrap(True)

        meta = QLabel(
            f"{item.get('year','2024')}  ·  "
            f"{item.get('genre','Drama')}  ·  "
            f"★ {item.get('rating','8.2')}"
        )
        meta.setStyleSheet("color: #a8a59c; font-size: 13px;")

        desc = QLabel(item.get('plot', 'No description available.'))
        desc.setStyleSheet("color: #a8a59c; font-size: 13px; line-height: 1.5;")
        desc.setWordWrap(True)
        desc.setMaximumWidth(520)

        actions = QHBoxLayout()
        actions.setSpacing(10)
        play_btn = QPushButton("▶  Play now")
        play_btn.setObjectName("BtnPrimaryGlow")
        play_btn.setFixedHeight(44)
        play_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #ffb547,stop:1 #ff7a1a);
                color: #1a1004; border: none; border-radius: 10px;
                font-size: 14px; font-weight: 600; padding: 0 24px;
            }
            QPushButton:hover { background: #ffc060; }
        """)
        play_btn.clicked.connect(lambda: self.play_clicked.emit(item))

        wl_btn = QPushButton("+ Watchlist")
        wl_btn.setObjectName("BtnSecondary")
        wl_btn.setFixedHeight(44)

        actions.addWidget(play_btn)
        actions.addWidget(wl_btn)
        actions.addStretch()

        info.addStretch()
        info.addWidget(badge)
        info.addWidget(title)
        info.addWidget(meta)
        info.addWidget(desc)
        info.addLayout(actions)

        # Right poster placeholder
        poster = QFrame()
        poster.setFixedSize(180, 270)
        poster.setStyleSheet(
            "background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #3d2e1a,stop:1 #1a1004);"
            "border-radius: 12px; border: 1px solid #232329;"
        )
        apply_card_shadow(poster)

        layout.addLayout(info, stretch=1)
        layout.addWidget(poster, alignment=Qt.AlignmentFlag.AlignVCenter)


class HomeWidget(QWidget):
    status_message = pyqtSignal(str)
    navigate_to    = pyqtSignal(str, dict)   # ('vod' | 'series', data)

    def __init__(self, api, parent=None):
        super().__init__(parent)
        self.api = api
        self._build_ui()

    def _build_ui(self):
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

        content = QWidget()
        scroll.setWidget(content)
        v = QVBoxLayout(content)
        v.setContentsMargins(28, 28, 28, 28)
        v.setSpacing(32)

        if self.api is None:
            self._build_empty(v)
            return

        # Hero
        featured = self._get_featured()
        if featured:
            hero = HeroPanel(featured)
            v.addWidget(hero)

        # Continue Watching
        history = db.get_history(limit=4)
        if history:
            v.addWidget(SectionHeader("Continue Watching"))
            cw_grid = QHBoxLayout()
            cw_grid.setSpacing(14)
            for item in history[:4]:
                card_data = {
                    'name': item.get('name', ''),
                    'sub': item.get('stream_type', '').capitalize(),
                    'pct': 35,
                    'stream_id': item.get('stream_id', ''),
                    'stream_type': item.get('stream_type', ''),
                    'stream_icon': item.get('stream_icon', ''),
                }
                card = ContinueCard(card_data)
                card.clicked.connect(self._on_continue_click)
                cw_grid.addWidget(card)
            cw_grid.addStretch()
            v.addLayout(cw_grid)

        # Popular Movies
        movies = db.get_vod_streams_cached(limit=12)
        if movies:
            v.addWidget(SectionHeader("Popular Movies"))
            chips = QHBoxLayout()
            chips.setSpacing(8)
            for genre in ["All", "Action", "Drama", "Comedy", "Sci-Fi"]:
                chip = QPushButton(genre)
                chip.setObjectName("Chip")
                chip.setFixedHeight(34)
                chips.addWidget(chip)
            chips.addStretch()
            v.addLayout(chips)

            grid = QGridLayout()
            grid.setSpacing(14)
            cols = 6
            for i, m in enumerate(movies[:cols]):
                card = self._make_poster_card(m)
                grid.addWidget(card, 0, i)
            v.addLayout(grid)

        # Live right now
        live = db.get_live_streams_cached(limit=6)
        if live:
            v.addWidget(SectionHeader("Live Right Now"))
            live_grid = QGridLayout()
            live_grid.setSpacing(14)
            cols = 3
            for i, ch in enumerate(live[:cols * 2]):
                card = LiveCard({
                    'name': ch.get('name', ''),
                    'abbr': ch.get('name', '???')[:3].upper(),
                    'show': '',
                })
                live_grid.addWidget(card, i // cols, i % cols)
            v.addLayout(live_grid)

        v.addStretch()

    def _build_empty(self, layout: QVBoxLayout):
        empty = QWidget()
        ev = QVBoxLayout(empty)
        ev.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ev.setSpacing(16)

        title = QLabel("Welcome to Stream")
        title.setStyleSheet(
            'font-family: "Instrument Serif", Georgia, serif; '
            'font-size: 52px; color: #f1efe9; font-weight: 400;'
        )
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        sub = QLabel(
            "Connect an IPTV server to start streaming.\n"
            "You can add Xtream-compatible servers or local M3U playlists."
        )
        sub.setStyleSheet("color: #6b6960; font-size: 14px;")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub.setWordWrap(True)

        ev.addWidget(title)
        ev.addWidget(sub)
        layout.addStretch()
        layout.addWidget(empty)
        layout.addStretch()

    def _on_continue_click(self, item: dict):
        if not self.api:
            return
        t   = item.get('stream_type', '')
        sid = str(item.get('stream_id', ''))
        if t == 'live':
            data = db.get_live_stream_data(sid) or item
            url  = self.api.live_url(sid, data.get('container_extension', 'ts'))
            name = data.get('name', item.get('name', ''))
            try:
                import core.player as player
                player.play(url, name)
                db.add_history(sid, t, name, data.get('stream_icon', ''))
                self.status_message.emit(f"Playing: {name}")
            except FileNotFoundError as e:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.critical(self, "mpv not found", str(e))
            return
        if t == 'vod':
            data = db.get_vod_stream_data(sid)
            if data:
                self.navigate_to.emit('vod', data)
            else:
                self.status_message.emit("Movie not in library — re-sync.")
            return
        if t == 'series':
            data = db.get_series_data(sid)
            if data:
                self.navigate_to.emit('series', data)
            else:
                self.status_message.emit("Series not in library — re-sync.")
            return
        if t == 'series_ep':
            # Episode id — open parent series detail (best-effort).
            self.status_message.emit("Open series tab to resume episode.")

    def _get_featured(self) -> dict:
        movies = db.get_vod_streams_cached(limit=1)
        if movies:
            return movies[0]
        return {}

    def _make_poster_card(self, item: dict) -> QFrame:
        card = QFrame()
        card.setObjectName("PosterCard")
        card.setFixedSize(140, 210)
        card.setCursor(Qt.CursorShape.PointingHandCursor)
        apply_card_shadow(card)

        v = QVBoxLayout(card)
        v.setContentsMargins(0, 0, 0, 8)
        v.setSpacing(4)

        img = QFrame()
        img.setStyleSheet(
            "background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #3d2e1a,stop:1 #1a1004);"
            "border-radius: 8px 8px 0 0;"
        )
        img.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        v.addWidget(img, stretch=1)

        name = QLabel(item.get('name', ''))
        name.setStyleSheet(
            "color: #f1efe9; font-size: 12px; font-weight: 600; padding: 0 8px;"
        )
        name.setWordWrap(True)
        v.addWidget(name)

        rating = item.get('rating', '')
        if rating:
            r_lbl = QLabel(f"★ {rating}")
            r_lbl.setStyleSheet("color: #ffb547; font-size: 11px; padding: 0 8px;")
            v.addWidget(r_lbl)

        return card
