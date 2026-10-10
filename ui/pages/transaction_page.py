"""
Transaction page - port of Transaction.php controller
(manage-transaction.php): payments list (paidhistory) with date range
filter, add / edit / delete payment records, totals.
"""
from datetime import date, datetime

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, \
    QLabel

from database import db_manager
from ui import widgets as W
from ui.icons import icon_button
from utils.helpers import money
from ui.pages.master_pages import ExportButtonStrip, ColumnToggleStrip, \
    _generic_export
from ui.pages.reports_page import _apply_column_layout, _ViewportRelayout

# Column keys behind HEADERS[1:] - index 0 ('Sr No') is display-only.  Used by
# the shared width logic in reports_page to size each column from its content.
COLUMN_KEYS = ["c_name", "client_type", "amount", "bank", "dateofpayment",
               "purpose"]


def _to_date(v):
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    return date.today()


class TransactionPage(QWidget):
    title = "Transaction"

    def __init__(self, main):
        super().__init__()
        self.main = main
        self.clients = db_manager.list_clients()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(W.PageHeader("Transaction",
                                   "Manage payment transactions",
                                   breadcrumb="Transaction Report"))
        box = W.Box("Transactions - Data", "danger")

        # ---- row 1: "+ Add Transaction" pinned to the RIGHT corner ----
        add_row = QHBoxLayout()
        add_row.addStretch()
        btn_add = QPushButton("+ Add Transaction")
        btn_add.setObjectName("btnSuccess")
        btn_add.setFixedHeight(30)
        btn_add.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_add.clicked.connect(self._add)
        add_row.addWidget(btn_add)
        box.addLayout(add_row)

        # ---- row 2: date range on the left, search box shifted RIGHT ----
        bar = QHBoxLayout()
        bar.setSpacing(8)
        self.dates = W.DateRangeBar(on_change=self.refresh)
        bar.addWidget(self.dates)
        bar.addStretch()
        self.search = W.SearchBox(
            "Search client / bank / address / mobile / purpose...",
            on_change=self.refresh)
        self.search.setMinimumWidth(320)
        bar.addWidget(self.search, 0, Qt.AlignmentFlag.AlignVCenter)
        box.addLayout(bar)

        # ---- export buttons (centered strip, same as the master pages) ----
        self.export_strip = ExportButtonStrip(
            self, on_export=self._on_export)
        box.add(self.export_strip, 0)

        self.HEADERS = ["Sr No", "Client", "Type",
                        "Amount", "Bank", "Payment Date", "Purpose",
                        "Actions"]
        self.table = W.DataTable(self.HEADERS)
        # size each column from its content, and re-divide the width whenever
        # the table viewport is resized (same rule the report pages use)
        self._relayout_watch = _ViewportRelayout(
            self.table, self._relayout_columns)
        box.add(self.table, 1)
        self.paginator = W.Paginator(on_change=self._render)
        box.add(self.paginator, 0)

        # ---- column toggles (bottom-left, blue - same as the master pages) ----
        self.col_toggles = ColumnToggleStrip(self, self.HEADERS, self.table)
        box.add(self.col_toggles, 0)

        self.totals_label = QLabel("")
        self.totals_label.setStyleSheet("font-weight: 600; color: #444;")
        box.add(self.totals_label)
        lay.addWidget(box, 1)
        self._rows = []
        self.refresh()

    def refresh(self):
        start, end = self.dates.dates()
        try:
            self._rows = db_manager.list_transactions(
                start, end, self.search.edit.text().strip())
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
        total = 0.0
        for i, r in enumerate(page_rows):
            row = self.table.add_row(
                [start + i + 1, r["c_name"] or r["cid"],
                 "Supplier" if r.get("u_type") == 1 else "Customer",
                 money(r["amount"]), r["bank"], str(r["dateofpayment"]),
                 r["purpose"]], data=r["pay_id"])
            total += float(r["amount"] or 0)
            cell = QWidget()
            h = QHBoxLayout(cell)
            h.setContentsMargins(2, 2, 2, 2)
            h.setSpacing(4)
            eb = icon_button("edit", "btnDanger", "Edit")
            eb.clicked.connect(lambda _, rec=r: self._edit(rec))
            db = icon_button("delete", "btnWarning", "Delete")
            db.clicked.connect(lambda _, rec=r: self._delete(rec))
            h.addWidget(eb)
            h.addWidget(db)
            h.addStretch()
            self.table.setCellWidget(row, 7, cell)
        self.table.apply_totals_row([None, None, None, money(total),
                                     None, None, None, ""])
        # width the columns against the data that is actually displayed
        self._relayout_columns()
        overall = sum(float(r["amount"] or 0) for r in rows)
        self.totals_label.setText(f"{len(rows)} records  |  "
                                  f"Total Amount: {money(overall)}")

    def _display_samples(self):
        """The text each cell shows, in COLUMN_KEYS order.

        Mirrors the cell values built in `_render()` exactly - measuring the
        raw row instead would size columns to `12.0` rather than the
        `₹ 12.00` that is actually on screen.
        """
        out = []
        for r in self._rows:
            out.append([
                str(r["c_name"] or r["cid"]),
                "Supplier" if r.get("u_type") == 1 else "Customer",
                money(r["amount"]),
                str(r["bank"] or ""),
                str(r["dateofpayment"] or ""),
                str(r["purpose"] or ""),
            ])
        return out

    def _relayout_columns(self):
        """Re-measure the columns against the current data + viewport width.

        Called after every render and on every table resize, so the width is
        divided up by content need and follows the window size.
        """
        if not hasattr(self, "table") or self.table.viewport().width() <= 0:
            return          # not laid out yet - the viewport watcher catches up
        _apply_column_layout(self.table, self.HEADERS, COLUMN_KEYS,
                             self._rows, display=self._display_samples())

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._relayout_columns()

    def _bank_names(self):
        """Fresh bank names from bankdetails (Settings > Bank Details).

        Loaded on every Add/Edit open — __init__ runs only once because the
        page is cached, so a cached list would never show newly added banks.
        """
        try:
            names = [b["bname"] for b in db_manager.get_banks()
                     if (b.get("bname") or "").strip()]
        except Exception:
            names = []
        return names or ["Cash", "Bank Transfer"]

    def _specs(self):
        client_opts = [(c["cid"], f"{c['c_name']} (#{c['cid']})")
                       for c in self.clients]
        bank_opts = [(b, b) for b in self._bank_names()]
        return [
            ("Client *", "cid", "combo", client_opts),
            ("Amount *", "amount", "number", None),
            ("Bank", "bank", "combo", bank_opts),
            ("Date of Payment", "dateofpayment", "date", None),
            ("Purpose", "purpose", "text", None),
        ]

    def _add(self):
        dlg = W.FormDialog(self, "Add Transaction", self._specs(),
                           values={"dateofpayment": date.today()})
        if dlg.exec():
            data = dlg.get()
            try:
                amount = int(float(data["amount"] or 0))
            except ValueError:
                W.error(self, "Invalid amount.")
                return
            try:
                db_manager.insert_transaction({
                    "pay_id": db_manager.next_transaction_id(),
                    "cid": data["cid"], "amount": amount,
                    "bank": data["bank"] or "",
                    "dateofpayment": data["dateofpayment"],
                    "purpose": data["purpose"],
                    "created": datetime.now()})
            except Exception as exc:
                W.error(self, f"Insert failed: {exc}")
                return
            W.success(self, "Transaction added successfully.")
            self.refresh()

    def _edit(self, r):
        dlg = W.FormDialog(self, f"Edit Transaction {r['pay_id']}",
                           self._specs(),
                           values={"cid": int(r["cid"]),
                                   "amount": r["amount"],
                                   "bank": r["bank"],
                                   "dateofpayment":
                                       _to_date(r["dateofpayment"]),
                                   "purpose": r["purpose"]})
        if dlg.exec():
            data = dlg.get()
            try:
                amount = int(float(data["amount"] or 0))
            except ValueError:
                W.error(self, "Invalid amount.")
                return
            try:
                db_manager.update_transaction(r["pay_id"], {
                    "cid": data["cid"], "amount": amount,
                    "bank": data["bank"] or "",
                    "dateofpayment": data["dateofpayment"],
                    "purpose": data["purpose"]})
            except Exception as exc:
                W.error(self, f"Update failed: {exc}")
                return
            W.info(self, "Transaction updated successfully.")
            self.refresh()

    def _delete(self, r):
        if W.confirm(self, f"Delete transaction {r['pay_id']}?"):
            db_manager.delete_transaction(r["pay_id"])
            self.refresh()

    def _on_export(self, kind):
        """Multi-format export of the currently filtered transactions."""
        columns = [
            ("c_name", "Client"),
            ("client_type", "Type"),
            ("amount", "Amount"),
            ("bank", "Bank"),
            ("dateofpayment", "Payment Date"),
            ("purpose", "Purpose"),
        ]

        # `client_type` is derived for display only - the raw rows carry
        # `u_type`, which the _render() table also maps to a label.
        rows = []
        for r in getattr(self, "_rows", []):
            row = dict(r)
            row["client_type"] = ("Supplier" if r.get("u_type") == 1
                                  else "Customer")
            rows.append(row)

        _generic_export(
            self, kind, rows, columns,
            filename_stub="transactions",
            sql_table="paidhistory",
            sql_cols=["cid", "amount", "bank", "dateofpayment", "purpose"])

