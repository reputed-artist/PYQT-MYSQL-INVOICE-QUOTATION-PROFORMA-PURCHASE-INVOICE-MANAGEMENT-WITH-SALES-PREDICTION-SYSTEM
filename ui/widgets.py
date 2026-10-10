"""
Shared widgets: page headers, AdminLTE-style boxes, tables, toolbars,
confirm dialogs, CSV export - the UI building blocks used by every page.
"""
import csv
import json as _json
import os
import shutil
import time
from datetime import date

from PyQt6.QtCore import Qt, QDate, QTimer
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (QWidget, QLabel, QHBoxLayout, QVBoxLayout, QFrame,
                             QTableWidget, QTableWidgetItem, QHeaderView,
                             QLineEdit, QPushButton, QDateEdit, QMessageBox,
                             QAbstractItemView, QFileDialog, QDialog,
                             QDialogButtonBox, QFormLayout, QComboBox,
                             QListWidget, QListWidgetItem, QApplication)

from ui.app_icon import app_icon, apply
from ui.icons import check_pixmap, kind_icon
from config import UPLOAD_DIR, BUNDLE_IMG_DIR


def theme_icon(name, color="#b8c7ce", size=32):
    from ui.theme import icon
    return icon(name, color, size)


# ---------------------------------------------------------------------------
# Boxes / headers
# ---------------------------------------------------------------------------
class Box(QFrame):
    """AdminLTE '.box box-primary': white card with coloured top border."""

    def __init__(self, title="", variant="primary", parent=None):
        super().__init__(parent)
        self.setObjectName({"primary": "Box", "success": "BoxSuccess",
                            "danger": "BoxDanger", "warning": "BoxWarning",
                            "info": "BoxInfo"}[variant])
        self._body = QVBoxLayout(self)
        self._body.setContentsMargins(12, 10, 12, 12)
        self._body.setSpacing(10)
        if title:
            lbl = QLabel(title)
            lbl.setObjectName("BoxTitle")
            self._body.addWidget(lbl)

    def add(self, widget, stretch=0):
        self._body.addWidget(widget, stretch)

    def addLayout(self, layout, stretch=0):
        self._body.addLayout(layout, stretch)


def _esc(text):
    """Escape a value for the rich-text breadcrumb label."""
    return (str(text).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;"))


def breadcrumb_html(page_name):
    """AdminLTE 'ol.breadcrumb' markup for the rich-text QLabel.

    Mirrors every `C4/app/views` layout: a blue 'Home' link (fa-dashboard
    icon), the grey '>' separator Bootstrap puts between the list items and
    the current page name as the active item.
    """
    return ("<span style='color:#3c8dbc'>&#8962; Home</span>"
            "<span style='color:#cccccc'>&nbsp;&gt;&nbsp;</span>"
            f"<span style='color:#777777'>{_esc(page_name)}</span>")


class PageHeader(QWidget):
    """'.content-header' - big light title + small grey subtitle, with the
    AdminLTE breadcrumb (`ol.breadcrumb`, floated right in the PHP views)
    shown on the right of the title row.

    `breadcrumb` defaults to the page title - in the original views the last
    (active) crumb item names the page itself, e.g. 'Home > Manage-Clients'.
    """

    def __init__(self, title, subtitle="", breadcrumb=None, parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 4)
        lay.setSpacing(2)

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(10)

        t = QLabel(title)
        t.setObjectName("PageTitle")
        row.addWidget(t, 0, Qt.AlignmentFlag.AlignLeft |
                      Qt.AlignmentFlag.AlignVCenter)
        row.addStretch(1)

        self.crumb = QLabel(breadcrumb_html(breadcrumb or title))
        self.crumb.setObjectName("PageCrumb")
        self.crumb.setTextFormat(Qt.TextFormat.RichText)
        row.addWidget(self.crumb, 0, Qt.AlignmentFlag.AlignRight |
                      Qt.AlignmentFlag.AlignVCenter)

        lay.addLayout(row)

        if subtitle:
            s = QLabel(subtitle)
            s.setObjectName("PageSubtitle")
            lay.addWidget(s)


# ---------------------------------------------------------------------------
# Stat card
# ---------------------------------------------------------------------------
class StatCard(QFrame):
    """AdminLTE '.small-box' style dashboard stat card."""

    def __init__(self, icon_name, value, text, color, parent=None):
        super().__init__(parent)
        self.setFixedHeight(110)
        self.setStyleSheet(
            f"QFrame {{ background: {color}; border-radius: 4px; border: none; }}")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 10, 14, 10)
        top = QHBoxLayout()
        ic = QLabel()
        ic.setPixmap(theme_icon(icon_name, "#ffffff", 40).pixmap(40, 40))
        top.addWidget(ic)
        top.addStretch()
        lay.addLayout(top)
        v = QLabel(str(value), self)
        v.setStyleSheet("color: white; background: transparent; font-size: 24px;"
                        " font-weight: bold;")
        lay.addWidget(v)
        t = QLabel(text, self)
        t.setStyleSheet("color: rgba(255,255,255,0.85); background: transparent;"
                        " font-size: 12.5px;")
        lay.addWidget(t)


# ---------------------------------------------------------------------------
# Table
# ---------------------------------------------------------------------------
class DataTable(QTableWidget):
    """DataTables-look table: bordered, striped, row selection, no editing."""

    def __init__(self, headers, parent=None, stretch_all=False):
        super().__init__(0, len(headers), parent)
        self.setHorizontalHeaderLabels(headers)
        self.verticalHeader().setVisible(False)
        self.setAlternatingRowColors(True)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setWordWrap(False)
        h = self.horizontalHeader()
        if stretch_all:
            h.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        else:
            h.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
            h.setStretchLastSection(True)
        v = self.verticalHeader()
        v.setDefaultSectionSize(30)

    def clear_rows(self):
        self.setRowCount(0)

    def add_row(self, cells, data=None):
        r = self.rowCount()
        self.insertRow(r)
        for c, text in enumerate(cells):
            item = QTableWidgetItem("" if text is None else str(text))
            item.setData(Qt.ItemDataRole.UserRole, data)
            self.setItem(r, c, item)
        return r

    def selected_data(self):
        items = self.selectedItems()
        if not items:
            return None
        return items[0].data(Qt.ItemDataRole.UserRole)

    def apply_totals_row(self, values, label="Total"):
        """Bold grey totals row appended at the bottom."""
        r = self.rowCount()
        self.insertRow(r)
        for c, v in enumerate(values):
            if v is None:
                v = label if c == 0 else ""
            it = QTableWidgetItem(str(v))
            f = it.font()
            f.setBold(True)
            it.setFont(f)
            it.setBackground(Qt.GlobalColor.lightGray)
            it.setFlags(it.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            self.setItem(r, c, it)


# ---------------------------------------------------------------------------
# Paginator
# ---------------------------------------------------------------------------
class Paginator(QFrame):
    """Bottom bar for a DataTable: pagination + per-page selector."""

    def __init__(self, on_change=None, parent=None):
        super().__init__(parent)
        self.on_change = on_change
        self._ready = False
        self.setObjectName("PaginatorBar")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet(
            "QFrame#PaginatorBar { background: #f4f4f5; border: 1px solid #d2d6de; "
            "border-top: none; border-radius: 0 0 4px 4px; padding: 6px 12px; }")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(8, 4, 8, 4)
        lay.setSpacing(6)

        self.info = QLabel("")
        self.info.setObjectName("PaginatorInfo")
        lay.addWidget(self.info)

        self.nav = QHBoxLayout()
        self.nav.setSpacing(2)
        lay.addLayout(self.nav, 1)

        self.first_btn = _nav_btn("chevronleft", "\u00ab")
        self.prev_btn = _nav_btn("chevronleft", "\u2039")
        self.next_btn = _nav_btn("chevronright", "\u203a")
        self.last_btn = _nav_btn("chevronright", "\u00bb")
        self.first_btn.clicked.connect(self._first)
        self.prev_btn.clicked.connect(self._prev)
        self.next_btn.clicked.connect(self._next)
        self.last_btn.clicked.connect(self._last)

        self.nav.addStretch()
        self.nav.addWidget(self.first_btn)
        self.nav.addWidget(self.prev_btn)
        self.pages_host = QWidget()
        self.pages_lay = QHBoxLayout(self.pages_host)
        self.pages_lay.setContentsMargins(0, 0, 0, 0)
        self.pages_lay.setSpacing(2)
        self.nav.addWidget(self.pages_host)
        self.nav.addWidget(self.next_btn)
        self.nav.addWidget(self.last_btn)
        self.nav.addStretch()

        self.per_page = QComboBox()
        self.per_page.setObjectName("PaginatorPerPage")
        self.per_page.addItem("10", 10)
        self.per_page.addItem("25", 25)
        self.per_page.addItem("50", 50)
        self.per_page.addItem("100", 100)
        self.per_page.addItem("All", -1)
        self.per_page.setCurrentIndex(0)
        lay.addWidget(self.per_page)
        lay.addStretch()

        self._page_buttons = []
        self._current = 0
        self._total = 0
        self._per_page = 10
        self._max_pages = 1
        self._preserve_current = False

        self.per_page.currentIndexChanged.connect(self._change_per_page)
        self._ready = True

    def set_total(self, total):
        self._preserve_current = False
        self._refresh_total(total)

    def _refresh_total(self, total):
        self._total = int(total or 0)
        self._per_page = self.per_page.currentData() or 10
        if self._per_page <= 0:
            self._max_pages = 1
            if not self._preserve_current:
                self._current = 0
        else:
            self._max_pages = max(1, -(-self._total // self._per_page))
            if self._preserve_current:
                self._current = max(0, min(self._current,
                                            self._max_pages - 1))
            else:
                self._current = 0
        self._rebuild_page_buttons()
        self._update_nav_state()
        self._update_info()

    def set(self, total, current_page=0, per_page=None):
        if per_page is not None and per_page != self._per_page:
            idx = self.per_page.findData(per_page)
            if idx >= 0:
                self.per_page.blockSignals(True)
                self.per_page.setCurrentIndex(idx)
                self.per_page.blockSignals(False)
            self._per_page = per_page
        if current_page is not None:
            self._current = max(0, int(current_page))
        self.set_total(total)

    def current_page(self):
        return self._current

    def page_range(self):
        p = self._per_page if self._per_page > 0 else self._total
        start = self._current * p
        end = min(start + p, self._total)
        return (start, end)

    def _clear_pages(self):
        while self.pages_lay.count():
            item = self.pages_lay.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()
        self._page_buttons = []

    def _rebuild_page_buttons(self):
        self._clear_pages()
        total = self._max_pages
        cur = self._current

        def add_page(p, label, current_flag=False, disabled=False):
            b = _nav_btn("circle", label)
            b.setFixedWidth(26)
            b.setFixedHeight(24)
            b.clicked.connect(lambda _checked=False, pp=p: self._go(pp))
            if current_flag:
                b.setProperty("pageNavCurrent", True)
                b.setStyleSheet(
                    "QPushButton { background: #3c8dbc; color: white; "
                    "border: 1px solid #367fa9; padding: 2px 6px; "
                    "border-radius: 4px; font-size: 12px; font-weight: bold; }"
                    "QPushButton:hover { background: #367fa9; }")
            if disabled or p is None or p < 0:
                b.setDisabled(True)
            self.pages_lay.addWidget(b)
            self._page_buttons.append(b)

        if total <= 11:
            for p in range(total):
                add_page(p, str(p + 1), current_flag=(p == cur))
        else:
            half = 5
            lo = max(0, cur - half)
            hi = min(total, cur + half + 1)
            if lo == 0:
                hi = min(total, 11)
            elif hi == total:
                lo = max(0, total - 11)
            if lo > 0:
                add_page(None, "...")
            for p in range(lo, hi):
                add_page(p, str(p + 1), current_flag=(p == cur))
            if hi < total:
                add_page(None, "...")

        self._update_nav_state()

    def _update_nav_state(self):
        cur = self._current
        total = self._max_pages
        self.first_btn.setEnabled(cur > 0)
        self.prev_btn.setEnabled(cur > 0)
        self.next_btn.setEnabled(cur < total - 1)
        self.last_btn.setEnabled(cur < total - 1)

    def _update_info(self):
        total = self._total
        p = self._per_page if self._per_page > 0 else total
        if total == 0:
            self.info.setText("Showing 0 to 0 of 0 entries")
        else:
            start = self._current * p + 1
            end = min(start + p - 1, total)
            self.info.setText(f"Showing {start} to {end} of {total} entries")

    def _notify(self):
        if not self._ready:
            return
        if self.on_change:
            QTimer.singleShot(0, self.on_change)
        else:
            self.set_total(self._total)

    def _change_per_page(self):
        if not self._ready:
            return
        self._per_page = self.per_page.currentData() or 10
        self._current = 0
        self._notify()

    def _go(self, page):
        if page is None:
            return
        page = int(page)
        if page != self._current and 0 <= page < self._max_pages:
            self._current = page
            self._notify()

    def _first(self):
        if self._current != 0:
            self._go(0)

    def _prev(self):
        if self._current > 0:
            self._go(self._current - 1)

    def _next(self):
        if self._current < self._max_pages - 1:
            self._go(self._current + 1)

    def _last(self):
        if self._max_pages > 1:
            self._go(self._max_pages - 1)


def _nav_btn(icon_name, text):
    b = QPushButton()
    b.setText(text)
    b.setFixedWidth(28)
    b.setFixedHeight(24)
    b.setProperty("pageNav", True)
    return b


# ---------------------------------------------------------------------------
# Search + date range
# ---------------------------------------------------------------------------
class SearchBox(QWidget):
    """Sidebar-form style search input."""

    def __init__(self, placeholder="Search...", on_change=None, parent=None):
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)
        self.edit = QLineEdit()
        self.edit.setPlaceholderText(placeholder)
        self.edit.setClearButtonEnabled(True)
        self.edit.setFixedWidth(220)
        self.edit.textChanged.connect(lambda *_: on_change() if on_change else None)
        lay.addWidget(self.edit)


class DateRangeBar(QWidget):
    """The daterange filter used by every list/report page."""

    def __init__(self, on_change=None, parent=None):
        super().__init__(parent)
        self.on_change = on_change
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)
        lay.addWidget(QLabel("Date Range:"))
        today = date.today()
        fy_start = (date(today.year, 4, 1) if today.month > 3
                    else date(today.year - 1, 4, 1))
        self.from_date = QDateEdit()
        self.from_date.setCalendarPopup(True)
        self.from_date.setDisplayFormat("dd-MM-yyyy")
        self.from_date.setDate(QDate(fy_start.year, fy_start.month, fy_start.day))
        self.to_date = QDateEdit()
        self.to_date.setCalendarPopup(True)
        self.to_date.setDisplayFormat("dd-MM-yyyy")
        self.to_date.setDate(QDate(today.year, today.month, today.day))
        lay.addWidget(self.from_date)
        lay.addWidget(QLabel("to"))
        lay.addWidget(self.to_date)
        btn = QPushButton("Go")
        btn.setObjectName("btnInfo")
        btn.clicked.connect(self._changed)
        lay.addWidget(btn)
        lay.addStretch()

    def _changed(self):
        if self.on_change:
            self.on_change()

    def dates(self):
        return (self.from_date.date().toString("yyyy-MM-dd"),
                self.to_date.date().toString("yyyy-MM-dd"))


# ---------------------------------------------------------------------------
# Dialogs / helpers
#
# Every box is branded - but the *kind* decides which icon the title bar
# shows, drawn by ui.icons.kind_icon():
#
#   confirm -> blue  disc + "?"      success -> green disc + tick
#   info    -> aqua  disc + "i"      warning -> amber disc + "!"
#   error   -> red   disc + "x"
#
# So an "invoice / proforma generated" confirmation is visually distinct from
# a neutral info message and from an error, both in the title bar and in the
# dialog body (`setIcon` / `setIconPixmap`).
# ---------------------------------------------------------------------------
def _box(parent, title, text, icon, buttons, kind=None):
    """QMessageBox with the icon for its ``kind`` on the title bar.

    ``kind`` (optional): "success" | "confirm" | "info" | "warning" | "error"
    - see `ui.icons.kind_icon()`. Without it the window icon is the app icon.
    """
    box = QMessageBox(parent)
    box.setWindowTitle(title)
    box.setText(text)
    box.setIcon(icon)
    box.setStandardButtons(buttons)
    title_icon = kind_icon(kind) if kind else None
    try:
        apply(box, title_icon)
    except Exception:
        try:
            box.setWindowIcon(title_icon or app_icon())
        except Exception:
            pass
    return box


def confirm(parent, text, title="Confirm"):
    """Yes/No confirmation - returns True when the user picked Yes.

    The title bar shows the blue question-mark icon (`kind_icon("confirm")`).
    """
    box = _box(parent, title, text, QMessageBox.Icon.Question,
               QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
               kind="confirm")
    box.setDefaultButton(QMessageBox.StandardButton.No)
    return int(box.exec()) == int(QMessageBox.StandardButton.Yes)


def success(parent, text, title="Success"):
    """Confirmation box with a green right-tick icon.

    Used for every completed action: invoice / proforma / quotation /
    purchase generated, quick quotation saved, records added or updated,
    settings saved. The title bar carries the matching green tick.
    """
    box = _box(parent, title, text, QMessageBox.Icon.NoIcon,
               QMessageBox.StandardButton.Ok, kind="success")
    box.setIconPixmap(check_pixmap(56))
    return box.exec()


def info(parent, text, title="Info"):
    """Neutral blue information box (aqua 'i' on the title bar)."""
    return _box(parent, title, text, QMessageBox.Icon.Information,
                QMessageBox.StandardButton.Ok, kind="info").exec()


def warning(parent, text, title="Warning"):
    """Yellow warning box (amber '!' on the title bar)."""
    return _box(parent, title, text, QMessageBox.Icon.Warning,
                QMessageBox.StandardButton.Ok, kind="warning").exec()


def error(parent, text, title="Error"):
    """Red error box (red 'x' on the title bar)."""
    return _box(parent, title, text, QMessageBox.Icon.Critical,
                QMessageBox.StandardButton.Ok, kind="error").exec()


# ---------------------------------------------------------------------------
# Universal export (CSV / Excel / TXT / JSON / DOC / SQL / PDF / Clipboard)
# ---------------------------------------------------------------------------
def export_csv(parent, headers, rows, default_name="export.csv", mode="csv"):
    """Universal export helper. `mode` selects the file format.

    Supported modes:
        csv, excel, txt, json, doc, sql, pdf, clipboard
    """
    # ---------- clipboard ----------
    if mode == "clipboard":
        lines = ["\t".join(str(h) for h in headers)]
        for r in rows:
            lines.append("\t".join(
                "" if c is None else str(c) for c in r))
        QApplication.clipboard().setText("\n".join(lines))
        info(parent, "Table copied to clipboard.")
        return

    # ---------- file dialog filter + extension ----------
    filters = {
        "csv":   ("CSV (*.csv)",        ".csv"),
        "excel": ("Excel/CSV (*.csv)",  ".csv"),
        "txt":   ("Text (*.txt)",       ".txt"),
        "json":  ("JSON (*.json)",      ".json"),
        "doc":   ("Word (*.doc)",       ".doc"),
        "sql":   ("SQL (*.sql)",        ".sql"),
        "pdf":   ("PDF (*.pdf)",        ".pdf"),
    }
    ffilter, ext = filters.get(mode, ("CSV (*.csv)", ".csv"))

    base, _ = os.path.splitext(default_name)
    path, _ = QFileDialog.getSaveFileName(
        parent, "Save as", base + ext, ffilter)
    if not path:
        return

    try:
        # ---------- csv / excel ----------
        if mode in ("csv", "excel"):
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                w = csv.writer(f)
                w.writerow(headers)
                for r in rows:
                    w.writerow(["" if c is None else c for c in r])

        # ---------- txt ----------
        elif mode == "txt":
            with open(path, "w", encoding="utf-8") as f:
                f.write("\t".join(str(h) for h in headers) + "\n")
                for r in rows:
                    f.write("\t".join(
                        "" if c is None else str(c) for c in r) + "\n")

        # ---------- json ----------
        elif mode == "json":
            payload = [dict(zip(headers, r)) for r in rows]
            with open(path, "w", encoding="utf-8") as f:
                _json.dump(payload, f, indent=2, default=str)

        # ---------- doc (HTML wrapped, opens in Word) ----------
        elif mode == "doc":
            html = ("<html><body><table border='1' "
                    "cellspacing='0' cellpadding='4'><tr>")
            html += "".join(f"<th>{h}</th>" for h in headers) + "</tr>"
            for r in rows:
                html += "<tr>" + "".join(
                    f"<td>{'' if c is None else c}</td>"
                    for c in r) + "</tr>"
            html += "</table></body></html>"
            with open(path, "w", encoding="utf-8") as f:
                f.write(html)

        # ---------- sql ----------
        elif mode == "sql":
            table_name = base.replace(" ", "_").lower()
            cols = ", ".join(str(h) for h in headers)
            with open(path, "w", encoding="utf-8") as f:
                for r in rows:
                    vals = ", ".join(
                        "NULL" if c is None
                        else "'" + str(c).replace("'", "''") + "'"
                        for c in r)
                    f.write(
                        f"INSERT INTO {table_name} ({cols}) "
                        f"VALUES ({vals});\n")

        # ---------- pdf ----------
        elif mode == "pdf":
            from PyQt6.QtPrintSupport import QPrinter
            from PyQt6.QtGui import QTextDocument
            html = ("<table border='1' cellspacing='0' "
                    "cellpadding='4'><tr>")
            html += "".join(f"<th>{h}</th>" for h in headers) + "</tr>"
            for r in rows:
                html += "<tr>" + "".join(
                    f"<td>{'' if c is None else c}</td>"
                    for c in r) + "</tr>"
            html += "</table>"
            doc = QTextDocument()
            doc.setHtml(html)
            printer = QPrinter(QPrinter.PrinterMode.HighResolution)
            printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
            printer.setOutputFileName(path)
            doc.print(printer)

        else:
            error(parent, f"Unsupported export mode: {mode}")
            return

    except Exception as exc:
        error(parent, f"Export failed: {exc}")
        return

    info(parent, f"Exported to {path}")


# ---------------------------------------------------------------------------
# Searchable client combobox
# ---------------------------------------------------------------------------
class ClientSearchCombo(QWidget):
    """Searchable combobox for client selection."""

    def __init__(self, clients, parent=None, on_select=None,
                 placeholder="Search client name...", u_type=0):
        super().__init__(parent)
        self._clients = clients or []
        self._on_select = on_select
        self._u_type = u_type
        self._selected_cid = None
        self._build_ui(placeholder)

    def _build_ui(self, placeholder):
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)

        self._display = QLineEdit()
        self._display.setReadOnly(True)
        self._display.setPlaceholderText(placeholder)
        self._display.setClearButtonEnabled(True)
        self._display.setFixedWidth(260)
        lay.addWidget(self._display)

        self._arrow = QPushButton("▼")
        self._arrow.setObjectName("btnDefault")
        self._arrow.setFixedSize(28, 24)
        self._arrow.setFlat(True)
        self._arrow.setStyleSheet("QPushButton { color: #6c757d; } "
                                   "QPushButton:hover { color: #343a40; }")
        self._arrow.clicked.connect(self._toggle)
        lay.addWidget(self._arrow)

        self._popup = QWidget()
        self._popup.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)
        pop_lay = QVBoxLayout(self._popup)
        pop_lay.setContentsMargins(0, 0, 0, 0)
        pop_lay.setSpacing(0)

        self._search = QLineEdit()
        self._search.setPlaceholderText("Type to search...")
        self._search.setClearButtonEnabled(True)
        self._search.textChanged.connect(self._filter)
        pop_lay.addWidget(self._search)

        self._list = QListWidget()
        self._list.setMaximumHeight(250)
        self._list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._list.itemClicked.connect(self._on_click)
        self._list.itemDoubleClicked.connect(self._on_double_click)
        pop_lay.addWidget(self._list)

        self._popup.move(0, -10000)
        self._popup.setVisible(False)
        self.mousePressEvent = self._on_press
        self._display.returnPressed.connect(self._toggle)

    def _toggle(self):
        if self._popup.isVisible():
            self._popup.setVisible(False)
            self._search.clear()
        else:
            self._show()

    def _show(self):
        geo = self.screen().availableGeometry()
        w = self.geometry()
        pw = min(w.width(), 350)
        ph = 300
        x = w.x()
        y = w.y() + w.height() + 2
        if x + pw > geo.x() + geo.width():
            x = geo.x() + geo.width() - pw
        if y + ph > geo.y() + geo.height():
            y = w.y() - ph - 2
            if y < geo.y():
                y = geo.y()
        self._popup.setGeometry(x, y, pw, ph)
        self._search.clear()
        self._search.setFocus()
        self._list.clear()
        for c in self._clients:
            self._add(c)
        self._popup.setVisible(True)

    def _add(self, c):
        item = QListWidgetItem()
        name = c.get("c_name", "")
        mob = c.get("mob", "")
        gst = c.get("gst", "")
        addr = c.get("c_add", "")
        cid = c.get("cid")
        txt = f"<b>{name}</b>" if name else "<i>Unnamed</i>"
        if mob:
            txt += f"<br/><span style='color:#6c757d;'>Mobile: {mob}</span>"
        if gst:
            txt += f"<br/><span style='color:#6c757d;'>GST: {gst}</span>"
        if addr:
            s = addr[:50]
            txt += f"<br/><span style='color:#6c757d;'>{s}{'...' if len(addr)>50 else ''}</span>"
        item.setText(txt)
        item.setData(Qt.ItemDataRole.UserRole, cid)
        self._list.addItem(item)

    def _filter(self, text):
        text = text.strip().lower()
        self._list.clear()
        for c in self._clients:
            if not text:
                self._add(c)
            elif any(str(c.get(f, "")).lower().find(text) >= 0
                     for f in ("c_name", "mob", "gst", "c_add")):
                self._add(c)

    def _on_click(self, item):
        cid = item.data(Qt.ItemDataRole.UserRole)
        self._pick(cid)

    def _on_double_click(self, item):
        self._on_click(item)
        self._popup.setVisible(False)
        self._search.clear()

    def _on_press(self, ev):
        self._toggle()
        super().mousePressEvent(ev)

    def _pick(self, cid):
        for c in self._clients:
            if c.get("cid") == cid:
                self._selected_cid = cid
                self._display.setText(c.get("c_name", ""))
                if self._on_select:
                    self._on_select(cid)
                return
        self._selected_cid = None
        self._display.clear()

    def set_clients(self, clients):
        self._clients = clients or []
        if self._selected_cid:
            for c in self._clients:
                if c.get("cid") == self._selected_cid:
                    self._display.setText(c.get("c_name", ""))
                    return
            self._selected_cid = None
            self._display.clear()

    def current_cid(self):
        return self._selected_cid

    def set_cid(self, cid):
        self._pick(cid)

    def clear(self):
        self._selected_cid = None
        self._display.clear()


# ---------------------------------------------------------------------------
# Form dialog
# ---------------------------------------------------------------------------
class FormDialog(QDialog):
    """Modal add/edit dialog built from a list of field specs.

    spec: (label, key, kind, extra) where kind in
      text, textarea, number, combo, date, image
    """

    def __init__(self, parent, title, specs, values=None, size=(520, 0)):
        super().__init__(parent)
        self.setWindowTitle(title)
        apply(self)                             # brand icon on the title bar
        self.setMinimumSize(*size)
        self._editors = {}
        values = values or {}
        form = QFormLayout(self)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setSpacing(10)
        for label, key, kind, extra in specs:
            if kind in ("text", "number"):
                w = QLineEdit(str(values.get(key, "")))
            elif kind == "textarea":
                from PyQt6.QtWidgets import QPlainTextEdit
                w = QPlainTextEdit(str(values.get(key, "")))
                w.setFixedHeight(70)
            elif kind == "combo":
                w = QComboBox()
                for val, text in extra:
                    w.addItem(text, val)
                cur = values.get(key)
                if cur is not None:
                    idx = w.findData(cur)
                    if idx < 0:
                        # No exact data match. Before appending the value as a
                        # new row, check whether it is already present as the
                        # visible text or as an equivalent string - otherwise
                        # the combo ends up listing e.g. "IGST, Loc, Loc".
                        # Appending is a genuine last resort, for a value that
                        # is not in the option list at all.
                        already = w.findText(str(cur)) >= 0
                        if not already:
                            for i in range(w.count()):
                                if str(w.itemData(i)) == str(cur):
                                    already = True
                                    idx = i
                                    break
                        if not already:
                            w.addItem(str(cur), cur)
                            idx = w.findData(cur)
                    w.setCurrentIndex(max(0, idx))
            elif kind == "image":
                w = ImagePickerField(values.get(key, ""))
            elif kind == "date":
                from PyQt6.QtWidgets import QDateEdit
                w = QDateEdit()
                w.setCalendarPopup(True)
                w.setDisplayFormat("dd-MM-yyyy")
                v = values.get(key)
                if isinstance(v, date):
                    w.setDate(QDate(v.year, v.month, v.day))
                else:
                    w.setDate(QDate.currentDate())
            else:
                w = QLineEdit(str(values.get(key, "")))
            form.addRow(label, w)
            self._editors[key] = (kind, w)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok |
                              QDialogButtonBox.StandardButton.Cancel)
        ok_btn = bb.button(QDialogButtonBox.StandardButton.Ok)
        ok_btn.setObjectName("btnSuccess")
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        form.addRow(bb)

    def get(self):
        out = {}
        for key, (kind, w) in self._editors.items():
            if kind in ("text", "number"):
                out[key] = w.text().strip()
            elif kind == "textarea":
                out[key] = w.toPlainText().strip()
            elif kind == "combo":
                out[key] = w.currentData()
            elif kind == "image":
                out[key] = w.value()
            elif kind == "date":
                q = w.date()
                out[key] = date(q.year(), q.month(), q.day())
        return out


# ---------------------------------------------------------------------------
# Image picker
# ---------------------------------------------------------------------------
PRODUCT_IMG_DIR = UPLOAD_DIR
# Product pictures are user uploads, so they go to the same writable per-user
# folder as the avatar / company logo (config.UPLOAD_DIR). The old path walked
# up out of the app folder into `<repo>/../public/dist/img`, which inside a
# frozen build resolves under `Program Files\Sales Aura` - read-only, so the
# copy silently failed (it was wrapped in a bare `except: pass`) and the
# product ended up without its picture.


class ImagePickerField(QWidget):
    """'Choose File' button + readonly name box + image preview thumbnail."""

    def __init__(self, value="", parent=None):
        super().__init__(parent)
        self._copied = ""
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)

        self.btn = QPushButton("Choose File")
        self.btn.setObjectName("btnPrimary")
        self.name_edit = QLineEdit(value or "")
        self.name_edit.setReadOnly(True)
        self.name_edit.setPlaceholderText("No file chosen")
        self.preview = QLabel()
        self.preview.setFixedSize(350, 200)
        self.preview.setObjectName("ImgPreview")
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview.setStyleSheet(
            "QLabel { border: 1px solid #ddd; background: #f5f5f5; }"
            "QLabel:!hasPixmap { color: #999; }"
        )

        lay.addWidget(self.btn)
        lay.addWidget(self.name_edit, 1)
        lay.addWidget(self.preview)
        self.btn.clicked.connect(self._pick)
        if value:
            full_path = self._resolve_image_path(value)
            self._show_preview(full_path if os.path.isfile(full_path) else value)
        else:
            self._show_preview("")
        self._current_filename = value or ""

    def _resolve_image_path(self, filename):
        # Look in the writable uploads folder first (where a new pick is
        # saved), then the historical read-only locations so product images
        # stored by an older build or by the PHP app still resolve.
        base = os.path.dirname(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__))))
        candidates = [
            os.path.join(PRODUCT_IMG_DIR, filename),
            os.path.join(BUNDLE_IMG_DIR, filename),
            os.path.join(base, "public", "dist", "img", filename),
        ]
        for cand in candidates:
            if os.path.isfile(cand):
                return cand
        return candidates[0]

    def _pick(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Product Image", "",
            "Images (*.png *.jpg *.jpeg *.gif *.bmp)")
        if not path:
            return
        ext = os.path.splitext(path)[1].lower() or ".jpg"
        self._copied = f"prod_{int(time.time())}{ext}"
        self.name_edit.setText(self._copied)
        self._current_filename = self._copied
        self._show_preview(path)
        self._pending_src = path

    def _show_preview(self, src):
        pm = QPixmap(src)
        if not pm.isNull():
            self.preview.setPixmap(pm.scaled(
                self.preview.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation))
            self.preview.setStyleSheet(
                "QLabel { border: 1px solid #ddd; background: #fff; }"
            )
        else:
            self.preview.clear()
            self.preview.setText("No Image")
            self.preview.setStyleSheet(
                "QLabel { border: 1px solid #ddd; background: #f5f5f5; "
                "color: #999; }"
            )
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)

    def value(self):
        if self._copied:
            src = getattr(self, "_pending_src", "")
            try:
                os.makedirs(PRODUCT_IMG_DIR, exist_ok=True)
                shutil.copy2(src, os.path.join(PRODUCT_IMG_DIR, self._copied))
            except Exception:
                # Copying into the app folder can still fail (locked file,
                # antivirus, genuinely read-only target). Previously this was
                # swallowed and the product was saved pointing at a file that
                # did not exist, so the picture silently vanished. Fall back
                # to storing the absolute source path, which resolves and
                # displays correctly.
                fallback = os.path.abspath(src) if src else ""
                if fallback:
                    self.name_edit.setText(fallback)
                    self._copied = ""
                    self._current_filename = fallback
        return self.name_edit.text().strip()


# ---------------------------------------------------------------------------
# Row-action helper
# ---------------------------------------------------------------------------
def info_action_button(tooltip="View Info"):
    """Small square 'Info' button used in the Action columns of the list
    pages."""
    from PyQt6.QtCore import QSize
    b = QPushButton()
    b.setObjectName("btnInfo")
    b.setIcon(theme_icon("info", "#ffffff", 14))
    b.setIconSize(QSize(14, 14))
    b.setFixedSize(30, 26)
    b.setToolTip(tooltip)
    return b