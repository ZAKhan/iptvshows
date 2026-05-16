DARK_THEME = """
/* ── Global reset ───────────────────────────────────────────────────────────── */
QMainWindow, QDialog, QWidget {
    background-color: #0b0b0d;
    color: #f1efe9;
    font-family: "Inter Tight", "Inter", "SF Pro Display", "Segoe UI", system-ui, sans-serif;
    font-size: 13px;
}

/* ── Sidebar ────────────────────────────────────────────────────────────────── */
#Sidebar {
    background-color: #121216;
    border-right: 1px solid #232329;
    min-width: 180px;
    max-width: 180px;
}

/* ── Brand mark ─────────────────────────────────────────────────────────────── */
#BrandMark {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #ffb547, stop:1 #ff7a1a);
    border-radius: 8px;
    color: #1a1004;
    font-size: 14px;
    font-weight: 700;
    min-width: 30px;
    max-width: 30px;
    min-height: 30px;
    max-height: 30px;
    border: none;
}
#BrandName {
    color: #f1efe9;
    font-size: 15px;
    font-weight: 700;
    letter-spacing: -0.3px;
}

/* ── Nav groups / labels ────────────────────────────────────────────────────── */
#NavGroup {
    background: transparent;
}
#NavLabel {
    color: #6b6960;
    font-size: 11px;
    font-weight: 500;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    padding: 0 12px;
}

/* ── Nav items ──────────────────────────────────────────────────────────────── */
QPushButton#NavItem, QPushButton#NavBtn {
    background: transparent;
    border: none;
    color: #a8a59c;
    text-align: left;
    padding: 9px 12px;
    font-size: 13px;
    font-weight: 500;
    border-radius: 8px;
    margin: 1px 8px;
}
QPushButton#NavItem:hover, QPushButton#NavBtn:hover {
    background-color: #18181d;
    color: #f1efe9;
}
QPushButton#NavItem[active="true"], QPushButton#NavBtn[active="true"] {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 rgba(255,181,71,0.12), stop:1 transparent);
    color: #ffb547;
    border-left: 2px solid #ffb547;
    padding-left: 10px;
}

/* ── Top bar ────────────────────────────────────────────────────────────────── */
#TopBar {
    background-color: rgba(11, 11, 13, 0.95);
    border-bottom: 1px solid #232329;
    min-height: 56px;
    max-height: 64px;
}

/* ── Search field (pill) ────────────────────────────────────────────────────── */
QLineEdit#Search {
    background-color: #16161b;
    border: 1px solid #2a2a32;
    border-radius: 8px;
    padding: 0 14px 0 6px;
    color: #f1efe9;
    font-size: 13px;
    min-height: 38px;
    max-height: 38px;
    max-width: 520px;
    selection-background-color: rgba(255,181,71,0.3);
    selection-color: #1a1004;
}
QLineEdit#Search:hover {
    border-color: #3a3a44;
    background-color: #1a1a20;
}
QLineEdit#Search:focus {
    border: 1px solid #ffb547;
    background-color: #1a1a1f;
}
QLineEdit#Search[text=""] { color: #6b6960; }

/* ── Icon buttons ───────────────────────────────────────────────────────────── */
QPushButton#IconBtn, QPushButton#BtnIconOnly {
    background-color: rgba(255,255,255,0.05);
    border: 1px solid #232329;
    border-radius: 10px;
    color: #a8a59c;
    min-width: 38px;
    max-width: 38px;
    min-height: 38px;
    max-height: 38px;
    font-size: 16px;
}
QPushButton#IconBtn:hover, QPushButton#BtnIconOnly:hover {
    background-color: #18181d;
    border-color: #2e2e36;
    color: #f1efe9;
}

/* ── Primary button ─────────────────────────────────────────────────────────── */
QPushButton#BtnPrimary {
    background-color: #f1efe9;
    color: #0b0b0d;
    border: none;
    padding: 12px 24px;
    border-radius: 10px;
    font-size: 13px;
    font-weight: 600;
}
QPushButton#BtnPrimary:hover {
    background-color: #ffb547;
}
QPushButton#BtnPrimary:pressed {
    background-color: #e0a03a;
}

/* ── Primary glow button ────────────────────────────────────────────────────── */
QPushButton#BtnPrimaryGlow {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #ffb547, stop:1 #ff7a1a);
    color: #1a1004;
    border: none;
    padding: 12px 24px;
    border-radius: 10px;
    font-size: 13px;
    font-weight: 600;
}
QPushButton#BtnPrimaryGlow:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #ffc060, stop:1 #ff8f30);
}
QPushButton#BtnPrimaryGlow:pressed {
    background: #e09030;
}

/* ── Play button (legacy compat) ────────────────────────────────────────────── */
QPushButton#PlayBtn {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #ffb547, stop:1 #ff7a1a);
    color: #1a1004;
    border: none;
    padding: 8px 20px;
    border-radius: 10px;
    font-size: 13px;
    font-weight: 600;
}
QPushButton#PlayBtn:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #ffc060, stop:1 #ff8f30);
}
QPushButton#PlayBtn:pressed {
    background: #e09030;
}

/* ── Secondary button ───────────────────────────────────────────────────────── */
QPushButton#BtnSecondary {
    background-color: rgba(255,255,255,0.08);
    color: #f1efe9;
    border: 1px solid #2e2e36;
    padding: 12px 18px;
    border-radius: 10px;
    font-size: 13px;
    font-weight: 500;
}
QPushButton#BtnSecondary:hover {
    background-color: #1f1f25;
    border-color: #ffb547;
    color: #ffb547;
}

/* ── Fav button (legacy compat) ─────────────────────────────────────────────── */
QPushButton#FavBtn {
    background-color: rgba(255,255,255,0.08);
    border: 1px solid #2e2e36;
    color: #a8a59c;
    padding: 9px 18px;
    border-radius: 10px;
    font-size: 13px;
}
QPushButton#FavBtn:hover {
    border-color: #ff6b6b;
    color: #ff6b6b;
    background-color: rgba(255,107,107,0.08);
}
QPushButton#FavBtn[favorited="true"] {
    color: #ff6b6b;
    border-color: rgba(255,107,107,0.5);
    background-color: rgba(255,107,107,0.1);
}

/* ── Generic buttons ─────────────────────────────────────────────────────────── */
QPushButton {
    background-color: rgba(255,255,255,0.06);
    border: 1px solid #232329;
    border-radius: 8px;
    padding: 6px 14px;
    color: #a8a59c;
    font-size: 13px;
}
QPushButton:hover {
    background-color: #1f1f25;
    border-color: #2e2e36;
    color: #f1efe9;
}
QPushButton:pressed {
    background-color: #18181d;
}
QPushButton:disabled {
    color: #6b6960;
    border-color: #1a1a1f;
    background-color: transparent;
}

/* ── Filter chip ────────────────────────────────────────────────────────────── */
QPushButton#Chip {
    padding: 7px 14px;
    border-radius: 100px;
    background-color: #18181d;
    border: 1px solid #232329;
    font-size: 13px;
    color: #a8a59c;
    font-weight: 400;
}
QPushButton#Chip:hover {
    border-color: #2e2e36;
    color: #f1efe9;
}
QPushButton#ChipActive, QPushButton#Chip[active="true"] {
    background-color: #f1efe9;
    color: #0b0b0d;
    border: 1px solid #f1efe9;
    font-weight: 500;
}

/* ── Active filter pill ─────────────────────────────────────────────────────── */
QFrame#ActiveFilter {
    background-color: #18181d;
    border: 1px solid #2e2e36;
    border-radius: 100px;
}
QLabel#ActiveFilterText {
    color: #a8a59c;
    font-size: 12px;
}

/* ── Status dot ─────────────────────────────────────────────────────────────── */
QLabel#StatusDot {
    color: #6cd97e;
    font-size: 10px;
}

/* ── LIVE pill ──────────────────────────────────────────────────────────────── */
QLabel#LivePill {
    background-color: #ff4d4d;
    color: #ffffff;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.08em;
    padding: 4px 10px;
    border-radius: 6px;
}

/* ── Quality badge ──────────────────────────────────────────────────────────── */
QLabel#QualityBadge {
    background-color: rgba(255,255,255,0.95);
    color: #000000;
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 0.04em;
    padding: 2px 5px;
    border-radius: 3px;
}
QLabel#QualityBadge4K {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #ffb547, stop:1 #ff7a1a);
    color: #1a1004;
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 0.04em;
    padding: 2px 5px;
    border-radius: 3px;
}

/* ── Rating badge ───────────────────────────────────────────────────────────── */
QLabel#RatingBadge, QLabel#RatingLabel, QLabel#TmdbScore {
    background-color: rgba(0,0,0,0.7);
    color: #ffb547;
    font-size: 11px;
    font-weight: 600;
    padding: 3px 7px;
    border-radius: 5px;
}

/* ── Page / section titles ──────────────────────────────────────────────────── */
QLabel#PageTitleSerif, QLabel#SectionTitleSerif {
    color: #f1efe9;
    font-family: "Instrument Serif", "Georgia", serif;
    font-weight: 400;
}
QLabel#PageTitleSerif {
    font-size: 44px;
    letter-spacing: -0.02em;
}
QLabel#SectionTitleSerif {
    font-size: 26px;
}
QLabel#SectionTitle {
    font-size: 20px;
    font-weight: 700;
    color: #f1efe9;
    letter-spacing: -0.3px;
}

/* ── Cards ───────────────────────────────────────────────────────────────────── */
QFrame#Card, QFrame#MediaCard {
    background-color: #18181d;
    border: 1px solid #232329;
    border-radius: 14px;
}
QFrame#Card:hover, QFrame#MediaCard:hover {
    border-color: #2e2e36;
    background-color: #1f1f25;
}
QFrame#PosterCard {
    background-color: #18181d;
    border: 1px solid #232329;
    border-radius: 10px;
}
QFrame#PosterCard:hover {
    border-color: #2e2e36;
}

/* ── Episode rows ───────────────────────────────────────────────────────────── */
QFrame#EpisodeRow {
    background-color: #18181d;
    border: 1px solid #232329;
    border-radius: 10px;
}
QFrame#EpisodeRowWatched {
    background-color: #18181d;
    border: 1px solid #232329;
    border-radius: 10px;
    opacity: 0.6;
}
QFrame#EpisodeRowNext {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 rgba(255,181,71,0.06), stop:1 transparent);
    border: 1px solid #ffb547;
    border-radius: 10px;
}

/* ── Live channel items ─────────────────────────────────────────────────────── */
QFrame#ChannelItem {
    background-color: transparent;
    border: none;
    border-radius: 8px;
}
QFrame#ChannelItem:hover {
    background-color: #18181d;
}
QFrame#ChannelItemPlaying {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 rgba(255,181,71,0.12), stop:1 transparent);
    border-radius: 8px;
    border-left: 2px solid #ffb547;
}

/* ── EPG show blocks ────────────────────────────────────────────────────────── */
QFrame#EpgShow {
    background-color: #18181d;
    border: 1px solid #232329;
    border-radius: 6px;
}
QFrame#EpgShowNow {
    background-color: rgba(255,181,71,0.08);
    border: 1px solid transparent;
    border-left: 2px solid #ffb547;
    border-radius: 6px;
}
QLabel#EpgCurrent {
    color: #f1efe9;
    font-size: 12px;
    font-weight: 600;
}
QLabel#EpgNext {
    color: #6b6960;
    font-size: 11px;
}

/* ── Settings cards ─────────────────────────────────────────────────────────── */
QFrame#SettingCard, QFrame#Surface, QFrame#InsetPanel {
    background-color: #18181d;
    border: 1px solid #232329;
    border-radius: 14px;
}
QFrame#SettingRow {
    background: transparent;
    border-bottom: 1px solid #232329;
}

/* ── Danger zone ────────────────────────────────────────────────────────────── */
QFrame#DangerZone {
    background-color: rgba(255,107,107,0.04);
    border: 1px solid rgba(255,107,107,0.3);
    border-radius: 14px;
}
QPushButton#BtnDanger {
    background: transparent;
    border: 1px solid #ff6b6b;
    color: #ff6b6b;
    border-radius: 8px;
    padding: 7px 16px;
    font-size: 13px;
}
QPushButton#BtnDanger:hover {
    background-color: #ff6b6b;
    color: #ffffff;
}

/* ── Server cards ───────────────────────────────────────────────────────────── */
QFrame#ServerCard {
    background-color: #18181d;
    border: 1px solid #232329;
    border-radius: 12px;
}
QFrame#ServerCardActive {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 rgba(255,181,71,0.06), stop:1 transparent);
    border: 1px solid #ffb547;
    border-radius: 12px;
}

/* ── Nav tab (used for settings and series) ─────────────────────────────────── */
QPushButton#NavTab {
    background: transparent;
    border: none;
    border-bottom: 2px solid transparent;
    color: #a8a59c;
    padding: 10px 22px;
    font-size: 14px;
    font-weight: 500;
    border-radius: 0px;
    min-width: 110px;
    min-height: 40px;
}
QPushButton#NavTab:hover {
    color: #f1efe9;
    border-bottom: 2px solid #2e2e36;
}
QPushButton#NavTab[active="true"] {
    color: #ffb547;
    border-bottom: 2px solid #ffb547;
}

/* ── View toggle ────────────────────────────────────────────────────────────── */
QPushButton#ViewToggle {
    background: transparent;
    border: 1px solid #232329;
    border-radius: 8px;
    padding: 6px 10px;
    color: #6b6960;
    font-size: 14px;
}
QPushButton#ViewToggle[active="true"] {
    background-color: #18181d;
    color: #f1efe9;
    border-color: #2e2e36;
}

/* ── Hero panel ─────────────────────────────────────────────────────────────── */
QFrame#Hero, QFrame#HeroPanel {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #131320, stop:0.5 #0e0e1a, stop:1 #0b0b0d);
    border-radius: 20px;
    border: 1px solid #232329;
    min-height: 380px;
}

/* ── Labels / info ──────────────────────────────────────────────────────────── */
QLabel#InfoLabel, QLabel#NetworkLabel, QLabel#GenresLabel {
    color: #6b6960;
    font-size: 12px;
}
QLabel#HeroTitle {
    color: #f1efe9;
    font-family: "Instrument Serif", "Georgia", serif;
    font-size: 56px;
    font-weight: 400;
    letter-spacing: -0.02em;
}
QLabel#HeroBadge {
    background-color: rgba(255,181,71,0.15);
    color: #ffb547;
    font-size: 11px;
    font-weight: 600;
    padding: 4px 10px;
    border-radius: 6px;
    border: 1px solid rgba(255,181,71,0.3);
}
QLabel#HeroDesc {
    color: #a8a59c;
    font-size: 13px;
    line-height: 1.5;
}

/* ── Inputs ─────────────────────────────────────────────────────────────────── */
QLineEdit {
    background-color: #18181d;
    border: 1px solid #232329;
    border-radius: 10px;
    padding: 9px 14px;
    color: #f1efe9;
    font-size: 13px;
    selection-background-color: rgba(255,181,71,0.3);
}
QLineEdit:focus {
    border-color: #ffb547;
    background-color: #1a1a1f;
}
QLineEdit:hover:!focus {
    border-color: #2e2e36;
}
QLineEdit::placeholder {
    color: #6b6960;
}

/* ── Combo box ──────────────────────────────────────────────────────────────── */
QComboBox {
    background-color: #18181d;
    border: 1px solid #232329;
    border-radius: 10px;
    padding: 8px 14px;
    color: #f1efe9;
    font-size: 13px;
    min-height: 36px;
}
QComboBox:hover { border-color: #2e2e36; }
QComboBox:focus { border-color: #ffb547; }
QComboBox::drop-down {
    border: none;
    width: 28px;
    subcontrol-position: center right;
}
QComboBox QAbstractItemView {
    background-color: #18181d;
    border: 1px solid #2e2e36;
    border-radius: 10px;
    selection-background-color: rgba(255,181,71,0.15);
    selection-color: #ffb547;
    outline: none;
    padding: 4px;
    color: #f1efe9;
}

/* ── Check boxes ────────────────────────────────────────────────────────────── */
QCheckBox {
    color: #a8a59c;
    spacing: 8px;
    font-size: 13px;
}
QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border: 1.5px solid #2e2e36;
    border-radius: 4px;
    background: #18181d;
}
QCheckBox::indicator:checked {
    background-color: #ffb547;
    border-color: #ffb547;
    image: none;
}
QCheckBox::indicator:hover {
    border-color: #ffb547;
}

/* ── Progress bar ───────────────────────────────────────────────────────────── */
QProgressBar {
    background-color: #232329;
    border: none;
    border-radius: 3px;
    height: 3px;
    text-align: center;
    color: transparent;
    max-height: 3px;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #ffb547, stop:1 #ff7a1a);
    border-radius: 3px;
}

/* ── Scroll bars ────────────────────────────────────────────────────────────── */
QScrollBar:vertical {
    background: transparent;
    width: 4px;
    margin: 0;
}
QScrollBar::handle:vertical {
    background: #2e2e36;
    border-radius: 2px;
    min-height: 32px;
}
QScrollBar::handle:vertical:hover { background: #ffb547; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal {
    background: transparent;
    height: 4px;
}
QScrollBar::handle:horizontal {
    background: #2e2e36;
    border-radius: 2px;
    min-width: 32px;
}
QScrollBar::handle:horizontal:hover { background: #ffb547; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }

/* ── Lists / trees ──────────────────────────────────────────────────────────── */
QListWidget {
    background-color: #0b0b0d;
    border: none;
    outline: none;
    font-size: 13px;
}
QListWidget::item {
    padding: 4px 10px;
    border-radius: 6px;
    margin: 1px 4px;
    border: none;
    color: #a8a59c;
}
QListWidget::item:selected {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 rgba(255,181,71,0.12), stop:1 transparent);
    color: #ffb547;
    border-left: 2px solid #ffb547;
}
QListWidget::item:hover:!selected {
    background-color: #18181d;
    color: #f1efe9;
}

/* ── Category list ──────────────────────────────────────────────────────────── */
QListWidget#CategoryList {
    background-color: #121216;
    border-right: 1px solid #232329;
    min-width: 185px;
    max-width: 185px;
    font-size: 13px;
}
QListWidget#CategoryList::item {
    padding: 6px 12px;
    border-radius: 6px;
    margin: 1px 6px;
}
QListWidget#CategoryList::item:selected {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 rgba(255,181,71,0.12), stop:1 transparent);
    color: #ffb547;
    border-left: 2px solid #ffb547;
}

/* ── Splitter ───────────────────────────────────────────────────────────────── */
QSplitter::handle { background-color: #232329; }
QSplitter::handle:hover { background-color: #ffb547; }
QSplitter::handle:vertical { height: 1px; }
QSplitter::handle:horizontal { width: 1px; }

/* ── Status bar (legacy fallback) ───────────────────────────────────────────── */
QStatusBar {
    background-color: #0b0b0d;
    border-top: 1px solid #232329;
    color: #a8a59c;
    font-size: 12px;
    padding: 4px 12px;
}
QStatusBar QLabel { color: #a8a59c; font-size: 12px; }
QStatusBar::item { border: none; }

/* ── Custom bottom bar ──────────────────────────────────────────────────────── */
QFrame#BottomBar {
    background-color: #0b0b0d;
    border-top: 1px solid #232329;
}
QLabel#StatusMsg { color: #a8a59c; font-size: 12px; }
QLabel#ServerStatus { color: #6b6960; font-size: 12px; padding: 0; }
QProgressBar#BottomProgress {
    background-color: #232329;
    border: none;
    border-radius: 3px;
    max-height: 6px;
}
QProgressBar#BottomProgress::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #ffb547, stop:1 #ff7a1a);
    border-radius: 3px;
}

/* ── Tab widget (fallback) ──────────────────────────────────────────────────── */
QTabWidget::pane {
    border: none;
    background: #0b0b0d;
}
QTabBar::tab {
    background: transparent;
    color: #6b6960;
    padding: 9px 18px;
    border: none;
    border-bottom: 2px solid transparent;
    font-size: 13px;
    font-weight: 500;
    margin-right: 2px;
}
QTabBar::tab:selected {
    color: #ffb547;
    border-bottom: 2px solid #ffb547;
}
QTabBar::tab:hover:!selected {
    color: #a8a59c;
    background: rgba(255,255,255,0.03);
}

/* ── Table widget ───────────────────────────────────────────────────────────── */
QTableWidget {
    background-color: #0b0b0d;
    border: none;
    gridline-color: #232329;
    color: #f1efe9;
    font-size: 13px;
}
QTableWidget::item {
    padding: 7px 12px;
    border-radius: 4px;
    color: #f1efe9;
}
QTableWidget::item:selected {
    background-color: rgba(255,181,71,0.12);
    color: #ffb547;
}
QHeaderView::section {
    background-color: #0b0b0d;
    border: none;
    border-bottom: 1px solid #232329;
    padding: 9px 14px;
    color: #6b6960;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.1em;
}

/* ── Tooltip ────────────────────────────────────────────────────────────────── */
QToolTip {
    background-color: #1f1f25;
    color: #f1efe9;
    border: 1px solid #2e2e36;
    padding: 5px 10px;
    border-radius: 8px;
    font-size: 12px;
}

/* ── Dialog ─────────────────────────────────────────────────────────────────── */
QDialog {
    background-color: #121216;
    border: 1px solid #232329;
    border-radius: 14px;
}
QGroupBox {
    border: 1px solid #232329;
    border-radius: 10px;
    margin-top: 10px;
    padding-top: 12px;
    color: #6b6960;
    font-size: 11px;
    font-weight: 500;
    letter-spacing: 0.08em;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 14px;
    padding: 0 6px;
    background-color: #121216;
}

/* ── ScrollArea ─────────────────────────────────────────────────────────────── */
QScrollArea {
    background: transparent;
    border: none;
}
QScrollArea > QWidget > QWidget {
    background: transparent;
}

/* ── Tab header bar (top of Movies/Series/Live tabs) ────────────────────────── */
QWidget#TabHeader {
    background-color: #0b0b0d;
    border-bottom: 1px solid #232329;
}

/* ── Section dividers ───────────────────────────────────────────────────────── */
QFrame#HDiv { background-color: #232329; max-height: 1px; border: none; }
QFrame#VDiv { background-color: #232329; max-width: 1px;  border: none; }

/* ── Heading variants (Instrument Serif) ────────────────────────────────────── */
QLabel#TabHeading {
    font-family: "Instrument Serif", Georgia, serif;
    font-size: 24px;
    color: #f1efe9;
}
QLabel#DetailHeading {
    font-family: "Instrument Serif", Georgia, serif;
    font-size: 32px;
    color: #f1efe9;
}
QLabel#PanelHeading {
    font-family: "Instrument Serif", Georgia, serif;
    font-size: 22px;
    color: #f1efe9;
}
QLabel#FavHeading {
    font-family: "Instrument Serif", Georgia, serif;
    font-size: 22px;
    color: #f1efe9;
    font-weight: 400;
}

/* ── Small muted labels ─────────────────────────────────────────────────────── */
QLabel#CountLbl       { color: #6b6960; font-size: 12px; }
QLabel#MutedSmall     { color: #6b6960; font-size: 11px; }
QLabel#MutedMedium    { color: #a8a59c; font-size: 13px; }
QLabel#MutedDesc      { color: #a8a59c; font-size: 12px; }
QLabel#SectionLbl     { color: #6b6960; font-size: 10px; font-weight: 600; letter-spacing: 0.10em; }
QLabel#DetailBarTitle { color: #f1efe9; font-size: 14px; font-weight: 600; padding-left: 12px; }
QLabel#EpgHint        { color: #6b6960; font-size: 10px; font-weight: 600; letter-spacing: 0.08em; }
QLabel#EpgNow         { color: #f1efe9; font-size: 13px; font-weight: 600; }
QLabel#EpgNext        { color: #a8a59c; font-size: 13px; }
QLabel#EpStatus       { color: #6b6960; font-size: 11px; padding: 4px 16px;
                        background-color: #0b0b0d; border-top: 1px solid #232329; }
QLabel#NetworkLbl     { color: #6b6960; font-size: 11px; }
QLabel#RatingPill {
    background-color: rgba(0,0,0,0.5);
    color: #ffb547;
    font-size: 13px;
    font-weight: 600;
    padding: 4px 10px;
    border-radius: 6px;
}

/* ── Sync button (outline amber) ────────────────────────────────────────────── */
QPushButton#SyncBtn {
    background-color: rgba(255,181,71,0.12);
    border: 1px solid #ffb547;
    color: #ffb547;
    border-radius: 8px;
    padding: 0 6px;
    font-size: 12px;
    font-weight: 600;
}
QPushButton#SyncBtn:hover { background-color: #ffb547; color: #1a1004; }

/* ── Back / outline button ──────────────────────────────────────────────────── */
QPushButton#BackBtn {
    background-color: transparent;
    border: 1px solid #232329;
    color: #a8a59c;
    border-radius: 8px;
    padding: 6px 14px;
}
QPushButton#BackBtn:hover { border-color: #ffb547; color: #ffb547; }

/* ── Play / continue gradient button ────────────────────────────────────────── */
QPushButton#PrimaryGradBtn {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #ffb547, stop:1 #ff7a1a);
    color: #1a1004;
    border: none;
    border-radius: 10px;
    padding: 0 24px;
    font-weight: 600;
    font-size: 13px;
}
QPushButton#PrimaryGradBtn:hover { background: #ffc060; }

/* ── Mark-watched outline button ────────────────────────────────────────────── */
QPushButton#WatchedBtn {
    background-color: rgba(255,255,255,0.06);
    border: 1px solid #232329;
    color: #a8a59c;
    border-radius: 10px;
    padding: 0 18px;
    font-size: 13px;
}
QPushButton#WatchedBtn:hover { border-color: #2e2e36; color: #f1efe9; }

/* ── Detail description text edit ───────────────────────────────────────────── */
QTextEdit#DetailDesc {
    background-color: #18181d;
    border: 1px solid #232329;
    border-radius: 10px;
    color: #a8a59c;
    padding: 10px;
    font-size: 13px;
}

/* ── Sidebar frame variants ─────────────────────────────────────────────────── */
QFrame#SidebarPanel {
    background-color: #121216;
    border-right: 1px solid #232329;
    border-radius: 0;
}

/* ── Inline panels / strips ─────────────────────────────────────────────────── */
QFrame#DetailInfoStrip {
    background-color: #121216;
    border-bottom: 1px solid #232329;
    border-radius: 0;
}
QFrame#EpgStrip {
    background-color: #121216;
    border-top: 1px solid #232329;
    border-radius: 0;
}
QFrame#PlayerHero {
    background-color: #0a0a0d;
    border-bottom: 1px solid #232329;
    border-radius: 0;
}
QLabel#PlayerInfo { color: #6b6960; font-size: 16px; }

/* ── Inline category filter line edit ───────────────────────────────────────── */
QLineEdit#CatFilter {
    border: none;
    border-bottom: 1px solid #232329;
    border-radius: 0;
    background-color: #0b0b0d;
    padding: 0 14px;
    color: #f1efe9;
    font-size: 12px;
}

/* ── Channel list (left rail in Live TV) ────────────────────────────────────── */
QListWidget#ChannelList {
    border: none;
    background-color: #121216;
}
QListWidget#ChannelList::item {
    padding: 8px 12px;
    border-bottom: 1px solid #1a1a1f;
    border-radius: 0;
    margin: 0;
}
QListWidget#ChannelList::item:selected {
    background-color: rgba(255,181,71,0.1);
    border-left: 2px solid #ffb547;
}
QListWidget#ChannelList::item:hover:!selected { background-color: #18181d; }

/* ── Season / episode lists ─────────────────────────────────────────────────── */
QListWidget#SeasonList {
    border: none;
    border-right: 1px solid #232329;
    background-color: #121216;
}
QListWidget#SeasonList::item {
    padding: 8px 14px;
    border-radius: 0;
    margin: 0;
    color: #a8a59c;
}
QListWidget#SeasonList::item:selected {
    background-color: rgba(255,181,71,0.12);
    color: #ffb547;
    border-left: 2px solid #ffb547;
}
QListWidget#EpisodeList {
    border: none;
    background-color: #0b0b0d;
}
QListWidget#EpisodeList::item {
    padding: 10px 16px;
    border-bottom: 1px solid #232329;
    border-radius: 0;
    margin: 0;
    color: #a8a59c;
}
QListWidget#EpisodeList::item:selected {
    background-color: rgba(255,181,71,0.1);
    color: #ffb547;
}
QListWidget#EpisodeList::item:hover:!selected {
    background-color: #18181d;
    color: #f1efe9;
}

/* ── Favorites / search tabs ────────────────────────────────────────────────── */
QTabWidget#SubTabs::pane { border: none; background-color: #0b0b0d; }
QTabWidget#SubTabs QTabBar::tab {
    background: transparent;
    color: #6b6960;
    padding: 10px 20px;
    font-size: 13px;
    border: none;
    border-bottom: 2px solid transparent;
}
QTabWidget#SubTabs QTabBar::tab:selected {
    color: #ffb547;
    border-bottom: 2px solid #ffb547;
}
QTabWidget#SubTabs QTabBar::tab:hover:!selected { color: #f1efe9; }

/* ── Header strip used in favorites/search ──────────────────────────────────── */
QWidget#PageHeader {
    background-color: #121216;
    border-bottom: 1px solid #232329;
}

/* ── Generic plain list (favorites rows) ────────────────────────────────────── */
QListWidget#PlainList {
    background-color: #0b0b0d;
    border: none;
    outline: none;
    color: #f1efe9;
    font-size: 13px;
}
QListWidget#PlainList::item {
    padding: 10px 16px;
    border-bottom: 1px solid #1a1a1f;
}
QListWidget#PlainList::item:selected {
    background-color: rgba(255,181,71,0.1);
    border-left: 2px solid #ffb547;
    color: #ffb547;
}
QListWidget#PlainList::item:hover:!selected { background-color: #18181d; }

/* ── Loading overlay label ──────────────────────────────────────────────────── */
QLabel#LoadingOverlay {
    color: #6b6960;
    font-size: 15px;
    background-color: #0b0b0d;
}
"""
