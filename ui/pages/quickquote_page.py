"""
Quick Quotation page - PyQt6 port of C4/app/views/layout/genquickquotation.php.

UI: product image cards in a responsive grid (4 per row).
Clicking a card opens a modal (Mobile, Qty, Price, auto Sub-Total / GST / Total).
Submit -> insert record -> print preview.

Images are resolved from <app_base>/dist/img/<imagename>.
"""
import os
import traceback
from datetime import date

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QLineEdit, QDialog, QGridLayout,
                             QScrollArea, QFrame, QMessageBox,
                             QFormLayout, QDialogButtonBox)

from database import db_manager
from ui.app_icon import apply
from ui import widgets as W
from utils import invoice_print
from utils.helpers import money


# --------------------------------------------------------------------------- #
# App base folder  (…/pyqt_app/)
# --------------------------------------------------------------------------- #
def _app_base_dir() -> str:
    """Return the app's base folder (where dist/ lives)."""
    here = os.path.dirname(os.path.abspath(__file__))
    cur = here
    for _ in range(5):
        if os.path.isdir(os.path.join(cur, "dist")):
            return cur
        parent = os.path.dirname(cur)
        if parent == cur:
            break
        cur = parent
    return os.path.abspath(os.path.join(here, "..", ".."))


APP_BASE = _app_base_dir()
IMG_DIR = os.path.join(APP_BASE, "dist", "img")


def _resolve_image(img_value: str) -> str:
    """Turn whatever the DB stores for `img_loc` into a real filesystem path
    inside <app_base>/dist/img/.
    """
    if not img_value:
        return ""
    v = str(img_value).strip().replace("\\", "/")

    if os.path.isabs(v) and os.path.isfile(v):
        return v

    base = os.path.basename(v)
    candidate = os.path.join(IMG_DIR, base)

    alternates = [
        candidate,
        os.path.join(APP_BASE, v.lstrip("/")),
        os.path.join(IMG_DIR, v.lstrip("/")),
    ]
    for path in alternates:
        if os.path.isfile(path):
            return path
    return candidate


# --------------------------------------------------------------------------- #
# Product card
# --------------------------------------------------------------------------- #
class _ProductCard(QFrame):
    CARD_W = 240
    IMG_H = 180

    def __init__(self, product, on_click):
        super().__init__()
        self.product = product
        self._on_click = on_click

        self.setObjectName("productCard")
        self.setFixedWidth(self.CARD_W)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet("""
            QFrame#productCard {
                background: #ffffff;
                border: 1px solid #d2d6de;
                border-radius: 3px;
            }
            QFrame#productCard:hover {
                border: 1px solid #3c8dbc;
                background: #f4faff;
            }
        """)

        v = QVBoxLayout(self)
        v.setContentsMargins(8, 8, 8, 8)
        v.setSpacing(6)

        img = QLabel()
        img.setAlignment(Qt.AlignmentFlag.AlignCenter)
        img.setFixedHeight(self.IMG_H)
        img.setStyleSheet("background:#f7f9fb; border:1px solid #eee;")

        loc = _resolve_image(product.get("img_loc") or "")
        loaded = False
        if loc and os.path.isfile(loc):
            pm = QPixmap(loc)
            if not pm.isNull():
                img.setPixmap(pm.scaled(
                    self.CARD_W - 20, self.IMG_H,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation))
                loaded = True
        if not loaded:
            img.setText("No image")
            img.setStyleSheet(
                "background:#f7f9fb; border:1px solid #eee; color:#888;")
        v.addWidget(img)

        name = QLabel(product.get("name") or "")
        name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name.setWordWrap(True)
        name.setStyleSheet(
            "font-size: 13.5px; font-weight: 600; color:#222;"
            " background: transparent;")
        v.addWidget(name)

        price = product.get("price")
        if price not in (None, "", 0):
            p = QLabel(f"\u20B9 {money(price)}")
            p.setAlignment(Qt.AlignmentFlag.AlignCenter)
            p.setStyleSheet(
                "color:#3c8dbc; font-weight:600;"
                " background: transparent;")
            v.addWidget(p)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._on_click(self.product)
        super().mousePressEvent(event)


# --------------------------------------------------------------------------- #
# Quick-quote modal
# --------------------------------------------------------------------------- #
class _QuickQuoteDialog(QDialog):
    def __init__(self, parent, product):
        super().__init__(parent)
        self.product = product
        self.result_data = None

        self.setWindowTitle("Quick Quote")
        apply(self)
        self.setModal(True)
        self.setMinimumWidth(520)
        self.setStyleSheet("""
            QDialog { background:#ffffff; }
            QLabel#title { font-size:20px; font-weight:600; color:#222; }
            QLabel#fieldLabel { font-size:14px; color:#333; }
            QLineEdit[readOnly="true"] { background:#f7f9fb; }
        """)

        v = QVBoxLayout(self)
        v.setContentsMargins(20, 18, 20, 18)
        v.setSpacing(14)

        title = QLabel(f"Quick Quote \u2014 {product.get('name') or ''}")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v.addWidget(title)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setFormAlignment(Qt.AlignmentFlag.AlignTop)
        form.setHorizontalSpacing(14)
        form.setVerticalSpacing(10)

        self.mob = QLineEdit()
        self.mob.setPlaceholderText("Mobile")
        form.addRow(self._lbl("Mobile *"), self.mob)

        self.qty = QLineEdit("1")
        form.addRow(self._lbl("Quantity *"), self.qty)

        self.price = QLineEdit()
        self.price.setPlaceholderText("Price")
        form.addRow(self._lbl("Price *"), self.price)

        self.subtotal = QLineEdit("0")
        self.subtotal.setReadOnly(True)
        form.addRow(self._lbl("Sub-Total"), self.subtotal)

        self.gst_rate = QLineEdit("18")
        self.gst_rate.setFixedWidth(60)
        gst_rate_row = QWidget()
        gr = QHBoxLayout(gst_rate_row)
        gr.setContentsMargins(0, 0, 0, 0)
        gr.addWidget(self.gst_rate)
        gr.addWidget(QLabel("%"))
        gr.addStretch()
        form.addRow(self._lbl("GST"), gst_rate_row)

        self.gst_amt = QLineEdit("0")
        self.gst_amt.setReadOnly(True)
        form.addRow(self._lbl("GST Amount"), self.gst_amt)

        self.total = QLineEdit("0")
        self.total.setReadOnly(True)
        form.addRow(self._lbl("Total"), self.total)

        v.addLayout(form)

        for w in (self.qty, self.price, self.gst_rate):
            w.textChanged.connect(self._recalc)

        btns = QDialogButtonBox()
        self.save_btn = QPushButton("Submit")
        self.save_btn.setObjectName("btnSuccess")
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setObjectName("btnDefault")
        btns.addButton(self.save_btn, QDialogButtonBox.ButtonRole.AcceptRole)
        btns.addButton(self.cancel_btn, QDialogButtonBox.ButtonRole.RejectRole)
        btns.accepted.connect(self._on_submit)
        btns.rejected.connect(self.reject)
        v.addWidget(btns)

        QTimer.singleShot(0, self.mob.setFocus)

    @staticmethod
    def _lbl(text):
        l = QLabel(text)
        l.setObjectName("fieldLabel")
        return l

    def _recalc(self):
        try:
            qty = float(self.qty.text() or 0)
            price = float(self.price.text() or 0)
            rate = float(self.gst_rate.text() or 0)
        except ValueError:
            qty = price = rate = 0.0
        sub = qty * price
        gst = sub * rate / 100.0
        self.subtotal.setText(f"{sub:.2f}")
        self.gst_amt.setText(f"{gst:.2f}")
        self.total.setText(f"{sub + gst:.2f}")

    def _on_submit(self):
        mob = self.mob.text().strip()
        if not mob:
            W.warning(self, "Mobile is required.", "Validation")
            return
        try:
            qty = float(self.qty.text() or 0)
            price = float(self.price.text() or 0)
            rate = float(self.gst_rate.text() or 0)
        except ValueError:
            W.warning(self, "Quantity / Price must be numbers.", "Validation")
            return
        if qty <= 0 or price <= 0:
            W.warning(self, "Quantity and Price must be greater than 0.", "Validation")
            return

        sub = int(qty * price)
        gst = int(sub * rate / 100.0)
        self.result_data = {
            "p_id": self.product.get("p_id"),
            "mob": mob,
            "quantity": str(qty),
            "price": str(price),
            "subtotal": sub,
            "gst": gst,
            "total": sub + gst,
            "created": date.today(),
        }
        self.accept()


# --------------------------------------------------------------------------- #
# Main page
# --------------------------------------------------------------------------- #
class QuickQuotePage(QWidget):
    title = "Quick Quotation"

    def __init__(self, main):
        super().__init__()
        self.main = main
        self.products = db_manager.list_products()

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)
        lay.addWidget(W.PageHeader("Quick Quotation",
                                   breadcrumb="Quick Quotation"))

        grid_box = W.Box("Select a Product", "info")

        self._grid_host = QWidget()
        self._grid = QGridLayout(self._grid_host)
        self._grid.setContentsMargins(8, 8, 8, 8)
        self._grid.setHorizontalSpacing(12)
        self._grid.setVerticalSpacing(12)
        self._populate_grid()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self._grid_host)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        grid_box.add(scroll, 1)
        lay.addWidget(grid_box, 1)

    # -------------------------------------------------------------- grid
    def _populate_grid(self):
        while self._grid.count():
            item = self._grid.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        if not self.products:
            self._grid.addWidget(QLabel("No products available."), 0, 0)
            return

        cols = 4
        for i, p in enumerate(self.products):
            card = _ProductCard(p, self._on_product_clicked)
            self._grid.addWidget(card, i // cols, i % cols)
        self._grid.setColumnStretch(cols, 1)
        self._grid.setRowStretch((len(self.products) // cols) + 1, 1)

    # -------------------------------------------------------------- click
    def _on_product_clicked(self, product):
        dlg = _QuickQuoteDialog(self, product)
        if dlg.exec() != QDialog.DialogCode.Accepted or not dlg.result_data:
            return

        payload = dict(dlg.result_data)
        payload["q_id"] = db_manager.next_quickquote_id()

        try:
            db_manager.insert_quickquote(payload)
        except Exception as exc:
            W.error(self, f"Save failed: {exc}")
            return

        # ---------- confirmation: green right-tick box ----------
        W.success(self, f"Quick Quotation {payload['q_id']} generated "
                        f"successfully.")

        # ---------- print preview ----------
        try:
            master, items = self._load_for_print(payload["q_id"])
            print(f"[quickquote] master = {master}")
            print(f"[quickquote] items  = {items}")

            ok = invoice_print.show_quick_quotation_preview(
                self,
                master,
                items,
                cattype=(product.get("cattype")
                         or master.get("c_name")
                         or ""),
                debug=True,
            )
            print(f"[quickquote] preview opened = {ok}")
        except Exception:
            traceback.print_exc()
            W.error(self, "Failed to open the quick quotation preview.\n"
                          "See the terminal for details.")

    # -------------------------------------------------------------- load
    def _load_for_print(self, q_id):
        """Fetch a saved quick quote and normalise to (master, items).

        The quick-quotation HTML builder expects these keys on `master`:
            q_id, name, img_loc, techs, quantity, subtotal, gst, total,
            mob, created, invid (alias for q_id)

        and on each item in `items`:
            item_name, img_loc, techs, hsn, quantity, price, total
        """
        rec = db_manager.get_quickquote(q_id)
        if not rec:
            raise RuntimeError(f"Quick quote {q_id} not found after insert.")

        subtotal = float(rec.get("subtotal") or 0)
        gst = float(rec.get("gst") or 0)
        total = float(rec.get("total") or 0)
        taxrate = (gst / subtotal * 100.0) if subtotal else 18.0

        product_name = (rec.get("product_name")
                        or rec.get("name")
                        or "")
        img_loc = rec.get("img_loc") or ""
        techs = rec.get("techs") or ""
        hsn = rec.get("hsn") or 8443
        quantity = rec.get("quantity", 1)
        price = rec.get("price", 0)

        master = {
            # quick-quotation builder keys
            "q_id": rec.get("q_id"),
            "name": product_name,
            "img_loc": img_loc,
            "techs": techs,
            "quantity": quantity,
            "subtotal": subtotal,
            "gst": gst,
            "total": total,
            "mob": rec.get("mob"),
            "created": rec.get("created"),
            # fallback / shared keys
            "invid": rec.get("q_id"),
            "c_name": product_name,
            "c_add": "",
            "taxrate": taxrate,
            "taxamount": gst,
            "totalamount": total,
        }

        items = [{
            "item_name": product_name,
            "img_loc": img_loc,
            "techs": techs,
            "hsn": hsn,
            "quantity": quantity,
            "price": price,
            "total": subtotal,
        }]

        return master, items