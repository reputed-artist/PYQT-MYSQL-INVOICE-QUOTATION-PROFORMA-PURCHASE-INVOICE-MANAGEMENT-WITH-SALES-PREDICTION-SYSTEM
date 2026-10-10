"""
Client / Product / Supplier Info pages - port of the CodeIgniter 'Info layout'
views (getclientinfo.php, getproductinfo.php, getsupplierinfo.php).
"""
import os

from PyQt6.QtCore import Qt, QPointF, QByteArray, QEvent
from PyQt6.QtGui import (QPixmap, QPainter, QColor, QPen, QPainterPath,
                         QFont, QIcon)
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QScrollArea, QFrame, QSizePolicy,
                             QHeaderView)

try:
    from PyQt6.QtSvg import QSvgRenderer
    _HAS_SVG = True
except ImportError:
    _HAS_SVG = False

from database import db_manager
from ui import widgets as W
from utils.helpers import money

from ui.pages.master_pages import ExportButtonStrip, _generic_export


# =========================================================================== #
# Qt safety helper — true if the C++ side of a widget still exists
# =========================================================================== #
def _qt_alive(widget):
    """
    Return True if the underlying C++ object still exists.
    Accessing any attribute raises RuntimeError once it has been deleted.
    """
    try:
        _ = widget.objectName()
        return True
    except RuntimeError:
        return False
    except Exception:
        return False


# =========================================================================== #
# ICON HELPERS
# =========================================================================== #
SVG_VIEW = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="#ffffff"><path d="M12 4.5C7 4.5 2.73 7.61 1 12c1.73 4.39 6 7.5 11 7.5s9.27-3.11 11-7.5c-1.73-4.39-6-7.5-11-7.5zM12 17c-2.76 0-5-2.24-5-5s2.24-5 5-5 5 2.24 5 5-2.24 5-5 5zm0-8c-1.66 0-3 1.34-3 3s1.34 3 3 3 3-1.34 3-3-1.34-3-3-3z"/></svg>"""
SVG_EDIT = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="#ffffff"><path d="M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25zM20.71 7.04c.39-.39.39-1.02 0-1.41l-2.34-2.34c-.39-.39-1.02-.39-1.41 0l-1.83 1.83 3.75 3.75 1.83-1.83z"/></svg>"""
SVG_DELETE = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="#ffffff"><path d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z"/></svg>"""

_SVG_MAP = {"view": SVG_VIEW, "edit": SVG_EDIT, "delete": SVG_DELETE}

_BTN_BG = {
    "btnPrimary": "#007bff",
    "btnDanger":  "#dc3545",
    "btnWarning": "#ffc107",
    "btnDefault": "#6c757d",
}
_BTN_HOVER = {
    "btnPrimary": "#0069d9",
    "btnDanger":  "#c82333",
    "btnWarning": "#e0a800",
    "btnDefault": "#5a6268",
}


def _svg_to_icon(svg_str: str, size: int = 16) -> QIcon:
    if not _HAS_SVG:
        return QIcon()
    renderer = QSvgRenderer(QByteArray(svg_str.encode("utf-8")))
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    renderer.render(p)
    p.end()
    return QIcon(pm)


def icon_button(icon_name: str, btn_style: str, tooltip: str = "") -> QPushButton:
    btn = QPushButton()
    btn.setToolTip(tooltip)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    btn.setFixedSize(32, 28)

    svg = _SVG_MAP.get(icon_name.lower())
    if svg:
        btn.setIcon(_svg_to_icon(svg, 16))
        btn.setIconSize(QPixmap(16, 16).size())
    else:
        btn.setText("?")

    bg = _BTN_BG.get(btn_style, _BTN_BG["btnDefault"])
    hv = _BTN_HOVER.get(btn_style, _BTN_HOVER["btnDefault"])

    btn.setStyleSheet(f"""
        QPushButton {{
            background-color: {bg};
            border: none;
            border-radius: 3px;
            padding: 0px;
        }}
        QPushButton:hover {{ background-color: {hv}; }}
        QPushButton:pressed {{ background-color: {hv}; }}
    """)
    return btn


_DONUT_COLORS = [
    "#007bff", "#28a745", "#dc3545", "#ffc107",
    "#17a2b8", "#e83e8c", "#6610f2", "#fd7e14",
]


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
IMG_DIR = os.path.join(APP_BASE, "dist", "img")
UPLOAD_DIR = os.path.join(IMG_DIR, "uploads")


def _circular_pixmap(path: str, size: int) -> QPixmap:
    pm = QPixmap(path) if path and os.path.isfile(path) else QPixmap()
    if pm.isNull():
        fallback = os.path.join(IMG_DIR, "avatar5.png")
        if os.path.isfile(fallback):
            pm = QPixmap(fallback)
    if pm.isNull():
        pm = QPixmap(size, size)
        pm.fill(QColor("#3c8dbc"))

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


def _client_avatar_path(client: dict) -> str:
    pic = (client or {}).get("picture") or ""
    if pic:
        base = os.path.basename(str(pic).replace("\\", "/"))
        candidate = os.path.join(UPLOAD_DIR, base)
        if os.path.isfile(candidate):
            return candidate
    return os.path.join(IMG_DIR, "avatar5.png")


def _product_image_path(product: dict) -> str:
    pic = (product or {}).get("img_loc") or ""
    if pic:
        base = os.path.basename(str(pic).replace("\\", "/"))
        for folder in (UPLOAD_DIR, IMG_DIR):
            candidate = os.path.join(folder, base)
            if os.path.isfile(candidate):
                return candidate
    for name in ("no_image.png", "placeholder.png", "avatar5.png"):
        fallback = os.path.join(IMG_DIR, name)
        if os.path.isfile(fallback):
            return fallback
    return ""


# =========================================================================== #
# Circular-avatar widget-user card (client / supplier)
# =========================================================================== #
class _WidgetUserCard(QFrame):
    HEADER_H = 100
    AVATAR   = 110
    FOOT_H   = 110

    def __init__(self, parent=None):
        super().__init__(parent)
        total_h = self.HEADER_H + self.FOOT_H
        self.setFixedHeight(total_h)
        self.setSizePolicy(QSizePolicy.Policy.Expanding,
                           QSizePolicy.Policy.Fixed)
        self.setMinimumWidth(220)

        self.setObjectName("WidgetUser")
        self.setStyleSheet(
            "QFrame#WidgetUser {"
            "  background: #ffffff;"
            "  border: 1px solid #d2d6de;"
            "  border-radius: 3px;"
            "}")

        self.header = QFrame(self)
        self.header.setObjectName("WidgetUserHeader")
        self.header.setStyleSheet(
            "QFrame#WidgetUserHeader {"
            "  background: #00c0ef;"
            "  border: none;"
            "  border-top-left-radius: 3px;"
            "  border-top-right-radius: 3px;"
            "}")
        hv = QVBoxLayout(self.header)
        hv.setContentsMargins(14, 10, 14, 0)
        hv.setSpacing(2)

        self.name_lbl = QLabel("—")
        self.name_lbl.setStyleSheet(
            "color: #ffffff; font-size: 17px; font-weight: 600;"
            " background: transparent;")
        hv.addWidget(self.name_lbl)

        self.since_lbl = QLabel("")
        self.since_lbl.setStyleSheet(
            "color: #f0f8ff; font-size: 12px; background: transparent;")
        hv.addWidget(self.since_lbl)
        hv.addStretch()

        self.footer = QFrame(self)
        self.footer.setObjectName("WidgetUserFooter")
        self.footer.setStyleSheet(
            "QFrame#WidgetUserFooter {"
            "  background: #ffffff;"
            "  border: none;"
            "  border-bottom-left-radius: 3px;"
            "  border-bottom-right-radius: 3px;"
            "}")

        fl = QHBoxLayout(self.footer)
        fl.setContentsMargins(0, self.AVATAR // 2, 0, 10)
        fl.setSpacing(0)

        self._stat_values: list[QLabel] = []
        self._stat_caps: list[QLabel] = []

        for i in range(3):
            block = QFrame()
            block.setStyleSheet(
                "QFrame { background: transparent;"
                + (" border-right: 1px solid #f4f4f4;" if i < 2 else "")
                + " }")
            bv = QVBoxLayout(block)
            bv.setContentsMargins(4, 6, 4, 6)
            bv.setSpacing(6)

            val = QLabel("0")
            val.setAlignment(Qt.AlignmentFlag.AlignCenter)
            val.setStyleSheet(
                "font-size: 17px; font-weight: 700; color: #333;"
                " background: transparent;")
            val.setMinimumWidth(80)
            val.setSizePolicy(QSizePolicy.Policy.Expanding,
                              QSizePolicy.Policy.Preferred)
            bv.addWidget(val)

            cap = QLabel("")
            cap.setAlignment(Qt.AlignmentFlag.AlignCenter)
            cap.setStyleSheet(
                "font-size: 10px; font-weight: 600; color: #999;"
                " letter-spacing: 0.5px; background: transparent;")
            bv.addWidget(cap)

            self._stat_values.append(val)
            self._stat_caps.append(cap)
            fl.addWidget(block, 1)

        self.avatar_lbl = QLabel(self)
        self.avatar_lbl.setFixedSize(self.AVATAR, self.AVATAR)
        self.avatar_lbl.setStyleSheet(
            "background: transparent; border: none;")

        self._layout_children()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._layout_children()

    def showEvent(self, event):
        super().showEvent(event)
        self._layout_children()

    def _layout_children(self):
        w = self.width()
        self.header.setGeometry(0, 0, w, self.HEADER_H)
        self.footer.setGeometry(0, self.HEADER_H, w, self.FOOT_H)
        ax = (w - self.AVATAR) // 2
        ay = self.HEADER_H - self.AVATAR // 2
        self.avatar_lbl.move(ax, ay)
        self.avatar_lbl.raise_()

    def set_name(self, name: str):
        self.name_lbl.setText(name or "—")

    def set_since(self, text: str):
        self.since_lbl.setText(text or "")

    def set_avatar(self, path: str):
        self.avatar_lbl.setPixmap(_circular_pixmap(path, self.AVATAR))
        self._layout_children()

    def set_stat(self, index: int, value, caption: str):
        self._stat_values[index].setText(str(value))
        self._stat_caps[index].setText(str(caption).upper())


# =========================================================================== #
# Rectangular-image widget-user card (product)
# =========================================================================== #
class _ProductUserCard(QFrame):
    """
    Product widget-user card.

    Layout:
        ┌─────────────────────────┐
        │  cyan header            │  HEADER_H  = 90
        │   name + since          │
        ├─────────────────────────┤  image top = HEADER_H + IMG_TOP_GAP
        │      [ yellow image ]   │  IMG_H     = 160
        ├─────────────────────────┤  image bottom = top + IMG_H
        │  SALES | PROD | INVOICE │  FOOT_H    = 110
        └─────────────────────────┘
    """
    HEADER_H = 90
    IMG_W = 240
    IMG_H = 160
    IMG_TOP_GAP = 12
    IMG_RIGHT_SHIFT = 18
    FOOT_H = 110

    def __init__(self, parent=None):
        super().__init__(parent)
        total_h = (self.HEADER_H
                   + self.IMG_TOP_GAP
                   + self.IMG_H
                   + self.FOOT_H
                   + 8)
        self.setFixedHeight(total_h)
        self.setSizePolicy(QSizePolicy.Policy.Expanding,
                           QSizePolicy.Policy.Fixed)
        self.setMinimumWidth(300)

        self.setObjectName("WidgetUser")
        self.setStyleSheet(
            "QFrame#WidgetUser {"
            "  background: #ffffff;"
            "  border: 1px solid #d2d6de;"
            "  border-radius: 3px;"
            "}")

        # ---------- cyan header ----------
        self.header = QFrame(self)
        self.header.setObjectName("WidgetUserHeader")
        self.header.setStyleSheet(
            "QFrame#WidgetUserHeader {"
            "  background: #00c0ef;"
            "  border: none;"
            "  border-top-left-radius: 3px;"
            "  border-top-right-radius: 3px;"
            "}")
        hv = QVBoxLayout(self.header)
        hv.setContentsMargins(14, 10, 14, 0)
        hv.setSpacing(2)

        self.name_lbl = QLabel("—")
        self.name_lbl.setStyleSheet(
            "color: #ffffff; font-size: 17px; font-weight: 600;"
            " background: transparent;")
        hv.addWidget(self.name_lbl)

        self.since_lbl = QLabel("")
        self.since_lbl.setStyleSheet(
            "color: #f0f8ff; font-size: 12px; background: transparent;")
        hv.addWidget(self.since_lbl)
        hv.addStretch()

        # ---------- white footer with 3 stats ----------
        self.footer = QFrame(self)
        self.footer.setObjectName("WidgetUserFooter")
        self.footer.setStyleSheet(
            "QFrame#WidgetUserFooter {"
            "  background: #ffffff;"
            "  border: none;"
            "  border-bottom-left-radius: 3px;"
            "  border-bottom-right-radius: 3px;"
            "}")

        fl = QHBoxLayout(self.footer)
        fl.setContentsMargins(0, 8, 0, 10)
        fl.setSpacing(0)

        self._stat_values: list[QLabel] = []
        self._stat_caps: list[QLabel] = []

        for i in range(3):
            block = QFrame()
            block.setStyleSheet(
                "QFrame { background: transparent;"
                + (" border-right: 1px solid #f4f4f4;" if i < 2 else "")
                + " }")
            bv = QVBoxLayout(block)
            bv.setContentsMargins(4, 6, 4, 6)
            bv.setSpacing(6)

            val = QLabel("0")
            val.setAlignment(Qt.AlignmentFlag.AlignCenter)
            val.setStyleSheet(
                "font-size: 17px; font-weight: 700; color: #333;"
                " background: transparent;")
            val.setMinimumWidth(80)
            val.setSizePolicy(QSizePolicy.Policy.Expanding,
                              QSizePolicy.Policy.Preferred)
            bv.addWidget(val)

            cap = QLabel("")
            cap.setAlignment(Qt.AlignmentFlag.AlignCenter)
            cap.setStyleSheet(
                "font-size: 10px; font-weight: 600; color: #999;"
                " letter-spacing: 0.5px; background: transparent;")
            bv.addWidget(cap)

            self._stat_values.append(val)
            self._stat_caps.append(cap)
            fl.addWidget(block, 1)

        # ---------- rectangular image thumbnail ----------
        self.image_lbl = QLabel(self)
        self.image_lbl.setFixedSize(self.IMG_W, self.IMG_H)
        self.image_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_lbl.setStyleSheet(
            "background: #ffd966;"
            " border: 1px solid #d2d6de;"
            " padding: 4px;")

        self._layout_children()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._layout_children()

    def showEvent(self, event):
        super().showEvent(event)
        self._layout_children()

    def _layout_children(self):
        """Position header, image, and footer without overlap."""
        w = self.width()

        # ---- header (top strip) ----
        self.header.setGeometry(0, 0, w, self.HEADER_H)

        # ---- image (below header, shifted right a bit) ----
        img_top = self.HEADER_H + self.IMG_TOP_GAP
        ax = (w - self.IMG_W) // 2 + self.IMG_RIGHT_SHIFT
        ax = max(6, min(ax, w - self.IMG_W - 6))
        self.image_lbl.move(ax, img_top)

        # ---- footer (below the image) ----
        foot_top = img_top + self.IMG_H + 4
        self.footer.setGeometry(0, foot_top, w, self.FOOT_H)

        self.image_lbl.raise_()

    # ---- public API ----
    def set_name(self, name: str):
        self.name_lbl.setText(name or "—")

    def set_since(self, text: str):
        self.since_lbl.setText(text or "")

    def set_image(self, path: str):
        if path and os.path.isfile(path):
            pm = QPixmap(path)
            if not pm.isNull():
                pm = pm.scaled(
                    self.IMG_W - 12, self.IMG_H - 12,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation)
                self.image_lbl.setPixmap(pm)
            else:
                self.image_lbl.setText("No image")
        else:
            self.image_lbl.setText("No image")
        self._layout_children()

    def set_stat(self, index: int, value, caption: str):
        self._stat_values[index].setText(str(value))
        self._stat_caps[index].setText(str(caption).upper())


# =========================================================================== #
# Donut chart
# =========================================================================== #
class _DonutChart(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.slices: list[tuple[str, float]] = []
        self.setSizePolicy(QSizePolicy.Policy.Expanding,
                           QSizePolicy.Policy.Expanding)
        self.setStyleSheet("background: #ffffff; border: none;")

    def set_data(self, data):
        self.slices = [(str(l), float(v or 0)) for l, v in (data or [])]
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        w, h = self.width(), self.height()

        legend_rows = max(1, (len(self.slices) + 2) // 3)
        legend_h = legend_rows * 20 + 12
        pie_area = max(80, h - legend_h - 8)

        data = [(l, v) for l, v in self.slices if v > 0]
        total = sum(v for _, v in data)

        if not data or total <= 0:
            p.setPen(QColor("#888"))
            f = p.font(); f.setPointSize(10); p.setFont(f)
            p.drawText(0, 0, w, h, Qt.AlignmentFlag.AlignCenter,
                       "No data available")
            p.end()
            return

        size = int(min(w - 20, pie_area - 8) * 0.82)
        cx, cy = w // 2, pie_area // 2 + 2
        outer = size
        inner = int(size * 0.55)

        start = 90 * 16
        for i, (label, value) in enumerate(data):
            span = int(value / total * 360 * 16)
            color = QColor(_DONUT_COLORS[i % len(_DONUT_COLORS)])
            p.setBrush(color)
            p.setPen(Qt.PenStyle.NoPen)
            p.drawPie(cx - outer // 2, cy - outer // 2,
                      outer, outer, start, -span)
            start -= span

        p.setBrush(QColor("#ffffff"))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QPointF(cx, cy), inner / 2, inner / 2)

        if data:
            fy_first = str(data[0][0])
            f = p.font(); f.setPointSize(11); f.setBold(True)
            p.setFont(f); p.setPen(QColor("#333"))
            fm = p.fontMetrics()
            tw = fm.horizontalAdvance(fy_first)
            p.drawText(cx - tw // 2, cy - 4, fy_first)

            f.setPointSize(10); f.setBold(False)
            p.setFont(f); p.setPen(QColor("#555"))
            tot_txt = str(int(total))
            tw = fm.horizontalAdvance(tot_txt)
            p.drawText(cx - tw // 2, cy + 14, tot_txt)

        cols = 3
        col_w = max(1, w // cols)
        f = p.font(); f.setPointSize(8); f.setBold(False)
        p.setFont(f)
        for i, (label, value) in enumerate(data):
            col = i % cols
            row = i // cols
            lx = 10 + col * col_w
            ly = pie_area + 6 + row * 20
            color = _DONUT_COLORS[i % len(_DONUT_COLORS)]

            p.setBrush(QColor(color))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRect(lx, ly + 4, 9, 9)

            p.setPen(QColor("#555"))
            p.drawText(lx + 14, ly, col_w - 18, 16,
                       Qt.AlignmentFlag.AlignLeft |
                       Qt.AlignmentFlag.AlignVCenter,
                       str(label))
        p.end()


# =========================================================================== #
# AdminLTE box with a bordered header
# =========================================================================== #
class _AdminBox(QFrame):
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setObjectName("AdminBox")
        self.setStyleSheet(
            "QFrame#AdminBox {"
            "  background: #ffffff;"
            "  border: 1px solid #d2d6de;"
            "  border-top: 3px solid #00c0ef;"
            "  border-radius: 3px;"
            "}")

        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)

        head = QFrame()
        head.setObjectName("AdminBoxHeader")
        head.setFixedHeight(38)
        head.setStyleSheet(
            "QFrame#AdminBoxHeader {"
            "  background: #ffffff;"
            "  border: none;"
            "  border-bottom: 1px solid #f4f4f4;"
            "}")
        hl = QHBoxLayout(head)
        hl.setContentsMargins(12, 0, 12, 0)
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(
            "font-size: 15px; font-weight: 600; color: #444;"
            " background: transparent;")
        hl.addWidget(title_lbl)
        hl.addStretch()
        v.addWidget(head)

        self.body = QVBoxLayout()
        self.body.setContentsMargins(10, 8, 10, 8)
        self.body.setSpacing(6)
        v.addLayout(self.body, 1)

    def add(self, w, stretch=0):
        self.body.addWidget(w, stretch)

    def addLayout(self, l, stretch=0):
        self.body.addLayout(l, stretch)


# =========================================================================== #
# Helpers
# =========================================================================== #
def _info_row(label: str, value) -> QLabel:
    text = value if value not in (None, "") else "-"
    lbl = QLabel(f"<strong>{label}: </strong> {text}")
    lbl.setWordWrap(True)
    lbl.setStyleSheet("color: #333; font-size: 13px;"
                      " background: transparent;")
    return lbl


def _fmt_int(v) -> str:
    """Format a numeric-ish value as a plain integer string."""
    if v in (None, ""):
        return "0"
    try:
        return f"{float(v):g}"
    except (TypeError, ValueError):
        return str(v)


# =========================================================================== #
# PercentageColumnTable — full-width, no horizontal scrollbar
# =========================================================================== #
class _PercentageTable(W.DataTable):
    ACTIONS_MIN_WIDTH = 130

    def __init__(self, headers, ratios, parent=None):
        super().__init__(headers, parent)
        self._ratios = list(ratios)

        header = self.horizontalHeader()
        header.setStretchLastSection(False)

        for col in range(len(headers)):
            header.setSectionResizeMode(
                col, QHeaderView.ResizeMode.Fixed)

        self.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        self.installEventFilter(self)

    def _apply_ratios(self):
        vw = self.viewport().width()
        if vw <= 0:
            return

        total_cols = len(self._ratios)

        actions_w = min(self.ACTIONS_MIN_WIDTH, vw // 3)
        available = vw - actions_w
        if available <= 0:
            available = vw

        ratio_sum = sum(self._ratios)
        if ratio_sum <= 0:
            ratio_sum = 1

        used = 0
        for i, r in enumerate(self._ratios):
            col_w = max(20, int(available * r / ratio_sum))
            if i == total_cols - 1:
                col_w = max(20, available - used)
            else:
                used += col_w
            self.setColumnWidth(i, col_w)

        self.setColumnWidth(total_cols - 1, actions_w)

    def showEvent(self, event):
        super().showEvent(event)
        self._apply_ratios()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._apply_ratios()

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.Show:
            self._apply_ratios()
        return super().eventFilter(obj, event)


# =========================================================================== #
# InfoPage (client / supplier) — with automatic product redirect
# =========================================================================== #
INFO_HEADERS = ["Sr No", "Invoice Id", "Company Name", "Location",
                "Item Name", "Amount", "Created", "Actions"]

INFO_RATIOS = [10, 25, 35, 35, 45, 25, 20]


class InfoPage(QWidget):
    KIND_TITLE = {"client": "Client Details", "product": "Product Details",
                  "supplier": "Supplier Details"}
    LIST_KEY = {"client": "clients", "supplier": "suppliers",
                "product": "products"}
    KIND_CRUMB = {"client": "Client Details", "product": "Product Details",
                  "supplier": "Suppliers Details"}

    def __new__(cls, main, kind, info_id):
        """
        When kind == 'product', transparently return a ProductInfoPage
        so the product layout works even if the caller still constructs
        InfoPage(...) directly.
        """
        if cls is InfoPage and kind == "product":
            return super().__new__(ProductInfoPage)
        return super().__new__(cls)

    def __init__(self, main, kind, info_id):
        super().__init__()
        self.main = main
        self.kind = kind
        self.info_id = info_id
        self.title = self.KIND_TITLE[kind]
        self.data = None
        self._docs = []
        # store references to any opened invoice preview dialogs
        self._view_windows = []
        self._build()
        self.refresh()

    def _build(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(
            "QScrollArea { border: none; background: transparent; }")
        outer.addWidget(scroll, 1)

        inner = QWidget()
        inner.setStyleSheet("background: transparent;")
        scroll.setWidget(inner)
        v = QVBoxLayout(inner)
        v.setContentsMargins(14, 12, 14, 14)
        v.setSpacing(12)

        v.addWidget(W.PageHeader(self.title,
                                 breadcrumb=self.KIND_CRUMB[self.kind]))
        self.sub_label = QLabel("")
        self.sub_label.setObjectName("PageSubtitle")
        v.addWidget(self.sub_label)

        top = QHBoxLayout()
        top.setSpacing(12)
        top.setAlignment(Qt.AlignmentFlag.AlignTop)

        CARD_HEIGHT = 220

        self._user_card = _WidgetUserCard()
        self._user_card.setFixedHeight(CARD_HEIGHT)
        self._user_card.setSizePolicy(QSizePolicy.Policy.Expanding,
                                      QSizePolicy.Policy.Fixed)
        top.addWidget(self._user_card, 1)

        details_title = {"client": "Client Information",
                         "supplier": "Supplier Information",
                         "product": "Technical Information"}[self.kind]
        self.details_box = _AdminBox(details_title)
        self.details_box.setFixedHeight(CARD_HEIGHT)
        self.details_box.setSizePolicy(QSizePolicy.Policy.Expanding,
                                       QSizePolicy.Policy.Fixed)

        details_scroll = QScrollArea()
        details_scroll.setWidgetResizable(True)
        details_scroll.setFrameShape(QFrame.Shape.NoFrame)
        details_scroll.setStyleSheet(
            "QScrollArea { background: transparent; border: none; }")

        details_content = QWidget()
        details_content.setStyleSheet("background: transparent;")
        self.details_body = QVBoxLayout(details_content)
        self.details_body.setContentsMargins(0, 0, 0, 0)
        self.details_body.setSpacing(4)
        details_scroll.setWidget(details_content)

        self.details_box.add(details_scroll, 1)
        top.addWidget(self.details_box, 1)

        summary_title = ("Yearly Sold Item Count" if self.kind == "product"
                         else "Turnover as per FY")
        self.summary_box = _AdminBox(summary_title)
        self.summary_box.setFixedHeight(CARD_HEIGHT)
        self.summary_box.setSizePolicy(QSizePolicy.Policy.Expanding,
                                       QSizePolicy.Policy.Fixed)
        self.summary_chart = _DonutChart()
        self.summary_box.add(self.summary_chart, 1)
        top.addWidget(self.summary_box, 1)

        v.addLayout(top)

        for doc, box_title in db_manager.INFO_DOCS[self.kind]:
            box = _AdminBox(box_title)

            export_strip = ExportButtonStrip(
                self, on_export=(lambda k, d=doc: self._on_export(d, k)))
            box.add(export_strip, 0)

            table = _PercentageTable(list(INFO_HEADERS), INFO_RATIOS)
            table.setMinimumHeight(180)

            try:
                table.verticalHeader().setDefaultSectionSize(36)
            except Exception:
                pass

            box.add(table, 1)

            foot = QFrame()
            foot.setStyleSheet(
                "QFrame { background: #ffffff;"
                " border: none; border-top: 1px solid #f4f4f4; }")
            fl = QHBoxLayout(foot)
            fl.setContentsMargins(6, 4, 6, 4)

            page = W.Paginator(on_change=(lambda d=doc: self._render_doc(d)))
            fl.addWidget(page, 1)

            totals = QLabel("")
            totals.setStyleSheet(
                "font-weight: 600; color: #444; font-size: 12px;"
                " background: transparent;")
            fl.addWidget(totals, 0, Qt.AlignmentFlag.AlignRight)

            box.add(foot, 0)
            v.addWidget(box)
            self._docs.append([doc, table, page, [], totals])

        v.addStretch()

    def refresh(self):
        loader = {"client": db_manager.client_info,
                  "supplier": db_manager.supplier_info,
                  "product": db_manager.product_info}[self.kind]
        try:
            self.data = loader(self.info_id)
        except Exception as exc:
            W.error(self, f"Database error: {exc}")
            return

        self._fill_user_card()
        self._fill_details()
        self._fill_summary()
        for entry in self._docs:
            doc = entry[0]
            entry[3] = (self.data or {}).get("invoices", {}).get(doc, [])
            self._render_doc(doc)

    def _fill_user_card(self):
        if not self.data:
            return
        d = self.data["details"]

        if self.kind == "product":
            self._user_card.set_name(d.get("name") or "—")
            self._user_card.set_since(f"Created {d.get('created') or ''}")
            self._user_card.set_stat(0, f"{self.data['total_sold']:g}", "Sold")
            self._user_card.set_stat(1, d.get("p_type") or "—", "Type")
            self._user_card.set_stat(2, d.get("hsn") or "—", "HSN")
            self._user_card.set_avatar(
                _client_avatar_path({"picture": d.get("img_loc")}))
        else:
            self._user_card.set_name(d.get("c_name") or "—")
            self._user_card.set_since(f"Since {d.get('created') or ''}")
            self._user_card.set_stat(
                0, money(self.data.get("total_amount", 0)), "Sales")
            self._user_card.set_stat(
                1,
                str(self.data.get("total_items",
                                  self.data.get("total_invoices", 0))),
                "Products")
            self._user_card.set_stat(
                2, d.get("invid") or str(self.data.get("total_invoices", 0)),
                "Invoice")
            self._user_card.set_avatar(_client_avatar_path(d))

    def _fill_details(self):
        self._clear_layout(self.details_body)
        if not self.data:
            self.sub_label.setText("Record not found.")
            self.details_body.addWidget(
                QLabel("No details available for this record."))
            return

        d = self.data["details"]
        if self.kind == "product":
            tech = self.data.get("tech") or []
            specs = ", ".join(str(t.get("techs") or "").strip()
                              for t in tech if (t.get("techs") or "").strip())
            rows = [("Name", d.get("name")), ("HSN", d.get("hsn")),
                    ("Description", d.get("description")),
                    ("Product Type", d.get("p_type")),
                    ("Technical Information",
                     specs or "No technical details available")]
            self.sub_label.setText(
                f"{d.get('name') or ''}  |  {self.data['total_sold']:g}"
                f" item(s) sold  |  Created {d.get('created') or ''}")
        else:
            u_type = {0: "Client", 1: "Supplier",
                      2: "Dual (Client/Supplier)"}.get(d.get("u_type"),
                                                       "Unknown Type")
            rows = [("Name", d.get("c_name")), ("Address", d.get("c_add")),
                    ("Mob", d.get("mob")), ("GST No.", d.get("gst")),
                    ("Bill Type", d.get("c_type")), ("User Type", u_type),
                    ("Nationality", d.get("country"))]
            self.sub_label.setText(
                f"#{d.get('cid')}  |  {self.data['total_invoices']} invoice(s)"
                f"  |  Total {money(self.data['total_amount'])}")

        for label, value in rows:
            self.details_body.addWidget(_info_row(label, value))

    @staticmethod
    def _clear_layout(layout):
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)
            elif item.layout() is not None:
                InfoPage._clear_layout(item.layout())

    def _fill_summary(self):
        rows = ((self.data or {}).get("yearly", []) if self.kind == "product"
                else (self.data or {}).get("fy", []))
        chart_data = []
        for r in rows:
            if self.kind == "product":
                chart_data.append((str(r.get("fy")),
                                   float(r.get("quantity") or 0)))
            else:
                chart_data.append((str(r.get("fy")),
                                   float(r.get("amount") or 0)))
        self.summary_chart.set_data(chart_data)

    def _render_doc(self, doc):
        for entry in self._docs:
            if entry[0] != doc:
                continue
            _, table, page, rows, totals_label = entry
            page._preserve_current = True
            page._refresh_total(len(rows))
            start, end = page.page_range()
            page_rows = rows[start:end]

            table.clear_rows()
            page_total = 0.0
            for i, r in enumerate(page_rows):
                row = table.add_row(
                    [start + i + 1, r["invid"], r["c_name"] or "",
                     r["location"] or "", (r["item_name"] or "")[:80],
                     money(r["totalamount"]), str(r["created"])],
                    data=r["orderid"])
                page_total += float(r["totalamount"] or 0)

                cell = QWidget()
                h = QHBoxLayout(cell)
                h.setContentsMargins(2, 2, 2, 2)
                h.setSpacing(4)

                vb = icon_button("view", "btnPrimary", "View")
                vb.clicked.connect(
                    lambda _, rec=r, d=doc: self._view(d, rec))
                h.addWidget(vb)

                eb = icon_button("edit", "btnDanger", "Edit")
                eb.clicked.connect(
                    lambda _, rec=r, d=doc: self._edit(d, rec))
                h.addWidget(eb)

                db = icon_button("delete", "btnWarning", "Delete")
                db.clicked.connect(
                    lambda _, rec=r, d=doc: self._delete(d, rec))
                h.addWidget(db)

                h.addStretch()
                table.setCellWidget(row, 7, cell)

            table.apply_totals_row([None, None, None, None, None,
                                    money(page_total), "", ""])
            overall = sum(float(x["totalamount"] or 0) for x in rows)
            totals_label.setText(
                f"{len(rows)} records  |  Total: {money(overall)}")

    def _on_export(self, doc, kind):
        all_rows = (self.data or {}).get("invoices", {}).get(doc, []) or []

        columns = [
            ("invid", "Invoice Id"),
            ("c_name", "Company Name"),
            ("location", "Location"),
            ("item_name", "Item Name"),
            ("totalamount", "Amount"),
            ("created", "Created"),
        ]

        sql_cols = ["invid", "c_name", "location", "item_name",
                    "totalamount", "created"]

        doc_label = db_manager.DOC_REGISTRY[doc]["label"].lower() \
            .replace(" ", "_")
        stub = f"{doc_label}_{self.kind}_{self.info_id}"

        registry_entry = db_manager.DOC_REGISTRY[doc]
        if isinstance(registry_entry, dict):
            sql_table = registry_entry.get("table", doc)
        else:
            sql_table = doc

        _generic_export(
            self, kind, all_rows, columns,
            filename_stub=stub,
            sql_table=sql_table,
            sql_cols=sql_cols)

    # ------------------------------------------------------------------ view
    def _view(self, doc, r):
        """
        Open the invoice preview dialog.

        The first call after login can trigger lazy-init of heavy Qt
        subsystems (WebEngine / print support). Those are pre-warmed in
        main.py so the first click never crashes the process.

        Stale dialog references are pruned so we never touch already-
        deleted C++ objects on subsequent opens.
        """
        import traceback
        from utils import invoice_print

        try:
            master, items = db_manager.get_invoice(doc, r["orderid"])
        except Exception as exc:
            W.error(self, f"Load failed: {exc}")
            return

        # Prune closed/destroyed dialogs before opening a new one.
        self._view_windows = [w for w in getattr(self, "_view_windows", [])
                              if _qt_alive(w)]

        try:
            dlg = invoice_print.show_invoice_view(
                self, doc, master, items,
                title=f"{db_manager.DOC_REGISTRY[doc]['label']} {r['invid']}")
        except Exception:
            # Never let a preview failure take the whole app down.
            try:
                with open("view_crash.log", "a", encoding="utf-8") as f:
                    f.write("=" * 60 + "\n")
                    traceback.print_exc(file=f)
            except Exception:
                pass
            traceback.print_exc()
            W.error(self, "Could not open preview (see view_crash.log).")
            return

        if dlg is not None:
            try:
                dlg.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
                dlg.destroyed.connect(
                    lambda *_: self._prune_views())
            except Exception:
                pass
            self._view_windows.append(dlg)

    def _prune_views(self):
        self._view_windows = [w for w in getattr(self, "_view_windows", [])
                              if _qt_alive(w)]

    def _edit(self, doc, r):
        from ui.pages.invoice_pages import InvoiceGenPage
        page = InvoiceGenPage(self.main, doc, edit_orderid=r["orderid"])
        key = f"edit_{doc}_{r['orderid']}"
        self.main._pages[key] = page
        self.main.stack.addWidget(page)
        self.main.stack.setCurrentWidget(page)

    def _delete(self, doc, r):
        label = db_manager.DOC_REGISTRY[doc]["label"]
        if not W.confirm(self, f"Delete {label} {r['invid']}?"):
            return
        try:
            db_manager.delete_invoice(doc, r["orderid"])
        except Exception as exc:
            W.error(self, f"Delete failed: {exc}")
            return
        self.refresh()


# =========================================================================== #
# ProductInfoPage — matches getproductinfo.php
# =========================================================================== #
class ProductInfoPage(InfoPage):
    """
    Product-specific layout:
      ┌──────────────────────┬───────────────────────┬───────────────────────┐
      │ widget-user          │ Technical Information │ Yearly Sold Item Count│
      │  name + Since date   │  product name (bold)  │  donut + legend       │
      │  [rectangular image] │  • spec 1             │                       │
      │  SALES|PRODUCTS|INV  │  • spec 2             │                       │
      └──────────────────────┴───────────────────────┴───────────────────────┘
    """

    def _build(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(
            "QScrollArea { border: none; background: transparent; }")
        outer.addWidget(scroll, 1)

        inner = QWidget()
        inner.setStyleSheet("background: transparent;")
        scroll.setWidget(inner)
        v = QVBoxLayout(inner)
        v.setContentsMargins(14, 12, 14, 14)
        v.setSpacing(12)

        v.addWidget(W.PageHeader(self.title,
                                 breadcrumb=self.KIND_CRUMB[self.kind]))
        self.sub_label = QLabel("")
        self.sub_label.setObjectName("PageSubtitle")
        v.addWidget(self.sub_label)

        top = QHBoxLayout()
        top.setSpacing(12)
        top.setAlignment(Qt.AlignmentFlag.AlignTop)

        CARD_HEIGHT = 380

        # (a) product widget-user card
        self._user_card = _ProductUserCard()
        self._user_card.setFixedHeight(CARD_HEIGHT)
        self._user_card.setSizePolicy(QSizePolicy.Policy.Expanding,
                                      QSizePolicy.Policy.Fixed)
        top.addWidget(self._user_card, 1)

        # (b) Technical Information
        self.details_box = _AdminBox("Technical Information")
        self.details_box.setFixedHeight(CARD_HEIGHT)
        self.details_box.setSizePolicy(QSizePolicy.Policy.Expanding,
                                       QSizePolicy.Policy.Fixed)

        ti_scroll = QScrollArea()
        ti_scroll.setWidgetResizable(True)
        ti_scroll.setFrameShape(QFrame.Shape.NoFrame)
        ti_scroll.setStyleSheet(
            "QScrollArea { background: transparent; border: none; }")

        ti_content = QWidget()
        ti_content.setStyleSheet("background: transparent;")
        self.details_body = QVBoxLayout(ti_content)
        self.details_body.setContentsMargins(0, 0, 0, 0)
        self.details_body.setSpacing(6)
        ti_scroll.setWidget(ti_content)

        self.details_box.add(ti_scroll, 1)
        top.addWidget(self.details_box, 1)

        # (c) Yearly Sold Item Count
        self.summary_box = _AdminBox("Yearly Sold Item Count")
        self.summary_box.setFixedHeight(CARD_HEIGHT)
        self.summary_box.setSizePolicy(QSizePolicy.Policy.Expanding,
                                       QSizePolicy.Policy.Fixed)
        self.summary_chart = _DonutChart()
        self.summary_box.add(self.summary_chart, 1)
        top.addWidget(self.summary_box, 1)

        v.addLayout(top)

        for doc, box_title in db_manager.INFO_DOCS[self.kind]:
            box = _AdminBox(box_title)

            export_strip = ExportButtonStrip(
                self, on_export=(lambda k, d=doc: self._on_export(d, k)))
            box.add(export_strip, 0)

            table = _PercentageTable(list(INFO_HEADERS), INFO_RATIOS)
            table.setMinimumHeight(180)

            try:
                table.verticalHeader().setDefaultSectionSize(36)
            except Exception:
                pass

            box.add(table, 1)

            foot = QFrame()
            foot.setStyleSheet(
                "QFrame { background: #ffffff;"
                " border: none; border-top: 1px solid #f4f4f4; }")
            fl = QHBoxLayout(foot)
            fl.setContentsMargins(6, 4, 6, 4)

            page = W.Paginator(on_change=(lambda d=doc: self._render_doc(d)))
            fl.addWidget(page, 1)

            totals = QLabel("")
            totals.setStyleSheet(
                "font-weight: 600; color: #444; font-size: 12px;"
                " background: transparent;")
            fl.addWidget(totals, 0, Qt.AlignmentFlag.AlignRight)

            box.add(foot, 0)
            v.addWidget(box)
            self._docs.append([doc, table, page, [], totals])

        v.addStretch()

    # ------------------------------------------------------------------ data
    def _fill_user_card(self):
        """
        Product card stats. Falls back through several key names so it
        works regardless of the loader's exact output shape.
        """
        if not self.data:
            return
        d = self.data["details"]

        self._user_card.set_name(d.get("name") or "—")
        created = d.get("created") or ""
        self._user_card.set_since(f"Since {created}")
        self._user_card.set_image(_product_image_path(d))

        # ---------------- SALES ----------------
        sales_val = (self.data.get("total_amount")
                     or self.data.get("total_sales")
                     or self.data.get("total_value"))
        if sales_val not in (None, "", 0):
            sales_txt = money(sales_val)
        else:
            sold = self.data.get("total_sold")
            sales_txt = _fmt_int(sold)

        # ---------------- PRODUCTS ----------------
        products_val = (self.data.get("total_items")
                        or self.data.get("item_count")
                        or self.data.get("total_products"))
        if products_val in (None, "", 0):
            products_val = self.data.get("total_sold")
        products_txt = _fmt_int(products_val)

        # ---------------- INVOICE ----------------
        invoices_val = self.data.get("total_invoices")
        if invoices_val in (None, ""):
            invoices_val = sum(
                len(v or []) for v in
                (self.data.get("invoices") or {}).values()
            )
        invoices_txt = _fmt_int(invoices_val)

        self._user_card.set_stat(0, sales_txt,    "Sales")
        self._user_card.set_stat(1, products_txt, "Products")
        self._user_card.set_stat(2, invoices_txt, "Invoice")

    # -------------------------------------------------------- details card
    def _fill_details(self):
        """Technical Information: product name + bulleted specs."""
        self._clear_layout(self.details_body)

        if not self.data:
            self.sub_label.setText("Record not found.")
            self.details_body.addWidget(
                QLabel("No details available for this record."))
            return

        d = self.data["details"]
        product_name = d.get("name") or ""

        # 1. Product name (bold, underlined)
        if product_name:
            name_lbl = QLabel(f"<b><u>{product_name}</u></b>")
            name_lbl.setStyleSheet(
                "font-size: 14px; color: #222; background: transparent;")
            name_lbl.setWordWrap(True)
            self.details_body.addWidget(name_lbl)

        # 2. Gather specs
        raw = ""
        if d.get("techs"):
            raw = str(d.get("techs"))
        else:
            tech_rows = self.data.get("tech") or []
            parts = [str(t.get("techs") or "").strip()
                     for t in tech_rows if (t.get("techs") or "").strip()]
            raw = "; ".join(parts)

        specs = [s.strip() for s in raw.replace("\r", " ").split(";")]
        specs = [s for s in specs if s]

        # 3. Render bullet list (or empty message)
        if specs:
            html_items = "".join(
                f"<li style='margin-bottom:3px;'>{s}</li>" for s in specs)
            list_lbl = QLabel(
                f"<ul style='margin-left:-14px; margin-top:6px;'>"
                f"{html_items}</ul>")
            list_lbl.setTextFormat(Qt.TextFormat.RichText)
            list_lbl.setWordWrap(True)
            list_lbl.setStyleSheet(
                "font-size: 13px; color: #333; background: transparent;")
            self.details_body.addWidget(list_lbl)
        else:
            empty = QLabel("<b><u>No technical details available</u></b>")
            empty.setStyleSheet(
                "font-size: 13px; color: #666; background: transparent;")
            self.details_body.addWidget(empty)

        self.details_body.addStretch()

        self.sub_label.setText(
            f"{product_name}  |  "
            f"{_fmt_int(self.data.get('total_sold'))} item(s) sold  |  "
            f"Created {d.get('created') or ''}")

    # -------------------------------------------------------- donut chart
    def _fill_summary(self):
        rows = (self.data or {}).get("yearly", []) or []
        chart_data = []
        for r in rows:
            chart_data.append((str(r.get("fy")),
                               float(r.get("quantity") or 0)))
        self.summary_chart.set_data(chart_data)


# =========================================================================== #
# Factory
# =========================================================================== #
def get_info_page(main, kind, info_id):
    if kind == "product":
        return ProductInfoPage(main, kind, info_id)
    return InfoPage(main, kind, info_id)