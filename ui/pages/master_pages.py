"""
Master CRUD pages - Manage Clients / Suppliers / Products

Layout matches the DataTables chrome in the PHP view:

  Manage-Suppliers
  ─────────────────────
  ┌──────────────────────────────────────────────────────────────────┐
  │ All Supplier Details                          [+ Add Supplier]   │
  │ Show [10 ▾] entries                    Search: [.............]   │
  │    [ Copy ][ JSON ][ Excel ][ CSV ][ PDF ][ Print ][ TXT ] …     │
  │ ──────────────────────────────────────────────────────────────── │
  │  table                                                           │
  │ ──────────────────────────────────────────────────────────────── │
  │  Showing 1 to 10 of N entries   [ « ] [1] [2] [3] … [ » ]        │
  │                          [Sr.No.] [Supplier Name] [Address] …    │
  └──────────────────────────────────────────────────────────────────┘

Fixes in this revision
----------------------
1. Manage Clients shows u_type = 0 (Client) AND u_type = 2 (Dual).
   Suppliers shows u_type = 1 (Supplier) AND u_type = 2 (Dual).
   (Handled in db_manager.list_clients via a list argument.)

2. Added a "Show:" dropdown so you can quickly filter to
   "Dual only", "Clients only", etc., even with thousands of rows.

3. "Bill - Type" now falls back through three tiers, so nothing shows blank.
4. "User - Type" falls back to the page's own u_type when the DB value is NULL.
"""
import csv
import json
import os
from datetime import date

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QTextDocument
from PyQt6.QtPrintSupport import QPrinter, QPrintPreviewDialog
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QHeaderView, QComboBox, QLabel, QLineEdit,
                             QFrame, QFileDialog, QApplication)

from database import db_manager
from ui import widgets as W
from ui.icons import icon_button


# --------------------------------------------------------------------------- #
# Top bar: Show [N] entries on the left, Search: on the right
# --------------------------------------------------------------------------- #
class DTTopBar(QWidget):
    def __init__(self, parent, on_search, on_page_size,
                 search_placeholder="Search..."):
        super().__init__(parent)
        h = QHBoxLayout(self)
        h.setContentsMargins(0, 4, 0, 4)
        h.setSpacing(8)

        h.addWidget(QLabel("Show"))
        self.page_size = QComboBox()
        self.page_size.addItem("10", 10)
        self.page_size.addItem("20", 20)
        self.page_size.addItem("50", 50)
        self.page_size.addItem("100", 100)
        self.page_size.addItem("All", 0)
        self.page_size.setCurrentIndex(0)
        self.page_size.setFixedWidth(80)
        self.page_size.currentIndexChanged.connect(
            lambda: on_page_size(self.page_size.currentData()))
        h.addWidget(self.page_size)
        h.addWidget(QLabel("entries"))

        h.addStretch()

        h.addWidget(QLabel("Search:"))
        self.search = QLineEdit()
        self.search.setPlaceholderText(search_placeholder)
        self.search.setFixedHeight(30)
        self.search.setMinimumWidth(240)
        self.search.textChanged.connect(lambda _: on_search())
        h.addWidget(self.search)


# --------------------------------------------------------------------------- #
# Footer: Showing X to Y on the left, page buttons on the right
# --------------------------------------------------------------------------- #
class DTFooter(QWidget):
    def __init__(self, parent, on_goto):
        super().__init__(parent)
        self._on_goto = on_goto
        self._current = 1
        self._total = 1
        self._per_page = 10
        self._count = 0

        h = QHBoxLayout(self)
        h.setContentsMargins(0, 4, 0, 4)
        h.setSpacing(8)

        self.info = QLabel("Showing 0 to 0 of 0 entries")
        self.info.setStyleSheet("color:#555; font-size:12px;")
        h.addWidget(self.info)

        h.addStretch()

        self._nav_host = QWidget()
        self._nav = QHBoxLayout(self._nav_host)
        self._nav.setContentsMargins(0, 0, 0, 0)
        self._nav.setSpacing(4)
        h.addWidget(self._nav_host)

    def update_state(self, current, total, per_page, count):
        self._current = max(1, current)
        self._total = max(1, total)
        self._per_page = per_page or count or 1
        self._count = count

        if count == 0:
            self.info.setText("Showing 0 to 0 of 0 entries")
        else:
            first = (self._current - 1) * self._per_page + 1
            last = min(self._current * self._per_page, count)
            self.info.setText(
                f"Showing {first} to {last} of {count} entries")

        self._rebuild_nav()

    def _clear_nav(self):
        while self._nav.count():
            item = self._nav.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

    def _nav_button(self, text, page, enabled=True, current=False):
        b = QPushButton(text)
        b.setFixedHeight(28)
        b.setMinimumWidth(34)
        b.setCursor(Qt.CursorShape.PointingHandCursor)
        if current:
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
                "QPushButton:disabled { color:#aaa; background:#fafafa; }")
            b.setEnabled(enabled)
        if enabled and not current:
            b.clicked.connect(lambda _, p=page: self._on_goto(p))
        return b

    def _rebuild_nav(self):
        self._clear_nav()
        total = self._total
        cur = self._current

        self._nav.addWidget(self._nav_button("«", cur - 1, enabled=cur > 1))

        window = 5
        start = max(1, cur - window // 2)
        end = min(total, start + window - 1)
        start = max(1, end - window + 1)

        if start > 1:
            self._nav.addWidget(self._nav_button("1", 1,
                                                 current=(cur == 1)))
            if start > 2:
                ell = QLabel("…")
                ell.setStyleSheet("color:#888; padding:0 4px;")
                self._nav.addWidget(ell)

        for p in range(start, end + 1):
            self._nav.addWidget(self._nav_button(str(p), p,
                                                 current=(p == cur)))

        if end < total:
            if end < total - 1:
                ell = QLabel("…")
                ell.setStyleSheet("color:#888; padding:0 4px;")
                self._nav.addWidget(ell)
            self._nav.addWidget(self._nav_button(str(total), total,
                                                 current=(cur == total)))

        self._nav.addWidget(self._nav_button("»", cur + 1,
                                             enabled=cur < total))


# --------------------------------------------------------------------------- #
# Column-toggle strip (bottom-LEFT, blue buttons - matches Ledger page)
# --------------------------------------------------------------------------- #
class ColumnToggleStrip(QWidget):
    """Row of checkable buttons that show/hide each table column.

    Colours match the Ledger page strip: blue while the column is visible,
    red once it is toggled off.
    """

    def __init__(self, parent, headers, table):
        super().__init__(parent)
        self._table = table
        h = QHBoxLayout(self)
        h.setContentsMargins(0, 8, 0, 0)
        h.setSpacing(4)

        for i, label in enumerate(headers):
            b = QPushButton(label)
            b.setFixedHeight(26)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setStyleSheet(
                "QPushButton { background:#3c8dbc; color:#ffffff;"
                " border:1px solid #367fa9; border-radius:3px;"
                " padding:2px 10px; font-size:11.5px; }"
                "QPushButton:hover { background:#367fa9; }"
                "QPushButton:!checked { background:#dd4b39;"
                " border-color:#c23321; }")
            b.setCheckable(True)
            b.setChecked(True)
            b.toggled.connect(
                lambda on, col=i: table.setColumnHidden(col, not on))
            h.addWidget(b)

        # trailing stretch pins the strip to the bottom-LEFT corner
        h.addStretch()


# --------------------------------------------------------------------------- #
# Centered red export button strip (DataTables "Buttons" style)
# --------------------------------------------------------------------------- #
class ExportButtonStrip(QWidget):
    BUTTONS = (
        ("Copy",  "copy",  "🗐"),
        ("JSON",  "json",  "{}"),
        ("Excel", "excel", "📊"),
        ("CSV",   "csv",   "📄"),
        ("PDF",   "pdf",   "📄"),
        ("Print", "print", "🖨"),
        ("TXT",   "txt",   "📃"),
        ("SQL",   "sql",   "🗄"),
        ("Docx",  "docx",  "📝"),
        ("PNG",   "png",   "🖼"),
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


# --------------------------------------------------------------------------- #
# Paging state
# --------------------------------------------------------------------------- #
class _TableState:
    def __init__(self):
        self.per_page = 10
        self.current = 1

    def total_pages(self, count):
        if self.per_page == 0 or self.per_page <= 0:
            return 1
        return max(1, (count + self.per_page - 1) // self.per_page)

    def page_range(self, count):
        if self.per_page == 0 or self.per_page <= 0:
            return 0, count
        start = (self.current - 1) * self.per_page
        end = min(start + self.per_page, count)
        return start, end


# --------------------------------------------------------------------------- #
# Column width helper
# --------------------------------------------------------------------------- #
def _apply_column_widths(table, stretch_cols, fixed_cols):
    header = table.horizontalHeader()
    header.setStretchLastSection(False)
    header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
    for col, width in fixed_cols.items():
        header.setSectionResizeMode(col, QHeaderView.ResizeMode.Fixed)
        table.setColumnWidth(col, width)
    for col in stretch_cols:
        header.setSectionResizeMode(col, QHeaderView.ResizeMode.Stretch)


# --------------------------------------------------------------------------- #
# Card wrapper
# --------------------------------------------------------------------------- #
def _make_card(parent):
    card = QFrame(parent)
    card.setStyleSheet(
        "QFrame { background: #ffffff; border: 1px solid #d2d6de;"
        " border-radius: 3px; }")
    v = QVBoxLayout(card)
    v.setContentsMargins(14, 12, 14, 12)
    v.setSpacing(6)
    return card, v


# =========================================================================== #
# Generic export helper
# =========================================================================== #
def _generic_export(parent, kind, rows, columns, filename_stub,
                    sql_table, sql_cols):
    if not rows:
        W.info(parent, "Nothing to export.")
        return

    keys = [k for k, _ in columns]
    headers = [h for _, h in columns]

    if kind == "copy":
        lines = ["\t".join(headers)]
        for r in rows:
            lines.append("\t".join(str(r.get(k, "")) for k in keys))
        QApplication.clipboard().setText("\n".join(lines))
        W.info(parent, f"Copied {len(rows)} rows to clipboard.")
        return

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
            return "NULL" if v is None else "'" + str(v).replace("'", "''") + "'"
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


# =========================================================================== #
# Client / Supplier master page
# =========================================================================== #
class ClientMasterPage(QWidget):
    title = "Manage Clients"
    u_type = 0

    HEADERS = ["Sr. No.", "Supplier Name", "Address", "Mobile",
               "GST No.", "Email", "Bill - Type", "User - Type",
               "Edit", "View", "Delete"]

    FIXED_WIDTHS = {
        0: 60,
        6: 90,
        7: 90,
        8: 50,
        9: 50,
        10: 50,
    }
    STRETCH_COLS = [1, 2, 3, 4, 5]

    def __init__(self, main):
        super().__init__()
        self.main = main
        self._state = _TableState()

        header_title = "Manage-Suppliers" if self.u_type else "Manage-Clients"

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)

        lay.addWidget(W.PageHeader(header_title))

        self.types_cache = [(c["id"], c["type"]) for c in
                            db_manager.get_client_types()]

        # Each page shows its own u_type PLUS Dual (2).
        #   0 = Client,  1 = Supplier,  2 = Dual (Cust/Sup)
        if self.u_type in (0, 1):
            self._filter_types = [self.u_type, 2]
        else:
            self._filter_types = None

        card, body = _make_card(self)

        # ---- header row: "All X Details" + [+ Add] ----
        header_row = QHBoxLayout()
        title_lbl = QLabel(
            f"All {'Supplier' if self.u_type else 'Client'} Details")
        title_lbl.setStyleSheet(
            "font-size: 15px; font-weight: 600; color: #444;"
            " background: transparent; border: none;")
        header_row.addWidget(title_lbl)
        header_row.addStretch()

        btn_add = QPushButton("+ Add Supplier" if self.u_type
                              else "+ Add Client")
        btn_add.setObjectName("btnSuccess")
        btn_add.setFixedHeight(30)
        btn_add.clicked.connect(self._add)
        header_row.addWidget(btn_add)
        body.addLayout(header_row)

        # ---- Show entries + Search ----
        self.top = DTTopBar(
            self, on_search=self.refresh, on_page_size=self._set_page_size,
            search_placeholder="Search name / address / mobile / GST...")
        body.addWidget(self.top)

        # ---- user-type filter (All / own type / Dual only) ----
        filter_row = QHBoxLayout()
        filter_row.setSpacing(8)
        filter_row.addWidget(QLabel("Show:"))
        self.utype_filter = QComboBox()
        self.utype_filter.setFixedHeight(30)

        # The default first entry matches the page's own default filter.
        if self.u_type == 0:
            self.utype_filter.addItem("All (Clients + Dual)", [0, 2])
            self.utype_filter.addItem("Clients only", [0])
            self.utype_filter.addItem("Dual only", [2])
        elif self.u_type == 1:
            self.utype_filter.addItem("All (Suppliers + Dual)", [1, 2])
            self.utype_filter.addItem("Suppliers only", [1])
            self.utype_filter.addItem("Dual only", [2])
        else:
            self.utype_filter.addItem("All", None)

        self.utype_filter.currentIndexChanged.connect(self._utype_changed)
        filter_row.addWidget(self.utype_filter)
        filter_row.addStretch()
        body.addLayout(filter_row)

        # ---- export buttons (centered) ----
        self.export_strip = ExportButtonStrip(
            self, on_export=self._on_export)
        body.addWidget(self.export_strip)

        # ---- table ----
        self.table = W.DataTable(self.HEADERS)
        _apply_column_widths(self.table, self.STRETCH_COLS, self.FIXED_WIDTHS)
        body.addWidget(self.table, 1)

        # ---- footer ----
        self.footer = DTFooter(self, on_goto=self._goto_page)
        body.addWidget(self.footer)

        # ---- column-toggle strip (bottom-left) ----
        self.col_toggles = ColumnToggleStrip(self, self.HEADERS, self.table)
        body.addWidget(self.col_toggles)

        lay.addWidget(card, 1)

        self._rows = []
        self.refresh()

    # ------------------------------------------------------------ state
    def _set_page_size(self, size):
        self._state.per_page = int(size) if size else 0
        self._state.current = 1
        self._render()

    def _goto_page(self, page):
        self._state.current = max(1, page)
        self._render()

    def _utype_changed(self):
        """User-type filter dropdown changed."""
        self._filter_types = self.utype_filter.currentData()
        self._state.current = 1
        self.refresh()

    # ------------------------------------------------------------ data
    def refresh(self):
        try:
            self._rows = db_manager.list_clients(
                self.top.search.text().strip(), self._filter_types)
        except Exception as exc:
            W.error(self, f"Database error: {exc}")
            return
        self._render()

    def _render(self):
        rows = self._rows
        total_pages = self._state.total_pages(len(rows))
        if self._state.current > total_pages:
            self._state.current = total_pages
        start, end = self._state.page_range(len(rows))
        page_rows = rows[start:end]

        self.table.clear_rows()
        tmap = dict(self.types_cache)

        for i, r in enumerate(page_rows):
            # ---- Bill - Type: three-tier fallback so nothing shows blank ---
            bill_type = (
                r.get("c_type_name")
                or tmap.get(self._type_key(r))
                or (str(r.get("c_type"))
                    if r.get("c_type") not in (None, "") else "")
            )

            # ---- User - Type (0/1/2) ------------------------------------
            user_type = self._utype_label(r)

            row = self.table.add_row(
                [start + i + 1,
                 r["c_name"], r["c_add"], r["mob"],
                 r["gst"], r["email"] or "",
                 bill_type,
                 user_type,
                 "", "", ""],
                data=r["cid"])
            self._add_action_buttons(row, r)

        self.footer.update_state(
            self._state.current, total_pages,
            self._state.per_page or len(rows) or 1, len(rows))

    def _type_key(self, r):
        """Resolve c_type to a types_cache id (support name or id)."""
        c_type = r.get("c_type")
        if c_type is None:
            return None
        for tid, tname in self.types_cache:
            if str(c_type) == str(tname):
                return tid
        try:
            return int(c_type)
        except (TypeError, ValueError):
            return c_type

    def _utype_label(self, r):
        """0=Client, 1=Supplier, 2=Dual(Cust/Sup). NULL -> page's own type."""
        ut = r.get("u_type")
        if ut is None:
            ut = self.u_type
        try:
            ut = int(ut)
        except (TypeError, ValueError):
            return str(ut) if ut not in (None, "") else ""
        # Same source of truth as the dialog combo (UTYPE_OPTIONS).
        labels = dict(self.UTYPE_OPTIONS)
        return labels.get(ut, "")

    def _add_action_buttons(self, row, record):
        # Edit
        cell_e = QWidget()
        he = QHBoxLayout(cell_e)
        he.setContentsMargins(0, 0, 0, 0)
        he.setSpacing(0)
        eb = icon_button("edit", "btnDanger", "Edit")
        eb.clicked.connect(lambda _, r=record: self._edit(r))
        he.addWidget(eb, 0, Qt.AlignmentFlag.AlignCenter)
        self.table.setCellWidget(row, 8, cell_e)

        # View
        cell_v = QWidget()
        hv = QHBoxLayout(cell_v)
        hv.setContentsMargins(0, 0, 0, 0)
        hv.setSpacing(0)
        vb = W.info_action_button(f"View {record['c_name']} info")
        vb.clicked.connect(lambda _, r=record: self._info(r))
        hv.addWidget(vb, 0, Qt.AlignmentFlag.AlignCenter)
        self.table.setCellWidget(row, 9, cell_v)

        # Delete
        cell_d = QWidget()
        hd = QHBoxLayout(cell_d)
        hd.setContentsMargins(0, 0, 0, 0)
        hd.setSpacing(0)
        db = icon_button("delete", "btnWarning", "Delete")
        db.clicked.connect(lambda _, r=record: self._delete(r))
        hd.addWidget(db, 0, Qt.AlignmentFlag.AlignCenter)
        self.table.setCellWidget(row, 10, cell_d)

    # ------------------------------------------------------------ export
    def _on_export(self, kind):
        columns = [
            ("c_name", "Name"),
            ("c_add", "Address"),
            ("mob", "Mobile"),
            ("gst", "GST"),
            ("email", "Email"),
        ]
        _generic_export(
            self, kind, self._rows, columns,
            filename_stub="clients",
            sql_table="client",
            sql_cols=["c_name", "c_add", "mob", "gst", "email"])

    # ------------------------------------------------------------ form
    def _specs(self):
        return [
            ("Name *", "c_name", "text", None),
            ("Address", "c_add", "textarea", None),
            ("Mobile *", "mob", "text", None),
            ("Country", "country", "text", None),
            ("GST No", "gst", "text", None),
            ("Email", "email", "text", None),
            ("Client Type", "c_type", "combo", self.type_name_options()),
            # Mirrors the "User Type" <select> in the CodeIgniter
            # manage-clients / manage-suppliers modals (add AND edit):
            #   0 = Client, 1 = Supplier, 2 = Dual(Cust/Sup)
            # Same labels and same codes, so the stored u_type is identical
            # to what the web app writes.
            ("User Type", "u_type", "combo", self.UTYPE_OPTIONS),
        ]

    # User-Type choices for the add/edit dialog. Kept in one place so the
    # combo and _utype_label() can never drift apart.
    UTYPE_OPTIONS = [(0, "Client"),
                     (1, "Supplier"),
                     (2, "Dual(Cust/Sup)")]

    def type_name_options(self):
        """[(name, name)] for the Bill/Client-Type combo.

        client.c_type is a varchar(4) that stores the TYPE NAME ('IGST',
        'Loc') - exactly what the CodeIgniter form posts
        (<option value="IGST">IGST</option>) - NOT clienttype.id.

        The combo therefore has to use the name as BOTH the label and the
        data. Feeding it the ids instead meant the row's stored name never
        matched, and FormDialog's "unknown value" fallback appended it as an
        extra row, so every Edit dialog listed e.g. IGST / Loc / Loc.
        Names are de-duplicated case-insensitively so a dirty clienttype table
        cannot reintroduce the same duplicate.
        """
        out, seen = [], set()
        for _tid, tname in self.types_cache:
            t = str(tname).strip()
            if t and t.lower() not in seen:
                seen.add(t.lower())
                out.append((t, t))
        return out

    def _ctype_name(self, row=None):
        """Normalise a row's c_type to the stored type NAME.

        Accepts the name (normal case) and also an id, which is what an older
        build of this app wrote into that varchar column; both resolve to the
        proper name so editing such a row repairs it instead of duplicating.
        """
        val = (row or {}).get("c_type")
        if val in (None, ""):
            opts = self.type_name_options()
            return opts[0][0] if opts else ""
        s = str(val).strip()
        for _tid, tname in self.types_cache:
            if s.lower() == str(tname).strip().lower():
                return str(tname).strip()
        try:
            n = int(s)
        except (TypeError, ValueError):
            return s
        for tid, tname in self.types_cache:
            try:
                if int(tid) == n:
                    return str(tname).strip()
            except (TypeError, ValueError):
                continue
        return s

    def _utype_value(self, row=None):
        """Normalised u_type (int) for the dialog.

        A row can carry NULL/blank u_type on legacy data, in which case we
        fall back to the page's own type (0 = Clients page, 1 = Suppliers
        page) - the same fallback _utype_label() uses when rendering.
        Without this the combo would silently show "Client" (index 0) for a
        legacy supplier and an edit would rewrite its type.
        """
        val = (row or {}).get("u_type")
        if val in (None, ""):
            return self.u_type
        try:
            return int(val)
        except (TypeError, ValueError):
            return self.u_type

    def _add(self):
        type_opts = self.type_name_options()
        dlg = W.FormDialog(self, "Add New Client", self._specs(),
                           values={"c_type": type_opts[0][0]
                                   if type_opts else "",
                                   # Default to this page's own type
                                   # (Client page -> Client, Suppliers page ->
                                   # Supplier), matching the web app's
                                   # Manage-Clients / Manage-Suppliers split.
                                   "u_type": self.u_type})
        if dlg.exec():
            data = dlg.get()
            if not data["c_name"] or not data["mob"]:
                W.error(self, "Name and Mobile are required.")
                return
            # User Type now comes from the dialog instead of being forced.
            if data.get("u_type") is None:
                data["u_type"] = self.u_type
            data["created"] = date.today()
            try:
                db_manager.insert_client(data)
            except Exception as exc:
                W.error(self, f"Insert failed: {exc}")
                return
            W.info(self, "Record added successfully.")
            self.refresh()

    def _edit(self, r):
        values = dict(r)
        # Normalise so the combo selects the row's real type even for
        # NULL/legacy values.
        values["u_type"] = self._utype_value(r)
        # c_type is stored as the type NAME; feed the combo that exact value
        # so findData() hits an existing entry instead of appending a
        # duplicate one.
        values["c_type"] = self._ctype_name(r)
        dlg = W.FormDialog(self, f"Edit Client #{r['cid']}", self._specs(),
                           values=values)
        if dlg.exec():
            data = dlg.get()
            if not data["c_name"] or not data["mob"]:
                W.error(self, "Name and Mobile are required.")
                return
            # Honour the User Type chosen in the dialog; keep the previous
            # value only when the combo somehow yields nothing.
            if data.get("u_type") is None:
                data["u_type"] = self._utype_value(r)
            try:
                db_manager.update_client(r["cid"], data)
            except Exception as exc:
                W.error(self, f"Update failed: {exc}")
                return
            W.info(self, "Record updated successfully.")
            self.refresh()

    def _info(self, r):
        kind = "supplier" if self.u_type == 1 else "client"
        self.main.open_info(kind, r["cid"])

    def _delete(self, r):
        if W.confirm(self, f"Delete '{r['c_name']}' (#{r['cid']})?"):
            db_manager.delete_client(r["cid"])
            self.refresh()


class ClientsPage(ClientMasterPage):
    title = "Manage Clients"
    u_type = 0


class SuppliersPage(ClientMasterPage):
    title = "Suppliers"
    u_type = 1


# =========================================================================== #
# Products page
# =========================================================================== #
class ProductsPage(QWidget):
    title = "Products"

    HEADERS = ["Sr No", "Name", "HSN", "Description", "Type",
               "Tech Specs", "Created", "Edit", "View", "Delete"]

    FIXED_WIDTHS = {
        0: 60,
        2: 90,
        4: 110,
        6: 100,
        7: 50,
        8: 50,
        9: 50,
    }
    STRETCH_COLS = [1, 3, 5]

    def __init__(self, main):
        super().__init__()
        self.main = main
        self._state = _TableState()

        self._types = sorted({r["p_type"] for r in db_manager.list_products()})

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)

        lay.addWidget(W.PageHeader("Manage-Products"))

        card, body = _make_card(self)

        header_row = QHBoxLayout()
        title_lbl = QLabel("All Product Details")
        title_lbl.setStyleSheet(
            "font-size: 15px; font-weight: 600; color: #444;"
            " background: transparent; border: none;")
        header_row.addWidget(title_lbl)
        header_row.addStretch()
        btn_add = QPushButton("+ Add Product")
        btn_add.setObjectName("btnSuccess")
        btn_add.setFixedHeight(30)
        btn_add.clicked.connect(self._add)
        header_row.addWidget(btn_add)
        body.addLayout(header_row)

        # ---- Show entries + Search ----
        self.top = DTTopBar(
            self, on_search=self.refresh, on_page_size=self._set_page_size,
            search_placeholder="Search name / description / HSN / type...")
        body.addWidget(self.top)

        # ---- export buttons (centered) ----
        self.export_strip = ExportButtonStrip(
            self, on_export=self._on_export)
        body.addWidget(self.export_strip)

        # ---- type filter ----
        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel("Type:"))
        self.type_filter = QComboBox()
        self.type_filter.addItem("All Types", None)
        for t in self._types:
            self.type_filter.addItem(t, t)
        self.type_filter.currentIndexChanged.connect(self.refresh)
        filter_row.addWidget(self.type_filter)
        filter_row.addStretch()
        body.addLayout(filter_row)

        # ---- table ----
        self.table = W.DataTable(self.HEADERS)
        _apply_column_widths(self.table, self.STRETCH_COLS, self.FIXED_WIDTHS)
        body.addWidget(self.table, 1)

        # ---- footer ----
        self.footer = DTFooter(self, on_goto=self._goto_page)
        body.addWidget(self.footer)

        # ---- column toggles (bottom-left) ----
        self.col_toggles = ColumnToggleStrip(self, self.HEADERS, self.table)
        body.addWidget(self.col_toggles)

        lay.addWidget(card, 1)

        self._rows = []
        self.refresh()

    # ------------------------------------------------------------ state
    def _set_page_size(self, size):
        self._state.per_page = int(size) if size else 0
        self._state.current = 1
        self._render()

    def _goto_page(self, page):
        self._state.current = max(1, page)
        self._render()

    # ------------------------------------------------------------ data
    def refresh(self):
        try:
            self._rows = db_manager.list_products(
                self.top.search.text().strip(),
                self.type_filter.currentData())
        except Exception as exc:
            W.error(self, f"Database error: {exc}")
            return
        self._render()

    def _render(self):
        rows = self._rows
        total_pages = self._state.total_pages(len(rows))
        if self._state.current > total_pages:
            self._state.current = total_pages
        start, end = self._state.page_range(len(rows))
        page_rows = rows[start:end]

        self.table.clear_rows()
        for i, r in enumerate(page_rows):
            row = self.table.add_row(
                [start + i + 1, r["name"], r["hsn"],
                 r["description"], r["p_type"], (r["techs"] or "")[:60],
                 str(r["created"]), "", "", ""],
                data=r["p_id"])

            ce = QWidget(); he = QHBoxLayout(ce)
            he.setContentsMargins(0, 0, 0, 0); he.setSpacing(0)
            eb = icon_button("edit", "btnDanger", "Edit")
            eb.clicked.connect(lambda _, r=r: self._edit(r))
            he.addWidget(eb, 0, Qt.AlignmentFlag.AlignCenter)
            self.table.setCellWidget(row, 7, ce)

            cv = QWidget(); hv = QHBoxLayout(cv)
            hv.setContentsMargins(0, 0, 0, 0); hv.setSpacing(0)
            ib = W.info_action_button(f"View {r['name']} info")
            ib.clicked.connect(lambda _, r=r: self._info(r))
            hv.addWidget(ib, 0, Qt.AlignmentFlag.AlignCenter)
            self.table.setCellWidget(row, 8, cv)

            cd = QWidget(); hd = QHBoxLayout(cd)
            hd.setContentsMargins(0, 0, 0, 0); hd.setSpacing(0)
            db_btn = icon_button("delete", "btnWarning", "Delete")
            db_btn.clicked.connect(lambda _, r=r: self._delete(r))
            hd.addWidget(db_btn, 0, Qt.AlignmentFlag.AlignCenter)
            self.table.setCellWidget(row, 9, cd)

        self.footer.update_state(
            self._state.current, total_pages,
            self._state.per_page or len(rows) or 1, len(rows))

    # ------------------------------------------------------------ export
    def _on_export(self, kind):
        columns = [
            ("name", "Name"),
            ("hsn", "HSN"),
            ("description", "Description"),
            ("p_type", "Type"),
            ("cattype", "Category"),
            ("techs", "Tech Specs"),
            ("created", "Created"),
        ]
        _generic_export(
            self, kind, self._rows, columns,
            filename_stub="products",
            sql_table="products",
            sql_cols=["name", "hsn", "description", "p_type", "cattype",
                      "techs", "created"])

    # ------------------------------------------------------------ form
    def _specs(self):
        types = [("Machine", "Machine"), ("Consumables", "Consumables"),
                 ("Freight", "Freight")]
        cats = [("", ""), ("Manual", "Manual"),
                ("Semi-Automatic", "Semi-Automatic"), ("Automatic", "Automatic")]
        return [
            ("Product Name *", "name", "text", None),
            ("Description *", "description", "textarea", None),
            ("HSN Code *", "hsn", "text", None),
            ("Product Type *", "p_type", "combo", types),
            ("Category", "cattype", "combo", cats),
            ("Product Image", "img_loc", "image", None),
            ("Technical Description", "techs", "textarea", None),
        ]

    def _validate(self, data):
        if not data["name"]:
            W.error(self, "Product Name is required.")
            return False
        if not data["description"]:
            W.error(self, "Description is required.")
            return False
        if not data["p_type"]:
            W.error(self, "Product Type is required.")
            return False
        if not data["hsn"]:
            W.error(self, "HSN Code is required.")
            return False
        if not data["hsn"].isdigit():
            W.error(self, "HSN Code must be numeric.")
            return False
        return True

    def _add(self):
        dlg = W.FormDialog(self, "Add Product", self._specs(),
                           values={"hsn": "8443", "p_type": "Machine",
                                   "cattype": ""},
                           size=(560, 0))
        if dlg.exec():
            data = dlg.get()
            if not self._validate(data):
                return
            data["p_id"] = db_manager.get_next_product_id()
            data["created"] = date.today()
            try:
                db_manager.insert_product(data)
            except Exception as exc:
                W.error(self, f"Insert failed: {exc}")
                return
            W.info(self, "Product added successfully.")
            self.refresh()

    def _edit(self, r):
        dlg = W.FormDialog(self, f"Edit Product #{r['p_id']}", self._specs(),
                           values=r, size=(560, 0))
        if dlg.exec():
            data = dlg.get()
            if not self._validate(data):
                return
            try:
                db_manager.update_product(r["p_id"], data)
            except Exception as exc:
                W.error(self, f"Update failed: {exc}")
                return
            W.info(self, "Product updated successfully.")
            self.refresh()

    def _info(self, r):
        self.main.open_info("product", r["p_id"])

    def _delete(self, r):
        if W.confirm(self, f"Delete product '{r['name']}'?"):
            db_manager.delete_product(r["p_id"])
            self.refresh()