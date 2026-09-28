"""
Reports page - generic port of the report views (sitem_report, shsn_report,
sale_report, pitem_report, phsn_report, purchase_report, quoteitem_report,
quote_report, quickquote_report): date-range filter, item search,
DataTables-style table with bold totals row and CSV export.
"""
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton

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
        btn_exp = QPushButton("Export CSV")
        btn_exp.setObjectName("btnDefault")
        btn_exp.clicked.connect(self._export)
        bar.addWidget(btn_exp)
        box.addLayout(bar)

        self.headers, self.columns, self.total_cols = self._spec()
        self.table = W.DataTable(self.headers)
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
        # footer: overall totals across all filtered rows
        ov = {c: sum(float(r.get(self.columns[c]) or 0) for r in rows)
              for c in self.total_cols}
        parts = ", ".join(f"{self.headers[c + 1]}: {money(ov[c])}"
                          for c in self.total_cols)
        self.totals_label.setText(f"{len(rows)} records  |  {parts}")

    def _export(self):
        rows = getattr(self, "_rows", [])
        data = []
        for r in rows:
            data.append([r.get(c, "") for c in self.columns])
        W.export_csv(self, self.headers, data,
                     default_name=f"{self.title.lower().replace(' ', '_')}.csv")
