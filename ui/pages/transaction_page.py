"""
Transaction page - port of Transaction.php controller
(manage-transaction.php): payments list (paidhistory) with date range
filter, add / edit / delete payment records, totals.
"""
from datetime import date, datetime

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, \
    QLabel

from database import db_manager
from ui import widgets as W
from ui.icons import icon_button
from utils.helpers import money


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
        self.banks = [b["bname"] for b in db_manager.get_banks()] or \
            ["Cash", "Bank Transfer"]
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(W.PageHeader("Transaction",
                                   "Manage payment transactions",
                                   breadcrumb="Transaction Report"))
        box = W.Box("Transactions - Data", "danger")

        bar = QHBoxLayout()
        self.dates = W.DateRangeBar(on_change=self.refresh)
        bar.addWidget(self.dates)
        self.search = W.SearchBox("Search client / bank / address / mobile / purpose...",
                                  on_change=self.refresh)
        bar.addWidget(self.search)
        bar.addStretch()
        btn_add = QPushButton("+ Add Transaction")
        btn_add.setObjectName("btnSuccess")
        btn_add.clicked.connect(self._add)
        bar.addWidget(btn_add)
        btn_exp = QPushButton("Export CSV")
        btn_exp.setObjectName("btnDefault")
        btn_exp.clicked.connect(self._export)
        bar.addWidget(btn_exp)
        box.addLayout(bar)

        self.table = W.DataTable(["Sr No", "Client", "Type",
                                  "Amount", "Bank", "Payment Date", "Purpose",
                                  "Actions"])
        box.add(self.table, 1)
        self.paginator = W.Paginator(on_change=self._render)
        box.add(self.paginator, 0)
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
        overall = sum(float(r["amount"] or 0) for r in rows)
        self.totals_label.setText(f"{len(rows)} records  |  "
                                  f"Total Amount: {money(overall)}")

    def _specs(self):
        client_opts = [(c["cid"], f"{c['c_name']} (#{c['cid']})")
                       for c in self.clients]
        bank_opts = [(b, b) for b in self.banks]
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

    def _export(self):
        W.export_csv(self,
                     ["Client", "Amount", "Bank", "Date", "Purpose"],
                     [[r["c_name"] or r["cid"], r["amount"],
                       r["bank"], str(r["dateofpayment"]), r["purpose"]]
                      for r in getattr(self, "_rows", [])],
                     default_name="transactions.csv")

