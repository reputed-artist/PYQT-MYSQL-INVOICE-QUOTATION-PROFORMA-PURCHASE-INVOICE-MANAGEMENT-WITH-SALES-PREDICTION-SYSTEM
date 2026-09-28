"""
Client / Product / Supplier Info pages - port of the CodeIgniter 'Info layout'
views (getclientinfo.php, getproductinfo.php, getsupplierinfo.php) that are
reached from the per-row Info button of Manage Clients / Products / Suppliers
(addview.php -> client/viewclientinfo/<cid>, product/viewproductinfo/<p_id>,
supplier/viewsupplierinfo/<cid>).

Layout mirrors the originals:
  content-header (title + record name + invoice summary)
  details box ('Client / Supplier Information' | 'Technical Information')
     |  summary box ('Turnover as per FY' | 'Yearly Sold Item Count')
  one '... Invoice Details' box per document type with the original columns
  Sr No | Invoice Id | Company Name | Location | Item Name | Amount | Created |
  Actions (View / Edit / Delete) - DataTables paging + totals row.
"""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QScrollArea, QProgressBar)

from database import db_manager
from ui import widgets as W
from ui.icons import icon_button
from utils.helpers import money

INFO_HEADERS = ["Sr No", "Invoice Id", "Company Name", "Location",
                "Item Name", "Amount", "Created", "Actions"]


class InfoPage(QWidget):
    """One record's Info page (client, product or supplier)."""

    KIND_TITLE = {"client": "Client Details", "product": "Product Details",
                  "supplier": "Supplier Details"}
    LIST_KEY = {"client": "clients", "supplier": "suppliers",
                "product": "products"}
    # active breadcrumb item exactly as written in the original views
    # (getclientinfo.php / getproductinfo.php / getsupplierinfo.php)
    KIND_CRUMB = {"client": "Client Details", "product": "Product Details",
                  "supplier": "Suppliers Details"}

    def __init__(self, main, kind, info_id):
        super().__init__()
        self.main = main
        self.kind = kind
        self.info_id = info_id
        self.title = self.KIND_TITLE[kind]
        self.data = None
        self._docs = []          # [doc, table, paginator, rows, totals label]
        self._build()
        self.refresh()

    # ------------------------------------------------------------------- UI
    def _build(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(
            "QScrollArea { border: none; background: transparent; }")
        inner = QWidget()
        v = QVBoxLayout(inner)
        v.setContentsMargins(0, 0, 0, 0)

        bar = QHBoxLayout()
        back = QPushButton("  Back to list")
        back.setObjectName("btnDefault")
        back.clicked.connect(
            lambda: self.main.navigate(self.LIST_KEY[self.kind]))
        bar.addWidget(back)
        bar.addStretch()
        v.addLayout(bar)

        v.addWidget(W.PageHeader(self.title,
                                 breadcrumb=self.KIND_CRUMB[self.kind]))
        self.sub_label = QLabel("")
        self.sub_label.setObjectName("PageSubtitle")
        v.addWidget(self.sub_label)

        top = QHBoxLayout()
        details_title = {"client": "Client Information",
                         "supplier": "Supplier Information",
                         "product": "Technical Information"}[self.kind]
        self.details_box = W.Box(details_title, "info")
        self.details_body = QVBoxLayout()
        self.details_box.addLayout(self.details_body)
        top.addWidget(self.details_box, 1)

        summary_title = ("Yearly Sold Item Count" if self.kind == "product"
                         else "Turnover as per FY")
        self.summary_box = W.Box(summary_title, "info")
        self.summary_body = QVBoxLayout()
        self.summary_box.addLayout(self.summary_body)
        top.addWidget(self.summary_box, 1)
        v.addLayout(top)

        for doc, box_title in db_manager.INFO_DOCS[self.kind]:
            box = W.Box(box_title, "info")
            table = W.DataTable(list(INFO_HEADERS))
            box.add(table, 1)
            page = W.Paginator(on_change=(lambda d=doc: self._render_doc(d)))
            box.add(page, 0)
            totals = QLabel("")
            totals.setStyleSheet("font-weight: 600; color: #444;")
            box.add(totals)
            v.addWidget(box)
            self._docs.append([doc, table, page, [], totals])

        v.addStretch()
        scroll.setWidget(inner)
        outer.addWidget(scroll)

    # ----------------------------------------------------------------- data
    def refresh(self):
        loader = {"client": db_manager.client_info,
                  "supplier": db_manager.supplier_info,
                  "product": db_manager.product_info}[self.kind]
        try:
            self.data = loader(self.info_id)
        except Exception as exc:
            W.error(self, f"Database error: {exc}")
            return

        self._fill_details()
        self._fill_summary()
        for entry in self._docs:
            doc = entry[0]
            entry[3] = (self.data or {}).get("invoices", {}).get(doc, [])
            self._render_doc(doc)

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
            text = value if value not in (None, "") else "-"
            lbl = QLabel(f"<strong>{label}: </strong> {text}")
            lbl.setWordWrap(True)
            self.details_body.addWidget(lbl)

    @staticmethod
    def _clear_layout(layout):
        """Empty a layout, deleting the widgets it owns."""
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)
            elif item.layout() is not None:
                InfoPage._clear_layout(item.layout())

    def _fill_summary(self):
        """'Turnover as per FY' / 'Yearly Sold Item Count' box."""
        self._clear_layout(self.summary_body)
        rows = ((self.data or {}).get("yearly", []) if self.kind == "product"
                else (self.data or {}).get("fy", []))
        if not rows:
            self.summary_body.addWidget(QLabel("No data available."))
            return
        if self.kind == "product":
            values = [float(r["quantity"] or 0) for r in rows]
        else:
            values = [float(r["amount"] or 0) for r in rows]
        top = max(values) or 1.0

        for r, value in zip(rows, values):
            line = QHBoxLayout()
            fy = QLabel(str(r["fy"]))
            fy.setStyleSheet("color: #555; font-size: 12.5px;")
            line.addWidget(fy)
            line.addStretch()
            amount = QLabel(f"{value:g} sold" if self.kind == "product"
                            else money(value))
            amount.setStyleSheet(
                "color: #3c8dbc; font-size: 12.5px; font-weight: 600;")
            line.addWidget(amount)
            self.summary_body.addLayout(line)

            bar = QProgressBar()
            bar.setFixedHeight(12)
            bar.setTextVisible(False)
            bar.setRange(0, 100)
            bar.setValue(int(value / top * 100))
            bar.setStyleSheet(
                "QProgressBar { background: #f0f0f0; border: none;"
                " border-radius: 6px; }"
                "QProgressBar::chunk { background: #00c0ef;"
                " border-radius: 6px; }")
            self.summary_body.addWidget(bar)

    # ------------------------------------------------------ invoice tables
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
                for maker, obj, cb in (
                        (lambda: QPushButton("View"), "btnInfo", self._view),
                        (lambda: icon_button("edit", "btnDanger", "Edit"),
                         None, self._edit),
                        (lambda: icon_button("delete", "btnWarning", "Delete"),
                         None, self._delete)):
                    b = maker()
                    if obj is not None:
                        b.setObjectName(obj)
                        b.setFixedHeight(24)
                    b.clicked.connect(
                        lambda _, rec=r, f=cb, d=doc: f(d, rec))
                    h.addWidget(b)
                h.addStretch()
                table.setCellWidget(row, 7, cell)

            # totals of the visible page + overall totals in the footer
            table.apply_totals_row([None, None, None, None, None,
                                    money(page_total), "", ""])
            overall = sum(float(x["totalamount"] or 0) for x in rows)
            totals_label.setText(
                f"{len(rows)} records  |  Total: {money(overall)}")

    # ------------------------------------------------------------- actions
    def _view(self, doc, r):
        try:
            master, items = db_manager.get_invoice(doc, r["orderid"])
        except Exception as exc:
            W.error(self, f"Load failed: {exc}")
            return
        reg = db_manager.DOC_REGISTRY[doc]
        dlg = QWidget()
        dlg.setWindowTitle(f"{reg['label']} {r['invid']}")
        W.apply(dlg)                       # brand mark on the title bar
        v = QVBoxLayout(dlg)
        v.addWidget(QLabel(f"<b>{r['invid']}</b><br/>Client: "
                           f"{master.get('c_name')}<br/>Date: "
                           f"{master[reg['date_col']]}"))
        t = W.DataTable(["#", "Item", "Description", "HSN", "Qty", "Price",
                         "Total"], stretch_all=True)
        for i, it in enumerate(items, 1):
            # .get() on every column: a document whose items table has no
            # hsn / item_desc column (the `quote` table) must not crash the
            # info-page view.
            t.add_row([i, it.get("item_name") or "",
                       it.get("item_desc") or "",
                       it.get("hsn") or "",
                       it.get("quantity") or 0,
                       money(it.get("price")),
                       money(it.get("total"))])
        v.addWidget(t)
        v.addWidget(QLabel(f"<b>Subtotal:</b> {money(master['subtotal'])}"
                           f" &nbsp; <b>GST:</b> {money(master['taxamount'])}"
                           f" &nbsp; <b>Total:</b>"
                           f" {money(master['totalamount'])}"))
        dlg.resize(700, 500)
        dlg.show()
        self._windows = getattr(self, "_windows", []) + [dlg]

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
