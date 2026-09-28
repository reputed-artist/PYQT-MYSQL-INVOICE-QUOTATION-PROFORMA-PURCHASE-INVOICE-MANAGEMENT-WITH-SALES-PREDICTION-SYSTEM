"""
Dashboard page - port of Dashboard controller + Dashboard-layout2.php:
breadcrumb content-header, AdminLTE info-box row (colored icon square +
number), 'Monthly Recap Report' box (sales chart + goal completion bars),
'Latest Tax Invoices' table box.

UI FIXES:
- Every QPainter-based chart now paints its own white background so it
  never shows the window grey through it.
- Every chart has a matching white card with border.
- Donut charts are wrapped in titled white cards.
"""
from datetime import date

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPainter, QColor, QPen
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
                             QFrame, QLabel, QComboBox, QScrollArea,
                             QProgressBar)

from database import db_manager
from ui import widgets as W
from ui.theme import icon
from utils.helpers import money
from utils import dashboard_cache

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


# --------------------------------------------------------------------------- #
# Shared chart styling helpers
# --------------------------------------------------------------------------- #
_CHART_WHITE = QColor("#ffffff")
_CHART_BORDER = "#d2d6de"


def _chart_frame_style():
    """Common stylesheet for every chart / chart-wrapper frame."""
    return (
        "QFrame { background: #ffffff;"
        " border: 1px solid %s;"
        " border-radius: 3px; }" % _CHART_BORDER
    )


def _fill_white(painter, widget):
    """Paint a solid white background covering the widget's rect."""
    painter.fillRect(widget.rect(), _CHART_WHITE)


def _fmt_axis(v):
    """Compact axis label: 1200 -> 1.2k, 1500000 -> 1.5M."""
    try:
        v = float(v)
    except (TypeError, ValueError):
        return str(v)
    a = abs(v)
    if a >= 1_000_000:
        return f"{v / 1_000_000:.1f}M"
    if a >= 1_000:
        return f"{v / 1_000:.1f}k"
    return f"{v:.0f}"


# =========================================================================== #
# AdminLTE info-box
# =========================================================================== #
class InfoBox(QFrame):
    """AdminLTE '.info-box': white card, colored icon square on the left,
    small grey text + big bold number on the right."""

    def __init__(self, icon_name, text, color, parent=None):
        super().__init__(parent)
        self.setStyleSheet(
            "QFrame { background: #ffffff; border: 1px solid #e0e0e0;"
            " border-radius: 3px; }")
        self.setFixedHeight(72)
        h = QHBoxLayout(self)
        h.setContentsMargins(8, 6, 12, 6)
        h.setSpacing(10)

        sq = QFrame()
        sq.setFixedSize(58, 58)
        sq.setStyleSheet(f"QFrame {{ background: {color}; border: none;"
                         f" border-radius: 2px; }}")
        sq_lay = QVBoxLayout(sq)
        sq_lay.setContentsMargins(0, 0, 0, 0)
        ic = QLabel()
        ic.setPixmap(icon(icon_name, "#ffffff", 32).pixmap(32, 32))
        ic.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sq_lay.addWidget(ic)
        h.addWidget(sq)

        col = QVBoxLayout()
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(0)

        self.text_label = QLabel(text, self)
        self.text_label.setStyleSheet(
            "color: #666; font-size: 12px; background: transparent;"
            " border: none;")
        self.text_label.setFixedHeight(16)

        self.value_label = QLabel("0", self)
        self.value_label.setStyleSheet(
            "color: #333; font-size: 18px; font-weight: bold;"
            " background: transparent; border: none;")
        self.value_label.setFixedHeight(24)

        col.addStretch(1)
        col.addWidget(self.text_label)
        col.addWidget(self.value_label)
        col.addStretch(1)
        h.addLayout(col, 1)

    def set_value(self, v):
        self.value_label.setText(str(v))


# =========================================================================== #
# Goal bar
# =========================================================================== #
class GoalBar(QWidget):
    def __init__(self, text, color, parent=None):
        super().__init__(parent)
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 4, 0, 4)
        v.setSpacing(4)
        top = QHBoxLayout()
        lbl = QLabel(text, self)
        lbl.setStyleSheet("color: #555; font-size: 12.5px;")
        top.addWidget(lbl)
        top.addStretch()
        self.pct = QLabel("0%", self)
        self.pct.setStyleSheet(
            "color: #555; font-size: 12.5px; font-weight: 600;")
        top.addWidget(self.pct)
        v.addLayout(top)
        self.bar = QProgressBar()
        self.bar.setFixedHeight(14)
        self.bar.setTextVisible(False)
        self.bar.setRange(0, 100)
        self.bar.setStyleSheet(
            f"QProgressBar {{ background: #f0f0f0; border: none;"
            f" border-radius: 6px; }}"
            f"QProgressBar::chunk {{ background: {color}; border-radius: 6px; }}")
        v.addWidget(self.bar)

    def set(self, value, pct_text=None):
        self.bar.setValue(int(max(0, min(100, value))))
        self.pct.setText(pct_text if pct_text is not None else f"{value:.1f}%")


# =========================================================================== #
# Recap box (AdminLTE ".box")
# =========================================================================== #
class RecapBox(QFrame):
    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.setStyleSheet(
            "QFrame { background: #ffffff; border: 1px solid #d2d6de;"
            " border-top: 3px solid #3c8dbc; border-radius: 3px; }")
        v = QVBoxLayout(self)
        v.setContentsMargins(12, 8, 12, 12)
        v.setSpacing(8)
        hdr = QHBoxLayout()
        self.title_label = QLabel(title, self)
        self.title_label.setStyleSheet(
            "font-size: 15px; font-weight: 600; color: #444;"
            " background: transparent; border: none;")
        hdr.addWidget(self.title_label)
        hdr.addStretch()
        self._tools_row = hdr
        v.addLayout(hdr)
        self.body = v

    def tools(self):
        return self._tools_row

    def add(self, w, stretch=0):
        self.body.addWidget(w, stretch)

    def addLayout(self, lay, stretch=0):
        self.body.addLayout(lay, stretch)


# =========================================================================== #
# Monthly Bar chart  (BarChart)
# =========================================================================== #
class BarChart(QFrame):
    """Canvas-style bar chart with x/y axes + hover tooltips.

    UI FIX: paints its own white background so the parent's grey window
    background never bleeds through.
    """

    def __init__(self, values, color="#3c8dbc", parent=None):
        super().__init__(parent)
        self.values = list(values) if values else []
        self.color = color
        self.setMinimumHeight(240)
        self.setMouseTracking(True)
        self._bar_rects = []
        self._hover_idx = -1
        self.setToolTip("")
        # white background + subtle border, consistent with other cards
        self.setStyleSheet(_chart_frame_style())
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

    def set_values(self, values):
        self.values = list(values) if values else []
        self._hover_idx = -1
        self.setToolTip("")
        self.update()

    # ------------------------------------------------------------ painting
    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        # ---- FIX: paint our own white background first ----
        _fill_white(p, self)

        w, h = self.width(), self.height()

        left   = 56
        right  = 20
        top    = 14
        bottom = 34

        plot_l = left
        plot_r = max(left + 10, w - right)
        plot_t = top
        plot_b = h - bottom
        avail_w = plot_r - plot_l
        avail_h = plot_b - plot_t

        # ---- grid + y-axis tick labels ----
        vmax = max(self.values) if self.values else 1
        vmax = vmax or 1
        f = p.font()
        f.setPointSize(8)
        p.setFont(f)
        fm = p.fontMetrics()

        p.setPen(QPen(QColor("#eeeeee")))
        for i in range(5):
            y = plot_t + avail_h * i / 4
            p.drawLine(plot_l, int(y), plot_r, int(y))

        p.setPen(QColor("#888"))
        for i in range(5):
            y = plot_t + avail_h * i / 4
            val = vmax * (1 - i / 4)
            label = _fmt_axis(val)
            lw = fm.horizontalAdvance(label)
            p.drawText(plot_l - lw - 6, int(y) + 4, label)

        # ---- bars (clipped) ----
        self._bar_rects = []
        if self.values:
            n = len(self.values)
            bw = avail_w / max(n, 1)

            p.save()
            p.setClipRect(plot_l, plot_t, int(avail_w), int(avail_h))
            for i, v in enumerate(self.values):
                bh = avail_h * (v / vmax) if vmax else 0
                bar_w = bw * 0.62
                x = plot_l + i * bw + (bw - bar_w) / 2
                y = plot_b - bh

                if i == self._hover_idx:
                    p.setBrush(QColor(self.color).lighter(115))
                else:
                    p.setBrush(QColor(self.color))
                p.setPen(Qt.PenStyle.NoPen)
                p.drawRect(int(x), int(y), int(bar_w), int(bh))

                self._bar_rects.append((x, y, bar_w, bh, MONTHS[i], v))
            p.restore()

            # ---- month labels ----
            p.setPen(QColor("#777"))
            for i in range(n):
                label_rect = (int(plot_l + i * bw), plot_b + 4,
                              int(bw), bottom - 6)
                p.drawText(*label_rect, Qt.AlignmentFlag.AlignCenter, MONTHS[i])

        # ---- axis lines ----
        p.setPen(QPen(QColor("#cccccc")))
        p.drawLine(plot_l, plot_t, plot_l, plot_b)
        p.drawLine(plot_l, plot_b, plot_r, plot_b)

        p.end()

    # ------------------------------------------------------------ hover
    def mouseMoveEvent(self, event):
        x = event.position().x()
        idx = -1
        for i, (bx, by, bw_, bh_, label, value) in enumerate(self._bar_rects):
            if bx - 6 <= x <= bx + bw_ + 6:
                idx = i
                break

        if idx != self._hover_idx:
            self._hover_idx = idx
            if idx >= 0:
                label, value = self._bar_rects[idx][4], self._bar_rects[idx][5]
                self.setToolTip(f"<b>{label}</b><br/>Sales: {value:,.2f}")
            else:
                self.setToolTip("")
            self.update()
        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        if self._hover_idx != -1:
            self._hover_idx = -1
            self.setToolTip("")
            self.update()
        super().leaveEvent(event)


# =========================================================================== #
# Small box
# =========================================================================== #
class SmallBox(QFrame):
    def __init__(self, text, color, parent=None):
        super().__init__(parent)
        self.setStyleSheet(
            f"QFrame {{ background: {color}; border: none;"
            f" border-radius: 3px; }}")
        self.setFixedHeight(90)
        v = QVBoxLayout(self)
        v.setContentsMargins(12, 8, 12, 8)
        v.setSpacing(2)
        self.value_label = QLabel("0", self)
        self.value_label.setStyleSheet(
            "color: #ffffff; font-size: 26px; font-weight: bold;"
            " background: transparent; border: none;")
        v.addWidget(self.value_label)
        self.text_label = QLabel(text, self)
        self.text_label.setStyleSheet(
            "color: #f5f5f5; font-size: 12.5px; background: transparent;"
            " border: none;")
        v.addWidget(self.text_label)
        v.addStretch()

    def set_value(self, v):
        self.value_label.setText(str(v))


# =========================================================================== #
# Donut chart
# =========================================================================== #
class DonutChart(QFrame):
    """Morris.Donut replacement: pie drawn with QPainter + centered legend.

    UI FIX: paints its own white background so the parent's grey window
    background never bleeds through.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.slices = []
        self.setMinimumHeight(160)
        # white background + subtle border, consistent with other cards
        self.setStyleSheet(_chart_frame_style())
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

    def set_data(self, data):
        self.slices = [(str(d["label"]), float(d["value"] or 0)) for d in data]
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        # ---- FIX: paint our own white background first ----
        _fill_white(p, self)

        w, h = self.width(), self.height()
        data = [(l, v) for l, v in self.slices if v > 0]
        total = sum(v for _, v in data)
        f = p.font()
        f.setPointSize(8)
        p.setFont(f)
        fm = p.fontMetrics()

        cols = max(1, w // 130)
        legend_rows = (len(data) + cols - 1) // max(cols, 1)
        pie_bottom = h - (legend_rows * 16 + 6 if data else 0)

        d = min(w - 20, pie_bottom - 10)
        if d > 20 and total > 0:
            cx, cy, r = w // 2, pie_bottom // 2, d // 2
            start = 90 * 16
            for i, (label, value) in enumerate(data):
                span = int(value / total * 360 * 16)
                color = QColor(
                    db_manager.MORRIS_COLORS[i % len(db_manager.MORRIS_COLORS)])
                p.setBrush(color)
                p.setPen(QPen(QColor("#ffffff"), 1))
                p.drawPie(cx - r, cy - r, d, d, start, -span)
                start -= span

        x, row = 6, 0
        p.setPen(Qt.PenStyle.NoPen)
        for i, (label, value) in enumerate(data):
            color = db_manager.MORRIS_COLORS[i % len(db_manager.MORRIS_COLORS)]
            col = i % cols
            if col == 0 and i > 0:
                row += 1
            lx = 6 + col * (w // cols if cols else w)
            ly = pie_bottom + 2 + row * 16
            p.setBrush(QColor(color))
            p.drawRect(lx, ly + 3, 9, 9)
            p.setPen(QColor("#666"))
            p.drawText(lx + 14, ly, fm.horizontalAdvance(label) + 6, 15,
                       Qt.AlignmentFlag.AlignLeft, label)
            p.setPen(Qt.PenStyle.NoPen)
        p.end()


# =========================================================================== #
# FY bar chart
# =========================================================================== #
class FYBarChart(QFrame):
    """Morris.Bar replacement with x/y axes, hover tooltips, clipping-safe
    layout.

    UI FIX: paints its own white background so the parent's grey window
    background never bleeds through.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.rows = []
        self.keys = ["b", "a", "c"]
        self.labels = ["GST", "Turnover", "item_sold"]
        self.colors = ["#00a65a", "#03a9f3", "#f56954"]
        self.setMinimumHeight(240)
        self.setMouseTracking(True)
        self.title = ""
        self._group_rects = []
        self._hover_idx = -1
        self.setToolTip("")
        # white background + subtle border, consistent with other cards
        self.setStyleSheet(_chart_frame_style())
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

    def set_data(self, rows, title=""):
        self.rows = rows or []
        self.title = title
        self._hover_idx = -1
        self.setToolTip("")
        self.update()

    # ------------------------------------------------------------ painting
    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        # ---- FIX: paint our own white background first ----
        _fill_white(p, self)

        w, h = self.width(), self.height()
        f = p.font()
        f.setPointSize(8)
        p.setFont(f)
        fm = p.fontMetrics()

        left, right, bottom = 56, 20, 34
        top = 34 if self.title else 16

        plot_l = left
        plot_r = max(left + 10, w - right)
        plot_t = top
        plot_b = h - bottom
        avail_w = plot_r - plot_l
        avail_h = plot_b - plot_t

        # ---- title ----
        if self.title:
            p.setPen(QColor("#555"))
            p.drawText(0, 4, w, 16, Qt.AlignmentFlag.AlignCenter, self.title)

        # ---- legend ----
        lx = plot_l
        for i, lab in enumerate(self.labels):
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(self.colors[i]))
            p.drawRect(lx, 8, 9, 9)
            p.setPen(QColor("#666"))
            p.drawText(lx + 13, 3, 90, 18,
                       Qt.AlignmentFlag.AlignLeft, lab)
            lx += 76

        # ---- y-axis ----
        series = [[r.get(k) or 0 for r in self.rows] for k in self.keys]
        vmax = max((max(s) for s in series), default=1) or 1

        p.setPen(QPen(QColor("#eeeeee")))
        for i in range(5):
            y = plot_t + avail_h * i / 4
            p.drawLine(plot_l, int(y), plot_r, int(y))

        p.setPen(QColor("#888"))
        for i in range(5):
            y = plot_t + avail_h * i / 4
            val = vmax * (1 - i / 4)
            label = _fmt_axis(val)
            lw = fm.horizontalAdvance(label)
            p.drawText(plot_l - lw - 6, int(y) + 4, label)

        # ---- bars (clipped) ----
        self._group_rects = []
        if self.rows:
            n = len(self.rows)
            group_w = avail_w / max(n, 1)
            bar_w = group_w * 0.68 / len(self.keys)

            p.save()
            p.setClipRect(plot_l, plot_t, int(avail_w), int(avail_h))
            for gi, vals in enumerate(series):
                for i, v in enumerate(vals):
                    bh = avail_h * (v / vmax) if vmax else 0
                    x = plot_l + i * group_w + group_w * 0.16 + gi * bar_w
                    base = QColor(self.colors[gi])
                    if i == self._hover_idx:
                        base = base.lighter(115)
                    p.setBrush(base)
                    p.setPen(Qt.PenStyle.NoPen)
                    p.drawRect(int(x), int(plot_b - bh),
                               int(bar_w * 0.85), int(bh))
            p.restore()

            for i, r in enumerate(self.rows):
                gx = plot_l + i * group_w
                self._group_rects.append(
                    (gx, plot_t, group_w, avail_h, r))

            # ---- x labels ----
            p.setPen(QColor("#777"))
            for i, r in enumerate(self.rows):
                label_rect = (int(plot_l + i * group_w), plot_b + 4,
                              int(group_w), bottom - 6)
                p.drawText(*label_rect, Qt.AlignmentFlag.AlignCenter,
                           str(r["y"]))

        # ---- axis lines ----
        p.setPen(QPen(QColor("#cccccc")))
        p.drawLine(plot_l, plot_t, plot_l, plot_b)
        p.drawLine(plot_l, plot_b, plot_r, plot_b)

        p.end()

    # ------------------------------------------------------------ hover
    def mouseMoveEvent(self, event):
        x = event.position().x()
        idx = -1
        for i, (gx, gy, gw, gh, row) in enumerate(self._group_rects):
            if gx <= x <= gx + gw:
                idx = i
                break

        if idx != self._hover_idx:
            self._hover_idx = idx
            if idx >= 0:
                row = self._group_rects[idx][4]
                gst = row.get("b") or 0
                turn = row.get("a") or 0
                items = row.get("c") or 0
                self.setToolTip(
                    f"<b>{row.get('y')}</b><br/>"
                    f"GST: {gst:,.2f}<br/>"
                    f"Turnover: {turn:,.2f}<br/>"
                    f"Items sold: {items:,}")
            else:
                self.setToolTip("")
            self.update()
        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        if self._hover_idx != -1:
            self._hover_idx = -1
            self.setToolTip("")
            self.update()
        super().leaveEvent(event)


# =========================================================================== #
# Donut card wrapper (new)
# =========================================================================== #
class DonutCard(QFrame):
    """A white card containing a titled DonutChart.

    Adds the missing white background + title + border around each donut,
    so the donuts look like the rest of the dashboard.
    """

    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.setStyleSheet(
            "QFrame { background: #ffffff; border: 1px solid #d2d6de;"
            " border-radius: 3px; }")
        v = QVBoxLayout(self)
        v.setContentsMargins(10, 8, 10, 10)
        v.setSpacing(4)

        lbl = QLabel(title, self)
        lbl.setStyleSheet(
            "font-size: 13px; font-weight: 600; color: #444;"
            " background: transparent; border: none;")
        v.addWidget(lbl)

        self.chart = DonutChart(self)
        # inner donut doesn't need its own border once inside the card
        self.chart.setStyleSheet(
            "QFrame { background: #ffffff; border: none; }")
        v.addWidget(self.chart, 1)

    def set_data(self, data):
        self.chart.set_data(data)


# =========================================================================== #
# Dashboard page
# =========================================================================== #
class DashboardPage(QWidget):
    title = "Dashboard"

    def __init__(self, main):
        super().__init__()
        self.main = main
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)

        lay.addWidget(W.PageHeader("Dashboard", breadcrumb="Dashboard"))

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(
            "QScrollArea { border: none; background: transparent; }")
        inner = QWidget()
        inner.setObjectName("DashboardInner")
        inner.setStyleSheet(
            "QWidget#DashboardInner { background: transparent; }")
        v = QVBoxLayout(inner)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(12)

        # ---- info-box row #1 ----
        self.infoboxes = {}
        row1 = QHBoxLayout()
        row1.setSpacing(12)
        for key, ic, text, color in (
                ("clients", "clients", "Clients", "#00c0ef"),
                ("suppliers", "suppliers", "Suppliers", "#00a65a"),
                ("products", "products", "Products", "#f39c12"),
                ("tax_invoices", "file", "Tax Invoices", "#dd4b39")):
            box = InfoBox(ic, text, color, inner)
            self.infoboxes[key] = box
            row1.addWidget(box)
        v.addLayout(row1)

        # ---- info-box row #2 ----
        row2 = QHBoxLayout()
        row2.setSpacing(12)
        for key, ic, text, color in (
                ("quotations", "file", "Quotations", "#605ca8"),
                ("proforma", "file", "Proforma Invoices", "#39cccc"),
                ("purchases", "cart", "Purchase Invoices", "#3c8dbc"),
                ("received_amount", "exchange", "Transactions Done", "#001f3f")):
            box = InfoBox(ic, text, color, inner)
            self.infoboxes[key] = box
            row2.addWidget(box)
        v.addLayout(row2)

        # ---- Monthly Recap Report ----
        recap = RecapBox("Monthly Recap Report")
        self.year_combo = QComboBox()
        self.year_combo.setStyleSheet(
            "QComboBox { font-size: 12px; padding: 2px 8px; }")
        y = date.today().year
        for yy in range(y, y - 6, -1):
            self.year_combo.addItem(str(yy), yy)
        self.year_combo.currentIndexChanged.connect(self.refresh)
        recap.tools().addWidget(QLabel("Year:"))
        recap.tools().addWidget(self.year_combo)
        recap_row = QHBoxLayout()
        recap_row.setSpacing(12)
        left_col = QVBoxLayout()
        cap = QLabel("<b>Sales: Jan - Dec (Tax Invoices)</b>")
        cap.setTextFormat(Qt.TextFormat.RichText)
        cap.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cap.setStyleSheet("color: #555; border: none;")
        left_col.addWidget(cap)
        self.chart = BarChart([0] * 12)
        left_col.addWidget(self.chart, 1)
        recap_row.addLayout(left_col, 3)
        right_col = QVBoxLayout()
        goal = QLabel("<b>Goal Completion</b>")
        goal.setTextFormat(Qt.TextFormat.RichText)
        goal.setAlignment(Qt.AlignmentFlag.AlignCenter)
        goal.setStyleSheet("color: #555; border: none;")
        right_col.addWidget(goal)
        self.bar_received = GoalBar("Payments received vs Sales", "#00a65a")
        self.bar_purchase = GoalBar("Purchases vs Sales", "#dd4b39")
        self.bar_quote = GoalBar("Quotations vs Tax Invoices", "#f39c12")
        for bar in (self.bar_received, self.bar_purchase, self.bar_quote):
            right_col.addWidget(bar)
        right_col.addStretch()
        recap_row.addLayout(right_col, 1)
        recap.addLayout(recap_row, 1)
        recap.setMinimumHeight(320)
        v.addWidget(recap)

        # ---- Latest Tax Invoices ----
        latest = W.Box("Latest Tax Invoices", "info")
        self.recent_table = W.DataTable(
            ["Invoice No", "Client", "Date", "Items",
             "Subtotal", "GST %", "GST Amt", "Total"])
        latest.add(self.recent_table)
        v.addWidget(latest)

        # ---- footer small boxes ----
        small_row = QHBoxLayout()
        small_row.setSpacing(12)
        self.small_boxes = {}
        for key, text, color in (
                ("invcount", "Invoices", "#3c8dbc"),
                ("bounce_rate", "Bounce Rate", "#f39c12"),
                ("clientcount", "Clients", "#00c0ef"),
                ("monthturn", "Turnover", "#00a65a")):
            sb = SmallBox(text, color, inner)
            self.small_boxes[key] = sb
            small_row.addWidget(sb)
        v.addLayout(small_row)

        # ---- donut charts (wrapped in titled cards) ----
        donut_grid = QGridLayout()
        donut_grid.setSpacing(10)
        self.donuts = {}
        donut_titles = {
            "consumables":      "Consumables",
            "user_category":    "User Category",
            "country":          "Country",
            "product_category": "Product Category",
            "billed":           "Billed Clients",
            "docs":             "Documents",
            "client_type":      "Client Type",
        }
        for i, key in enumerate(("consumables", "user_category", "country",
                                   "product_category", "billed", "docs",
                                   "client_type")):
            card = DonutCard(donut_titles[key], inner)
            self.donuts[key] = card
            donut_grid.addWidget(card, i // 4, i % 4)
        # make columns stretch evenly
        for c in range(4):
            donut_grid.setColumnStretch(c, 1)
        v.addLayout(donut_grid)

        # ---- FY sales chart ----
        fy_box = W.Box("Financial Year Sales", "primary")
        self.fy_combo = QComboBox()
        self.fy_combo.setStyleSheet(
            "QComboBox { font-size: 12px; padding: 2px 8px; }")
        fy_y = date.today().year
        for yy in range(fy_y, fy_y - 6, -1):
            self.fy_combo.addItem(f"Apr {yy} - Mar {yy + 1}", yy)
        self.fy_combo.currentIndexChanged.connect(self._load_fy_chart)
        fy_tools = QHBoxLayout()
        fy_tools.addStretch()
        fy_tools.addWidget(QLabel("Financial Year:"))
        fy_tools.addWidget(self.fy_combo)
        fy_box.addLayout(fy_tools)
        self.fy_chart = FYBarChart()
        fy_box.add(self.fy_chart, 1)
        v.addWidget(fy_box)

        # ---- reminder tables ----
        rem_box = W.Box("Payment Reminders (Latest Tax Invoices)", "warning")
        self.reminder_table = W.DataTable(
            ["#", "Invoice No", "Client Name", "Item Name", "Mobile"])
        rem_box.add(self.reminder_table)
        v.addWidget(rem_box)

        qq_box = W.Box("Quick Quote Follow-ups", "success")
        self.qq_table = W.DataTable(
            ["#", "Q ID", "Name", "Mobile", "Qty", "Subtotal", "GST", "Total"])
        qq_box.add(self.qq_table)
        v.addWidget(qq_box)

        scroll.setWidget(inner)
        lay.addWidget(scroll)

    # ------------------------------------------------------------------ #
    def refresh(self):
        try:
            db_manager.ensure_dashboard_indexes()
        except Exception:
            pass
        try:
            stats = db_manager.dashboard_stats()
        except Exception as exc:
            W.error(self, f"Database error: {exc}")
            return
        for key, box in self.infoboxes.items():
            if key == "received_amount":
                box.set_value(money(stats["received_amount"]))
            else:
                box.set_value(stats.get(key, 0))

        sales = max(stats["sales_amount"], 1.0)
        recv_pct = stats["received_amount"] / sales * 100
        purch_pct = stats["purchase_amount"] / sales * 100
        docs = max(stats["tax_invoices"], 1)
        quote_pct = stats["quotations"] / docs * 100
        self.bar_received.set(recv_pct)
        self.bar_purchase.set(purch_pct)
        self.bar_quote.set(quote_pct)

        year = self.year_combo.currentData()
        self.chart.set_values(
            db_manager.monthly_sales("invtest2", "created", year))

        self.recent_table.clear_rows()
        for r in db_manager.recent_invoices("tax", 8):
            self.recent_table.add_row([
                r["invid"], r["c_name"] or "", str(r["doc_date"]),
                r["totalitems"], money(r["subtotal"]),
                f"{float(r['taxrate']):g}%",
                money(r["taxamount"]), money(r["totalamount"])])

        try:
            cms = db_manager.current_month_stats()
        except Exception as exc:
            W.error(self, f"Dashboard stats error: {exc}")
            return
        self.small_boxes["invcount"].set_value(cms["invcount"])
        self.small_boxes["bounce_rate"].set_value(f"{cms['bounce_rate']:.1f}%")
        self.small_boxes["clientcount"].set_value(cms["clientcount"])
        self.small_boxes["monthturn"].set_value(money(cms["monthturn"]))

        fylab = self.fy_combo.currentData() or ""
        sy = int(str(fylab).split("-")[0]) if fylab else date.today().year - 1
        ey = sy + 1
        donut_sources = {
            "consumables": lambda: db_manager.donut_consumables(sy, ey),
            "user_category": db_manager.donut_user_category,
            "country": db_manager.donut_client_country,
            "product_category": lambda: db_manager.donut_product_category(sy, ey),
            "billed": db_manager.donut_billed_clients,
            "docs": lambda: db_manager.donut_doc_count(sy, ey),
            "client_type": db_manager.donut_client_type,
        }
        for key, fn in donut_sources.items():
            try:
                self.donuts[key].set_data(fn())
            except Exception:
                self.donuts[key].set_data([])

        self.reminder_table.clear_rows()
        try:
            for i, r in enumerate(db_manager.client_reminder(), 1):
                self.reminder_table.add_row([
                    i, r["invid"], r["c_name"] or "", r["item_name"] or "",
                    r["mob"] or ""])
        except Exception:
            pass

        self.qq_table.clear_rows()
        try:
            for i, r in enumerate(db_manager.quickquote_reminder(), 1):
                self.qq_table.add_row([
                    i, r["q_id"], r["name"] or "", r["mob"] or "",
                    r["quantity"], money(r["subtotal"]), money(r["gst"]),
                    money(r["total"])])
        except Exception:
            pass

        self._load_fy_chart()

    def _load_fy_chart(self):
        if not hasattr(self, "fy_chart"):
            return
        fylab = self.fy_combo.currentData()
        if not fylab:
            return
        sy = int(str(fylab).split("-")[0])
        ey = sy + 1
        try:
            rows = db_manager.fy_sales_chart(sy, ey)
        except Exception as exc:
            W.error(self, f"FY chart error: {exc}")
            rows = []
        title = f"Apr {sy} - Mar {ey}"
        self.fy_chart.set_data(rows, title)