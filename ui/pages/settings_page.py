"""
Settings page - PyQt6 port of C4/app/views/infolayout/profileinfo.php.

Layout:
  col-md-3  :  Profile card (avatar, name, profession, stats)  +  About Me
  col-md-9  :  QTabWidget with tabs, each ending in a Save/action button.
"""
import os
import shutil
from datetime import datetime

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap, QPainter, QPainterPath
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
                             QLabel, QPushButton, QLineEdit, QPlainTextEdit,
                             QFormLayout, QGroupBox, QScrollArea, QFrame,
                             QTabWidget, QFileDialog, QSizePolicy)

from database import db_manager
from ui import widgets as W
from utils.helpers import money


# --------------------------------------------------------------------------- #
# App base folder  +  asset folders
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


APP_BASE   = _app_base_dir()
IMG_DIR    = os.path.join(APP_BASE, "dist", "img")
UPLOAD_DIR = os.path.join(IMG_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


def _resolve_upload(name: str) -> str:
    if not name:
        return ""
    v = str(name).strip().replace("\\", "/")
    base = os.path.basename(v)
    candidate = os.path.join(UPLOAD_DIR, base)
    return candidate if os.path.isfile(candidate) else ""


def _resolve_image(name: str) -> str:
    if not name:
        return ""
    path = os.path.join(IMG_DIR, name)
    return path if os.path.isfile(path) else ""


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _circular_pixmap(path: str, size: int) -> QPixmap:
    pm = QPixmap(path) if path and os.path.isfile(path) else QPixmap()
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


def _big_image_label(image_name: str, size: int = 150,
                     fallback_glyph: str = "") -> QLabel:
    lbl = QLabel()
    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    lbl.setFixedSize(size, size)

    path = _resolve_image(image_name)
    pm = QPixmap(path) if path else QPixmap()
    if not pm.isNull():
        pm = pm.scaled(size, size,
                       Qt.AspectRatioMode.KeepAspectRatio,
                       Qt.TransformationMode.SmoothTransformation)
        lbl.setPixmap(pm)
    else:
        lbl.setText(fallback_glyph or "🖼")
        lbl.setStyleSheet("font-size:64px; color:#999;")
    return lbl


def _edit_overlay_label() -> QLabel:
    lbl = QLabel()
    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    path = _resolve_image("edit.png")
    pm = QPixmap(path) if path else QPixmap()
    if not pm.isNull():
        pm = pm.scaled(24, 24,
                       Qt.AspectRatioMode.KeepAspectRatio,
                       Qt.TransformationMode.SmoothTransformation)
        lbl.setPixmap(pm)
    else:
        lbl.setText("✎")
        lbl.setStyleSheet("color:#3c8dbc; font-size:16px; font-weight:700;")
    lbl.setFixedSize(24, 24)
    return lbl


def _skill_chip(text: str, color: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setStyleSheet(
        f"background:{color}; color:#fff; padding:2px 8px;"
        f"border-radius:3px; font-size:11px; font-weight:600;")
    lbl.setSizePolicy(QSizePolicy.Policy.Maximum,
                      QSizePolicy.Policy.Maximum)
    return lbl


_BTN_COLORS = {
    "btnSuccess": ("#00a65a", "#008d4c", "#ffffff"),
    "btnInfo":    ("#00c0ef", "#00a7d0", "#ffffff"),
    "btnDanger":  ("#dd4b39", "#c23321", "#ffffff"),
    "btnWarning": ("#f39c12", "#e08e0b", "#ffffff"),
    "btnDefault": ("#f4f4f4", "#e7e7e7", "#444444"),
}


def _action_button(text: str, obj_name: str, slot,
                   min_width: int = 180) -> QPushButton:
    bg, hover, fg = _BTN_COLORS.get(obj_name, _BTN_COLORS["btnDefault"])
    b = QPushButton(text)
    b.setObjectName(obj_name)
    b.setMinimumWidth(min_width)
    b.setFixedHeight(36)
    b.setCursor(Qt.CursorShape.PointingHandCursor)
    b.setStyleSheet(
        f"QPushButton#{obj_name} {{"
        f"  background:{bg}; color:{fg}; border:1px solid {bg};"
        f"  border-radius:3px; padding:6px 16px; font-weight:600;"
        f"}}"
        f"QPushButton#{obj_name}:hover {{"
        f"  background:{hover}; border-color:{hover};"
        f"}}"
        f"QPushButton#{obj_name}:pressed {{"
        f"  background:{hover};"
        f"}}"
        f"QPushButton#{obj_name}:disabled {{"
        f"  background:#cfcfcf; border-color:#cfcfcf; color:#888888;"
        f"}}"
    )
    b.clicked.connect(slot)
    return b


class _FlowLayout(QWidget):
    def __init__(self, spacing=6, parent=None):
        super().__init__(parent)
        self._spacing = spacing
        self._items = []
        self.setSizePolicy(QSizePolicy.Policy.Preferred,
                           QSizePolicy.Policy.Minimum)

    def add(self, w: QWidget):
        self._items.append(w)
        w.setParent(self)
        w.show()
        self._relayout()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._relayout()

    def _relayout(self):
        x = y = 0
        row_h = 0
        max_w = max(self.width(), 1)
        for w in self._items:
            ww = w.sizeHint().width()
            wh = w.sizeHint().height()
            if x + ww > max_w and x > 0:
                x = 0
                y += row_h + self._spacing
                row_h = 0
            w.setGeometry(x, y, ww, wh)
            x += ww + self._spacing
            row_h = max(row_h, wh)
        self.setMinimumHeight(y + row_h)


# --------------------------------------------------------------------------- #
# SettingsPage
# --------------------------------------------------------------------------- #
class SettingsPage(QWidget):
    title = "Settings"

    PROFILE_FIELDS = [
        ("Name", "name"),
        ("Email", "email"),
        ("Profession", "profession"),
        ("Qualification", "qualification"),
        ("Location", "location"),
    ]

    COMPANY_FIELDS = [
        ("Company Name", "c_name"),
        ("Company Address", "c_add"),
        ("Mobile", "mob"),
        ("Email", "email"),
        ("GST", "gst"),
        ("PAN", "pan"),
    ]

    BANK_FIELDS = [("Bank Name", "bname"), ("A/c Number", "ac"),
                   ("IFSC Code", "ifsc"), ("Branch", "branch")]

    MAX_BANKS = 2

    def __init__(self, main):
        super().__init__()
        self.main = main
        self._editors = {}
        self._bank_rows = []
        self._picture_name = ""
        self._logo_name = ""

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(6)

        outer.addWidget(W.PageHeader("User Profile",
                                     breadcrumb="User profile"))

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border:none; }")
        outer.addWidget(scroll, 1)

        inner = QWidget()
        scroll.setWidget(inner)

        root = QVBoxLayout(inner)
        root.setContentsMargins(12, 6, 12, 12)
        root.setSpacing(0)

        columns = QHBoxLayout()
        columns.setContentsMargins(0, 0, 0, 0)
        columns.setSpacing(12)
        columns.setAlignment(Qt.AlignmentFlag.AlignTop |
                             Qt.AlignmentFlag.AlignLeft)

        # ---------------- LEFT COLUMN ----------------
        left_host = QWidget()
        left_host.setFixedWidth(280)
        left = QVBoxLayout(left_host)
        left.setContentsMargins(0, 0, 0, 0)
        left.setSpacing(12)
        left.setAlignment(Qt.AlignmentFlag.AlignTop)
        left.addWidget(self._build_profile_card())
        left.addWidget(self._build_about_card())
        left.addStretch()

        columns.addWidget(left_host, 0,
                          Qt.AlignmentFlag.AlignLeft |
                          Qt.AlignmentFlag.AlignTop)

        # ---------------- RIGHT COLUMN ----------------
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #d2d6de;
                background: #ffffff;
                top: -1px;
            }
            QTabBar::tab {
                background: #f4f4f4;
                color: #444;
                border: 1px solid #d2d6de;
                border-bottom: none;
                padding: 0px 14px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background: #ffffff;
                color: #222;
                font-weight: 600;
            }
            QTabBar::tab:hover:!selected {
                background: #eaeaea;
            }
        """)

        self.tabs.addTab(self._wrap_tab(self._build_profile_tab()), "Profile")
        self.tabs.addTab(self._wrap_tab(self._build_company_tab()),
                         "Company Details")
        self.tabs.addTab(self._wrap_tab(self._build_bank_tab()),
                         "Bank Details")
        self.tabs.addTab(self._wrap_tab(self._build_backup_tab()),
                         "Backup & Restore")
        self.tabs.addTab(self._wrap_tab(self._build_password_tab()),
                         "Change Password")

        columns.addWidget(self.tabs, 1,
                          Qt.AlignmentFlag.AlignTop |
                          Qt.AlignmentFlag.AlignVCenter)

        root.addLayout(columns)

        self._load_all()

    # ------------------------------------------------------------------ utils
    @staticmethod
    def _wrap_tab(widget: QWidget) -> QWidget:
        widget.setStyleSheet("background:#ffffff;")
        host = QWidget()
        host.setStyleSheet("background:#ffffff;")
        v = QVBoxLayout(host)
        v.setContentsMargins(0, 0, 0, 0)
        v.addWidget(widget)
        return host

    def _action_row(self, buttons, align=Qt.AlignmentFlag.AlignLeft) -> QWidget:
        host = QWidget()
        host.setMinimumHeight(52)
        host.setStyleSheet("background:transparent;")
        row = QHBoxLayout(host)
        row.setContentsMargins(0, 8, 0, 8)
        row.setSpacing(8)
        if align == Qt.AlignmentFlag.AlignLeft:
            for b in buttons:
                row.addWidget(b)
            row.addStretch()
        else:
            row.addStretch()
            for b in buttons:
                row.addWidget(b)
            row.addStretch()
        return host

    # =====================================================================
    #  LEFT: Profile card
    # =====================================================================
    def _build_profile_card(self) -> QWidget:
        """White card with a blue top strip; interior content sits inside the
        card's padding, so no child draws an edge-to-edge border."""
        card = QFrame()
        card.setObjectName("ProfileCard")
        card.setStyleSheet("""
            QFrame#ProfileCard {
                background: #ffffff;
                border: 1px solid #d2d6de;
                border-radius: 3px;
                border-top: 3px solid #3c8dbc;
            }
            QFrame#ProfileCard QLabel {
                background: transparent;
                border: none;
            }
        """)

        v = QVBoxLayout(card)
        v.setContentsMargins(14, 16, 14, 14)
        v.setSpacing(6)

        # avatar
        self.avatar = QLabel()
        self.avatar.setFixedSize(110, 110)
        self.avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v.addWidget(self.avatar, 0, Qt.AlignmentFlag.AlignHCenter)

        # name + profession
        self.p_name_lbl = QLabel("—")
        self.p_name_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.p_name_lbl.setStyleSheet(
            "font-size:16px; font-weight:700; color:#111;")
        v.addWidget(self.p_name_lbl)

        self.p_prof_lbl = QLabel("")
        self.p_prof_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.p_prof_lbl.setStyleSheet(
            "color:#777; font-size:12.5px;")
        v.addWidget(self.p_prof_lbl)

        v.addSpacing(4)

        # single thin rule, kept inside the padding
        rule = QFrame()
        rule.setFixedHeight(1)
        rule.setStyleSheet("background: #d9d9d9; border: none;")
        v.addWidget(rule)

        v.addSpacing(4)

        # 4 stat rows as a grid: labels left, values right.
        # using QGridLayout on plain QLabels means nothing draws its own border,
        # so the white stays neatly inside the card.
        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(6)
        grid.setVerticalSpacing(10)

        self._stat_value_labels = {}
        for i, (key, name) in enumerate((("clients", "Total Clients"),
                                         ("products", "Products"),
                                         ("sales", "Sales"),
                                         ("purchases", "Purchases"))):
            lbl = QLabel(name)
            lbl.setStyleSheet("color:#333; font-size:13px;")

            val = QLabel("0")
            val.setAlignment(Qt.AlignmentFlag.AlignRight |
                             Qt.AlignmentFlag.AlignVCenter)
            val.setStyleSheet("color:#3c8dbc; font-size:13px;")
            self._stat_value_labels[key] = val

            grid.addWidget(lbl, i, 0)
            grid.addWidget(val, i, 1)
        grid.setColumnStretch(0, 1)

        v.addLayout(grid)
        return card

    # =====================================================================
    #  LEFT: About Me card
    # =====================================================================
    def _build_about_card(self) -> QWidget:
        card = QFrame()
        card.setObjectName("AboutCard")
        card.setStyleSheet("""
            QFrame#AboutCard {
                background: #ffffff;
                border: 1px solid #d2d6de;
                border-radius: 3px;
                border-top: 3px solid #3c8dbc;
            }
            QFrame#AboutCard QLabel {
                background: transparent;
                border: none;
            }
        """)

        v = QVBoxLayout(card)
        v.setContentsMargins(14, 14, 14, 14)
        v.setSpacing(8)

        title = QLabel("About Me")
        title.setStyleSheet(
            "font-size:15px; font-weight:600; color:#3c8dbc;")
        v.addWidget(title)

        rule = QFrame()
        rule.setFixedHeight(1)
        rule.setStyleSheet("background: #d9d9d9; border: none;")
        v.addWidget(rule)

        # Education
        hdr_e = QLabel("\U0001F4D6   Education")
        hdr_e.setStyleSheet("color:#333; font-size:12.5px; font-weight:600;")
        v.addWidget(hdr_e)

        self.a_edu = QLabel("—")
        self.a_edu.setWordWrap(True)
        self.a_edu.setStyleSheet("color:#666; font-size:12.5px;")
        v.addWidget(self.a_edu)

        sep1 = QFrame(); sep1.setFixedHeight(1)
        sep1.setStyleSheet("background: #ececec; border: none;")
        v.addWidget(sep1)

        # Location
        hdr_l = QLabel("\U0001F4CD   Location")
        hdr_l.setStyleSheet("color:#333; font-size:12.5px; font-weight:600;")
        v.addWidget(hdr_l)

        self.a_loc = QLabel("—")
        self.a_loc.setWordWrap(True)
        self.a_loc.setStyleSheet("color:#666; font-size:12.5px;")
        v.addWidget(self.a_loc)

        sep2 = QFrame(); sep2.setFixedHeight(1)
        sep2.setStyleSheet("background: #ececec; border: none;")
        v.addWidget(sep2)

        # Skills
        hdr_s = QLabel("\u270E   Skills")
        hdr_s.setStyleSheet("color:#333; font-size:12.5px; font-weight:600;")
        v.addWidget(hdr_s)

        self._skills_flow = _FlowLayout()
        v.addWidget(self._skills_flow)

        v.addStretch()
        return card

    # =====================================================================
    #  RIGHT: tabs
    # =====================================================================
    def _build_profile_tab(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(12, 12, 12, 12)

        top = QHBoxLayout()
        top.addStretch()
        self.tab_avatar = QLabel()
        self.tab_avatar.setFixedSize(130, 130)
        self.tab_avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        top.addWidget(self.tab_avatar)

        btn_edit = _action_button("Change", "btnDefault",
                                  self._upload_profile_picture,
                                  min_width=120)
        avatar_col = QVBoxLayout()
        avatar_col.addWidget(self.tab_avatar, 0, Qt.AlignmentFlag.AlignHCenter)
        avatar_col.addWidget(_edit_overlay_label(), 0,
                             Qt.AlignmentFlag.AlignHCenter)
        avatar_col.addWidget(btn_edit, 0, Qt.AlignmentFlag.AlignHCenter)
        top.addLayout(avatar_col)
        top.addStretch()
        v.addLayout(top)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setHorizontalSpacing(14)
        form.setVerticalSpacing(10)

        for label, key in self.PROFILE_FIELDS:
            e = QLineEdit()
            form.addRow(f"{label}", e)
            self._editors[key] = e
        v.addLayout(form)

        v.addWidget(self._action_row([
            _action_button("Save Profile", "btnDanger", self._save_profile)
        ]))
        v.addStretch()
        return w

    def _build_company_tab(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(12, 12, 12, 12)

        top = QHBoxLayout()
        top.addStretch()
        self.tab_logo = QLabel()
        self.tab_logo.setFixedSize(130, 130)
        self.tab_logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        top.addWidget(self.tab_logo)

        btn_edit = _action_button("Change Logo", "btnDefault",
                                  self._upload_company_logo, min_width=140)
        col = QVBoxLayout()
        col.addWidget(self.tab_logo, 0, Qt.AlignmentFlag.AlignHCenter)
        col.addWidget(_edit_overlay_label(), 0,
                      Qt.AlignmentFlag.AlignHCenter)
        col.addWidget(btn_edit, 0, Qt.AlignmentFlag.AlignHCenter)
        top.addLayout(col)
        top.addStretch()
        v.addLayout(top)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setHorizontalSpacing(14)
        form.setVerticalSpacing(10)

        for label, key in self.COMPANY_FIELDS:
            if key == "c_add":
                e = QPlainTextEdit()
                e.setFixedHeight(70)
                form.addRow(label, e)
            elif key == "email":
                e = QLineEdit()
                self._editors["company_email"] = e
                form.addRow(label, e)
                continue
            else:
                e = QLineEdit()
                if key in ("gst", "pan"):
                    e.setStyleSheet("text-transform: uppercase;")
                    if key == "gst":
                        e.setMaxLength(15)
                    else:
                        e.setMaxLength(10)
                form.addRow(label, e)
            self._editors[key] = e
        v.addLayout(form)

        v.addWidget(self._action_row([
            _action_button("Save Company Details", "btnDanger",
                           self._save_company, min_width=200)
        ]))
        v.addStretch()
        return w

    def _build_bank_tab(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(12, 12, 12, 12)
        v.setSpacing(10)

        icon = _big_image_label("901425.png", size=150, fallback_glyph="🏦")
        v.addWidget(icon, 0, Qt.AlignmentFlag.AlignHCenter)

        self.bank_container = QVBoxLayout()
        self.bank_container.setSpacing(10)
        v.addLayout(self.bank_container)

        self.add_bank_btn = _action_button("+ Add More Bank", "btnSuccess",
                                           self._add_bank_row, min_width=170)
        v.addWidget(self._action_row([self.add_bank_btn]))

        v.addWidget(self._action_row([
            _action_button("Save Bank Details", "btnDanger",
                           self._save_banks, min_width=180)
        ]))
        v.addStretch()
        return w

    def _build_backup_tab(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(12, 12, 12, 12)
        v.setSpacing(10)

        icon = _big_image_label("Backup-Logo.png", size=150,
                                fallback_glyph="💾")
        v.addWidget(icon, 0, Qt.AlignmentFlag.AlignHCenter)

        one_click = _action_button("One Click Backup", "btnInfo",
                                   self._one_click_backup, min_width=220)
        v.addWidget(self._action_row([one_click],
                                     align=Qt.AlignmentFlag.AlignHCenter))

        self.backup_msg = QLabel("")
        self.backup_msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.backup_msg.setWordWrap(True)
        v.addWidget(self.backup_msg)

        line = QFrame(); line.setFrameShape(QFrame.Shape.HLine)
        v.addWidget(line)

        choose_row = QHBoxLayout()
        choose_row.addWidget(QLabel("Choose Backup File:"))
        self.backup_path = QLineEdit()
        self.backup_path.setReadOnly(True)
        choose_row.addWidget(self.backup_path, 1)
        browse = _action_button("Browse…", "btnDefault",
                                self._choose_backup_file, min_width=120)
        choose_row.addWidget(browse)
        v.addLayout(choose_row)

        restore = _action_button("Restore", "btnDanger",
                                 self._restore_backup, min_width=180)
        v.addWidget(self._action_row([restore],
                                     align=Qt.AlignmentFlag.AlignHCenter))

        v.addStretch()
        return w

    def _build_password_tab(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(12, 12, 12, 12)

        icon = _big_image_label("1234 (1).png", size=150, fallback_glyph="🔒")
        v.addWidget(icon, 0, Qt.AlignmentFlag.AlignHCenter)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setHorizontalSpacing(14)
        form.setVerticalSpacing(10)

        self.pw_user = QLineEdit()
        self.pw_user.setReadOnly(True)
        form.addRow("User Name", self.pw_user)

        self.pw_new = QLineEdit()
        self.pw_new.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("New Password", self.pw_new)

        self.pw_conf = QLineEdit()
        self.pw_conf.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("Confirm Password", self.pw_conf)

        v.addLayout(form)

        v.addWidget(self._action_row([
            _action_button("Save Password", "btnDanger", self._save_password)
        ]))
        v.addStretch()
        return w

    # =====================================================================
    #  Loading data
    # =====================================================================
    def _load_all(self):
        admin = db_manager.get_admin() or {}

        for _, key in self.PROFILE_FIELDS:
            self._editors[key].setText(str(admin.get(key, "") or ""))

        for _, key in self.COMPANY_FIELDS:
            if key == "email":
                self._editors["company_email"].setText(
                    str(admin.get("email", "") or ""))
                continue
            e = self._editors.get(key)
            if isinstance(e, QPlainTextEdit):
                e.setPlainText(str(admin.get(key, "") or ""))
            elif isinstance(e, QLineEdit):
                e.setText(str(admin.get(key, "") or ""))

        self._picture_name = admin.get("picture", "") or ""
        self._refresh_avatar()

        self.p_name_lbl.setText(admin.get("name", "") or "—")
        self.p_prof_lbl.setText(admin.get("profession", "") or "")

        # ---- stats ----
        try:
            stats = db_manager.get_dashboard_stats()
        except Exception:
            stats = {}

        # map card keys to the keys your db_manager returns.
        # change the right-hand side strings if your API uses other names.
        stat_sources = {
            "clients":   stats.get("clients", 0),
            "products":  stats.get("products", 0),
            "sales":     stats.get("sales", stats.get("sales_amount", 0)),
            "purchases": stats.get("purchases",
                                   stats.get("purchase_amount", 0)),
        }
        for key, val in stat_sources.items():
            try:
                if key in ("sales", "purchases"):
                    text = money(val)
                else:
                    text = str(val)
            except Exception:
                text = str(val)
            self._stat_value_labels[key].setText(text)

        self.a_edu.setText(admin.get("qualification", "") or "—")
        self.a_loc.setText(admin.get("location", "") or "—")
        self._render_skills(admin.get("skills", "") or "")

        self.pw_user.setText(admin.get("username", "") or "")

        for row in list(self._bank_rows):
            self._remove_bank_row(row)
        banks = []
        try:
            banks = db_manager.list_bank_details() or []
        except Exception:
            single = db_manager.get_bank_details()
            if single:
                banks = [single]
        if not banks:
            banks = [{}]
        for b in banks[: self.MAX_BANKS]:
            self._add_bank_row(b)
        self._update_add_bank_button()

        self._refresh_logo()

    def _render_skills(self, skills_text: str):
        for w in list(getattr(self._skills_flow, "_items", [])):
            w.setParent(None)
        self._skills_flow._items = []

        tokens = [t.strip() for t in skills_text.replace(",", " ").split()
                  if t.strip()]
        palette = ["#dd4b39", "#00a65a", "#00c0ef",
                   "#f39c12", "#3c8dbc", "#605ca8", "#f56954"]
        for i, t in enumerate(tokens):
            self._skills_flow.add(_skill_chip(t, palette[i % len(palette)]))
        if not tokens:
            self._skills_flow.add(_skill_chip("No skills listed", "#aaa"))

    def _refresh_avatar(self):
        path = _resolve_upload(self._picture_name)
        self.avatar.setPixmap(_circular_pixmap(path, 110))
        self.tab_avatar.setPixmap(_circular_pixmap(path, 130))

    def _refresh_logo(self):
        logo_name = ""
        try:
            admin = db_manager.get_admin() or {}
            logo_name = (
                admin.get("picturelogo", "")
                or admin.get("logo", "")       # keep old fallback, harmless
                or admin.get("c_logo", "")
            )
        except Exception:
            logo_name = ""

        path = _resolve_upload(logo_name)
        pm = QPixmap(path) if path else QPixmap()
        if pm.isNull():
            pm = QPixmap(130, 130)
            pm.fill(Qt.GlobalColor.lightGray)
        pm = pm.scaled(130, 130,
                       Qt.AspectRatioMode.KeepAspectRatio,
                       Qt.TransformationMode.SmoothTransformation)
        self.tab_logo.setPixmap(pm)

        # =====================================================================
    #  Bank rows
    # =====================================================================
    def _add_bank_row(self, data=None):
        if len(self._bank_rows) >= self.MAX_BANKS:
            return
        data = data or {}

        box = QGroupBox(f"Bank #{len(self._bank_rows) + 1}")
        form = QFormLayout(box)
        editors = {}
        for label, key in self.BANK_FIELDS:
            e = QLineEdit(str(data.get(key, "") or ""))
            if key == "ifsc":
                e.setStyleSheet("text-transform: uppercase;")
            form.addRow(label, e)
            editors[key] = e

        row = {"box": box, "editors": editors}
        self._bank_rows.append(row)
        self.bank_container.addWidget(box)
        self._update_add_bank_button()

    def _remove_bank_row(self, row):
        try:
            self._bank_rows.remove(row)
            row["box"].setParent(None)
        except ValueError:
            pass
        self._update_add_bank_button()

    def _update_add_bank_button(self):
        self.add_bank_btn.setEnabled(len(self._bank_rows) < self.MAX_BANKS)

    # =====================================================================
    #  Save handlers
    # =====================================================================
    def _save_profile(self):
        data = {key: self._editors[key].text().strip()
                for _, key in self.PROFILE_FIELDS}
        try:
            db_manager.update_admin(self.main.admin.get("id", 1), data)
            self.main.admin.update(data)
            self.main.name_label.setText(data.get("name", ""))
        except Exception as exc:
            W.error(self, f"Save failed: {exc}")
            return
        self.p_name_lbl.setText(data.get("name") or "—")
        self.p_prof_lbl.setText(data.get("profession") or "")
        self.a_edu.setText(data.get("qualification") or "—")
        self.a_loc.setText(data.get("location") or "—")
        W.info(self, "Profile updated successfully.")

    def _save_company(self):
        data = {}
        for label, key in self.COMPANY_FIELDS:
            if key == "email":
                data[key] = self._editors["company_email"].text().strip()
                continue
            e = self._editors.get(key)
            if isinstance(e, QPlainTextEdit):
                data[key] = e.toPlainText().strip()
            else:
                data[key] = e.text().strip()
        try:
            db_manager.update_admin(self.main.admin.get("id", 1), data)
            self.main.admin.update(data)
        except Exception as exc:
            W.error(self, f"Save failed: {exc}")
            return
        W.info(self, "Company details saved successfully.")

    def _save_banks(self):
        banks = []
        for row in self._bank_rows:
            d = {k: row["editors"][k].text().strip()
                 for _, k in self.BANK_FIELDS}
            if any(d.values()):
                banks.append(d)
        try:
            if hasattr(db_manager, "save_all_bank_details"):
                db_manager.save_all_bank_details(banks)
            else:
                if banks:
                    db_manager.save_bank_details(banks[0])
        except Exception as exc:
            W.error(self, f"Save failed: {exc}")
            return
        W.info(self, "Bank details saved successfully.")

    def _save_password(self):
        new = self.pw_new.text()
        conf = self.pw_conf.text()
        if not new or new != conf:
            W.error(self, "Passwords do not match (or are empty).")
            return
        try:
            db_manager.update_admin(self.main.admin.get("id", 1),
                                    {"password": new})
        except Exception as exc:
            W.error(self, f"Save failed: {exc}")
            return
        self.pw_new.clear()
        self.pw_conf.clear()
        W.info(self, "Password updated successfully.")

    # =====================================================================
    #  Uploads
    # =====================================================================
    def _upload_profile_picture(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Choose profile picture", "",
            "Images (*.png *.jpg *.jpeg *.bmp *.gif)")
        if not path:
            return
        try:
            name = f"avatar_{datetime.now():%Y%m%d%H%M%S}_" + \
                   os.path.basename(path)
            shutil.copy2(path, os.path.join(UPLOAD_DIR, name))
            db_manager.update_admin(self.main.admin.get("id", 1),
                                    {"picture": name})
            self._picture_name = name
            self._refresh_avatar()
            W.info(self, "Profile picture updated.")
        except Exception as exc:
            W.error(self, f"Upload failed: {exc}")

    def _upload_company_logo(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Choose company logo", "",
            "Images (*.png *.jpg *.jpeg *.bmp *.gif)")
        if not path:
            return
        try:
            name = f"logo_{datetime.now():%Y%m%d%H%M%S}_" + \
                   os.path.basename(path)
            shutil.copy2(path, os.path.join(UPLOAD_DIR, name))
            db_manager.update_admin(self.main.admin.get("id", 1),
                                    {"logo": name})
            self._refresh_logo()
            W.info(self, "Company logo updated.")
        except Exception as exc:
            W.error(self, f"Upload failed: {exc}")

    # =====================================================================
    #  Backup / restore
    # =====================================================================
    def _one_click_backup(self):
        try:
            if hasattr(db_manager, "backup_database"):
                out = db_manager.backup_database()
                self.backup_msg.setText(f"Backup created: {out}")
            else:
                self.backup_msg.setText(
                    "Backup API not available in db_manager.")
        except Exception as exc:
            W.error(self, f"Backup failed: {exc}")

    def _choose_backup_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Choose backup file", "", "All files (*)")
        if path:
            self.backup_path.setText(path)

    def _restore_backup(self):
        path = self.backup_path.text().strip()
        if not path:
            W.error(self, "Please choose a backup file first.")
            return
        if not W.confirm(self, f"Restore database from\n{path}\n?"):
            return
        try:
            if hasattr(db_manager, "restore_database"):
                db_manager.restore_database(path)
                W.info(self, "Database restored. Please restart the app.")
            else:
                W.error(self, "Restore API not available in db_manager.")
        except Exception as exc:
            W.error(self, f"Restore failed: {exc}")

    # =====================================================================
    #  Public
    # =====================================================================
    def refresh(self):
        self._load_all()