"""
AdminLTE 2 theme ported to Qt stylesheets.
Colours/fonts mirror the original views (header.php, sidebar.php, links.php).
"""
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon, QFont, QPainter, QPixmap, QColor

# Segoe MDL2 Assets glyph codes (bundled with Windows 10/11) used for the
# FontAwesome icons of the original app.
ICONS = {
    "dashboard": "\uE80F",
    "accounts": "\uE8A5",
    "clients": "\uE716",
    "products": "\uE8FD",
    "suppliers": "\uE719",
    "cart": "\uE7BF",
    "list": "\uE8A9",
    "bolt": "\uE945",
    "file": "\uE8A1",
    "folder": "\uE8B7",
    "folderopen": "\uE8B5",
    "exchange": "\uE895",
    "cartplus": "\uE7C3",
    "userplus": "\uE8FA",
    "table": "\uE8EF",
    "thlist": "\uE8EA",
    "linechart": "\uE9D2",
    "barchart": "\uE9D9",
    "tree": "\uE8EC",
    "money": "\uE968",
    "whatsapp": "\uEB51",
    "plus": "\uE710",
    "chart": "\uE9D2",
    "settings": "\uE713",
    "power": "\uE7E8",
    "bell": "\uEA8F",
    "gear": "\uE713",
    "search": "\uE721",
    "add": "\uE710",
    "edit": "\uE70F",
    "delete": "\uE74D",
    "save": "\uE74E",
    "print": "\uE749",
    "download": "\uE896",
    "refresh": "\uE72C",
    "chevron": "\uE70D",
    "chevronright": "\uE76C",
    "calendar": "\uE787",
    "close": "\uE711",
    "info": "\uE946",
    "user": "\uE77B",
}

_icon_font = None


def _load_icon_font():
    global _icon_font
    if _icon_font is None:
        f = QFont("Segoe MDL2 Assets")
        f.setPixelSize(14)
        _icon_font = f
    return _icon_font


def icon(name: str, color: str = "#b8c7ce", size: int = 32) -> QIcon:
    """Render a Segoe MDL2 glyph into a QIcon (falls back to a dot)."""
    ch = ICONS.get(name, "\u25CF")
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    f = QFont(_load_icon_font())
    f.setPixelSize(int(size * 0.6))
    p.setFont(f)
    p.setPen(QColor(color))
    p.drawText(pm.rect(), Qt.AlignmentFlag.AlignCenter, ch)
    p.end()
    return QIcon(pm)


# ---------------------------------------------------------------------------
# Application stylesheet (AdminLTE 2)
# ---------------------------------------------------------------------------
QSS = """
* { font-family: 'Segoe UI', 'Source Sans Pro', Arial, sans-serif; font-size: 13px; }

QMainWindow, QDialog { background: #ecf0f5; }

#HeaderBar { background: #3c8dbc; border: none; }
#HeaderBar QLabel { color: #ffffff; }
#LogoLabel { font-size: 17px; font-weight: bold; color: #ffffff; }
QToolButton#HeaderButton { color: white; border: none; padding: 6px 12px; }
QToolButton#HeaderButton:hover { background: #367fa9; }

#Sidebar { background: #222d32; border: none; }
#Sidebar QLabel { color: #b8c7ce; }
#UserPanel { background: #1a2226; }
#UserPanel QLabel { color: #ffffff; }
#SidebarSearch { background: #36474e; color: #b8c7ce; border: none;
    padding: 6px 10px; margin: 12px; border-radius: 2px; }
#SidebarHeader { color: #4b646f !important; font-size: 11px; padding: 8px 14px 4px; }
QPushButton[sidebarItem="true"] {
    color: #b8c7ce; background: transparent; border: none;
    text-align: left; padding: 11px 14px; font-size: 13px;
}
QPushButton[sidebarItem="true"]:hover { background: #1e282c; color: #ffffff; }
QPushButton[sidebarItem="true"][active="true"] {
    background: #1e282c; color: #ffffff; border-left: 3px solid #3c8dbc;
}
QPushButton[sidebarSub="true"] {
    color: #8aa4af; background: transparent; border: none;
    text-align: left; padding: 8px 14px 8px 34px; font-size: 12.5px;
}
QPushButton[sidebarSub="true"]:hover { background: #1e282c; color: #ffffff; }
QPushButton[sidebarSub="true"][active="true"] {
    background: #1e282c; color: #ffffff; border-left: 3px solid #3c8dbc;
}
QToolButton#NavChevron { background: transparent; border: none; padding: 0; }
QToolButton#NavChevron:hover { background: #1e282c; }
#Sidebar QScrollArea { border: none; background: transparent; }

QFrame#Box { background: #ffffff; border-top: 3px solid #3c8dbc;
    border-radius: 3px; }
QFrame#BoxSuccess { border-top: 3px solid #00a65a; }
QFrame#BoxDanger { border-top: 3px solid #dd4b39; }
QFrame#BoxWarning { border-top: 3px solid #f39c12; }
QFrame#BoxInfo { border-top: 3px solid #00c0ef; }
#BoxTitle { color: #444; font-size: 15px; font-weight: 600; }
#PageTitle { color: #444; font-size: 21px; font-weight: 300; }
#PageSubtitle { color: #737373; font-size: 12.5px; }
#PageCrumb { color: #777777; font-size: 12px; background: transparent;
    padding: 0; }
QLabel#StatValue { font-size: 26px; font-weight: bold; color: #666; }
QLabel#StatText { color: #597596; font-size: 12.5px; }

QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QSpinBox, QDoubleSpinBox, QDateEdit {
    background: #ffffff; border: 1px solid #d2d6de; border-radius: 3px;
    padding: 5px 8px; color: #555; selection-background-color: #3c8dbc;
}
QLineEdit:focus, QTextEdit:focus, QComboBox:focus, QDateEdit:focus,
QSpinBox:focus, QDoubleSpinBox:focus { border-color: #3c8dbc; }
QComboBox::drop-down { border: none; width: 22px; }
QComboBox QAbstractItemView {
    background: white; border: 1px solid #ccc;
    selection-background-color: #3c8dbc; selection-color: white;
}

QPushButton { border-radius: 3px; padding: 6px 14px; color: white;
    background: #3c8dbc; border: 1px solid transparent; }
QPushButton:hover { background: #367fa9; }
QPushButton#btnPrimary { background: #3c8dbc; color: #ffffff; }
QPushButton#btnPrimary:hover { background: #367fa9; color: #ffffff; }
QPushButton#btnSuccess { background: #00a65a; color: #ffffff; }
QPushButton#btnSuccess:hover { background: #008d4c; color: #ffffff; }
QPushButton#btnDanger { background: #dd4b39; color: #ffffff; }
QPushButton#btnDanger:hover { background: #d73925; color: #ffffff; }
QPushButton#btnWarning { background: #f39c12; color: #ffffff; }
QPushButton#btnWarning:hover { background: #e08e0b; color: #ffffff; }
QPushButton#btnInfo { background: #00c0ef; color: #ffffff; }
QPushButton#btnInfo:hover { background: #00acd7; color: #ffffff; }
QPushButton#btnDefault { background: #ffffff; color: #444;
    border: 1px solid #d2d6de; }
QPushButton#btnDefault:hover { background: #f4f4f5; }
QPushButton:disabled { background: #b5bcc1; color: #eee; }

QTableWidget { background: white; border: 1px solid #d2d6de;
    gridline-color: #e8eaec; alternate-background-color: #fafbfc;
    selection-background-color: #3c8dbc; selection-color: white; }
QHeaderView::section {
    background: #f4f4f5; color: #444; border: 1px solid #e0e0e0;
    padding: 7px 6px; font-weight: 600;
}

QScrollBar:vertical { background: #f1f1f1; width: 12px; }
QScrollBar::handle:vertical { background: #c1c1c1; min-height: 30px; border-radius: 4px; }
QScrollBar::handle:vertical:hover { background: #a8a8a8; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal { background: #f1f1f1; height: 12px; }
QScrollBar::handle:horizontal { background: #c1c1c1; min-width: 30px; border-radius: 4px; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
QToolTip { background: #222d32; color: white; border: none; padding: 5px; }
QMenu { background: white; border: 1px solid #ccc; }
QMenu::item { padding: 7px 26px; }
QMenu::item:selected { background: #3c8dbc; color: white; }
QStatusBar { background: #ffffff; color: #777; border-top: 1px solid #e0e0e0; }
QGroupBox { font-weight: 600; color: #555; border: 1px solid #d2d6de;
    border-radius: 3px; margin-top: 12px; background: #fff; }
QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px; }

QPushButton[pageNav="true"] { background: #ffffff; color: #444;
    border: 1px solid #d2d6de; padding: 3px 8px; font-size: 12px;
    min-width: 10px; }
QPushButton[pageNav="true"]:hover { background: #f4f4f5; }
QPushButton[pageNav="true"]:disabled { background: #ffffff; color: #bbb;
    border: 1px solid #e8e8e8; }
QPushButton[pageNav="true"][pageNavCurrent="true"] { background: #3c8dbc;
    color: white; border-color: #367fa9; font-weight: bold; }
QPushButton[pageNavCurrent="true"] { background: #3c8dbc; color: white;
    border: 1px solid #367fa9; padding: 2px 6px; border-radius: 4px;
    font-size: 12px; font-weight: bold; }
QPushButton[pageNavCurrent="true"]:hover { background: #367fa9; }

QComboBox#PaginatorPerPage { background: white; border: 1px solid #d2d6de;
    border-radius: 3px; padding: 3px 6px; font-size: 12px; min-width: 60px; }
QLabel#PaginatorInfo { color: #777; font-size: 12px; padding: 0 4px; }
"""