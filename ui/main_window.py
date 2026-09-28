"""
Main window - replica of the AdminLTE shell.

Features:
  * AdminLTE-style skin switcher (gear icon in the header)
  * White hamburger toggle right of the logo - collapses the sidebar to a
    narrow "mini" strip that shows only the icons + avatar (AdminLTE
    sidebar-mini), and expands it back on the next click
  * Account dropdown popup (avatar + name + role + member since)
  * White tabbed account menu; state persisted across runs via QSettings
"""
import os
from datetime import date, datetime

from PyQt6.QtCore import Qt, QUrl, QSize, QTimer, QPoint, QSettings
from PyQt6.QtGui import (QDesktopServices, QPixmap, QPainter, QPainterPath,
                         QIcon, QColor)
from PyQt6.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
                             QLabel, QPushButton, QToolButton, QMenu,
                             QScrollArea, QStackedWidget, QLineEdit, QFrame,
                             QApplication, QGridLayout, QCheckBox)

from config import APP_TITLE, LOGO_MINI
from ui.app_icon import app_icon
from ui.theme import icon
import ui.widgets as W


# --------------------------------------------------------------------------- #
# App base folder + avatar helpers
# --------------------------------------------------------------------------- #
def _app_base_dir() -> str:
    here = os.path.dirname(os.path.abspath(__file__))
    cur = here
    for _ in range(6):
        if os.path.isdir(os.path.join(cur, "dist")):
            return cur
        parent = os.path.dirname(cur)
        if parent == cur:
            break
        cur = parent
    return os.path.abspath(os.path.join(here, "..", ".."))


APP_BASE = _app_base_dir()
UPLOAD_DIR = os.path.join(APP_BASE, "dist", "img", "uploads")


def _qicon_from_pixmap(pm: QPixmap) -> QIcon:
    return QIcon(pm)


def _circular_avatar(picture_name: str, size: int = 42) -> QPixmap:
    path = ""
    if picture_name:
        base = os.path.basename(str(picture_name).replace("\\", "/"))
        candidate = os.path.join(UPLOAD_DIR, base)
        if os.path.isfile(candidate):
            path = candidate

    pm = QPixmap(path) if path else QPixmap()
    if pm.isNull():
        pm = icon("user", "#ffffff", size).pixmap(size, size)
        if pm.isNull():
            pm = QPixmap(size, size)
            pm.fill(Qt.GlobalColor.lightGray)

    pm = pm.scaled(size, size,
                   Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                   Qt.TransformationMode.SmoothTransformation)

    result = QPixmap(size, size)
    result.fill(Qt.GlobalColor.transparent)
    p = QPainter(result)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    clip = QPainterPath()
    clip.addEllipse(0, 0, size, size)
    p.setClipPath(clip)
    x = (pm.width() - size) // 2
    y = (pm.height() - size) // 2
    p.drawPixmap(-x, -y, pm)
    p.end()
    return result


# --------------------------------------------------------------------------- #
# Skins
# --------------------------------------------------------------------------- #
SKINS = {
    "Blue":   ("#3c8dbc", "#222d32", "#3c8dbc"),
    "Black":  ("#222d32", "#222d32", "#222d32"),
    "Purple": ("#605ca8", "#222d32", "#605ca8"),
    "Green":  ("#00a65a", "#222d32", "#00a65a"),
    "Red":    ("#dd4b39", "#222d32", "#dd4b39"),
    "Yellow": ("#f39c12", "#222d32", "#f39c12"),
}
DEFAULT_SKIN = "Blue"


# --------------------------------------------------------------------------- #
# Skin switcher popup
# --------------------------------------------------------------------------- #
class SkinPanel(QFrame):
    WIDTH = 300

    def __init__(self, parent, current_skin, on_skin_change,
                 toggles, on_toggle_change):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Popup |
                            Qt.WindowType.FramelessWindowHint |
                            Qt.WindowType.NoDropShadowWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setFixedWidth(self.WIDTH)
        self.setStyleSheet(
            "SkinPanel { background: #222d32; border: 1px solid #2c3b41;"
            " border-radius: 3px; }")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        head = QFrame()
        head.setFixedHeight(44)
        head.setStyleSheet(
            "QFrame { background: #222d32;"
            " border-bottom: 1px solid #2c3b41;"
            " border-top-left-radius: 3px; border-top-right-radius: 3px; }")
        hl = QHBoxLayout(head)
        hl.setContentsMargins(14, 0, 8, 0)
        ttl = QLabel("Layout Options")
        ttl.setStyleSheet("color: #ffffff; font-size: 14px; font-weight: 600;")
        hl.addWidget(ttl)
        hl.addStretch()
        outer.addWidget(head)

        body = QWidget()
        bv = QVBoxLayout(body)
        bv.setContentsMargins(14, 10, 14, 10)
        bv.setSpacing(4)

        for label, sub, key in (
            ("Fixed layout", "Activate the fixed layout", "fixed_layout"),
            ("Boxed Layout", "Activate the boxed layout", "boxed_layout"),
            ("Toggle Sidebar", "Toggle the left sidebar", "toggle_sidebar"),
            ("Sidebar Expand on Hover", "Expand on hover", "sidebar_expand"),
            ("Toggle Right Sidebar Slide", "Right sidebar slide",
             "right_sidebar_slide"),
            ("Toggle Right Sidebar Skin", "Right sidebar skin",
             "right_sidebar_skin"),
        ):
            self._make_option(bv, label, sub, key, toggles, on_toggle_change)

        skins_lbl = QLabel("Skins")
        skins_lbl.setStyleSheet(
            "color: #ffffff; font-size: 14px; font-weight: 600;"
            " padding-top: 10px;")
        bv.addWidget(skins_lbl)

        swatch_grid = QGridLayout()
        swatch_grid.setContentsMargins(0, 6, 0, 0)
        swatch_grid.setHorizontalSpacing(8)
        swatch_grid.setVerticalSpacing(6)
        names = list(SKINS.keys())
        cols = 3
        for i, name in enumerate(names):
            swatch_grid.addWidget(
                self._make_swatch(name, current_skin, on_skin_change),
                i // cols, i % cols)
        bv.addLayout(swatch_grid)
        outer.addWidget(body)

    def _make_option(self, parent_layout, title, subtitle, key,
                     toggles, on_change):
        row = QFrame()
        row.setStyleSheet("QFrame { background: transparent; }")
        rv = QVBoxLayout(row)
        rv.setContentsMargins(0, 6, 0, 6)
        rv.setSpacing(2)

        top = QHBoxLayout()
        lbl = QLabel(title)
        lbl.setStyleSheet("color: #ffffff; font-size: 13px; font-weight: 600;")
        top.addWidget(lbl)
        top.addStretch()

        cb = QCheckBox()
        cb.setChecked(bool(toggles.get(key, False)))
        cb.setStyleSheet(
            "QCheckBox::indicator { width: 14px; height: 14px;"
            " border: 1px solid #ffffff; background: transparent; }"
            "QCheckBox::indicator:checked { background: #ffffff; }")
        cb.stateChanged.connect(
            lambda state, k=key: on_change(
                k, state == Qt.CheckState.Checked.value))
        top.addWidget(cb)
        rv.addLayout(top)

        sub = QLabel(subtitle)
        sub.setWordWrap(True)
        sub.setStyleSheet("color: #8aa4af; font-size: 11.5px;")
        rv.addWidget(sub)
        parent_layout.addWidget(row)

    def _make_swatch(self, name, current_skin, on_change):
        color = SKINS[name][0]
        wrap = QFrame()
        wrap.setStyleSheet("QFrame { background: transparent; }")
        wv = QVBoxLayout(wrap)
        wv.setContentsMargins(0, 0, 0, 0)
        wv.setSpacing(3)

        btn = QPushButton()
        btn.setFixedHeight(28)
        border = ("2px solid #ffffff" if name == current_skin
                  else "1px solid #2c3b41")
        btn.setStyleSheet(
            f"QPushButton {{ background: {color}; border: {border};"
            f" border-radius: 3px; }}"
            f"QPushButton:hover {{ border: 2px solid #ffffff; }}")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(lambda: on_change(name))
        wv.addWidget(btn)

        lbl = QLabel(name)
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setStyleSheet("color: #ffffff; font-size: 11.5px;")
        wv.addWidget(lbl)
        return wrap

    def show_under(self, anchor: QWidget):
        gp = anchor.mapToGlobal(QPoint(0, anchor.height()))
        x = gp.x() + anchor.width() - self.WIDTH
        self.move(x, gp.y())
        self.show()


# --------------------------------------------------------------------------- #
# Account dropdown
# --------------------------------------------------------------------------- #
class AccountDropdown(QFrame):
    WIDTH = 280
    HEADER_H = 180
    FOOTER_H = 46

    def __init__(self, parent, admin, on_profile, on_signout):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Popup |
                            Qt.WindowType.FramelessWindowHint |
                            Qt.WindowType.NoDropShadowWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setFixedWidth(self.WIDTH)
        self.setStyleSheet(
            "AccountDropdown { background: #ffffff;"
            " border: 1px solid #d2d6de; border-radius: 4px; }")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        head = QFrame()
        head.setFixedHeight(self.HEADER_H)
        head.setStyleSheet(
            "QFrame { background: #3c8dbc;"
            " border-top-left-radius: 4px; border-top-right-radius: 4px; }")
        hv = QVBoxLayout(head)
        hv.setContentsMargins(16, 18, 16, 14)
        hv.setSpacing(6)

        avatar = QLabel()
        avatar.setFixedSize(96, 96)
        avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        avatar.setStyleSheet("background: transparent; border: none;")
        avatar.setPixmap(_circular_avatar(admin.get("picture", ""), 96))
        hv.addWidget(avatar, 0, Qt.AlignmentFlag.AlignHCenter)

        name_lbl = QLabel(self._name_prof(admin))
        name_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_lbl.setWordWrap(True)
        name_lbl.setStyleSheet(
            "color: #ffffff; font-size: 15px; font-weight: 600;"
            " background: transparent; border: none;")
        hv.addWidget(name_lbl)

        member_lbl = QLabel(f"Member since {self._member_since(admin)}")
        member_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        member_lbl.setStyleSheet(
            "color: #d7ebf5; font-size: 12px;"
            " background: transparent; border: none;")
        hv.addWidget(member_lbl)
        hv.addStretch()
        outer.addWidget(head)

        foot = QFrame()
        foot.setFixedHeight(self.FOOTER_H)
        foot.setStyleSheet(
            "QFrame { background: #f9f9f9;"
            " border-bottom-left-radius: 4px;"
            " border-bottom-right-radius: 4px; }")
        f = QGridLayout(foot)
        f.setContentsMargins(6, 6, 6, 6)
        f.setSpacing(6)

        profile_btn = QPushButton("Profile")
        profile_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        profile_btn.setStyleSheet(
            "QPushButton { background: #ffffff; color: #444;"
            " border: 1px solid #ddd; border-radius: 3px;"
            " padding: 6px 16px; font-size: 13px; }"
            "QPushButton:hover { background: #e7e7e7; }")
        profile_btn.clicked.connect(lambda: (self.close(), on_profile()))

        signout_btn = QPushButton("Sign out")
        signout_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        signout_btn.setStyleSheet(
            "QPushButton { background: #ffffff; color: #444;"
            " border: 1px solid #ddd; border-radius: 3px;"
            " padding: 6px 16px; font-size: 13px; }"
            "QPushButton:hover { background: #e7e7e7; }")
        signout_btn.clicked.connect(lambda: (self.close(), on_signout()))

        f.addWidget(profile_btn, 0, 0)
        f.addWidget(signout_btn, 0, 1)
        outer.addWidget(foot)

    @staticmethod
    def _name_prof(admin):
        name = admin.get("name") or "User"
        prof = admin.get("profession") or ""
        return f"{name} - {prof}" if prof else name

    @staticmethod
    def _member_since(admin):
        d = admin.get("created") or admin.get("created_at")
        if d:
            try:
                if isinstance(d, str):
                    d = datetime.fromisoformat(str(d).split(" ")[0]).date()
                if hasattr(d, "strftime"):
                    return d.strftime("%b. %Y")
                return str(d)
            except Exception:
                return str(d)
        return date.today().strftime("%b. %Y")

    def show_below(self, anchor: QWidget):
        gp = anchor.mapToGlobal(QPoint(0, anchor.height()))
        x = gp.x() + anchor.width() - self.WIDTH
        self.move(x, gp.y())
        self.show()


# --------------------------------------------------------------------------- #
# MainWindow
# --------------------------------------------------------------------------- #
class MainWindow(QMainWindow):
    SIDEBAR_FULL_W = 230
    SIDEBAR_MINI_W = 56

    def __init__(self, admin):
        super().__init__()
        self.admin = admin
        self.setWindowTitle(f"{APP_TITLE} - Dashboard")
        self.setWindowIcon(app_icon())
        self.resize(1360, 800)
        self._pages = {}
        self._nav_items = []
        self._nav_rows = []
        self._nav_groups = {}
        self._nav_parent_of = {}
        self._account_popup = None
        self._skin_popup = None

        # ---- sidebar mini state ----
        self._sidebar_mini = False
        self._sidebar_user_labels = []   # name + "● Online" labels
        self._sidebar_search = None
        self._sidebar_header_lbl = None

        self._settings = QSettings("AntDev", "C4")
        self._skin_name = self._settings.value("skin", DEFAULT_SKIN)
        if self._skin_name not in SKINS:
            self._skin_name = DEFAULT_SKIN
        self._toggles = {
            "fixed_layout": self._settings.value("fixed_layout", False, bool),
            "boxed_layout": self._settings.value("boxed_layout", False, bool),
            "toggle_sidebar": self._settings.value("toggle_sidebar", False, bool),
            "sidebar_expand": self._settings.value("sidebar_expand", False, bool),
            "right_sidebar_slide": self._settings.value("right_sidebar_slide", False, bool),
            "right_sidebar_skin": self._settings.value("right_sidebar_skin", False, bool),
        }

        self._build_all()
        self._apply_skin(self._skin_name, persist=False)

        # restore sidebar-mini if it was on
        if self._settings.value("toggle_sidebar", False, bool):
            self._sidebar_mini = False      # toggle flips it to True
            self._toggle_sidebar()

        QTimer.singleShot(0, lambda: self.navigate("dashboard"))

    # ------------------------------------------------------------------ header
    def _build_all(self):
        self.header = QFrame()
        self.header.setObjectName("HeaderBar")
        self.header.setFixedHeight(52)
        h = QHBoxLayout(self.header)
        h.setContentsMargins(0, 0, 10, 0)
        h.setSpacing(6)

        # ---- left: logo + white hamburger to its right ----
        logo = QLabel(f"<b style='font-size:16px'>{LOGO_MINI}</b>"
                      f"<span style='font-size:16px'>&nbsp;{APP_TITLE}</span>")
        logo.setObjectName("LogoLabel")
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo.setFixedWidth(200)
        h.addWidget(logo)

        self.menu_btn = QToolButton()
        self.menu_btn.setObjectName("HeaderButton")
        self.menu_btn.setAutoRaise(True)
        self.menu_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.menu_btn.setText("\u2630")   # ☰
        self.menu_btn.setStyleSheet(
            "QToolButton { color: #ffffff; font-size: 20px;"
            " padding: 0 12px; background: transparent; border: none; }"
            "QToolButton:hover { background: rgba(255,255,255,0.12); }")
        self.menu_btn.setToolTip("Toggle navigation")
        self.menu_btn.clicked.connect(self._toggle_sidebar)
        h.addWidget(self.menu_btn)

        h.addStretch()

        self.name_label = QLabel(self.admin.get("name", ""))

        # ---- notifications ----
        bell = QToolButton()
        bell.setObjectName("HeaderButton")
        bell.setIcon(icon("bell", "#ffffff", 20))
        bell.setIconSize(QSize(20, 20))
        bell.setAutoRaise(True)
        bell.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        bell.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        bell.setArrowType(Qt.ArrowType.NoArrow)
        bell.setStyleSheet(
            "QToolButton::menu-indicator { image: none; width: 0; }")
        menu = QMenu(self)
        menu.addAction("You have 10 notifications")
        menu.addSeparator()
        for t in ("5 new members joined today", "25 sales made",
                  "You changed your username"):
            menu.addAction(t)
        bell.setMenu(menu)
        h.addWidget(bell)

        # ---- account button ----
        self.user_btn = QToolButton()
        self.user_btn.setObjectName("HeaderButton")
        self.user_btn.setAutoRaise(True)
        self.user_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.user_btn.setToolButtonStyle(
            Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.user_btn.setText(
            f"{self.admin.get('name', '') or 'Account'}  \u25BE")
        self.user_btn.setIconSize(QSize(22, 22))
        self.user_btn.setIcon(_qicon_from_pixmap(
            _circular_avatar(self.admin.get("picture", ""), 22)))
        self.user_btn.setArrowType(Qt.ArrowType.NoArrow)
        self.user_btn.setStyleSheet(
            "QToolButton::menu-indicator { image: none; width: 0; }")
        self.user_btn.clicked.connect(self._open_account_menu)
        h.addWidget(self.user_btn)

        # ---- gear (skin switcher) ----
        self.gear_btn = QToolButton()
        self.gear_btn.setObjectName("HeaderButton")
        self.gear_btn.setAutoRaise(True)
        self.gear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.gear_btn.setIcon(icon("settings", "#ffffff", 20))
        self.gear_btn.setIconSize(QSize(20, 20))
        self.gear_btn.setToolTip("Layout options & skins")
        self.gear_btn.clicked.connect(self._open_skin_menu)
        h.addWidget(self.gear_btn)

        # ---------------- central ----------------
        central = QWidget()
        outer = QVBoxLayout(central)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addWidget(self.header)

        body = QWidget()
        root = QHBoxLayout(body)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.sidebar = QFrame()
        self.sidebar.setObjectName("Sidebar")
        self.sidebar.setFixedWidth(self.SIDEBAR_FULL_W)
        sv = QVBoxLayout(self.sidebar)
        sv.setContentsMargins(0, 0, 0, 0)
        sv.setSpacing(0)

        # ---- user-panel ----
        up = QFrame()
        up.setObjectName("UserPanel")
        up.setFixedHeight(68)
        upl = QHBoxLayout(up)
        upl.setContentsMargins(12, 8, 8, 8)
        upl.setSpacing(10)

        self.sidebar_avatar = QLabel()
        self.sidebar_avatar.setFixedSize(46, 46)
        self.sidebar_avatar.setPixmap(
            _circular_avatar(self.admin.get("picture", ""), 46))
        self.sidebar_avatar.setStyleSheet(
            "background: transparent; border: none;")
        upl.addWidget(self.sidebar_avatar)

        iv = QVBoxLayout()
        iv.setSpacing(0)
        iv.setContentsMargins(0, 0, 0, 0)

        name_l = QLabel(self.admin.get("name", ""))
        name_l.setStyleSheet(
            "color: #ffffff; font-size: 13px; font-weight: 600;"
            " background: transparent;")
        iv.addWidget(name_l)
        self._sidebar_user_labels.append(name_l)

        online = QLabel("\u25CF Online")
        online.setStyleSheet(
            "color: #00a65a; font-size: 11px; background: transparent;")
        iv.addWidget(online)
        self._sidebar_user_labels.append(online)

        upl.addLayout(iv)
        upl.addStretch()
        sv.addWidget(up)

        # ---- search form ----
        self.search_edit = QLineEdit()
        self.search_edit.setObjectName("SidebarSearch")
        self.search_edit.setPlaceholderText("Search...")
        self.search_edit.textChanged.connect(self._filter_nav)
        sv.addWidget(self.search_edit)
        self._sidebar_search = self.search_edit

        # ---- section title ----
        header_lbl = QLabel("MAIN NAVIGATION")
        header_lbl.setObjectName("SidebarHeader")
        sv.addWidget(header_lbl)
        self._sidebar_header_lbl = header_lbl

        # ---- nav ----
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        nav_host = QWidget()
        nav_host.setObjectName("NavHost")
        nav_host.setStyleSheet("QWidget#NavHost { background: transparent; }")
        self.nav_layout = QVBoxLayout(nav_host)
        self.nav_layout.setContentsMargins(0, 0, 0, 20)
        self.nav_layout.setSpacing(0)
        self._build_nav(self.nav_layout)
        self.nav_layout.addStretch()
        scroll.setWidget(nav_host)
        sv.addWidget(scroll, 1)

        self.stack = QStackedWidget()
        self.stack.setObjectName("PageStack")
        self.stack.setStyleSheet(
            "QStackedWidget#PageStack { background: #ecf0f5; }")
        content_wrap = QWidget()
        cl = QVBoxLayout(content_wrap)
        cl.setContentsMargins(16, 12, 16, 12)
        cl.addWidget(self.stack)

        root.addWidget(self.sidebar)
        root.addWidget(content_wrap, 1)
        outer.addWidget(body, 1)
        self.setCentralWidget(central)

    # ------------------------------------------------------------------- nav
    NAV = [
        ("Dashboard", "dashboard", "dashboard", None),
        ("Accounts", None, "accounts", [
            ("Accounts", "accounts", "list"),
            ("Add/View Account Type", "account_types", "userplus"),
        ]),
        ("Manage Clients", "clients", "clients", None),
        ("Products", "products", "products", None),
        ("Suppliers", "suppliers", "suppliers", None),
        ("Add Purchase", "purchase_gen", "cartplus", None),
        ("Purchase List", "purchase_list", "table", None),
        ("Quick Quotation", "quickquote", "bolt", None),
        ("Gen. Quotation", "quote_gen", "file", None),
        ("Quotation List", "quote_list", "list", None),
        ("Whatsapp", "whatsapp", "whatsapp", None),
        ("Manage Invoice", None, "folderopen", [
            ("Proforma Invoice List", "proforma_list", "file"),
            ("Tax Invoice List", "tax_list", "file"),
        ]),
        ("Transaction", "transaction", "exchange", None),
        ("Generate", None, "plus", [
            ("Gen. Proforma Invoice", "proforma_gen", "file"),
            ("Gen. Tax Invoice", "tax_gen", "file"),
        ]),
        ("Quotation Report", None, "chart", [
            ("Quick Quote Report", "quickquote_report", "thlist"),
            ("Quote Item Report", "quote_item_report", "thlist"),
            ("Quote Report", "quote_report", "linechart"),
        ]),
        ("Proforma Report", None, "chart", [
            ("Proforma Item Report", "proforma_item_report", "thlist"),
            ("Proforma Report", "proforma_report", "linechart"),
        ]),
        ("Purchase Report", None, "cart", [
            ("Purchase Item Report", "purchase_item_report", "thlist"),
            ("Purchase Hsn Report", "purchase_hsn_report", "tree"),
            ("Purchase Report", "purchase_report", "barchart"),
        ]),
        ("Sales Report", None, "money", [
            ("Sale Item Report", "sale_item_report", "thlist"),
            ("Sale Hsn Report", "sale_hsn_report", "tree"),
            ("Sales Report", "sale_report", "linechart"),
        ]),
        ("Sales Prediction", "sales_prediction", "linechart", None),
        ("Settings", "settings", "settings", None),
        ("Logout", "logout", "power", None),
    ]

    def _build_nav(self, layout):
        for label, key, ic, submenu in self.NAV:
            row = QWidget()
            row.setObjectName("NavRow")
            row.setStyleSheet("QWidget#NavRow { background: transparent; }")
            rl = QHBoxLayout(row)
            rl.setContentsMargins(0, 0, 0, 0)
            rl.setSpacing(0)
            btn = QPushButton(f"  {label}")
            btn.setProperty("sidebarItem", True)
            btn.setProperty("fullText", label)
            btn.setIconSize(QSize(18, 18))
            if ic:
                btn.setIcon(icon(ic, "#b8c7ce", 18))
            rl.addWidget(btn, 1)
            chev = None
            if submenu is not None:
                chev = QToolButton()
                chev.setObjectName("NavChevron")
                chev.setIcon(icon("chevronright", "#b8c7ce", 14))
                chev.setIconSize(QSize(14, 14))
                chev.setFixedWidth(26)
                chev.setCursor(Qt.CursorShape.PointingHandCursor)
                rl.addWidget(chev, 0)
            layout.addWidget(row)
            self._nav_items.append((btn, label, key))
            self._nav_rows.append((btn, chev, label))
            btn.clicked.connect(lambda _, k=key: self._nav_clicked(k))
            if submenu is not None:
                sub_holder = QWidget()
                sub_holder.setObjectName("NavSubHolder")
                sub_holder.setStyleSheet(
                    "QWidget#NavSubHolder { background: transparent; }")
                subv = QVBoxLayout(sub_holder)
                subv.setContentsMargins(0, 0, 0, 0)
                subv.setSpacing(0)
                for slabel, skey, sic in submenu:
                    sb = QPushButton(f"  {slabel}")
                    sb.setProperty("sidebarSub", True)
                    sb.setProperty("fullText", slabel)
                    sb.setIconSize(QSize(14, 14))
                    if sic:
                        sb.setIcon(icon(sic, "#8aa4af", 14))
                    subv.addWidget(sb)
                    self._nav_items.append((sb, slabel, skey))
                    self._nav_parent_of[skey] = label
                    sb.clicked.connect(lambda _, k=skey: self._nav_clicked(k))
                sub_holder.setVisible(False)
                layout.addWidget(sub_holder)
                self._nav_groups[label] = (sub_holder, chev)

                def _toggle(checked=False, sh=sub_holder, ch=chev):
                    opened = not sh.isVisible()
                    sh.setVisible(opened)
                    ch.setIcon(icon("chevron" if opened else "chevronright",
                                    "#b8c7ce", 14))

                btn.clicked.connect(_toggle)
                chev.clicked.connect(_toggle)

    def _filter_nav(self, text):
        text = text.lower().strip()
        if not text:
            for btn, label, key in self._nav_items:
                btn.setVisible(True)
            for btn, chev, glabel in self._nav_rows:
                if chev is not None:
                    self._set_group_open(glabel, False)
                    chev.setVisible(True)
            return
        for btn, label, key in self._nav_items:
            btn.setVisible(text in label.lower())
        for btn, chev, glabel in self._nav_rows:
            if chev is None:
                continue
            child_match = any(text in l.lower()
                              for b, l, k in self._nav_items
                              if self._nav_parent_of.get(k) == glabel)
            if child_match:
                btn.setVisible(True)
                self._set_group_open(glabel, True)
            else:
                self._set_group_open(glabel, False)
            chev.setVisible(btn.isVisible())

    def _nav_clicked(self, key):
        self.navigate(key)

    def _set_group_open(self, key, opened):
        holder, chev = self._nav_groups.get(key, (None, None))
        if holder is None:
            return
        holder.setVisible(opened)
        if chev is not None:
            chev.setIcon(icon("chevron" if opened else "chevronright",
                              "#b8c7ce", 14))

    # ------------------------------------------------------ sidebar mini
    def _toggle_sidebar(self):
        """Toggle between full sidebar and mini (icons only)."""
        self._sidebar_mini = not self._sidebar_mini
        if self._sidebar_mini:
            self.sidebar.setFixedWidth(self.SIDEBAR_MINI_W)
            self._enter_mini()
        else:
            self.sidebar.setFixedWidth(self.SIDEBAR_FULL_W)
            self._exit_mini()
        self._toggles["toggle_sidebar"] = self._sidebar_mini
        self._settings.setValue("toggle_sidebar", self._sidebar_mini)

    def _enter_mini(self):
        """Hide all text; keep icons + avatar visible."""
        if self._sidebar_header_lbl:
            self._sidebar_header_lbl.setVisible(False)
        if self._sidebar_search:
            self._sidebar_search.setVisible(False)
        for lbl in self._sidebar_user_labels:
            lbl.setVisible(False)

        for btn, label, key in self._nav_items:
            btn.setText("")
            btn.setToolTip(label)

        # collapse treeview sub-holders and hide chevrons
        for holder, _chev in self._nav_groups.values():
            holder.setVisible(False)
        for _btn, chev, _label in self._nav_rows:
            if chev is not None:
                chev.setVisible(False)

        # hide the "MAIN NAVIGATION" section label as well
        # (it's kept in self._sidebar_header_lbl, done above)

    def _exit_mini(self):
        """Restore all text."""
        if self._sidebar_header_lbl:
            self._sidebar_header_lbl.setVisible(True)
        if self._sidebar_search:
            self._sidebar_search.setVisible(True)
        for lbl in self._sidebar_user_labels:
            lbl.setVisible(True)

        for btn, label, key in self._nav_items:
            btn.setText(f"  {label}")
            btn.setToolTip("")

        for btn, chev, glabel in self._nav_rows:
            if chev is not None:
                chev.setVisible(btn.isVisible())

        # reapply the current search filter
        self._filter_nav(self.search_edit.text())

    # ------------------------------------------------------ account / skin
    def _logout(self):
        self.close()
        if getattr(self, "_on_logout", None):
            self._on_logout()

    def set_logout_callback(self, fn):
        self._on_logout = fn

    def _open_account_menu(self):
        self._account_popup = AccountDropdown(
            self, self.admin,
            on_profile=lambda: self.navigate("settings"),
            on_signout=self._logout)
        self._account_popup.show_below(self.user_btn)

    def _open_skin_menu(self):
        self._skin_popup = SkinPanel(
            self, current_skin=self._skin_name,
            on_skin_change=self._apply_skin,
            toggles=self._toggles,
            on_toggle_change=self._on_toggle_changed)
        self._skin_popup.show_under(self.gear_btn)

    def _on_toggle_changed(self, key, value):
        self._toggles[key] = bool(value)
        self._settings.setValue(key, bool(value))
        if key == "toggle_sidebar":
            # route the toggle from the skin panel through the same path
            if self._sidebar_mini != bool(value):
                self._toggle_sidebar()
        elif key == "fixed_layout":
            if value and self._toggles.get("boxed_layout"):
                self._toggles["boxed_layout"] = False
                self._settings.setValue("boxed_layout", False)
        elif key == "boxed_layout":
            if value and self._toggles.get("fixed_layout"):
                self._toggles["fixed_layout"] = False
                self._settings.setValue("fixed_layout", False)

    def _apply_skin(self, name, persist=True):
        if name not in SKINS:
            return
        self._skin_name = name
        if persist:
            self._settings.setValue("skin", name)

        header_color, sidebar_bg, active_color = SKINS[name]

        if hasattr(self, "header"):
            self.header.setStyleSheet(
                f"QFrame#HeaderBar {{ background: {header_color}; }}"
                f"QFrame#HeaderBar QLabel, QFrame#HeaderBar QToolButton,"
                f" QFrame#HeaderBar QPushButton {{ color: #ffffff; }}")

        if hasattr(self, "sidebar"):
            self.sidebar.setStyleSheet(
                f"QFrame#Sidebar {{ background: {sidebar_bg}; }}"
                f"QFrame#Sidebar QPushButton[sidebarItem=\"true\"]:hover,"
                f" QFrame#Sidebar QPushButton[sidebarSub=\"true\"]:hover {{"
                f"   background: #1e282c; }}"
                f"QFrame#Sidebar QPushButton[sidebarItem=\"true\"][active=\"true\"],"
                f" QFrame#Sidebar QPushButton[sidebarSub=\"true\"][active=\"true\"] {{"
                f"   background: {active_color}; color: #ffffff; }}")

        for btn, label, key in getattr(self, "_nav_items", []):
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    # ---------------------------------------------------------------- pages
    def _page_factory(self, key):
        from ui.pages.dashboard_page import DashboardPage
        from ui.pages.master_pages import (ClientsPage, SuppliersPage,
                                           ProductsPage)
        from ui.pages.accounts_page import AccountsPage, AccountTypesPage
        from ui.pages.invoice_pages import InvoiceGenPage, InvoiceListPage
        from ui.pages.quickquote_page import QuickQuotePage
        from ui.pages.transaction_page import TransactionPage
        from ui.pages.reports_page import ReportPage
        from ui.pages.sales_prediction_page import SalesPredictionPage
        from ui.pages.settings_page import SettingsPage

        factories = {
            "dashboard": lambda: DashboardPage(self),
            "clients": lambda: ClientsPage(self),
            "suppliers": lambda: SuppliersPage(self),
            "products": lambda: ProductsPage(self),
            "accounts": lambda: AccountsPage(self),
            "account_types": lambda: AccountTypesPage(self),
            "tax_gen": lambda: InvoiceGenPage(self, "tax"),
            "proforma_gen": lambda: InvoiceGenPage(self, "proforma"),
            "quote_gen": lambda: InvoiceGenPage(self, "quote"),
            "purchase_gen": lambda: InvoiceGenPage(self, "purchase"),
            "tax_list": lambda: InvoiceListPage(self, "tax"),
            "proforma_list": lambda: InvoiceListPage(self, "proforma"),
            "quote_list": lambda: InvoiceListPage(self, "quote"),
            "purchase_list": lambda: InvoiceListPage(self, "purchase"),
            "quickquote": lambda: QuickQuotePage(self),
            "transaction": lambda: TransactionPage(self),
            "sale_item_report": lambda: ReportPage(self, "item", "tax",
                                                   "Sale Item Report"),
            "sale_hsn_report": lambda: ReportPage(self, "hsn", "tax",
                                                  "Sale Hsn Report"),
            "sale_report": lambda: ReportPage(self, "summary", "tax",
                                              "Sales Report"),
            "purchase_item_report": lambda: ReportPage(self, "item", "purchase",
                                                       "Purchase Item Report"),
            "purchase_hsn_report": lambda: ReportPage(self, "hsn", "purchase",
                                                      "Purchase Hsn Report"),
            "purchase_report": lambda: ReportPage(self, "summary", "purchase",
                                                  "Purchase Report"),
            "quote_item_report": lambda: ReportPage(self, "item", "quote",
                                                    "Quote Item Report"),
            "quote_report": lambda: ReportPage(self, "summary", "quote",
                                               "Quote Report"),
            "quickquote_report": lambda: ReportPage(self, "quickquote", None,
                                                    "Quick Quote Report"),
            "proforma_item_report": lambda: ReportPage(self, "item", "proforma",
                                                       "Proforma Item Report"),
            "proforma_report": lambda: ReportPage(self, "summary", "proforma",
                                                  "Proforma Report"),
            "sales_prediction": lambda: SalesPredictionPage(self),
            "settings": lambda: SettingsPage(self),
        }
        return factories[key]() if key in factories else None

    def navigate(self, key):
        if key == "logout":
            self._logout()
            return
        if key == "whatsapp":
            QDesktopServices.openUrl(QUrl("https://web.whatsapp.com/"))
            return
        if key not in self._pages:
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            try:
                page = self._page_factory(key)
            except Exception as exc:
                QApplication.restoreOverrideCursor()
                W.error(self, f"Could not open page: {exc}")
                return
            QApplication.restoreOverrideCursor()
            if page is None:
                return
            self._pages[key] = page
            self.stack.addWidget(page)
        page = self._pages[key]
        self.stack.setCurrentWidget(page)
        if hasattr(page, "title"):
            self.setWindowTitle(f"{page.title} - AntDev")
        for btn, label, k in self._nav_items:
            btn.setProperty("active", str(k == key).lower())
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        parent = self._nav_parent_of.get(key)
        if parent is not None and not self._sidebar_mini:
            self._set_group_open(parent, True)
        if hasattr(page, "refresh"):
            QTimer.singleShot(0, lambda: self._safe_refresh(page))

    def _safe_refresh(self, page):
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            page.refresh()
        except Exception as exc:
            W.error(self, f"Load failed on {type(page).__name__}: {exc}")
        finally:
            QApplication.restoreOverrideCursor()

    # -------------------------------------------------------------- Info pages
    def open_info(self, kind, info_id):
        from ui.pages.info_pages import InfoPage
        key = f"info_{kind}_{info_id}"
        if key not in self._pages:
            try:
                page = InfoPage(self, kind, info_id)
            except Exception as exc:
                W.error(self, f"Could not open info page: {exc}")
                return
            self._pages[key] = page
            self.stack.addWidget(page)
        page = self._pages[key]
        self.stack.setCurrentWidget(page)
        self.setWindowTitle(f"{page.title} - {APP_TITLE}")
        for btn, label, k in self._nav_items:
            btn.setProperty("active", "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        QTimer.singleShot(0, lambda: self._safe_refresh(page))

    # -------------------------------------------------------------- avatar
    def refresh_user_avatar(self):
        try:
            from database import db_manager
            new_admin = db_manager.get_admin() or {}
            self.admin.update(new_admin)
        except Exception:
            pass

        pic = self.admin.get("picture", "")

        if hasattr(self, "sidebar_avatar"):
            self.sidebar_avatar.setPixmap(_circular_avatar(pic, 46))

        if hasattr(self, "user_btn"):
            self.user_btn.setIcon(
                _qicon_from_pixmap(_circular_avatar(pic, 22)))