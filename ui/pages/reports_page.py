"""
Reports page - generic port of the report views (sitem_report, shsn_report,
sale_report, pitem_report, phsn_report, purchase_report, quoteitem_report,
quote_report, quickquote_report): date-range filter, item search,
DataTables-style table with bold totals row and the same red DataTables
export button strip (Copy / JSON / Excel / CSV / PDF / Print / TXT / SQL /
Docx / PNG) the master pages use.
"""
import csv
import json
import os

from PyQt6.QtCore import Qt, QObject, QEvent
from PyQt6.QtGui import QTextDocument, QFontMetrics
from PyQt6.QtPrintSupport import QPrinter, QPrintPreviewDialog
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QHeaderView, QApplication, QFileDialog)

from database import db_manager
from ui import widgets as W
from utils.helpers import money

# Active breadcrumb item (last 'li' of the original 'ol.breadcrumb'), exactly
# as written in the report views under C4/app/views/report.
REPORT_CRUMB = {
    ("item", "tax"): "Sale Item Report",
    ("hsn", "tax"): "Sale HSN Report",
    ("summary", "tax"): "Sale Report",
    ("item", "purchase"): "Purchase Item Report",
    ("hsn", "purchase"): "Purchase HSN Report",
    ("summary", "purchase"): "Purchase Report",
    ("item", "quote"): "Quotation Item Report",
    ("summary", "quote"): "Quotation Report",
    ("quickquote", None): "Quick Quotation Report",
    ("item", "proforma"): "Proforma Item Report",
    ("summary", "proforma"): "Proforma Invoice Report",
}

# --------------------------------------------------------------------------- #
# Column widths for every report page.
#
# Goal: the low-information columns (Sr No, Invoice/Quote id, Date, Actions)
# must not eat the table, and whatever horizontal room is left should go to the
# columns that actually carry data (client, item, description, amounts).
#
# Instead of a hand-written width table per report - which drifts as soon as a
# report gains a column - the widths are derived from the content itself:
#
#   1. Columns whose *header* is one of NARROW_COLUMNS are pinned to a small
#      fixed width; they hold short, low-entropy values (1,2,3 / INV/24-25/0007
#      / 12-04-2026 / three icon buttons), so they need very little space.
#   2. Every other column is measured with QFontMetrics over a sample of the
#      real rows, clamped to [MIN_FLEX, MAX_FLEX].
#   3. The remaining viewport width is then distributed across those flexible
#      columns *proportionally to their measured content*, so a wide "Item" or
#      "Description" gets more room than a short "Tax Amt" - and, if the window
#      is resized, the same rule re-applies at the new width.
#
# Keyed by header text, not column index, so it works for every report kind
# (item / hsn / summary / quickquote) and survives column reordering.
# --------------------------------------------------------------------------- #
NARROW_COLUMNS = {
    "sr no": 52,          # sequence number - at most 3-4 digits
    "invoice": 116,       # 'INV/2024-2025/0007' - fixed width by nature
    "quote id": 116,      # ditto for the quick-quote report
    "date": 96,           # dd-MM-yyyy
    "actions": 104,       # three icon buttons
    "qty": 68,
    "total qty": 82,
    "items": 72,
    "hsn": 96,
    "tax rate": 84,
    "gst": 88,
    "mobile": 110,
    # transaction page
    "type": 84,            # 'Customer' / 'Supplier'
    "amount": 110,         # money column, right-aligned values
    "bank": 104,
    "payment date": 116,   # dd-MM-yyyy
}

MIN_FLEX = 86            # a flexible column never shrinks below this
MAX_FLEX = 340           # nor grows past this, so one long cell can't take
CELL_PAD = 26            # cell padding + a little slack for the sort arrow
SAMPLE = 200             # rows measured when sizing (enough, and bounded)


def _display_rows(rows, data_keys):
    """Yield the text actually shown in the table for each row.

    The report table renders money columns through `money()` and leaves empty
    values blank, so sizing must look at that rendered text - not at the raw
    DB value (a raw `12.0` is far shorter than the `₹ 12.00` on screen, which
    is what made amount columns collapse).
    """
    money_cols = {"subtotal", "price", "taxamount", "totalamount",
                  "gst", "total"}
    out = []
    for r in rows[:SAMPLE]:
        line = []
        for key in data_keys:
            v = r.get(key, "")
            if v is None:
                v = ""
            elif key in money_cols:
                v = money(v)
            line.append(str(v))
        out.append(line)
    return out


def _text_width(fm, text, fallback_char_w=7.5):
    """Width of `text` in pixels, with a font-metrics fallback.

    Qt can report a width of 0 for every glyph when the platform has no fonts
    installed (the offscreen test environment does exactly this), so fall back
    to an average-character-width estimate to keep the layout sane.
    """
    text = str(text)
    if not text:
        return 0
    w = fm.horizontalAdvance(text)
    if w <= 0:
        w = len(text) * fallback_char_w
    return w


def _measure_column_widths(table, headers, data_keys, rows, display=None):
    """Return {column index: pixel width} for a report table.

    `data_keys` is aligned with `headers[1:]` (index 0 is the display-only
    'Sr No' column, which has no backing key).

    `display` optionally overrides how each row is turned into the text that
    is measured.  It is a list of lists aligned with `data_keys`, for pages
    whose cells are not a straight `str(row[key])` (the transaction page shows
    `c_name or cid`, a derived Customer/Supplier label, and `money(amount)`).
    When omitted, `_display_rows` derives the text from the rows.
    """
    view_w = table.viewport().width() or table.width()
    fm = QFontMetrics(table.font())
    samples = display if display is not None else _display_rows(rows,
                                                                 data_keys)

    fixed, flex = {}, []
    for i, head in enumerate(headers):
        w = NARROW_COLUMNS.get(str(head).strip().lower())
        if w is None:
            flex.append(i)
        else:
            fixed[i] = w

    # ---- measured width of each flexible column (header + rendered cells) ----
    content = {}
    for i in flex:
        # the header itself sets a floor: it must never be clipped
        best = _text_width(fm, headers[i])
        d = i - 1                      # index into data_keys / sample lines
        if 0 <= d < len(data_keys):
            for line in samples:
                w = _text_width(fm, line[d])
                if w > best:
                    best = w
                    if best >= MAX_FLEX:
                        break
        content[i] = max(MIN_FLEX, min(MAX_FLEX, int(best) + CELL_PAD))

    # ---- distribute what is left, proportionally to the content width ----
    widths = dict(fixed)
    budget = view_w - sum(fixed.values())
    total = sum(content.values())

    if flex and budget > 0:
        if total <= budget:
            # Spare room.  Cap each column at MAX_FLEX first, then spread
            # whatever is still left proportionally.  Without the cap a report
            # with only two or three data columns (the HSN reports) would
            # stretch a single amount column across half the window.  If even
            # the capped columns cannot absorb the room, the remainder is
            # spread evenly so the table still fills the width instead of
            # leaving a dead gap.
            room = budget - total
            growable = [i for i in flex if content[i] < MAX_FLEX]
            if growable:
                pool = sum(MAX_FLEX - content[i] for i in growable)
                add = min(room, pool)
                for i in growable:
                    content[i] += add * (MAX_FLEX - content[i]) / pool
            rest = budget - sum(content.values())
            if rest > 1:
                for i in flex:
                    content[i] += rest / len(flex)
        else:
            # too little room: shrink the flexible columns towards MIN_FLEX,
            # taking the space from the widest ones first
            over = total - budget
            slack = {i: content[i] - MIN_FLEX for i in flex}
            free = sum(slack.values())
            if free > 0:
                for i in flex:
                    content[i] -= over * slack[i] / free
            else:
                for i in flex:
                    content[i] = MIN_FLEX

    widths.update(content)

    # never leave a dead gap - hand any rounding remainder to the widest column
    leftover = view_w - sum(widths.values())
    if leftover > 1 and flex:
        widest = max(flex, key=lambda i: widths[i])
        widths[widest] += leftover

    return {i: max(1, int(round(w))) for i, w in widths.items()}


def _apply_column_layout(table, headers, data_keys, rows, display=None):
    """Pin every report column to its computed width (no auto re-fit).

    Resizing to contents is what made the columns jump around while paging and
    filtering; here each column keeps the width `_measure_column_widths`
    derived from the data.  See that function for the `display` override.
    """
    header = table.horizontalHeader()
    header.setStretchLastSection(False)
    header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
    for col, width in _measure_column_widths(table, headers,
                                             data_keys, rows,
                                             display).items():
        table.setColumnWidth(col, width)


# --------------------------------------------------------------------------- #
# Centered red export button strip (DataTables "Buttons" style)
#
# The exact strip the master / accounts / ledger pages use, so every report
# page carries the same toolbar:
#     [ Copy ][ JSON ][ Excel ][ CSV ][ PDF ][ Print ][ TXT ][ SQL ][ Docx ][ PNG ]
# --------------------------------------------------------------------------- #
class ExportButtonStrip(QWidget):
    BUTTONS = (
        ("Copy",  "copy",  "\U0001F5D0"),
        ("JSON",  "json",  "{}"),
        ("Excel", "excel", "\U0001F4CA"),
        ("CSV",   "csv",   "\U0001F4C4"),
        ("PDF",   "pdf",   "\U0001F4C4"),
        ("Print", "print", "\U0001F5A8"),
        ("TXT",   "txt",   "\U0001F4C3"),
        ("SQL",   "sql",   "\U0001F5C4"),
        ("Docx",  "docx",  "\U0001F4DD"),
        ("PNG",   "png",   "\U0001F5BC"),
    )

    def __init__(self, parent=None, on_export=None, buttons=None):
        super().__init__(parent)
        self._on_export = on_export

        h = QHBoxLayout(self)
        h.setContentsMargins(0, 6, 0, 6)
        h.setSpacing(0)
        h.addStretch()

        specs = buttons if buttons is not None else self.BUTTONS
        last_idx = len(specs) - 1

        for i, (label, kind, icon) in enumerate(specs):
            b = QPushButton(f"  {icon}  {label}  ")
            b.setFixedHeight(30)
            b.setCursor(Qt.CursorShape.PointingHandCursor)

            tl = "4px" if i == 0 else "0px"
            tr = "4px" if i == last_idx else "0px"
            bl = "4px" if i == 0 else "0px"
            br = "4px" if i == last_idx else "0px"

            b.setStyleSheet(
                f"QPushButton {{"
                f"  background: #dd4b39;"
                f"  color: #ffffff;"
                f"  border: 1px solid #c23321;"
                f"  border-right: 1px solid #b7301f;"
                f"  border-top-left-radius: {tl};"
                f"  border-top-right-radius: {tr};"
                f"  border-bottom-left-radius: {bl};"
                f"  border-bottom-right-radius: {br};"
                f"  padding: 4px 12px;"
                f"  font-size: 12px;"
                f"  font-weight: 600;"
                f"}}"
                f"QPushButton:hover   {{ background: #d73925; }}"
                f"QPushButton:pressed {{ background: #c23321; }}")
            b.clicked.connect(lambda _, k=kind: self._fire(k))
            h.addWidget(b)

        h.addStretch()

    def _fire(self, kind):
        if self._on_export:
            self._on_export(kind)


# =========================================================================== #
# Generic multi-format export helper
# =========================================================================== #
def _generic_export(parent, kind, rows, columns, filename_stub,
                    sql_table, sql_cols):
    """Export `rows` in the format requested.

    columns : list of (key, header) tuples
    """
    if not rows:
        W.info(parent, "Nothing to export.")
        return

    keys = [k for k, _ in columns]
    headers = [h for _, h in columns]

    # ------------------------------------------------------------------ copy
    if kind == "copy":
        lines = ["\t".join(headers)]
        for r in rows:
            lines.append("\t".join(str(r.get(k, "")) for k in keys))
        QApplication.clipboard().setText("\n".join(lines))
        W.info(parent, f"Copied {len(rows)} rows to clipboard.")
        return

    # ------------------------------------------------------------------ print
    if kind == "print":
        html = [
            "<html><body style='font-family:Segoe UI;font-size:10pt;'>",
            "<table border='1' cellspacing='0' cellpadding='4'"
            " style='border-collapse:collapse;'>",
            "<tr style='background:#dd4b39;color:#fff;'>",
        ]
        html += [f"<th>{h}</th>" for h in headers]
        html.append("</tr>")
        for r in rows:
            html.append("<tr>")
            for k in keys:
                html.append(f"<td>{r.get(k, '')}</td>")
            html.append("</tr>")
        html.append("</table></body></html>")

        doc = QTextDocument()
        doc.setHtml("".join(html))
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        dlg = QPrintPreviewDialog(printer, parent)
        dlg.setWindowTitle("Print")
        W.apply(dlg)                       # brand mark on the title bar
        dlg.paintRequested.connect(lambda p: doc.print(p))
        dlg.exec()
        return

    # ------------------------------------------------------------ file picker
    if kind == "csv":
        ext, filt = "csv", "CSV Files (*.csv)"
    elif kind == "txt":
        ext, filt = "txt", "Text Files (*.txt)"
    elif kind == "json":
        ext, filt = "json", "JSON Files (*.json)"
    elif kind == "sql":
        ext, filt = "sql", "SQL Files (*.sql)"
    elif kind == "excel":
        ext, filt = "csv", "Excel Files (*.csv)"
    elif kind == "docx":
        ext, filt = "html", "Word Documents (*.html)"
    elif kind == "pdf":
        ext, filt = "pdf", "PDF Files (*.pdf)"
    elif kind == "png":
        ext, filt = "png", "PNG Images (*.png)"
    else:
        W.info(parent, f"Export '{kind}' is not supported.")
        return

    default = os.path.join(os.path.expanduser("~"),
                           f"{filename_stub}.{ext}")
    fname, _ = QFileDialog.getSaveFileName(parent, f"Save {ext.upper()}",
                                           default, filt)
    if not fname:
        return
    if not fname.lower().endswith("." + ext):
        fname += "." + ext

    if kind in ("csv", "excel"):
        with open(fname, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(headers)
            for r in rows:
                w.writerow([r.get(k, "") for k in keys])
        W.info(parent, f"Saved to {fname}")

    elif kind == "txt":
        lines = ["\t".join(headers)]
        for r in rows:
            lines.append("\t".join(str(r.get(k, "")) for k in keys))
        with open(fname, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        W.info(parent, f"Saved to {fname}")

    elif kind == "json":
        data = [{k: r.get(k, "") for k in keys} for r in rows]
        with open(fname, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)
        W.info(parent, f"Saved to {fname}")

    elif kind == "sql":
        def esc(v):
            return ("NULL" if v is None
                    else "'" + str(v).replace("'", "''") + "'")
        lines = []
        for r in rows:
            vals = ", ".join(esc(r.get(k)) for k in sql_cols)
            lines.append(f"INSERT INTO {sql_table} "
                         f"({', '.join(sql_cols)}) VALUES ({vals});")
        with open(fname, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        W.info(parent, f"Saved to {fname}")

    elif kind == "docx":
        html = ["<html><body style='font-family:Calibri;font-size:11pt;'>"]
        html.append("<table border='1' cellspacing='0' cellpadding='4'"
                    " style='border-collapse:collapse;'>")
        html.append("<tr>")
        html += [f"<th>{h}</th>" for h in headers]
        html.append("</tr>")
        for r in rows:
            html.append("<tr>")
            for k in keys:
                html.append(f"<td>{r.get(k, '')}</td>")
            html.append("</tr>")
        html.append("</table></body></html>")
        with open(fname, "w", encoding="utf-8") as f:
            f.write("".join(html))
        W.info(parent, f"Saved to {fname}")

    elif kind == "pdf":
        from PyQt6.QtGui import QPageSize, QPageLayout
        from PyQt6.QtCore import QMarginsF
        html = ["<html><head><style>"
                "body{font-family:'Segoe UI';font-size:10pt;}"
                "table{border-collapse:collapse;width:100%;}"
                "th{background:#dd4b39;color:#fff;padding:6px;"
                "   border:1px solid #999;text-align:left;}"
                "td{padding:5px;border:1px solid #ccc;}"
                "</style></head><body>"]
        html.append("<table><tr>")
        html += [f"<th>{h}</th>" for h in headers]
        html.append("</tr>")
        for r in rows:
            html.append("<tr>")
            for k in keys:
                html.append(f"<td>{r.get(k, '')}</td>")
            html.append("</tr>")
        html.append("</table></body></html>")

        doc = QTextDocument()
        doc.setHtml("".join(html))

        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
        printer.setOutputFileName(fname)
        printer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
        printer.setPageMargins(QMarginsF(10, 10, 10, 10),
                               QPageLayout.Unit.Millimeter)
        doc.print(printer)
        W.info(parent, f"Saved to {fname}")

    elif kind == "png":
        from PyQt6.QtGui import QImage, QPainter, QColor
        html = ["<html><body style='background:#ffffff;"
                "font-family:Arial;font-size:11pt;color:#222;'>"]
        html.append("<table border='1' cellspacing='0' cellpadding='6'"
                    " style='border-collapse:collapse;'>")
        html.append("<tr style='background:#dd4b39;color:#fff;'>")
        html += [f"<th>{h}</th>" for h in headers]
        html.append("</tr>")
        for r in rows:
            html.append("<tr>")
            for k in keys:
                html.append(f"<td>{r.get(k, '')}</td>")
            html.append("</tr>")
        html.append("</table></body></html>")

        doc = QTextDocument()
        doc.setHtml("".join(html))
        doc.setTextWidth(1000)
        size = doc.size().toSize()
        size.setWidth(max(size.width() + 20, 800))
        size.setHeight(max(size.height() + 20, 200))

        img = QImage(size, QImage.Format.Format_ARGB32)
        img.fill(QColor("#ffffff"))
        painter = QPainter(img)
        doc.drawContents(painter)
        painter.end()
        img.save(fname, "PNG")
        W.info(parent, f"Saved to {fname}")


class _ViewportRelayout(QObject):
    """Re-apply the column layout whenever the table viewport is resized.

    The page's own `resizeEvent` is not enough: a page that is created at its
    final size never receives one, and the viewport width is still 0 while the
    constructor runs, so `_relayout_columns` would bail out and leave the
    columns at their `ResizeToContents` defaults.  Watching the viewport
    guarantees the layout is applied as soon as there is a real width to
    divide up.
    """

    def __init__(self, table, callback):
        super().__init__(table)
        self._callback = callback
        table.viewport().installEventFilter(self)

    def eventFilter(self, obj, event):
        if event.type() in (QEvent.Type.Resize, QEvent.Type.Show):
            self._callback()
        return False


class ReportPage(QWidget):
    def __init__(self, main, kind, doc, title):
        super().__init__()
        self.main = main
        self.kind = kind          # item | hsn | summary | quickquote
        self.doc = doc
        self.title = title
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(W.PageHeader(title,
                                   breadcrumb=REPORT_CRUMB.get((kind, doc),
                                                               title)))
        box = W.Box(f"{title}", "danger")

        bar = QHBoxLayout()
        self.dates = W.DateRangeBar(on_change=self.refresh)
        bar.addWidget(self.dates)
        if kind == "item":
            from PyQt6.QtWidgets import QLineEdit
            self.item_edit = QLineEdit()
            self.item_edit.setPlaceholderText("Item name...")
            self.item_edit.setFixedWidth(200)
            self.item_edit.setClearButtonEnabled(True)
            self.item_edit.textChanged.connect(self.refresh)
            bar.addWidget(self.item_edit)
        bar.addStretch()
        box.addLayout(bar)

        # ---- export buttons (centered red strip - same as the master pages) --
        self.export_strip = ExportButtonStrip(self, on_export=self._on_export)
        box.add(self.export_strip)

        self.headers, self.columns, self.total_cols = self._spec()
        self.table = W.DataTable(self.headers)
        # re-divide the width whenever the table itself gets a real width
        self._relayout_watch = _ViewportRelayout(
            self.table, self._relayout_columns)
        box.add(self.table, 1)
        self.paginator = W.Paginator(on_change=self._render)
        box.add(self.paginator, 0)
        from PyQt6.QtWidgets import QLabel
        self.totals_label = QLabel("")
        self.totals_label.setStyleSheet("font-weight: 600; color: #444;")
        box.add(self.totals_label)
        lay.addWidget(box, 1)
        self._rows = []
        self.refresh()

    def _spec(self):
        if self.kind == "item":
            return (["Sr No", "Invoice", "Client", "Date", "Item",
                     "Description", "HSN", "Qty", "Price", "Subtotal",
                     "Tax Rate", "Tax Amt", "Total"],
                    ["invid", "c_name", "doc_date", "item_name", "item_desc",
                     "hsn", "quantity", "price", "subtotal", "taxrate",
                     "taxamount", "totalamount"],
                    [6, 8, 10, 11])
        if self.kind == "hsn":
            return (["Sr No", "HSN", "Total Qty", "Total Price", "Subtotal"],
                    ["hsn", "quantity", "price", "subtotal"],
                    [1, 2, 3])
        if self.kind == "quickquote":
            return (["Sr No", "Quote ID", "Product", "Mobile", "Qty", "Price",
                     "Subtotal", "GST", "Total", "Date"],
                    ["q_id", "product_name", "mob", "quantity", "price",
                     "subtotal", "gst", "total", "created"],
                    [5, 6, 7])
        return (["Sr No", "Invoice", "Client", "Date", "Items", "Subtotal",
                 "Tax Rate", "Tax Amt", "Total"],
                ["invid", "c_name", "doc_date", "totalitems", "subtotal",
                 "taxrate", "taxamount", "totalamount"],
                [4, 6, 7])

    def _data(self):
        start, end = self.dates.dates()
        if self.kind == "item":
            return db_manager.item_report(self.doc, start, end,
                                          self.item_edit.text().strip())
        if self.kind == "hsn":
            return db_manager.hsn_report(self.doc, start, end)
        if self.kind == "quickquote":
            return db_manager.quickquote_report(start, end)
        return db_manager.list_invoices(self.doc, start, end)

    def refresh(self):
        try:
            self._rows = self._data()
        except Exception as exc:
            W.error(self, f"Database error: {exc}")
            return
        self._render()

    def _render(self):
        rows = self._rows
        self.paginator._preserve_current = True
        self.paginator._refresh_total(len(rows))
        start, end = self.paginator.page_range()
        page_rows = rows[start:end]

        self.table.clear_rows()
        # sums per data column (visible page), keyed by column index
        sums = {c: 0.0 for c in self.total_cols}
        for i, r in enumerate(page_rows):
            cells = [start + i + 1]
            for c, col in enumerate(self.columns):
                v = r.get(col, "")
                if col in ("subtotal", "price", "taxamount", "totalamount",
                           "gst", "total"):
                    v = money(v)
                    if c in sums:
                        sums[c] += float(r[col] or 0)
                cells.append(v)
            self.table.add_row(cells)
        # totals row: header position 0 is the Sr No column, data starts at 1
        totals_row = [None]        # 'Total' label goes here
        for c in range(len(self.columns)):
            totals_row.append(money(sums[c]) if c in sums else "")
        self.table.apply_totals_row(totals_row)
        # width the columns against the data that is actually displayed
        self._relayout_columns()
        # footer: overall totals across all filtered rows
        ov = {c: sum(float(r.get(self.columns[c]) or 0) for r in rows)
              for c in self.total_cols}
        parts = ", ".join(f"{self.headers[c + 1]}: {money(ov[c])}"
                          for c in self.total_cols)
        self.totals_label.setText(f"{len(rows)} records  |  {parts}")

    def _relayout_columns(self):
        """Re-measure the columns against the current data + viewport width.

        Called after every render (so the widths follow the filtered data) and
        on every window resize (so the spare width is redistributed at the new
        size instead of leaving a gap or forcing a scrollbar).
        """
        if not hasattr(self, "table") or not self.headers:
            return
        if self.table.viewport().width() <= 0:
            return          # not laid out yet - resizeEvent will catch up
        _apply_column_layout(self.table, self.headers, self.columns,
                             self._rows)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._relayout_columns()

    def _on_export(self, kind):
        """Export the filtered report rows in the requested format.

        Mirrors the master pages' DataTables "Buttons" strip: every filtered
        row is exported (not just the visible page), using the report's own
        column headings.  'Sr No' is display-only, so - exactly like the
        master pages skip their Sr.No column - it is left out of the export.
        """
        columns = list(zip(self.columns, self.headers[1:]))
        stub = self.title.lower().replace(" ", "_")
        _generic_export(
            self, kind, self._rows, columns,
            filename_stub=stub,
            sql_table=stub,
            sql_cols=list(self.columns))