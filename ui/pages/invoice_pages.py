"""
Invoice pages - port of the Generate/List flows for
Tax Invoice, Proforma, Quotation and Purchase Invoice.

SQLite edition — works with db_manager backed by sqlite3.
"""
from datetime import date, datetime

from PyQt6.QtCore import Qt, QDate, QTimer, QEvent, QSize, QRectF, QPointF
from PyQt6.QtGui import (QIcon, QPixmap, QPainter, QColor, QPen, QPainterPath)
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QLineEdit, QPlainTextEdit, QComboBox,
                             QDateEdit, QTableWidget, QTableWidgetItem,
                             QHeaderView, QGridLayout, QFrame, QScrollArea,
                             QListWidget, QListWidgetItem, QSizePolicy)

from database import db_manager, DOC_REGISTRY
from ui import widgets as W
from ui.icons import icon_button
from utils import invoice_print
from utils.helpers import money


# --------------------------------------------------------------------------- #
# SQLite-aware date coercion
# --------------------------------------------------------------------------- #
def _to_date(v):
    """
    Accept a date / datetime / ISO string (as SQLite returns) and coerce
    it into a python date object.
    """
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    if isinstance(v, str) and v:
        try:
            # Accept both "YYYY-MM-DD" and "YYYY-MM-DD HH:MM:SS"
            return datetime.fromisoformat(v.split(" ")[0]).date()
        except (ValueError, TypeError):
            pass
    return date.today()


def _first_item_names_for(doc, orderids):
    out = {}
    for oid in orderids:
        try:
            _master, items = db_manager.get_invoice(doc, oid)
            if items:
                out[oid] = items[0].get("item_name") or ""
        except Exception:
            pass
    return out


# --------------------------------------------------------------------------- #
# Hand-drawn icons (unchanged)
# --------------------------------------------------------------------------- #
def _eye_icon(color="#ffffff", size=16):
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    c = QColor(color)
    pen = QPen(c)
    pen.setWidthF(max(1.2, size * 0.11))
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    s = size / 16.0
    p.scale(s, s)
    path = QPainterPath()
    path.moveTo(1, 8)
    path.quadTo(8, 1.5, 15, 8)
    path.quadTo(8, 14.5, 1, 8)
    p.drawPath(path)
    p.setBrush(QColor(color))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawEllipse(QPointF(8, 8), 1.9, 1.9)
    p.end()
    return QIcon(pm)


def _pencil_icon(color="#ffffff", size=16):
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    c = QColor(color)
    pen = QPen(c)
    pen.setWidthF(max(1.2, size * 0.11))
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    s = size / 16.0
    p.scale(s, s)
    tip = QPainterPath()
    tip.moveTo(2, 14)
    tip.lineTo(3.6, 10.3)
    tip.lineTo(5.9, 12.6)
    tip.closeSubpath()
    p.setBrush(QColor(color))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawPath(tip)
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.setPen(pen)
    p.drawLine(QPointF(3.8, 11.2), QPointF(12.6, 2.4))
    p.drawLine(QPointF(5.4, 12.8), QPointF(13.6, 4.6))
    p.drawLine(QPointF(12.6, 2.4), QPointF(13.6, 4.6))
    p.end()
    return QIcon(pm)


def _trash_icon(color="#ffffff", size=16):
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    c = QColor(color)
    pen = QPen(c)
    pen.setWidthF(max(1.2, size * 0.11))
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    s = size / 16.0
    p.scale(s, s)
    p.drawLine(QPointF(3, 4.5), QPointF(13, 4.5))
    p.drawLine(QPointF(6.5, 4.5), QPointF(6.5, 2.6))
    p.drawLine(QPointF(9.5, 4.5), QPointF(9.5, 2.6))
    p.drawLine(QPointF(6.5, 2.6), QPointF(9.5, 2.6))
    body = QPainterPath()
    body.moveTo(4, 5.6)
    body.lineTo(12, 5.6)
    body.lineTo(11.2, 14)
    body.lineTo(4.8, 14)
    body.closeSubpath()
    p.drawPath(body)
    p.drawLine(QPointF(7, 7.6), QPointF(7, 12.4))
    p.drawLine(QPointF(9, 7.6), QPointF(9, 12.4))
    p.end()
    return QIcon(pm)


def _drive_icon(size=15):
    """(Legacy) Google-Drive-style triangle - kept, unused by the row now.

    The Purchase-List Download button now uses the white download-arrow
    glyph (_download_icon) so it matches Edit/View/Delete.
    """
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    s = size / 16.0
    p.scale(s, s)
    p.setPen(Qt.PenStyle.NoPen)
    # Simplified Drive triangle: three parallelograms.
    #   top bar    - yellow, left blade - green, right blade - blue
    top = QPainterPath()
    top.moveTo(5.2, 2.4)
    top.lineTo(10.8, 2.4)
    top.lineTo(8.6, 6.2)
    top.lineTo(3.0, 6.2)
    top.closeSubpath()
    p.setBrush(QColor("#FBBC05"))
    p.drawPath(top)
    left = QPainterPath()
    left.moveTo(3.0, 6.2)
    left.lineTo(8.6, 6.2)
    left.lineTo(5.6, 13.6)
    left.lineTo(1.4, 13.6)
    left.closeSubpath()
    p.setBrush(QColor("#34A853"))
    p.drawPath(left)
    right = QPainterPath()
    right.moveTo(8.6, 6.2)
    right.lineTo(14.6, 6.2)
    right.lineTo(10.4, 13.6)
    right.lineTo(5.6, 13.6)
    right.closeSubpath()
    p.setBrush(QColor("#4285F4"))
    p.drawPath(right)
    p.end()
    return QIcon(pm)


def _download_icon(color="#ffffff", size=15):
    """White download arrow (shaft into tray) for 'Download PDF'.

    Same stroke style as the other row icons so it matches Edit/View/Delete
    at 22x22 while reading clearly as Download.
    """
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    c = QColor(color)
    pen = QPen(c)
    pen.setWidthF(max(1.2, size * 0.11))
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    s = size / 16.0
    p.scale(s, s)
    # shaft + arrow head
    p.drawLine(QPointF(8, 1.8), QPointF(8, 9.4))
    head = QPainterPath()
    head.moveTo(4.8, 6.6)
    head.lineTo(8, 10.0)
    head.lineTo(11.2, 6.6)
    p.drawPath(head)
    # tray
    tray = QPainterPath()
    tray.moveTo(2.6, 10.2)
    tray.lineTo(2.6, 14.0)
    tray.lineTo(13.4, 14.0)
    tray.lineTo(13.4, 10.2)
    p.drawPath(tray)
    p.end()
    return QIcon(pm)


def _print_icon(color="#ffffff", size=15):
    """White printer glyph for the one-click 'Print' row button."""
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    c = QColor(color)
    pen = QPen(c)
    pen.setWidthF(max(1.1, size * 0.10))
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    s = size / 16.0
    p.scale(s, s)
    # top paper tray
    tray = QPainterPath()
    tray.moveTo(4.4, 1.6)
    tray.lineTo(11.6, 1.6)
    tray.lineTo(11.6, 4.6)
    tray.lineTo(4.4, 4.6)
    tray.closeSubpath()
    p.drawPath(tray)
    # printer body
    body = QPainterPath()
    body.moveTo(2.2, 4.6)
    body.lineTo(13.8, 4.6)
    body.lineTo(13.8, 10.6)
    body.lineTo(2.2, 10.6)
    body.closeSubpath()
    p.drawPath(body)
    # printed sheet coming out
    sheet = QPainterPath()
    sheet.moveTo(4.4, 10.6)
    sheet.lineTo(4.4, 14.2)
    sheet.lineTo(11.6, 14.2)
    sheet.lineTo(11.6, 10.6)
    p.drawPath(sheet)
    p.drawLine(QPointF(6.0, 12.2), QPointF(10.0, 12.2))
    p.end()
    return QIcon(pm)


def _pdf_preview_icon(color="#ffffff", size=15):
    """White document + magnifier glyph for 'Preview PDF'."""
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    c = QColor(color)
    pen = QPen(c)
    pen.setWidthF(max(1.2, size * 0.11))
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    s = size / 16.0
    p.scale(s, s)
    # document outline
    doc = QPainterPath()
    doc.moveTo(3.0, 1.6)
    doc.lineTo(8.6, 1.6)
    doc.lineTo(11.0, 4.0)
    doc.lineTo(11.0, 11.4)
    doc.lineTo(3.0, 11.4)
    doc.closeSubpath()
    p.drawPath(doc)
    p.drawLine(QPointF(8.6, 1.6), QPointF(8.6, 4.0))
    p.drawLine(QPointF(8.6, 4.0), QPointF(11.0, 4.0))
    # magnifier handle over the doc corner
    p.drawLine(QPointF(7.6, 9.2), QPointF(11.8, 13.4))
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(color))
    p.drawEllipse(QPointF(6.4, 8.0), 2.0, 2.0)
    p.setBrush(Qt.GlobalColor.transparent)
    pen2 = QPen(c)
    pen2.setWidthF(max(1.2, size * 0.11))
    p.setPen(pen2)
    p.drawEllipse(QPointF(6.4, 8.0), 2.0, 2.0)
    p.end()
    return QIcon(pm)


def _funnel_pixmap(size=22, color="#222"):
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    pen = QPen(QColor(color))
    pen.setWidthF(1.6)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)
    p.setBrush(QColor(color))
    s = size / 16.0
    p.scale(s, s)
    path = QPainterPath()
    path.moveTo(2, 3)
    path.lineTo(14, 3)
    path.lineTo(9, 8)
    path.lineTo(9, 13)
    path.lineTo(7, 14)
    path.lineTo(7, 8)
    path.closeSubpath()
    p.drawPath(path)
    p.end()
    return pm


def _plus_icon(color="#ffffff", size=18):
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    pen = QPen(QColor(color))
    pen.setWidthF(max(2.0, size * 0.16))
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    p.setPen(pen)
    p.drawLine(QPointF(size * 0.2, size * 0.5), QPointF(size * 0.8, size * 0.5))
    p.drawLine(QPointF(size * 0.5, size * 0.2), QPointF(size * 0.5, size * 0.8))
    p.end()
    return QIcon(pm)


def _minus_icon(color="#ffffff", size=18):
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    pen = QPen(QColor(color))
    pen.setWidthF(max(2.0, size * 0.16))
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    p.setPen(pen)
    p.drawLine(QPointF(size * 0.2, size * 0.5), QPointF(size * 0.8, size * 0.5))
    p.end()
    return QIcon(pm)


# =========================================================================== #
# Searchable client combo (unchanged)
# =========================================================================== #
class _ClientFilterCombo(QWidget):
    def __init__(self, parent=None, on_change=None,
                 placeholder="Select a Person or Company"):
        super().__init__(parent)
        self._on_change = on_change
        self._selected_cid = None
        self._clients = []

        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        self._display = QLineEdit()
        self._display.setReadOnly(True)
        self._display.setPlaceholderText(placeholder)
        self._display.setClearButtonEnabled(True)
        self._display.setFixedHeight(30)
        self._display.setCursor(Qt.CursorShape.PointingHandCursor)
        self._display.setStyleSheet(
            "QLineEdit { border: 1px solid #d2d6de; border-radius: 3px;"
            " padding: 0 6px; background: #ffffff; }"
            "QLineEdit:hover { border-color: #a8b8c8; }")
        lay.addWidget(self._display, 1)
        self._display.mousePressEvent = self._on_display_clicked

        self._popup = QFrame()
        self._popup.setWindowFlags(
            Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self._popup.setStyleSheet(
            "QFrame { background: #ffffff; border: 1px solid #d2d6de; }")
        pv = QVBoxLayout(self._popup)
        pv.setContentsMargins(0, 0, 0, 0)
        pv.setSpacing(0)

        self._search = QLineEdit()
        self._search.setPlaceholderText("Type to search...")
        self._search.setClearButtonEnabled(True)
        self._search.setStyleSheet(
            "QLineEdit { border: none; border-bottom: 1px solid #e5e5e5;"
            " padding: 6px 8px; background: #ffffff; }")
        self._search.textChanged.connect(self._filter)
        pv.addWidget(self._search)

        self._list = QListWidget()
        self._list.setStyleSheet(
            "QListWidget { border: none; background: #ffffff; }"
            "QListWidget::item { padding: 6px 8px; }"
            "QListWidget::item:selected { background: #3c8dbc; color: #fff; }")
        self._list.setMinimumHeight(180)
        self._list.setMaximumHeight(280)
        self._list.itemClicked.connect(self._on_pick)
        pv.addWidget(self._list)
        self._search.installEventFilter(self)

    def set_clients(self, clients):
        self._clients = clients or []
        self._apply_selection()

    def current_cid(self):
        return self._selected_cid

    def set_cid(self, cid):
        if cid is None:
            self._selected_cid = None
            self._display.clear()
            return
        self._selected_cid = cid
        self._apply_selection()

    def clear(self):
        self._selected_cid = None
        self._display.clear()

    def _apply_selection(self):
        if self._selected_cid is None:
            self._display.clear()
            return
        for c in self._clients:
            if c.get("cid") == self._selected_cid:
                self._display.setText(c.get("c_name", ""))
                return
        self._display.clear()

    def _on_display_clicked(self, ev):
        self._show_popup()

    def _show_popup(self):
        self._search.blockSignals(True)
        self._search.clear()
        self._search.blockSignals(False)
        self._populate("")
        gp = self.mapToGlobal(self.rect().bottomLeft())
        self._popup.setFixedWidth(max(self.width(), 300))
        self._popup.move(gp)
        self._popup.show()
        self._search.setFocus()

    def _populate(self, needle):
        self._list.clear()
        needle = (needle or "").lower().strip()
        for c in self._clients:
            name = c.get("c_name") or ""
            mob = c.get("mob") or ""
            gst = c.get("gst") or ""
            addr = c.get("c_add") or ""
            hay = f"{name} {mob} {gst} {addr}".lower()
            if needle and needle not in hay:
                continue
            it = QListWidgetItem(name or "(unnamed)")
            it.setData(Qt.ItemDataRole.UserRole, c.get("cid"))
            if mob:
                it.setToolTip(f"Mobile: {mob}\nGST: {gst}\n{addr}")
            self._list.addItem(it)

    def _filter(self, text):
        self._populate(text)

    def _on_pick(self, item):
        cid = item.data(Qt.ItemDataRole.UserRole)
        self._selected_cid = cid
        self._display.setText(item.text())
        self._popup.hide()
        if self._on_change:
            self._on_change()

    def eventFilter(self, obj, ev):
        if obj is self._search and ev.type() == QEvent.Type.KeyPress:
            key = ev.key()
            if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                if self._list.count():
                    self._on_pick(self._list.item(0))
                return True
            if key == Qt.Key.Key_Escape:
                self._popup.hide()
                return True
        return super().eventFilter(obj, ev)


# =========================================================================== #
# Searchable product combo (unchanged)
# =========================================================================== #
class _ProductFilterCombo(QWidget):
    def __init__(self, parent=None, on_change=None,
                 placeholder="Select product"):
        super().__init__(parent)
        self._on_change = on_change
        self._selected_name = None
        self._products = []

        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        self._display = QLineEdit()
        self._display.setReadOnly(True)
        self._display.setPlaceholderText(placeholder)
        self._display.setClearButtonEnabled(True)
        self._display.setFixedHeight(30)
        self._display.setCursor(Qt.CursorShape.PointingHandCursor)
        self._display.setStyleSheet(
            "QLineEdit { border: 1px solid #d2d6de; border-radius: 3px;"
            " padding: 0 6px; background: #ffffff; }"
            "QLineEdit:hover { border-color: #a8b8c8; }")
        lay.addWidget(self._display, 1)
        self._display.mousePressEvent = self._on_display_clicked

        self._popup = QFrame()
        self._popup.setWindowFlags(
            Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self._popup.setStyleSheet(
            "QFrame { background: #ffffff; border: 1px solid #d2d6de; }")
        pv = QVBoxLayout(self._popup)
        pv.setContentsMargins(0, 0, 0, 0)
        pv.setSpacing(0)

        self._search = QLineEdit()
        self._search.setPlaceholderText("Type to search...")
        self._search.setClearButtonEnabled(True)
        self._search.setStyleSheet(
            "QLineEdit { border: none; border-bottom: 1px solid #e5e5e5;"
            " padding: 6px 8px; background: #ffffff; }")
        self._search.textChanged.connect(self._filter)
        pv.addWidget(self._search)

        self._list = QListWidget()
        self._list.setStyleSheet(
            "QListWidget { border: none; background: #ffffff; }"
            "QListWidget::item { padding: 6px 8px; }"
            "QListWidget::item:selected { background: #3c8dbc; color: #fff; }")
        self._list.setMinimumHeight(180)
        self._list.setMaximumHeight(280)
        self._list.itemClicked.connect(self._on_pick)
        pv.addWidget(self._list)
        self._search.installEventFilter(self)

    def set_products(self, products):
        self._products = products or []

    def current_name(self):
        return self._selected_name

    def clear(self):
        self._selected_name = None
        self._display.clear()

    def _on_display_clicked(self, ev):
        self._show_popup()

    def _show_popup(self):
        self._search.blockSignals(True)
        self._search.clear()
        self._search.blockSignals(False)
        self._populate("")
        gp = self.mapToGlobal(self.rect().bottomLeft())
        self._popup.setFixedWidth(max(self.width(), 280))
        self._popup.move(gp)
        self._popup.show()
        self._search.setFocus()

    def _populate(self, needle):
        self._list.clear()
        needle = (needle or "").lower().strip()
        all_it = QListWidgetItem("All Products")
        all_it.setData(Qt.ItemDataRole.UserRole, None)
        self._list.addItem(all_it)
        for p in self._products:
            name = p.get("name") or ""
            desc = p.get("description") or ""
            hsn = str(p.get("hsn") or "")
            hay = f"{name} {desc} {hsn}".lower()
            if needle and needle not in hay:
                continue
            it = QListWidgetItem(name or "(unnamed)")
            it.setData(Qt.ItemDataRole.UserRole, name)
            if desc or hsn:
                it.setToolTip(f"HSN: {hsn}\n{desc}")
            self._list.addItem(it)

    def _filter(self, text):
        self._populate(text)

    def _on_pick(self, item):
        name = item.data(Qt.ItemDataRole.UserRole)
        self._selected_name = name
        self._display.setText(name or "")
        self._popup.hide()
        if self._on_change:
            self._on_change()

    def eventFilter(self, obj, ev):
        if obj is self._search and ev.type() == QEvent.Type.KeyPress:
            key = ev.key()
            if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                if self._list.count():
                    self._on_pick(self._list.item(0))
                return True
            if key == Qt.Key.Key_Escape:
                self._popup.hide()
                return True
        return super().eventFilter(obj, ev)


# =========================================================================== #
# InvoiceGenPage
# =========================================================================== #
class InvoiceGenPage(QWidget):
    def __init__(self, main, doc, edit_orderid=None):
        super().__init__()
        self.main = main
        self.doc = doc
        self.reg = DOC_REGISTRY[doc]
        self.edit_orderid = edit_orderid
        self.title = (f"Edit {self.reg['label']}" if edit_orderid
                      else f"Generate {self.reg['label']}")
        gen_label = ("Supplier Invoice" if doc == "purchase"
                     else self.reg["label"])
        self.breadcrumb = (f"Edit {gen_label}" if edit_orderid
                           else f"Generate {gen_label}")
        self.products = db_manager.list_products()
        self.clients = db_manager.list_clients(
            u_type=1 if doc == "purchase" else 0)
        self._build()
        if edit_orderid:
            self._load_existing(edit_orderid)

    # ------------------------------------------------------------------ UI
    def _build(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        outer.addWidget(W.PageHeader(self.title,
                                     breadcrumb=self.breadcrumb))

        page_scroll = QScrollArea()
        page_scroll.setWidgetResizable(True)
        page_scroll.setFrameShape(QFrame.Shape.NoFrame)
        page_scroll.setStyleSheet(
            "QScrollArea { border: none; background: transparent; }")
        outer.addWidget(page_scroll, 1)

        page_inner = QWidget()
        page_inner.setStyleSheet("background: transparent;")
        page_scroll.setWidget(page_inner)

        page_lay = QVBoxLayout(page_inner)
        page_lay.setContentsMargins(0, 0, 0, 0)
        page_lay.setSpacing(0)

        card = QFrame()
        card.setObjectName("InvoiceGenCard")
        card.setStyleSheet("""
            QFrame#InvoiceGenCard {
                background: #ffffff;
                border: 1px solid #d2d6de;
                border-top: 3px solid #3c8dbc;
                border-radius: 3px;
            }
            QFrame#InvoiceGenCard QLabel {
                background: transparent;
                border: none;
                color: #333;
                font-size: 12.5px;
            }
            QFrame#InvoiceGenCard QLineEdit,
            QFrame#InvoiceGenCard QPlainTextEdit,
            QFrame#InvoiceGenCard QComboBox,
            QFrame#InvoiceGenCard QDateEdit {
                background: #ffffff;
                border: 1px solid #d2d6de;
                border-radius: 3px;
                padding: 0 6px;
                min-height: 28px;
            }
            QFrame#InvoiceGenCard QLineEdit:focus,
            QFrame#InvoiceGenCard QPlainTextEdit:focus,
            QFrame#InvoiceGenCard QComboBox:focus,
            QFrame#InvoiceGenCard QDateEdit:focus {
                border-color: #3c8dbc;
            }
        """)

        card_lay = QVBoxLayout(card)
        card_lay.setContentsMargins(20, 4, 20, 18)
        card_lay.setSpacing(16)

        form = QGridLayout()
        form.setHorizontalSpacing(14)
        form.setVerticalSpacing(10)
        form.setColumnStretch(1, 1)
        form.setColumnStretch(3, 1)
        form.setColumnMinimumWidth(0, 110)
        form.setColumnMinimumWidth(2, 130)

        form.setRowMinimumHeight(0, 20)
        form.setRowStretch(0, 0)

        lbl_inv = QLabel("Invoice ID *")
        lbl_inv.setAlignment(Qt.AlignmentFlag.AlignRight |
                             Qt.AlignmentFlag.AlignVCenter)
        form.addWidget(lbl_inv, 1, 0)

        self.invid = QLineEdit()
        self.invid.setFixedHeight(30)
        form.addWidget(self.invid, 1, 1)

        lbl_sup = QLabel("Supplier Name *" if self.doc == "purchase"
                         else "Client Name *")
        lbl_sup.setAlignment(Qt.AlignmentFlag.AlignRight |
                             Qt.AlignmentFlag.AlignVCenter)
        form.addWidget(lbl_sup, 1, 2)

        self.client_combo = _ClientFilterCombo(
            on_change=self._client_changed,
            placeholder="Select a Person or Company")
        self.client_combo.setFixedHeight(30)
        self.client_combo.set_clients(self.clients)
        form.addWidget(self.client_combo, 1, 3)

        lbl_date = QLabel("Invoice Date")
        lbl_date.setAlignment(Qt.AlignmentFlag.AlignRight |
                              Qt.AlignmentFlag.AlignVCenter)
        form.addWidget(lbl_date, 2, 0)

        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("dd-MM-yyyy")
        self.date_edit.setDate(QDate.currentDate())
        self.date_edit.setFixedHeight(30)
        form.addWidget(self.date_edit, 2, 1)

        lbl_addr = QLabel("Address")
        lbl_addr.setAlignment(Qt.AlignmentFlag.AlignRight |
                              Qt.AlignmentFlag.AlignVCenter)
        form.addWidget(lbl_addr, 2, 2)

        self.address = QPlainTextEdit()
        self.address.setFixedHeight(70)
        form.addWidget(self.address, 2, 3)

        card_lay.addLayout(form)

        cols = ["", "Item No", "Item Name *", "Description Name",
                "HSN *", "Qty *", "Price *", "Total *", ""]
        self.items_table = QTableWidget(0, len(cols))
        self.items_table.setHorizontalHeaderLabels(cols)
        self.items_table.verticalHeader().setVisible(False)
        self.items_table.verticalHeader().setDefaultSectionSize(32)

        self.items_table.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.items_table.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.items_table.setSizePolicy(QSizePolicy.Policy.Expanding,
                                       QSizePolicy.Policy.Fixed)
        self.items_table.setMinimumHeight(60)

        self.items_table.setStyleSheet(
            "QTableWidget {"
            "  border: 1px solid #d2d6de;"
            "  background: #ffffff;"
            "  gridline-color: #e5e5e5;"
            "}"
            "QTableWidget::item { padding: 2px; }"
            "QHeaderView::section {"
            "  background: #f9f9f9;"
            "  color: #333;"
            "  border: none;"
            "  border-right: 1px solid #e5e5e5;"
            "  border-bottom: 1px solid #e5e5e5;"
            "  padding: 6px;"
            "  font-size: 11.5px;"
            "}")

        hh = self.items_table.horizontalHeader()
        hh.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        hh.setStretchLastSection(False)

        fixed = {0: 28, 1: 60, 4: 80, 5: 55, 6: 90, 7: 110, 8: 76}
        for i, w in fixed.items():
            self.items_table.setColumnWidth(i, w)

        hh.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)

        for c in (1, 4, 5, 6, 7):
            hitem = self.items_table.horizontalHeaderItem(c)
            if hitem is not None:
                hitem.setTextAlignment(
                    Qt.AlignmentFlag.AlignCenter |
                    Qt.AlignmentFlag.AlignVCenter)

        card_lay.addWidget(self.items_table)

        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(24)

        notes_col = QVBoxLayout()
        notes_col.setSpacing(6)

        notes_lbl = QLabel("Notes:")
        notes_lbl.setStyleSheet(
            "font-size: 15px; font-weight: 600; color: #333;"
            " background: transparent; border: none;")
        notes_col.addWidget(notes_lbl)

        self.notes = QPlainTextEdit()
        self.notes.setPlaceholderText("Your Notes")
        self.notes.setFixedHeight(90)
        self.notes.setStyleSheet(
            "QPlainTextEdit {"
            "  background: #ffffff;"
            "  border: 1px solid #d2d6de;"
            "  border-radius: 3px;"
            "  padding: 4px 6px;"
            "}")
        notes_col.addWidget(self.notes, 0)

        self.save_btn = QPushButton(
            "Submit" if not self.edit_orderid else "Update Invoice")
        self.save_btn.setFixedHeight(48)
        self.save_btn.setMinimumWidth(320)
        self.save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.save_btn.setStyleSheet(
            "QPushButton {"
            "  background: #00a65a; color: #ffffff;"
            "  border: 1px solid #008d4c;"
            "  border-radius: 3px;"
            "  padding: 8px 40px;"
            "  font-weight: 700;"
            "  font-size: 16px;"
            "  letter-spacing: 0.6px;"
            "}"
            "QPushButton:hover { background: #008d4c; }"
            "QPushButton:pressed { background: #008041; }")
        self.save_btn.clicked.connect(self._save)
        notes_col.addWidget(self.save_btn, 0, Qt.AlignmentFlag.AlignLeft)

        notes_col.addStretch(1)

        bottom_row.addLayout(notes_col, 3)

        totals_box = QFrame()
        totals_box.setStyleSheet(
            "QFrame { background: #ffffff; border: none; }")
        totals = QGridLayout(totals_box)
        totals.setContentsMargins(0, 0, 0, 0)
        totals.setHorizontalSpacing(6)
        totals.setVerticalSpacing(4)

        self.subtotal = QLineEdit("0")
        self.tax_rate = QLineEdit("0")
        self.tax_amount = QLineEdit("0")
        self.total_amount = QLineEdit("0")

        def _money_field(edit):
            edit.setReadOnly(True)
            edit.setFixedHeight(30)
            edit.setStyleSheet(
                "QLineEdit {"
                "  background: #f7f9fb;"
                "  border: 1px solid #d2d6de;"
                "  border-radius: 3px;"
                "  padding: 0 6px;"
                "}")
            edit.setAlignment(Qt.AlignmentFlag.AlignRight |
                              Qt.AlignmentFlag.AlignVCenter)
            return edit

        _money_field(self.subtotal)
        _money_field(self.tax_amount)
        _money_field(self.total_amount)

        self.tax_rate.setFixedHeight(30)
        self.tax_rate.setStyleSheet(
            "QLineEdit {"
            "  background: #ffffff;"
            "  border: 1px solid #d2d6de;"
            "  border-top-right-radius: 0;"
            "  border-bottom-right-radius: 0;"
            "  padding: 0 6px;"
            "}")
        self.tax_rate.setAlignment(Qt.AlignmentFlag.AlignRight |
                                   Qt.AlignmentFlag.AlignVCenter)

        rows = (("Subtotal *", self.subtotal, None),
                ("Tax Rate *", self.tax_rate, "%"),
                ("Tax Amount *", self.tax_amount, None),
                ("Total *", self.total_amount, None))
        for r, (label_text, field, unit) in enumerate(rows):
            lbl = QLabel(label_text)
            lbl.setStyleSheet(
                "font-size: 12px; font-weight: 600; color: #333;"
                " background: transparent; border: none;")
            totals.addWidget(lbl, r * 2, 0, 1, 2)

            if unit:
                wrap = QWidget()
                hl = QHBoxLayout(wrap)
                hl.setContentsMargins(0, 0, 0, 0)
                hl.setSpacing(0)
                hl.addWidget(field, 1)

                u = QLabel(unit)
                u.setFixedHeight(30)
                u.setStyleSheet(
                    "QLabel {"
                    "  background: #f4f4f4;"
                    "  color: #666;"
                    "  border: 1px solid #d2d6de;"
                    "  border-left: none;"
                    "  border-top-right-radius: 3px;"
                    "  border-bottom-right-radius: 3px;"
                    "  padding: 0 8px;"
                    "}")
                u.setAlignment(Qt.AlignmentFlag.AlignCenter)
                hl.addWidget(u)
                totals.addWidget(wrap, r * 2 + 1, 0, 1, 2)
            else:
                totals.addWidget(field, r * 2 + 1, 0, 1, 2)

            if r < len(rows) - 1:
                totals.setRowMinimumHeight(r * 2 + 1, 30)

        totals.setColumnStretch(0, 1)
        bottom_row.addWidget(totals_box, 2)

        card_lay.addLayout(bottom_row)

        page_lay.addWidget(card)

        self.tax_rate.textChanged.connect(self._recalc)

        if not self.edit_orderid:
            self.invid.setText(db_manager.next_invoice_no(self.doc))
            self._add_row()
            if self.clients:
                self._client_changed()
        self._autosize_items_table()

    # ------------------------------------------------------------- helpers
    def _autosize_items_table(self):
        header_h = self.items_table.horizontalHeader().height()
        rows = self.items_table.rowCount()
        row_h = self.items_table.verticalHeader().defaultSectionSize()
        target = header_h + rows * row_h + 2
        self.items_table.setFixedHeight(max(60, target))

    # ------------------------------------------------------------- behaviour
    def _client_changed(self):
        cid = self.client_combo.current_cid()
        if cid is None:
            return
        c = next((x for x in self.clients if x["cid"] == cid), None)
        if c:
            self.address.setPlainText(c["c_add"] or "")

    def _add_row(self, data=None):
        data = data or {}
        r = self.items_table.rowCount()
        self.items_table.insertRow(r)

        chk = QTableWidgetItem("")
        chk.setFlags(Qt.ItemFlag.ItemIsUserCheckable |
                     Qt.ItemFlag.ItemIsEnabled)
        chk.setCheckState(Qt.CheckState.Unchecked)
        chk.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.items_table.setItem(r, 0, chk)

        no = QTableWidgetItem(str(data.get("orderno", r + 1)))
        no.setTextAlignment(Qt.AlignmentFlag.AlignCenter |
                           Qt.AlignmentFlag.AlignVCenter)
        self.items_table.setItem(r, 1, no)

        combo = QComboBox()
        combo.addItem("Select Item", None)
        for p in self.products:
            combo.addItem(p["name"], p["p_id"])
        if data.get("item_name"):
            idx = combo.findText(data["item_name"])
            if idx >= 0:
                combo.setCurrentIndex(idx)
            else:
                combo.addItem(data["item_name"], -1)
                combo.setCurrentIndex(combo.count() - 1)
        combo.currentIndexChanged.connect(
            lambda _, row=r, cb=combo: self._item_picked(row, cb))
        self.items_table.setCellWidget(r, 2, combo)

        desc = QLineEdit(data.get("item_desc") or "")
        self.items_table.setCellWidget(r, 3, desc)
        hsn = QLineEdit(str(data.get("hsn", "8443")))
        hsn.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.items_table.setCellWidget(r, 4, hsn)
        qty = QLineEdit(str(data.get("quantity", 1)))
        qty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        qty.textChanged.connect(self._recalc)
        self.items_table.setCellWidget(r, 5, qty)
        price = QLineEdit(str(data.get("price", "")))
        price.setAlignment(Qt.AlignmentFlag.AlignCenter)
        price.textChanged.connect(self._recalc)
        self.items_table.setCellWidget(r, 6, price)
        total = QLineEdit(str(data.get("total", "")))
        total.setAlignment(Qt.AlignmentFlag.AlignCenter)
        total.setReadOnly(True)
        total.setStyleSheet("background:#f7f9fb;")
        self.items_table.setCellWidget(r, 7, total)

        cell = QWidget()
        h = QHBoxLayout(cell)
        h.setContentsMargins(2, 2, 2, 2)
        h.setSpacing(4)

        add_btn = QPushButton()
        add_btn.setFixedSize(26, 26)
        add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_btn.setIcon(_plus_icon("#ffffff", 14))
        add_btn.setIconSize(QSize(14, 14))
        add_btn.setToolTip("Add row")
        add_btn.setStyleSheet(
            "QPushButton { background:#00a65a; border:1px solid #008d4c;"
            " border-radius:3px; padding:0; }"
            "QPushButton:hover { background:#008d4c; }")
        add_btn.clicked.connect(lambda _=False, b=add_btn: self._add_after(b))

        del_btn = QPushButton()
        del_btn.setFixedSize(26, 26)
        del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        del_btn.setIcon(_minus_icon("#ffffff", 14))
        del_btn.setIconSize(QSize(14, 14))
        del_btn.setToolTip("Remove row")
        del_btn.setStyleSheet(
            "QPushButton { background:#dd4b39; border:1px solid #d73925;"
            " border-radius:3px; padding:0; }"
            "QPushButton:hover { background:#d73925; }")
        del_btn.clicked.connect(lambda _=False, b=del_btn: self._remove_row_of(b))

        h.addWidget(add_btn)
        h.addWidget(del_btn)
        h.addStretch()
        self.items_table.setCellWidget(r, 8, cell)

        self._autosize_items_table()
        self._recalc()

    def _add_after(self, btn):
        for r in range(self.items_table.rowCount()):
            w = self.items_table.cellWidget(r, 8)
            if w is None:
                continue
            for i in range(w.layout().count()):
                item = w.layout().itemAt(i)
                if item and item.widget() is btn:
                    self._add_row()
                    self._renumber()
                    self._recalc()
                    return
        self._add_row()

    def _remove_row_of(self, btn):
        for r in range(self.items_table.rowCount()):
            w = self.items_table.cellWidget(r, 8)
            if w is None:
                continue
            for i in range(w.layout().count()):
                item = w.layout().itemAt(i)
                if item and item.widget() is btn:
                    self._remove_row(r)
                    return

    def _remove_row(self, row):
        if self.items_table.rowCount() <= 1:
            return
        self.items_table.removeRow(row)
        self._renumber()
        self._autosize_items_table()
        self._recalc()

    def _renumber(self):
        for r in range(self.items_table.rowCount()):
            it = self.items_table.item(r, 1)
            if it is not None:
                it.setText(str(r + 1))

    def _item_picked(self, row, combo):
        p_id = combo.currentData()
        if not p_id:
            return
        p = next((x for x in self.products if x["p_id"] == p_id), None)
        if p:
            self.items_table.cellWidget(row, 3).setText(p["description"] or "")
            self.items_table.cellWidget(row, 4).setText(str(p["hsn"] or 8443))

    def _recalc(self):
        subtotal = 0.0
        for r in range(self.items_table.rowCount()):
            try:
                qty_w = self.items_table.cellWidget(r, 5)
                price_w = self.items_table.cellWidget(r, 6)
                if qty_w is None or price_w is None:
                    continue
                qty = float(qty_w.text() or 0)
                price = float(price_w.text() or 0)
            except ValueError:
                qty = price = 0.0
            t = qty * price
            subtotal += t
            tot_w = self.items_table.cellWidget(r, 7)
            if tot_w is not None:
                tot_w.setText(f"{t:.2f}")
        self.subtotal.setText(f"{subtotal:.2f}")
        try:
            rate = float(self.tax_rate.text() or 0)
        except ValueError:
            rate = 0.0
        tax = subtotal * rate / 100.0
        self.tax_amount.setText(f"{tax:.2f}")
        self.total_amount.setText(f"{subtotal + tax:.2f}")

    def _collect_items(self):
        items = []
        for r in range(self.items_table.rowCount()):
            combo = self.items_table.cellWidget(r, 2)
            if combo is None or combo.currentIndex() <= 0:
                continue
            try:
                qty = int(float(self.items_table.cellWidget(r, 5).text() or 0))
                price = int(float(self.items_table.cellWidget(r, 6).text() or 0))
            except ValueError:
                qty = price = 0
            items.append({
                "orderno": r + 1,
                "orderid": "",
                "item_name": combo.currentText(),
                "item_desc": self.items_table.cellWidget(r, 3).text(),
                "hsn": int(self.items_table.cellWidget(r, 4).text() or 8443),
                "quantity": qty,
                "price": price,
                "total": qty * price,
            })
        return items

    def _load_existing(self, orderid):
        master, items = db_manager.get_invoice(self.doc, orderid)
        if not master:
            return
        self.invid.setText(master["invid"])

        # Set the client WITHOUT triggering the on_change callback
        saved_cb = self.client_combo._on_change
        self.client_combo._on_change = None
        try:
            if master.get("cid") is not None:
                self.client_combo.set_cid(master["cid"])
        finally:
            self.client_combo._on_change = saved_cb

        # SQLite stores dates as TEXT; _to_date() handles both shapes.
        d = _to_date(master.get("created") or master.get("invdate"))
        self.date_edit.setDate(QDate(d.year, d.month, d.day))
        self.address.setPlainText(master.get("c_add") or "")
        self.notes.setPlainText(master.get("note", "") or "")
        self.subtotal.setText(str(master.get("subtotal", 0)))
        self.tax_rate.setText(str(master.get("taxrate", 0)))
        self.tax_amount.setText(str(master.get("taxamount", 0)))
        self.total_amount.setText(str(master.get("totalamount", 0)))
        self.items_table.setRowCount(0)
        for it in items:
            self._add_row(it)
        self._autosize_items_table()

    def _save(self):
        cid = self.client_combo.current_cid()
        items = self._collect_items()
        if cid is None:
            W.error(self, "Please select a client.")
            return
        if not items:
            W.error(self, "Please add at least one item row.")
            return
        self._recalc()
        invid = self.invid.text().strip()
        orderid = self.edit_orderid or f"ORD{invid.replace('/', '')}"
        d = self.date_edit.date()
        doc_date = date(d.year(), d.month(), d.day())
        master = {"invid": invid, "cid": cid,
                  "orderid": orderid,
                  "totalitems": len(items),
                  "subtotal": int(float(self.subtotal.text() or 0)),
                  "taxrate": int(float(self.tax_rate.text() or 0)),
                  "taxamount": int(float(self.tax_amount.text() or 0)),
                  "totalamount": int(float(self.total_amount.text() or 0)),
                  "created": doc_date}
        if self.doc == "quote":
            master["note"] = self.notes.toPlainText().strip()[:300]
        for it in items:
            it["orderid"] = orderid
        try:
            if self.edit_orderid:
                db_manager.update_invoice(self.doc, self.edit_orderid,
                                          master, items)
            else:
                if self.doc == "purchase":
                    master["invdate"] = doc_date
                db_manager.insert_invoice(self.doc, master, items)
        except Exception as exc:
            W.error(self, f"Save failed: {exc}")
            return
        W.success(self, f"{self.reg['label']} {invid} saved successfully.")

        # Attach client fields needed by the print invoice builder so mob,
        # gst, tax type, and country are available in the rendered PDF/HTML.
        # (Purchase needs this too: the purchase print shows supplier name,
        # address, mob and tax id.)
        if cid:
            try:
                _client = db_manager.get_client(cid)
                if _client:
                    master["c_name"] = _client.get("c_name") or ""
                    master["c_add"] = _client.get("c_add") or ""
                    master["mob"] = _client.get("mob") or ""
                    master["gst"] = _client.get("gst") or ""
                    master["c_type"] = _client.get("c_type") or ""
                    master["country"] = _client.get("country") or ""
            except Exception:
                pass

        # Save current page state (client + items) so we can restore it after
        # the print window closes. Only the invoice number changes.
        self._saved_cid = self.client_combo.current_cid()
        self._saved_items_data = self._collect_items()

        # Show print preview instead of redirecting to list.
        # When the print window is closed, refresh this generate page with a
        # brand-new invoice number so the user can issue another one easily.
        dlg = invoice_print.show_invoice_view(
            self, self.doc, master, items,
            title=f"{self.reg['label']} {invid}")
        if dlg is not None:
            dlg.finished.connect(
                lambda _result, page=self: page._refresh_after_print())

    # ------------------------------------------------------------- helpers
    def _refresh_after_print(self):
        """Refresh this generate page with a brand-new invoice number once the
        print window has closed. Resets the client combo, items and address so
        the user can start a fresh document."""
        # Edit mode: don't wipe the form — go back to the list instead.
        if self.edit_orderid:
            try:
                self.main.navigate(f"{self.doc}_list")
            except Exception:
                pass
            return
        # Fetch the NEXT number now that the previous one is saved, so the
        # page never shows a stale/duplicate number (0006 -> 0007).
        try:
            self.invid.setText(db_manager.next_invoice_no(self.doc))
        except Exception:
            pass

        # Reset client combo
        if getattr(self, "_saved_cid", None) is not None:
            saved = self.client_combo._on_change
            self.client_combo._on_change = None
            try:
                self.client_combo.set_cid(None)
            finally:
                self.client_combo._on_change = saved
        # Reset client name and address
        self.address.setPlainText("")
        # Reset items table (keep one empty row, like a fresh generate page)
        self.items_table.setRowCount(0)
        self._add_row()
        self._autosize_items_table()

    def refresh(self):
        """Called by MainWindow.navigate() every time the page is opened.

        Generate pages are cached, so without this the invoice number stays
        frozen at its construction-time value (e.g. 0006 forever). Refreshing
        here guarantees 0006 -> 0007 on every reopen. Edit mode keeps its
        existing number.
        """
        if self.edit_orderid:
            return
        # Don't clobber a number the user just saved-but-not-printed yet;
        # _refresh_after_print() already advanced it. Only advance when the
        # current text is no longer the live "next" number... simplest robust
        # rule: always sync to live next number when the form is pristine
        # (no client + single empty row), otherwise leave user input alone.
        try:
            pristine = (self.client_combo.current_cid() is None
                         and self.items_table.rowCount() <= 1)
            if pristine:
                self.invid.setText(db_manager.next_invoice_no(self.doc))
        except Exception:
            pass

# =========================================================================== #
# InvoiceListPage
# =========================================================================== #
class InvoiceListPage(QWidget):
    CARDS_PER_PAGE = 12
    COLS = 4

    def __init__(self, main, doc):
        super().__init__()
        self.main = main
        self.doc = doc
        self.reg = DOC_REGISTRY[doc]
        self.title = f"{self.reg['label']} List"

        self._all_rows = []
        self._page = 1
        self._filter_client = None
        self._filter_product = None
        self._filter_year = None
        self._item_names = {}

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)
        lay.addWidget(W.PageHeader(self.title))

        filter_box = QFrame()
        filter_box.setObjectName("InvoiceFilterBar")
        filter_box.setStyleSheet(
            "QFrame#InvoiceFilterBar {"
            "  background: #ffffff;"
            "  border: 1px solid #d2d6de;"
            "  border-radius: 3px;"
            "}")
        fbar = QHBoxLayout(filter_box)
        fbar.setContentsMargins(14, 8, 14, 8)
        fbar.setSpacing(18)

        fic = QLabel()
        fic.setFixedSize(24, 24)
        fic.setPixmap(_funnel_pixmap(22, "#222"))
        fic.setAlignment(Qt.AlignmentFlag.AlignCenter)
        fbar.addWidget(fic)

        client_col = QVBoxLayout()
        client_col.setSpacing(2)
        c_lbl = QLabel("Select Client:")
        c_lbl.setStyleSheet("font-size: 12px; color: #333;")
        client_col.addWidget(c_lbl)
        self.client_combo = _ClientFilterCombo(
            on_change=self._on_filter_changed,
            placeholder="Select a Person or Company")
        self.client_combo.setFixedWidth(320)
        try:
            self.client_combo.set_clients(
                db_manager.list_clients(
                    u_type=1 if doc == "purchase" else 0))
        except Exception:
            self.client_combo.set_clients([])
        client_col.addWidget(self.client_combo)
        cw = QWidget(); cw.setLayout(client_col)
        fbar.addWidget(cw, 0)

        prod_col = QVBoxLayout()
        prod_col.setSpacing(2)
        p_lbl = QLabel("Select Product:")
        p_lbl.setStyleSheet("font-size: 12px; color: #333;")
        prod_col.addWidget(p_lbl)
        self.product_combo = _ProductFilterCombo(
            on_change=self._on_filter_changed,
            placeholder="Select product")
        self.product_combo.setFixedWidth(260)
        try:
            self.product_combo.set_products(db_manager.list_products())
        except Exception:
            self.product_combo.set_products([])
        prod_col.addWidget(self.product_combo)
        pw = QWidget(); pw.setLayout(prod_col)
        fbar.addWidget(pw, 0)

        year_col = QVBoxLayout()
        year_col.setSpacing(2)
        y_lbl = QLabel("Select Year:")
        y_lbl.setStyleSheet("font-size: 12px; color: #333;")
        year_col.addWidget(y_lbl)
        self.year_combo = QComboBox()
        self.year_combo.setFixedHeight(30)
        self.year_combo.setFixedWidth(180)
        self.year_combo.addItem("Select Year", None)
        y = date.today().year
        for i in range(6):
            fy = (f"{y - i - 1}-{y - i}" if date.today().month <= 3
                  else f"{y - i}-{y - i + 1}")
            if self.year_combo.findData(fy) < 0:
                self.year_combo.addItem(fy, fy)
        self.year_combo.currentIndexChanged.connect(self._on_filter_changed)
        year_col.addWidget(self.year_combo)
        yw = QWidget(); yw.setLayout(year_col)
        fbar.addWidget(yw, 0)

        fbar.addStretch()
        lay.addWidget(filter_box)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet(
            "QScrollArea { border: none; background: transparent; }")
        self.cards_host = QWidget()
        self.cards_host.setStyleSheet("background: transparent;")
        self.cards_grid = QGridLayout(self.cards_host)
        self.cards_grid.setContentsMargins(0, 0, 0, 0)
        self.cards_grid.setHorizontalSpacing(10)
        self.cards_grid.setVerticalSpacing(10)
        self.scroll.setWidget(self.cards_host)
        lay.addWidget(self.scroll, 1)

        self.page_bar = QHBoxLayout()
        self.page_bar.setContentsMargins(0, 2, 0, 0)
        self.page_bar.addStretch()
        self.page_buttons_host = QWidget()
        self.page_buttons = QHBoxLayout(self.page_buttons_host)
        self.page_buttons.setContentsMargins(0, 0, 0, 0)
        self.page_buttons.setSpacing(4)
        self.page_bar.addWidget(self.page_buttons_host)
        self.page_bar.addStretch()
        lay.addLayout(self.page_bar)

        self.refresh()

    def refresh(self):
        try:
            self._all_rows = db_manager.list_invoices(
                self.doc, "1900-01-01", "2999-12-31", "")
        except Exception as exc:
            W.error(self, f"Database error: {exc}")
            self._all_rows = []
        self._page = 1
        self._render()

    def _on_filter_changed(self):
        self._filter_client = self.client_combo.current_cid()
        self._filter_product = self.product_combo.current_name()
        self._filter_year = self.year_combo.currentData()
        self._page = 1
        self._render()

    def _filtered_rows(self):
        rows = self._all_rows
        if self._filter_client:
            rows = [r for r in rows if r.get("cid") == self._filter_client]
        if self._filter_product:
            rows = [r for r in rows
                    if (self._item_names.get(r.get("orderid"), "")
                        or r.get("item_name") or "") == self._filter_product]
        if self._filter_year:
            rows = [r for r in rows
                    if self._row_fy(r) == self._filter_year]
        return rows

    def _row_fy(self, r):
        """
        Compute the financial year (Apr–Mar) label from the row's date.
        SQLite returns dates as TEXT so this handles both shapes.
        """
        dc = self.reg["date_col"]
        try:
            d = r[dc]
            if isinstance(d, str):
                d = datetime.fromisoformat(d.split(" ")[0]).date()
            elif isinstance(d, datetime):
                d = d.date()
            yr = d.year
            if d.month > 3:
                return f"{yr}-{yr + 1}"
            return f"{yr - 1}-{yr}"
        except Exception:
            return ""

    def _render(self):
        while self.cards_grid.count():
            item = self.cards_grid.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        rows = self._filtered_rows()
        total = len(rows)
        total_pages = max(1, (total + self.CARDS_PER_PAGE - 1)
                          // self.CARDS_PER_PAGE)
        self._page = max(1, min(self._page, total_pages))
        start = (self._page - 1) * self.CARDS_PER_PAGE
        page_rows = rows[start:start + self.CARDS_PER_PAGE]

        self._item_names = {}
        try:
            self._item_names = _first_item_names_for(
                self.doc, [r["orderid"] for r in page_rows])
        except Exception:
            self._item_names = {}

        if not page_rows:
            empty = QLabel("No records found.")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setStyleSheet("color:#dd4b39; font-size:14px;"
                                " padding: 40px;")
            self.cards_grid.addWidget(empty, 0, 0, 1, self.COLS)
        else:
            for i, r in enumerate(page_rows):
                card = self._build_card(r)
                self.cards_grid.addWidget(card, i // self.COLS,
                                          i % self.COLS)

        for c in range(self.COLS):
            self.cards_grid.setColumnStretch(c, 1)
        self.cards_grid.setRowStretch(self.cards_grid.rowCount(), 1)

        self._render_pager(total_pages)

    def _render_pager(self, total_pages):
        while self.page_buttons.count():
            item = self.page_buttons.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        def add_btn(label, page, enabled=True, active=False):
            b = QPushButton(label)
            b.setFixedHeight(28)
            b.setMinimumWidth(34)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            if active:
                b.setStyleSheet(
                    "QPushButton { background:#3c8dbc; color:#fff;"
                    " border:1px solid #367fa9; border-radius:3px;"
                    " font-weight:600; }")
                b.setEnabled(False)
            else:
                b.setStyleSheet(
                    "QPushButton { background:#f4f4f4; color:#444;"
                    " border:1px solid #d2d6de; border-radius:3px; }"
                    "QPushButton:hover { background:#e7e7e7; }"
                    "QPushButton:disabled { color:#aaa; }")
                b.setEnabled(enabled)
            if enabled and not active:
                b.clicked.connect(lambda _, p=page: self._goto(p))
            self.page_buttons.addWidget(b)

        add_btn("Prev", self._page - 1, enabled=self._page > 1)

        window = 7
        lo = max(1, self._page - window // 2)
        hi = min(total_pages, lo + window - 1)
        lo = max(1, hi - window + 1)
        if lo > 1:
            add_btn("1", 1, active=(self._page == 1))
            if lo > 2:
                dots = QLabel("…")
                dots.setStyleSheet("color:#888; padding:0 4px;")
                self.page_buttons.addWidget(dots)
        for p in range(lo, hi + 1):
            add_btn(str(p), p, active=(p == self._page))
        if hi < total_pages:
            if hi < total_pages - 1:
                dots = QLabel("…")
                dots.setStyleSheet("color:#888; padding:0 4px;")
                self.page_buttons.addWidget(dots)
            add_btn(str(total_pages), total_pages,
                    active=(self._page == total_pages))

        add_btn("Next", self._page + 1, enabled=self._page < total_pages)

    def _goto(self, page):
        self._page = max(1, page)
        self._render()

    def _build_card(self, r):
        card = QFrame()
        card.setStyleSheet(
            "QFrame { background: #ffffff; border: 1px solid #d2d6de;"
            " border-top: 3px solid #3c8dbc; border-radius: 3px; }")
        card.setSizePolicy(QSizePolicy.Policy.Preferred,
                           QSizePolicy.Policy.Fixed)
        v = QVBoxLayout(card)
        v.setContentsMargins(8, 8, 8, 8)
        v.setSpacing(4)

        invid_lbl = QLabel(str(r.get("invid", "")))
        invid_lbl.setStyleSheet(
            "font-size: 13px; font-weight: 600; color: #444;"
            " background: transparent; border: none;")
        invid_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v.addWidget(invid_lbl)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("background:#e5e5e5; max-height:1px;")
        v.addWidget(sep)

        def row_line(title, value, color="#333"):
            if title:
                lbl = QLabel(f"<span style='color:#666;'>{title}:</span> "
                             f"<b style='color:{color};'>{value}</b>")
            else:
                lbl = QLabel(f"<b style='color:{color};'>{value}</b>")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setWordWrap(True)
            lbl.setStyleSheet("background: transparent; border: none;"
                              " font-size: 11.5px;")
            return lbl

        oid = r.get("orderid")
        item_name = (self._item_names.get(oid)
                     or r.get("item_name")
                     or "").strip()
        if item_name:
            item_label = item_name
        else:
            n_items = r.get("totalitems") or 0
            item_label = f"Items: {n_items}" if n_items else "-"

        v.addWidget(row_line("", r.get("c_name") or "", "#000"))
        v.addWidget(row_line("Item", item_label))
        v.addWidget(row_line("Total", money(r.get("totalamount") or 0)))
        v.addWidget(row_line("Date", str(r.get(self.reg["date_col"], ""))))

        v.addStretch()

        actions = QHBoxLayout()
        actions.setSpacing(0)

        edit_btn = QPushButton()
        edit_btn.setFixedSize(22, 22)
        edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        edit_btn.setIcon(_pencil_icon("#ffffff", 15))
        edit_btn.setIconSize(QSize(15, 15))
        edit_btn.setToolTip("Edit")
        edit_btn.setStyleSheet(
            "QPushButton { background:#3c8dbc; border:1px solid #367fa9;"
            " border-radius:3px; padding:0; }"
            "QPushButton:hover { background:#367fa9; }")
        edit_btn.clicked.connect(lambda _, rec=r: self._edit(rec))

        view_btn = QPushButton()
        view_btn.setFixedSize(22, 22)
        view_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        view_btn.setIcon(_eye_icon("#ffffff", 15))
        view_btn.setIconSize(QSize(15, 15))
        view_btn.setToolTip("View")
        view_btn.setStyleSheet(
            "QPushButton { background:#f0ad4e; border:1px solid #eea236;"
            " border-radius:3px; padding:0; }"
            "QPushButton:hover { background:#ec971f; }")
        view_btn.clicked.connect(lambda _, rec=r: self._view(rec))

        del_btn = QPushButton()
        del_btn.setFixedSize(22, 22)
        del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        del_btn.setIcon(_trash_icon("#ffffff", 15))
        del_btn.setIconSize(QSize(15, 15))
        del_btn.setToolTip("Delete")
        del_btn.setStyleSheet(
            "QPushButton { background:#dd4b39; border:1px solid #d73925;"
            " border-radius:3px; padding:0; }"
            "QPushButton:hover { background:#d73925; }")
        del_btn.clicked.connect(lambda _, rec=r: self._delete(rec))

        actions.addWidget(edit_btn)
        actions.addStretch(1)
        actions.addWidget(view_btn)
        # Download + Print on every printable invoice list (tax / proforma /
        # purchase / quote) - same 22x22 size, equi-distant via equal stretches.
        if self.doc in ("tax", "proforma", "purchase", "quote"):
            actions.addStretch(1)
            dl_btn = QPushButton()
            dl_btn.setFixedSize(22, 22)
            dl_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            dl_btn.setIcon(_download_icon("#ffffff", 15))
            dl_btn.setIconSize(QSize(15, 15))
            dl_btn.setToolTip("Download PDF")
            dl_btn.setStyleSheet(
                "QPushButton { background:#00a65a; border:1px solid #008d4c;"
                " border-radius:3px; padding:0; }"
                "QPushButton:hover { background:#008d4c; }")
            dl_btn.clicked.connect(lambda _, rec=r: self._download_pdf(rec))
            actions.addWidget(dl_btn)

            actions.addStretch(1)
            print_btn = QPushButton()
            print_btn.setFixedSize(22, 22)
            print_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            print_btn.setIcon(_print_icon("#ffffff", 15))
            print_btn.setIconSize(QSize(15, 15))
            print_btn.setToolTip("Print")
            print_btn.setStyleSheet(
                "QPushButton { background:#00c0ef; border:1px solid #00acd7;"
                " border-radius:3px; padding:0; }"
                "QPushButton:hover { background:#00acd7; }")
            print_btn.clicked.connect(lambda _, rec=r: self._print(rec))
            actions.addWidget(print_btn)
        actions.addStretch(1)
        actions.addWidget(del_btn)
        v.addLayout(actions)

        return card

    def _view(self, r):
        master, items = db_manager.get_invoice(self.doc, r["orderid"])
        if invoice_print.show_invoice_view(
                self, self.doc, master, items,
                title=f"{self.reg['label']} {r['invid']}"):
            return

        dlg = QWidget()
        dlg.setWindowTitle(f"{self.reg['label']} {r['invid']}")
        W.apply(dlg)
        v = QVBoxLayout(dlg)
        v.addWidget(QLabel(
            f"<b>{r['invid']}</b><br/>Client: {master.get('c_name')}"
            f"<br/>Date: {master[self.reg['date_col']]}"))
        t = W.DataTable(["#", "Item", "Description", "HSN", "Qty", "Price",
                         "Total"], stretch_all=True)
        for i, it in enumerate(items, 1):
            t.add_row([i, it.get("item_name") or "",
                       it.get("item_desc") or "",
                       it.get("hsn") or "",
                       it.get("quantity") or 0,
                       money(it.get("price")),
                       money(it.get("total"))])
        v.addWidget(t)
        v.addWidget(QLabel(
            f"<b>Subtotal:</b> {money(master['subtotal'])} &nbsp; "
            f"<b>GST:</b> {money(master['taxamount'])} &nbsp; "
            f"<b>Total:</b> {money(master['totalamount'])}"))
        dlg.resize(700, 500)
        dlg.show()
        self._view_windows = getattr(self, "_view_windows", []) + [dlg]

    def _print(self, r):
        try:
            master, items = db_manager.get_invoice(self.doc, r["orderid"])
        except Exception as exc:
            W.error(self, f"Load failed: {exc}")
            return
        invoice_print.print_invoice(self, self.doc, master, items)

    def _preview_pdf(self, r):
        """On-screen PDF preview of the invoice (unused by row, kept)."""
        try:
            master, items = db_manager.get_invoice(self.doc, r["orderid"])
        except Exception as exc:
            W.error(self, f"Load failed: {exc}")
            return
        invoice_print.show_invoice_view(
            self, self.doc, master, items,
            title=f"{self.reg['label']} {r['invid']} - PDF Preview")

    def _download_pdf(self, r):
        """Direct 'Download PDF' (Save-As dialog, no preview)."""
        try:
            master, items = db_manager.get_invoice(self.doc, r["orderid"])
        except Exception as exc:
            W.error(self, f"Load failed: {exc}")
            return
        ok = invoice_print.save_invoice_pdf(
            self, self.doc, master, items,
            title=f"{self.reg['label']} {r['invid']}")
        if ok is False:
            W.error(self, "Failed to save PDF.")

    def _edit(self, r):
        page = InvoiceGenPage(self.main, self.doc, edit_orderid=r["orderid"])
        self.main._pages[f"edit_{self.doc}_{r['orderid']}"] = page
        self.main.stack.addWidget(page)
        self.main.stack.setCurrentWidget(page)

    def _delete(self, r):
        if W.confirm(self, f"Delete {self.reg['label']} {r['invid']}?"):
            db_manager.delete_invoice(self.doc, r["orderid"])
            self.refresh()