DARK_THEME = """
/* ── Base ────────────────────────────────────────────────────────────────── */
QMainWindow, QDialog, QWidget {
    background-color: #0d0d14;
    color: #ddddf0;
    font-family: "Inter", "Noto Sans", "Segoe UI", sans-serif;
    font-size: 12px;
}

/* ── Sidebar ─────────────────────────────────────────────────────────────── */
#Sidebar {
    background-color: #0a0a12;
    border-right: 1px solid #1e1e2e;
    min-width: 56px;
    max-width: 56px;
}
#Sidebar[expanded="true"] {
    min-width: 210px;
    max-width: 210px;
}

QPushButton#NavBtn {
    background: transparent;
    border: none;
    color: #5c5c7a;
    text-align: left;
    padding: 7px 10px;
    font-size: 12px;
    border-radius: 8px;
    margin: 1px 6px;
}
QPushButton#NavBtn:hover {
    background-color: rgba(124, 106, 245, 0.1);
    color: #a89ef5;
}
QPushButton#NavBtn[active="true"] {
    background-color: rgba(124, 106, 245, 0.18);
    color: #c4bbfc;
    border-left: 3px solid #7c6af5;
}

/* ── Scroll bars ─────────────────────────────────────────────────────────── */
QScrollBar:vertical {
    background: transparent;
    width: 5px;
    margin: 0;
}
QScrollBar::handle:vertical {
    background: #2a2a40;
    border-radius: 3px;
    min-height: 32px;
}
QScrollBar::handle:vertical:hover { background: #4a4a6a; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal {
    background: transparent;
    height: 5px;
}
QScrollBar::handle:horizontal {
    background: #2a2a40;
    border-radius: 3px;
    min-width: 32px;
}
QScrollBar::handle:horizontal:hover { background: #4a4a6a; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }

/* ── Lists ───────────────────────────────────────────────────────────────── */
QListWidget {
    background-color: #0d0d14;
    border: none;
    outline: none;
}
QListWidget::item {
    padding: 3px 10px;
    border-radius: 4px;
    margin: 0px 3px;
    border: none;
}
QListWidget::item:selected {
    background-color: rgba(124, 106, 245, 0.22);
    color: #c4bbfc;
}
QListWidget::item:hover:!selected {
    background-color: rgba(255, 255, 255, 0.04);
}

/* ── Category list ───────────────────────────────────────────────────────── */
QListWidget#CategoryList {
    background-color: #0a0a12;
    border-right: 1px solid #1e1e2e;
    min-width: 185px;
    max-width: 185px;
    font-size: 12px;
}
QListWidget#CategoryList::item {
    padding: 3px 10px;
    border-radius: 4px;
    margin: 0px 4px;
}
QListWidget#CategoryList::item:selected {
    background-color: rgba(124, 106, 245, 0.22);
    color: #c4bbfc;
    border-left: 3px solid #7c6af5;
}

/* ── Search / Input ──────────────────────────────────────────────────────── */
QLineEdit {
    background-color: #16162a;
    border: 1px solid #2a2a40;
    border-radius: 6px;
    padding: 4px 10px;
    color: #ddddf0;
    font-size: 12px;
    selection-background-color: rgba(124, 106, 245, 0.4);
}
QLineEdit:focus {
    border-color: #7c6af5;
    background-color: #1a1a30;
}
QLineEdit:hover:!focus {
    border-color: #3a3a58;
}

/* ── Buttons ─────────────────────────────────────────────────────────────── */
QPushButton {
    background-color: #16162a;
    border: 1px solid #2a2a40;
    border-radius: 5px;
    padding: 3px 12px;
    color: #aaaacc;
}
QPushButton:hover {
    background-color: #1e1e38;
    border-color: #4a4a6a;
    color: #ddddf0;
}
QPushButton:pressed {
    background-color: #12122a;
}
QPushButton:disabled {
    color: #3a3a50;
    border-color: #1e1e2e;
    background-color: #0d0d14;
}

QPushButton#PlayBtn {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 #7c6af5, stop:1 #9d8cf8);
    border: none;
    color: #fff;
    font-weight: 600;
    padding: 3px 16px;
    border-radius: 5px;
    letter-spacing: 0.3px;
}
QPushButton#PlayBtn:hover {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 #9178f7, stop:1 #b09ffa);
}
QPushButton#PlayBtn:pressed {
    background: #6a58e0;
}

QPushButton#FavBtn {
    background-color: transparent;
    border: 1px solid #2a2a40;
    color: #5c5c7a;
    padding: 7px 16px;
    border-radius: 8px;
}
QPushButton#FavBtn:hover {
    border-color: #f87171;
    color: #f87171;
    background-color: rgba(248, 113, 113, 0.08);
}
QPushButton#FavBtn[favorited="true"] {
    color: #f87171;
    border-color: rgba(248, 113, 113, 0.5);
    background-color: rgba(248, 113, 113, 0.1);
}

/* ── Combo box ───────────────────────────────────────────────────────────── */
QComboBox {
    background-color: #16162a;
    border: 1px solid #2a2a40;
    border-radius: 8px;
    padding: 6px 12px;
    color: #ddddf0;
}
QComboBox:hover { border-color: #3a3a58; }
QComboBox:focus { border-color: #7c6af5; }
QComboBox::drop-down { border: none; width: 24px; }
QComboBox QAbstractItemView {
    background-color: #16162a;
    border: 1px solid #2a2a40;
    border-radius: 8px;
    selection-background-color: rgba(124, 106, 245, 0.22);
    outline: none;
    padding: 4px;
}

/* ── Labels ──────────────────────────────────────────────────────────────── */
QLabel#SectionTitle {
    font-size: 20px;
    font-weight: 700;
    color: #eeeef8;
    padding: 4px 0;
    letter-spacing: -0.3px;
}
QLabel#InfoLabel {
    color: #5c5c7a;
    font-size: 12px;
}
QLabel#EpgCurrent {
    color: #ddddf0;
    font-size: 12px;
    font-weight: 600;
}
QLabel#EpgNext {
    color: #5c5c7a;
    font-size: 11px;
}
QLabel#RatingLabel {
    color: #fb923c;
    font-size: 12px;
    font-weight: 600;
}

/* ── Splitter ────────────────────────────────────────────────────────────── */
QSplitter::handle {
    background-color: #1e1e2e;
}
QSplitter::handle:hover {
    background-color: #7c6af5;
}
QSplitter::handle:vertical { height: 1px; }
QSplitter::handle:horizontal { width: 1px; }

/* ── Tab widget ──────────────────────────────────────────────────────────── */
QTabWidget::pane {
    border: none;
    background: #0d0d14;
}
QTabBar::tab {
    background: transparent;
    color: #5c5c7a;
    padding: 7px 16px;
    border: none;
    border-bottom: 2px solid transparent;
    font-size: 12px;
    font-weight: 500;
    margin-right: 2px;
}
QTabBar::tab:selected {
    color: #c4bbfc;
    border-bottom: 2px solid #7c6af5;
}
QTabBar::tab:hover:!selected {
    color: #9999cc;
    background: rgba(124, 106, 245, 0.07);
    border-radius: 8px 8px 0 0;
}

/* ── Status bar ──────────────────────────────────────────────────────────── */
QStatusBar {
    background-color: #0a0a12;
    border-top: 1px solid #1e1e2e;
    color: #4a4a6a;
    font-size: 11px;
    padding: 0 8px;
}

/* ── Media card ──────────────────────────────────────────────────────────── */
QFrame#MediaCard {
    background-color: #12121e;
    border-radius: 12px;
    border: 1px solid #1e1e30;
}
QFrame#MediaCard:hover {
    border-color: rgba(124, 106, 245, 0.5);
    background-color: #16162a;
}

/* ── Dialogs ─────────────────────────────────────────────────────────────── */
QDialog {
    background-color: #0d0d14;
    border: 1px solid #1e1e2e;
    border-radius: 12px;
}
QGroupBox {
    border: 1px solid #1e1e2e;
    border-radius: 10px;
    margin-top: 10px;
    padding-top: 10px;
    color: #5c5c7a;
    font-size: 12px;
    font-weight: 500;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
    background-color: #0d0d14;
}

/* ── Progress bar ────────────────────────────────────────────────────────── */
QProgressBar {
    background-color: #1e1e2e;
    border: none;
    border-radius: 3px;
    height: 4px;
    text-align: center;
    color: transparent;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 #7c6af5, stop:1 #9d8cf8);
    border-radius: 3px;
}

/* ── Table widget ────────────────────────────────────────────────────────── */
QTableWidget {
    background-color: #0d0d14;
    border: none;
    gridline-color: #1e1e2e;
    color: #ddddf0;
}
QTableWidget::item {
    padding: 6px 10px;
    border-radius: 4px;
}
QTableWidget::item:selected {
    background-color: rgba(124, 106, 245, 0.22);
    color: #c4bbfc;
}
QHeaderView::section {
    background-color: #0a0a12;
    border: none;
    border-bottom: 1px solid #1e1e2e;
    padding: 8px 12px;
    color: #5c5c7a;
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

/* ── Tooltip ─────────────────────────────────────────────────────────────── */
QToolTip {
    background-color: #1e1e2e;
    color: #ddddf0;
    border: 1px solid #2a2a40;
    padding: 5px 10px;
    border-radius: 6px;
}

/* ── Check box ───────────────────────────────────────────────────────────── */
QCheckBox {
    color: #aaaacc;
    spacing: 8px;
}
QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border: 1px solid #2a2a40;
    border-radius: 4px;
    background: #16162a;
}
QCheckBox::indicator:checked {
    background-color: #7c6af5;
    border-color: #7c6af5;
}
QCheckBox::indicator:hover {
    border-color: #7c6af5;
}

/* ── Detail panel labels ─────────────────────────────────────────────────── */
QLabel#GenresLabel {
    color: #9d8cf8;
    font-size: 11px;
}
QLabel#NetworkLabel {
    color: #5c5c7a;
    font-size: 11px;
}
QLabel#TmdbScore {
    color: #fb923c;
    font-size: 12px;
    font-weight: 700;
}
"""
