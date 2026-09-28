"""
Accounts pages - port of Account.php controller (manageaccounts / demo):
account list with client + type + opening balance, add/delete accounts,
account type management, and a client ledger view (getledger.php port).

Layout mirrors the DataTables chrome used on Manage-Clients / Manage-Suppliers
and includes the red DataTables "Buttons" export strip below the search bar.
"""
import csv
import json
import os
from datetime import date

from PyQt6.QtCore import Qt
from PyQt6.QtGui import (QTextDocument, QPageSize, QPageLayout,
                         QImage, QPainter, QColor)
from PyQt6.QtPrintSupport import QPrinter, QPrintPreviewDialog
from PyQt6.QtCore import QMarginsF
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QHeaderView, QComboBox, QLabel, QLineEdit,
                             QFrame, QFileDialog, QApplication)

from database import db_manager
from ui.app_icon import apply
from ui import widgets as W
from ui.icons import icon_button
from utils.helpers import money


# =========================================================================== #
# DataTables chrome helpers
# =========================================================================== #
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


class ColumnToggleStrip(QWidget):
    def __init__(self, parent, headers, table):
        super().__init__(parent)
        self._table = table
        h = QHBoxLayout(self)
        h.setContentsMargins(0, 8, 0, 0)
        h.setSpacing(4)
        h.addStretch()

        for i, label in enumerate(headers):
            b = QPushButton(label)
            b.setFixedHeight(26)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setStyleSheet(
                "QPushButton { background:#222222; color:#ffffff;"
                " border:1px solid #000000; border-radius:3px;"
                " padding:2px 10px; font-size:11.5px; }"
                "QPushButton:hover { background:#3a3a3a; }"
                "QPushButton:checked { background:#000000;"
                " border-color:#000000; color:#ffffff; }"
                "QPushButton:!checked { background:#888888;"
                " border-color:#555555; }")
            b.setCheckable(True)
            b.setChecked(True)
            b.toggled.connect(
                lambda on, col=i: table.setColumnHidden(col, not on))
            h.addWidget(b)


# =========================================================================== #
# Centered red export strip  (DataTables "Buttons" style)
# =========================================================================== #
class ExportButtonStrip(QWidget):
    """Centered red strip: [Copy][JSON][Excel][CSV][PDF][Print]
                           [TXT][SQL][Docx][PNG]
    Emits on_export(kind)."""
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


# =========================================================================== #
# Paging state + width helper + card
# =========================================================================== #
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


def _apply_column_widths(table, stretch_cols, fixed_cols):
    header = table.horizontalHeader()
    header.setStretchLastSection(False)
    header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
    for col, width in fixed_cols.items():
        header.setSectionResizeMode(col, QHeaderView.ResizeMode.Fixed)
        table.setColumnWidth(col, width)
    for col in stretch_cols:
        header.setSectionResizeMode(col, QHeaderView.ResizeMode.Stretch)


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
        apply(dlg)
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

    # ------------------------------------------------------------------ csv
    if kind in ("csv", "excel"):
        with open(fname, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(headers)
            for r in rows:
                w.writerow([r.get(k, "") for k in keys])
        W.info(parent, f"Saved to {fname}")

    # ------------------------------------------------------------------ txt
    elif kind == "txt":
        lines = ["\t".join(headers)]
        for r in rows:
            lines.append("\t".join(str(r.get(k, "")) for k in keys))
        with open(fname, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        W.info(parent, f"Saved to {fname}")

    # ----------------------------------------------------------------- json
    elif kind == "json":
        data = [{k: r.get(k, "") for k in keys} for r in rows]
        with open(fname, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)
        W.info(parent, f"Saved to {fname}")

    # ------------------------------------------------------------------ sql
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

    # ----------------------------------------------------------------- docx
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

    # ------------------------------------------------------------------ pdf
    elif kind == "pdf":
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

    # ------------------------------------------------------------------ png
    elif kind == "png":
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
# Accounts page
# =========================================================================== #
class AccountsPage(QWidget):
    title = "Accounts"

    HEADERS = ["Sr No", "Client", "Mobile", "GST", "Account Type",
               "Opening Bal", "Closing Bal", "Created", "Actions"]

    FIXED_WIDTHS = {
        0: 60,     # Sr No
        2: 130,    # Mobile
        3: 130,    # GST
        4: 130,    # Account Type
        5: 120,    # Opening Bal
        6: 120,    # Closing Bal
        7: 100,    # Created
        8: 80,     # Actions
    }
    STRETCH_COLS = [1]   # Client name

    def __init__(self, main):
        super().__init__()

        self.main = main
        self.clients = db_manager.list_clients()
        self.acc_types = db_manager.get_account_types()
        self._state = _TableState()

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)

        lay.addWidget(W.PageHeader("Accounts", breadcrumb="Manage-Accounts"))

        card, body = _make_card(self)

        # ---- header row ----
        header_row = QHBoxLayout()
        title_lbl = QLabel("All Account Details")
        title_lbl.setStyleSheet(
            "font-size: 15px; font-weight: 600; color: #444;"
            " background: transparent; border: none;")
        header_row.addWidget(title_lbl)
        header_row.addStretch()

        btn_add = QPushButton("+ Add Account")
        btn_add.setObjectName("btnSuccess")
        btn_add.setFixedHeight(30)
        btn_add.clicked.connect(self._add)
        header_row.addWidget(btn_add)
        body.addLayout(header_row)

        # ---- DataTables top bar ----
        self.top = DTTopBar(
            self, on_search=self.refresh, on_page_size=self._set_page_size,
            search_placeholder="Search client / name / address / mobile / GST...")
        body.addWidget(self.top)

        # ---- export buttons (centered, red, DataTables style) ----
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

        # ---- column toggles ----
        self.col_toggles = ColumnToggleStrip(self, self.HEADERS, self.table)
        body.addWidget(self.col_toggles)

        lay.addWidget(card, 1)

        self._rows = []
        self._closing = {}
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
            self._rows = db_manager.list_accounts(
                self.top.search.text().strip())
            self._closing = db_manager.list_account_closing_balances()
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
                [
                    start + i + 1,
                    r["c_name"],
                    r["mob"],
                    r["gst"],
                    r["acc_type_name"] or r["acc_type"],
                    money(r["opening_bal"]),
                    money(self._closing.get(r["aid"],
                                            r["opening_bal"] or 0)),
                    str(r["created"]),
                    ""   # Actions cell (widget)
                ],
                data=r["aid"])

            # Actions
            cell = QWidget()
            h = QHBoxLayout(cell)
            h.setContentsMargins(0, 0, 0, 0)
            h.setSpacing(4)

            lb = icon_button("view", "btnInfo", "View Ledger")
            lb.clicked.connect(lambda _, rec=r: self._ledger(rec))

            db = icon_button("delete", "btnWarning", "Delete")
            db.clicked.connect(lambda _, rec=r: self._delete(rec))

            h.addWidget(lb)
            h.addWidget(db)
            h.addStretch()
            self.table.setCellWidget(row, 8, cell)

        self.footer.update_state(
            self._state.current, total_pages,
            self._state.per_page or len(rows) or 1, len(rows))

    # ------------------------------------------------------------ add
    def _add(self):
        client_opts = [(c["cid"], f"{c['c_name']} (#{c['cid']})")
                       for c in self.clients]
        type_opts = [(t["id"], t["type"]) for t in self.acc_types]

        dlg = W.FormDialog(
            self, "Add Account",
            [
                ("Client *", "cid", "combo", client_opts),
                ("Account Type", "acc_type", "combo", type_opts),
                ("Opening Balance", "opening_bal", "number", None),
            ])

        if dlg.exec():
            data = dlg.get()
            try:
                data["aid"] = db_manager.get_next_account_id()
                data["opening_bal"] = float(data["opening_bal"] or 0)
                data["created"] = date.today()
                db_manager.insert_account(data)
            except Exception as exc:
                W.error(self, f"Insert failed: {exc}")
                return
            W.info(self, "Account added successfully.")
            self.refresh()

    # ------------------------------------------------------------ delete
    def _delete(self, r):
        if W.confirm(self, f"Delete account #{r['aid']}?"):
            db_manager.delete_account(r["aid"])
            self.refresh()

    # ------------------------------------------------------------ ledger
        # ------------------------------------------------------------ ledger
    def _ledger(self, r):
        """Open the full-page ledger for this client (mirrors getledger.php)."""
        cid = r["cid"]
        key = f"ledger_{cid}"
        if key not in self.main._pages:
            from ui.pages.ledger_page import LedgerPage
            page = LedgerPage(self.main, cid)
            self.main._pages[key] = page
            self.main.stack.addWidget(page)
        page = self.main._pages[key]
        self.main.stack.setCurrentWidget(page)
        self.main.setWindowTitle(f"Ledger - {r['c_name']} - Sales Aura")
        # mark nothing active in the sidebar
        for btn, label, k in self.main._nav_items:
            btn.setProperty("active", "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        # trigger a refresh so the FY list and totals load
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(0, page.refresh)

    def _print_ledger(self):
        from utils.invoice_print import show_ledger_print_preview
        if not getattr(self, "_dlg_data", None):
            W.info(self, "No ledger data to print.")
            return
        show_ledger_print_preview(
            self, self._dlg_client_name, self._dlg_fy, self._dlg_data)

    def _on_fy_changed(self, fy):
        if hasattr(self, "_dlg_cid"):
            self._dlg_fy = fy
            self._render_ledger()

    def _render_ledger(self):
        try:
            data = db_manager.get_ledger_fy(self._dlg_cid, self._dlg_fy)
        except Exception as exc:
            W.error(self, f"Ledger error: {exc}")
            return

        self._dlg_data = data

        fy_text = (f"FY: {data['start_year']} - {data['end_year']}  "
                   f"({data['start_year']}-04-01 to "
                   f"{data['end_year']}-03-31)")
        self._dlg_fy_lbl.setText(
            f"<b>{self._dlg_client_name}</b> &nbsp;|&nbsp; {fy_text}")

        if self._fy_combo.currentText() != data["fy"]:
            self._fy_combo.blockSignals(True)
            self._fy_combo.setCurrentText(data["fy"])
            self._fy_combo.blockSignals(False)

        t = self._ledger_table
        t.clear_rows()

        for row in data["rows"]:
            vtype = row.get("voucher_type", "")

            if vtype == "Opening":
                t.add_row([str(row["date"]), row["ref"], row["voucher_type"],
                           "", "", money(row["opening_bal"])])

            elif vtype == "Total":
                t.apply_totals_row(
                    [None, "TOTAL", "",
                     money(row["debit"]), money(row["credit"]), ""],
                    label="")
                t.add_row(["", "CLOSING BALANCE", "", "", "",
                           money(row["closing_bal"])])

            else:
                debit = money(row["debit"]) if row["debit"] else "-"
                credit = money(row["credit"]) if row["credit"] else "-"
                t.add_row([str(row["date"]), row["ref"], row["voucher_type"],
                           debit, credit, money(row["closing_bal"])])

    # ------------------------------------------------------------ export
    def _on_export(self, kind):
        # Build a list of dicts combining account + closing balance so the
        # export contains everything the table shows.
        rows = []
        for r in self._rows:
            rows.append({
                "c_name": r.get("c_name", ""),
                "mob": r.get("mob", ""),
                "gst": r.get("gst", ""),
                "acc_type_name": (r.get("acc_type_name")
                                  or r.get("acc_type", "")),
                "opening_bal": r.get("opening_bal", 0),
                "closing_bal": self._closing.get(
                    r.get("aid"), r.get("opening_bal") or 0),
                "created": str(r.get("created", "")),
            })

        columns = [
            ("c_name", "Client"),
            ("mob", "Mobile"),
            ("gst", "GST"),
            ("acc_type_name", "Account Type"),
            ("opening_bal", "Opening Balance"),
            ("closing_bal", "Closing Balance"),
            ("created", "Created"),
        ]
        _generic_export(
            self, kind, rows, columns,
            filename_stub="accounts",
            sql_table="accounts",
            sql_cols=["cid", "acc_type", "opening_bal", "created"])


# =========================================================================== #
# Account Types page
# =========================================================================== #
class AccountTypesPage(QWidget):
    title = "Add/View Account Type"

    HEADERS = ["Sr No", "Type", "Actions"]
    FIXED_WIDTHS = {0: 60, 2: 80}
    STRETCH_COLS = [1]

    def __init__(self, main):
        super().__init__()
        self.main = main
        self._state = _TableState()

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)

        lay.addWidget(W.PageHeader("Add/View Account Type",
                                   breadcrumb="Manage-Accounts"))

        card, body = _make_card(self)

        header_row = QHBoxLayout()
        title_lbl = QLabel("All Account Types")
        title_lbl.setStyleSheet(
            "font-size: 15px; font-weight: 600; color: #444;"
            " background: transparent; border: none;")
        header_row.addWidget(title_lbl)
        header_row.addStretch()

        btn_add = QPushButton("+ Add Type")
        btn_add.setObjectName("btnSuccess")
        btn_add.setFixedHeight(30)
        btn_add.clicked.connect(self._add)
        header_row.addWidget(btn_add)
        body.addLayout(header_row)

        # ---- export buttons (centered, red, DataTables style) ----
        self.export_strip = ExportButtonStrip(
            self, on_export=self._on_export)
        body.addWidget(self.export_strip)

        self.table = W.DataTable(self.HEADERS)
        _apply_column_widths(self.table, self.STRETCH_COLS, self.FIXED_WIDTHS)
        body.addWidget(self.table, 1)

        self.col_toggles = ColumnToggleStrip(self, self.HEADERS, self.table)
        body.addWidget(self.col_toggles)

        lay.addWidget(card, 1)

        self.refresh()

    # ------------------------------------------------------------ data
    def refresh(self):
        try:
            rows = db_manager.get_account_types()
        except Exception as exc:
            W.error(self, f"Database error: {exc}")
            return

        self.table.clear_rows()
        for i, r in enumerate(rows, 1):
            row = self.table.add_row([i, r["type"], ""], data=r.get("id"))
            cell = QWidget()
            h = QHBoxLayout(cell)
            h.setContentsMargins(0, 0, 0, 0)
            h.setSpacing(4)
            db = icon_button("delete", "btnWarning", "Delete")
            db.clicked.connect(
                lambda _, rec=r: self._delete(rec))
            h.addWidget(db)
            h.addStretch()
            self.table.setCellWidget(row, 2, cell)

    def _add(self):
        dlg = W.FormDialog(
            self, "Add Account Type",
            [("Type *", "type", "text", None)])
        if dlg.exec():
            data = dlg.get()
            if not data["type"].strip():
                W.error(self, "Type name is required.")
                return
            try:
                db_manager.insert_account_type(data)
            except Exception as exc:
                W.error(self, f"Insert failed: {exc}")
                return
            W.info(self, "Account type added.")
            self.refresh()

    def _delete(self, r):
        if W.confirm(self, f"Delete account type '{r['type']}'?"):
            try:
                db_manager.delete_account_type(r["id"])
            except Exception as exc:
                W.error(self, f"Delete failed: {exc}")
                return
            self.refresh()

    # ------------------------------------------------------------ export
    def _on_export(self, kind):
        try:
            db_rows = db_manager.get_account_types()
        except Exception:
            db_rows = []

        rows = [{"type": r.get("type", "")} for r in db_rows]
        columns = [("type", "Type")]
        _generic_export(
            self, kind, rows, columns,
            filename_stub="account_types",
            sql_table="account_types",
            sql_cols=["type"])