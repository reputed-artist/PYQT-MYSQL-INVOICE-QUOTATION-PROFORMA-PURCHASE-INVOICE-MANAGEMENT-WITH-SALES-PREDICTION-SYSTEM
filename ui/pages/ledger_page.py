"""
Client Ledger page - PyQt6 port of C4/app/views/infolayout/getledger.php.

Layout mirrors the PHP page:
  ┌──────────────────────────────────────────────────────────────────┐
  │  ⊞ Filter   [FY dropdown: All (2020-2024) ▾]                     │
  ├──────────────────────────────────────────────────────────────────┤
  │  ┌── box-success ────────────────────────────────────────────┐   │
  │  │                 Customer  (u_type heading)                │   │
  │  │           Accounts of Val Labs                            │   │
  │  │           Location : PALGHAR                              │   │
  │  │  CodeTech Engineers                Opening Balance: 5,000 │   │
  │  ├────────────────────────────────────────────────────────────┤   │
  │  │  [+ Add Transaction]                                      │   │
  │  │  [Copy][JSON][Excel][CSV][PDF][Print][TXT][SQL][Docx][PNG]│   │
  │  │  ┌────────────────────────────────────────────────────┐   │   │
  │  │  │ Sno │ Date │ Voucher Type │ Voucher No │ ...       │   │   │
  │  │  │ ...                                                │   │   │
  │  │  └────────────────────────────────────────────────────┘   │   │
  │  │  Total Bal. Credit & Debit:  X          Y                 │   │
  │  │  Closing Balance:           Z                             │   │
  │  └────────────────────────────────────────────────────────────┘  │
  │                                              ┌───┐               │
  │                                              │ + │  (floating)   │
  │                                              └───┘               │
  └──────────────────────────────────────────────────────────────────┘
"""
import csv
import json
import os
from datetime import date, datetime

from PyQt6.QtCore import Qt, QDate, QMarginsF, QPoint, QSize
from PyQt6.QtGui import QTextDocument, QPageSize, QPageLayout, QImage, QPainter, QColor
from PyQt6.QtPrintSupport import QPrinter, QPrintPreviewDialog
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
                             QLabel, QPushButton, QComboBox, QFrame,
                             QScrollArea, QLineEdit, QPlainTextEdit,
                             QDialog, QFormLayout, QDateEdit, QMessageBox,
                             QSizePolicy, QFileDialog, QApplication,
                             QToolButton)

from database import db_manager
from ui import widgets as W
from ui.app_icon import apply as _apply_brand
from utils.helpers import money


# --------------------------------------------------------------------------- #
# Indian number formatting (mirrors formatIndianNumber in the PHP view)
# --------------------------------------------------------------------------- #
def _fmt_inr(v) -> str:
    """Format a number in the Indian numbering system: 12,34,567.89"""
    try:
        v = float(v or 0)
    except (TypeError, ValueError):
        return "0.00"
    neg = v < 0
    v = abs(v)
    int_part, _, dec_part = f"{v:.2f}".partition(".")
    if len(int_part) > 3:
        last3 = int_part[-3:]
        rest = int_part[:-3]
        groups = []
        while len(rest) > 2:
            groups.insert(0, rest[-2:])
            rest = rest[:-2]
        if rest:
            groups.insert(0, rest)
        int_part = ",".join(groups + [last3])
    out = f"{int_part}.{dec_part}"
    return f"-{out}" if neg else out


# =========================================================================== #
# Floating "+" button (bottom-right of the page)
# =========================================================================== #
class FloatingAddButton(QToolButton):
    """Circular green '+' button pinned to the bottom-right of its parent.

    Repositions itself on resize via the parent's resizeEvent - install it by
    calling `install_on(parent_widget)` and re-calling `reposition()` from the
    parent's resizeEvent. Simpler: we call reposition() on show + resize.
    """

    SIZE = 58
    MARGIN = 26

    def __init__(self, parent, on_click):
        super().__init__(parent)
        self._on_click = on_click

        self.setText("+")
        self.setFixedSize(self.SIZE, self.SIZE)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Add Transaction")
        self.setStyleSheet(
            "QToolButton {"
            "  background: #28a745;"
            "  color: #ffffff;"
            "  border: none;"
            "  border-radius: %dpx;"
            "  font-size: 30px;"
            "  font-weight: 400;"
            "  padding: 0;"
            "}"
            "QToolButton:hover   { background: #218838; }"
            "QToolButton:pressed { background: #1e7e34; }"
            % (self.SIZE // 2))
        self.clicked.connect(self._on_click)
        self.raise_()

    def reposition(self):
        p = self.parentWidget()
        if p is None:
            return
        x = p.width() - self.SIZE - self.MARGIN
        y = p.height() - self.SIZE - self.MARGIN
        self.move(x, y)


# =========================================================================== #
# Centered red export strip  (DataTables "Buttons" style)
# =========================================================================== #
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


# =========================================================================== #
# Add-transaction modal
# =========================================================================== #
class _AddTransactionDialog(QDialog):
    def __init__(self, parent, cid, c_name, location, u_type):
        super().__init__(parent)
        self.cid = cid
        self.u_type = int(u_type)
        self.result_data = None

        self.setWindowTitle("Add Transaction")
        self.setModal(True)
        self.setMinimumWidth(520)
        _apply_brand(self)

        v = QVBoxLayout(self)
        v.setContentsMargins(18, 16, 18, 16)
        v.setSpacing(10)

        # transaction id
        self.payid = QLineEdit()
        try:
            self.payid.setText(db_manager.next_transaction_id())
        except Exception:
            self.payid.setText("")
        self.payid.setReadOnly(True)

        # company (fixed, read-only)
        self.company = QLineEdit(c_name)
        self.company.setReadOnly(True)

        # location (fixed, read-only)
        self.loc = QLineEdit(location or "")
        self.loc.setReadOnly(True)

        # purpose
        self.purpose = QPlainTextEdit()
        self.purpose.setFixedHeight(80)
        self.purpose.setPlaceholderText("Purpose")

        # amount
        self.amount = QLineEdit()
        self.amount.setPlaceholderText("Amount")

        # date of payment
        self.dt = QDateEdit()
        self.dt.setCalendarPopup(True)
        self.dt.setDisplayFormat("dd-MM-yyyy")
        self.dt.setDate(QDate.currentDate())

        # bank
        self.bank = QComboBox()
        self.bank.addItem("", "")
        self.bank.addItem("YES BANK", "YES BANK")
        self.bank.addItem("ICICI BANK", "ICICI BANK")

        # creation date (read-only)
        self.created = QLineEdit(date.today().strftime("%d-%b-%Y"))
        self.created.setReadOnly(True)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setHorizontalSpacing(14)
        form.setVerticalSpacing(8)
        form.addRow("Transaction ID", self.payid)
        form.addRow("Company Name *", self.company)
        form.addRow("Location *", self.loc)
        form.addRow("Purpose *", self.purpose)
        form.addRow("Amount *", self.amount)
        form.addRow("Date of Payment *", self.dt)
        form.addRow("Bank *", self.bank)
        form.addRow("Creation Date", self.created)
        v.addLayout(form)

        bar = QHBoxLayout()
        bar.addStretch(1)
        close_btn = QPushButton("Close")
        close_btn.setObjectName("btnDanger")
        close_btn.clicked.connect(self.reject)
        save_btn = QPushButton("Save changes")
        save_btn.setObjectName("btnPrimary")
        save_btn.clicked.connect(self._save)
        bar.addWidget(close_btn)
        bar.addWidget(save_btn)
        v.addLayout(bar)

    def _save(self):
        purpose = self.purpose.toPlainText().strip()
        amount = self.amount.text().strip()
        bank = self.bank.currentData()
        d = self.dt.date().toPyDate()

        if not purpose:
            QMessageBox.warning(self, "Validation", "Purpose is required.")
            return
        if not amount:
            QMessageBox.warning(self, "Validation", "Amount is required.")
            return
        try:
            amount_v = float(amount)
        except ValueError:
            QMessageBox.warning(self, "Validation",
                                "Amount must be a number.")
            return
        if not bank:
            QMessageBox.warning(self, "Validation", "Bank is required.")
            return

        self.result_data = {
            "pay_id": self.payid.text().strip(),
            "cid": self.cid,
            "amount": amount_v,
            "bank": bank,
            "dateofpayment": d,
            "purpose": purpose,
            "created": date.today(),
        }
        self.accept()


# =========================================================================== #
# Ledger page
# =========================================================================== #
class LedgerPage(QWidget):
    """Full-page ledger view - mirrors getledger.php."""

    # Column layout for the ledger table.
    # 0 Sno, 1 Date, 2 Voucher Type, 3 Voucher No,
    # 4 Credit, 5 Debit, 6 Subtotal
    # The trailing numeric columns get fixed widths; the middle text columns
    # stretch to fill the remaining space so the table covers full width.
    FIXED_WIDTHS = {0: 60, 1: 110, 4: 140, 5: 140, 6: 140}
    STRETCH_COLS = [2, 3]

    def __init__(self, main, cid):
        super().__init__()
        self.main = main
        self.cid = cid
        self._fys = []
        self._current_fy = ""
        self._ledger_data = None
        self._total_credit = 0.0
        self._total_debit = 0.0
        self._closing = 0.0
        self._opening = 0.0
        self._invoice_links = []

        # ---------------- client details ----------------
        client = db_manager.get_client(cid) or {}
        self.c_name = client.get("c_name") or ""
        self.c_add = client.get("c_add") or ""
        self.location = self._extract_location(self.c_add)
        self.u_type = int(client.get("u_type") or 0)
        self.u_type_label = {
            0: "Customer", 1: "Supplier", 2: "Dual (Cust/Sup)"
        }.get(self.u_type, "—")

        try:
            acc = db_manager.DB.one(
                "SELECT opening_bal FROM account WHERE cid=%s LIMIT 1",
                (cid,))
            self._account_opening = float(
                (acc or {}).get("opening_bal") or 0)
        except Exception:
            self._account_opening = 0.0

        self._build()
        self._floating_add = FloatingAddButton(self, self._add_transaction)
        self._floating_add.reposition()

    # ------------------------------------------------------------------ #
    @staticmethod
    def _extract_location(addr: str) -> str:
        if not addr:
            return ""
        parts = [p.strip() for p in str(addr).replace("\r", "").split(",")
                 if p.strip()]
        return parts[-1] if parts else ""

    # ------------------------------------------------------------------ #
    # UI build
    # ------------------------------------------------------------------ #
    def _build(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(6)

        outer.addWidget(W.PageHeader(
            f"Ledger - {self.c_name}",
            breadcrumb="Manage-Accounts > Ledger"))

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(
            "QScrollArea { border:none; background:transparent; }")
        outer.addWidget(scroll, 1)

        inner = QWidget()
        inner.setStyleSheet("background: transparent;")
        scroll.setWidget(inner)
        v = QVBoxLayout(inner)
        v.setContentsMargins(12, 6, 12, 12)
        v.setSpacing(12)

        v.addWidget(self._build_filter_bar())
        v.addWidget(self._build_success_box(), 1)

    def _build_filter_bar(self) -> QWidget:
        bar = QFrame()
        bar.setObjectName("LedgerFilterBar")
        bar.setStyleSheet(
            "QFrame#LedgerFilterBar { background:#ffffff;"
            " border:1px solid #d2d6de; border-radius:3px; }")
        h = QHBoxLayout(bar)
        h.setContentsMargins(12, 8, 12, 8)
        h.setSpacing(10)

        icon = QLabel("\u2630")
        icon.setFixedSize(24, 24)
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setStyleSheet(
            "font-size:18px; color:#444; background:transparent;")
        h.addWidget(icon)

        h.addWidget(QLabel("Select FY:"))

        self.fy_combo = QComboBox()
        self.fy_combo.setFixedWidth(220)
        self.fy_combo.setFixedHeight(32)
        # Force a light, modern look - the OS-native QComboBox popup is
        # normally dark on Windows; this pins it to a white admin theme.
        self.fy_combo.setStyleSheet("""
            QComboBox {
                background: #ffffff;
                color: #333333;
                border: 1px solid #d2d6de;
                border-radius: 3px;
                padding: 4px 10px;
                font-size: 13px;
            }
            QComboBox:hover  { border-color: #3c8dbc; }
            QComboBox:focus  { border-color: #3c8dbc; }
            QComboBox::drop-down {
                border: none;
                width: 24px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 6px solid #666;
                width: 0; height: 0;
                margin-right: 6px;
            }
            QComboBox QAbstractItemView {
                background: #ffffff;
                color: #333333;
                border: 1px solid #d2d6de;
                selection-background-color: #3c8dbc;
                selection-color: #ffffff;
                outline: 0;
            }
            QComboBox QAbstractItemView::item {
                min-height: 24px;
                padding: 4px 8px;
            }
            QComboBox QAbstractItemView::item:selected {
                background: #3c8dbc;
                color: #ffffff;
            }
        """)
        self.fy_combo.currentIndexChanged.connect(self._on_fy_changed)
        h.addWidget(self.fy_combo)

        h.addStretch()
        return bar

    def _build_success_box(self) -> QWidget:
        box = QFrame()
        box.setObjectName("LedgerSuccessBox")
        box.setStyleSheet(
            "QFrame#LedgerSuccessBox { background:#ffffff;"
            " border:1px solid #d2d6de; border-top:3px solid #00a65a;"
            " border-radius:3px; }")

        v = QVBoxLayout(box)
        v.setContentsMargins(18, 14, 18, 16)
        v.setSpacing(8)

        # ---- heading: account type ----
        self.lbl_type = QLabel(self.u_type_label)
        self.lbl_type.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_type.setStyleSheet(
            "font-size:15px; color:#444; font-weight:600;"
            " background:transparent;")
        v.addWidget(self.lbl_type)

        # ---- Accounts of <client> ----
        self.lbl_title = QLabel(f"Accounts of {self.c_name}")
        self.lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_title.setStyleSheet(
            "font-size:22px; font-weight:700; color:#333;"
            " background:transparent;")
        v.addWidget(self.lbl_title)

        # ---- Location ----
        self.lbl_loc = QLabel(f"Location : {self.location or '—'}")
        self.lbl_loc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_loc.setStyleSheet(
            "font-size:15px; color:#555; background:transparent;")
        v.addWidget(self.lbl_loc)

        rule = QFrame()
        rule.setFixedHeight(1)
        rule.setStyleSheet("background:#e5e5e5; border:none;")
        v.addWidget(rule)

        # ---- CodeTech Engineers ... Opening Balance ----
        row = QHBoxLayout()
        left = QLabel("CodeTech Engineers")
        left.setStyleSheet(
            "font-size:16px; font-weight:600; color:#333;"
            " background:transparent;")
        row.addWidget(left)
        row.addStretch()

        self.lbl_opening = QLabel("Opening Balance: 0.00")
        self.lbl_opening.setAlignment(Qt.AlignmentFlag.AlignRight |
                                      Qt.AlignmentFlag.AlignVCenter)
        self.lbl_opening.setStyleSheet(
            "font-size:15px; font-weight:600; color:#333;"
            " background:transparent;")
        row.addWidget(self.lbl_opening)
        v.addLayout(row)

        # ---- add button ----
        actions_row = QHBoxLayout()
        btn_add = QPushButton("\u002B  Add Transaction")
        btn_add.setObjectName("btnSuccess")
        btn_add.setFixedHeight(30)
        btn_add.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_add.clicked.connect(self._add_transaction)
        actions_row.addWidget(btn_add)
        actions_row.addStretch()
        v.addLayout(actions_row)

        # ---- export buttons (centered red strip) ----
        self.export_strip = ExportButtonStrip(
            self, on_export=self._on_export)
        v.addWidget(self.export_strip)

        # ---- ledger table ----
        self.table = W.DataTable(
            ["Sno.", "Date", "Voucher Type", "Voucher No.",
             "Credit", "Debit", "Subtotal"],
            stretch_all=False)
        self.table.setMinimumHeight(320)
        hh = self.table.horizontalHeader()
        hh.setStretchLastSection(False)
        hh.setSectionResizeMode(hh.ResizeMode.Interactive)
        for col, width in self.FIXED_WIDTHS.items():
            hh.setSectionResizeMode(col, hh.ResizeMode.Fixed)
            self.table.setColumnWidth(col, width)
        for col in self.STRETCH_COLS:
            hh.setSectionResizeMode(col, hh.ResizeMode.Stretch)
        v.addWidget(self.table, 1)

        # ---- totals ----
        self.totals_box = self._build_totals_box()
        v.addWidget(self.totals_box)

        # ---- column toggles ----
        self.col_toggles = self._build_column_toggles()
        v.addWidget(self.col_toggles)

        return box

    def _build_totals_box(self) -> QWidget:
        host = QFrame()
        host.setStyleSheet(
            "QFrame { background:#f9f9f9; border:1px solid #e5e5e5;"
            " border-radius:3px; }")
        g = QGridLayout(host)
        g.setContentsMargins(12, 8, 12, 8)
        g.setHorizontalSpacing(12)
        g.setVerticalSpacing(6)

        lbl_total = QLabel("Total Bal. Credit & Debit")
        lbl_total.setStyleSheet(
            "font-size:15px; font-weight:700; color:#333;"
            " background:transparent;")
        g.addWidget(lbl_total, 0, 0, 1, 3)

        self.lbl_total_credit = QLabel("0.00")
        self.lbl_total_credit.setAlignment(Qt.AlignmentFlag.AlignRight |
                                           Qt.AlignmentFlag.AlignVCenter)
        self.lbl_total_credit.setStyleSheet(
            "font-size:15px; font-weight:700; color:#00a65a;"
            " background:transparent;")
        g.addWidget(self.lbl_total_credit, 0, 4)

        self.lbl_total_debit = QLabel("0.00")
        self.lbl_total_debit.setAlignment(Qt.AlignmentFlag.AlignRight |
                                          Qt.AlignmentFlag.AlignVCenter)
        self.lbl_total_debit.setStyleSheet(
            "font-size:15px; font-weight:700; color:#dd4b39;"
            " background:transparent;")
        g.addWidget(self.lbl_total_debit, 0, 5)

        lbl_closing = QLabel("Closing Balance")
        lbl_closing.setStyleSheet(
            "font-size:15px; font-weight:700; color:#333;"
            " background:transparent;")
        g.addWidget(lbl_closing, 1, 0, 1, 3)

        self.lbl_closing = QLabel("0.00")
        self.lbl_closing.setAlignment(Qt.AlignmentFlag.AlignRight |
                                      Qt.AlignmentFlag.AlignVCenter)
        self.lbl_closing.setStyleSheet(
            "font-size:15px; font-weight:700; color:#3c8dbc;"
            " background:transparent;")
        g.addWidget(self.lbl_closing, 1, 5)

        g.setColumnStretch(3, 1)
        return host

    def _build_column_toggles(self) -> QWidget:
        host = QWidget()
        host.setStyleSheet("background:transparent;")
        h = QHBoxLayout(host)
        h.setContentsMargins(0, 4, 0, 0)
        h.setSpacing(4)

        for i, label in enumerate(
                ["Sno.", "Date", "Voucher Type", "Voucher No.",
                 "Credit", "Debit", "Subtotal"]):
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
                lambda on, col=i: self.table.setColumnHidden(col, not on))
            h.addWidget(b)
        h.addStretch()
        return host

    # ------------------------------------------------------------------ #
    # Floating button reposition
    # ------------------------------------------------------------------ #
    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "_floating_add") and self._floating_add:
            self._floating_add.reposition()

    def showEvent(self, event):
        super().showEvent(event)
        if hasattr(self, "_floating_add") and self._floating_add:
            self._floating_add.reposition()

    # ------------------------------------------------------------------ #
    # Data load
    # ------------------------------------------------------------------ #
    def refresh(self):
        try:
            fys, latest = db_manager.get_fys_for_client(self.cid)
        except Exception as exc:
            W.error(self, f"Could not load financial years: {exc}")
            return

        if not fys:
            if date.today().month > 3:
                latest = f"{date.today().year}-{date.today().year + 1}"
            else:
                latest = f"{date.today().year - 1}-{date.today().year}"
            fys = [latest]

        self._fys = fys
        self._current_fy = latest

        try:
            ys = sorted(fys)
            from_yr = ys[0].split("-")[0]
            to_yr = ys[-1].split("-")[1]
            all_label = f"All ({from_yr}-{to_yr})"
        except Exception:
            all_label = "All"

        self.fy_combo.blockSignals(True)
        self.fy_combo.clear()
        self.fy_combo.addItem(all_label, f"__ALL__{all_label}")
        for fy in fys:
            self.fy_combo.addItem(fy, fy)
        idx = self.fy_combo.findData(self._current_fy)
        if idx >= 0:
            self.fy_combo.setCurrentIndex(idx)
        self.fy_combo.blockSignals(False)

        self._load_ledger()

    def _on_fy_changed(self, _idx):
        fy = self.fy_combo.currentData() or ""
        if fy.startswith("__ALL__"):
            fy = self._current_fy
        self._current_fy = fy
        self._load_ledger()

    def _load_ledger(self):
        try:
            data = db_manager.get_ledger_fy(self.cid, self._current_fy)
        except Exception as exc:
            W.error(self, f"Ledger error: {exc}")
            return

        self._ledger_data = data
        self._opening = float(data.get("opening_balance") or 0)
        self._total_credit = float(data.get("total_credit") or 0)
        self._total_debit = float(data.get("total_debit") or 0)
        self._closing = float(data.get("closing_balance") or 0)

        self.lbl_opening.setText(
            f"Opening Balance: {_fmt_inr(self._opening)}")
        self._render_table(data)
        self.lbl_total_credit.setText(_fmt_inr(self._total_credit))
        self.lbl_total_debit.setText(_fmt_inr(self._total_debit))
        self.lbl_closing.setText(_fmt_inr(self._closing))

    def _render_table(self, data):
        self.table.clear_rows()
        self._invoice_links = []

        row_idx = 0
        receipt_idx = 0

        for r in data.get("rows") or []:
            vtype = r.get("voucher_type") or ""
            if vtype == "Opening":
                row_idx += 1
                self.table.add_row([
                    row_idx,
                    str(r.get("date") or ""),
                    "Opening",
                    "OPENING BALANCE",
                    "",
                    "",
                    _fmt_inr(r.get("opening_bal") or 0),
                ])
                continue

            if vtype == "Total":
                continue

            row_idx += 1
            if vtype == "Receipt":
                receipt_idx += 1
                voucher_no = f"REC-{receipt_idx}"
            else:
                voucher_no = r.get("ref") or str(row_idx)

            credit = float(r.get("credit") or 0)
            debit = float(r.get("debit") or 0)
            bal = float(r.get("closing_bal") or 0)

            table_row = self.table.add_row([
                row_idx,
                str(r.get("date") or ""),
                vtype,
                voucher_no,
                _fmt_inr(credit) if credit else "",
                _fmt_inr(debit) if debit else "",
                _fmt_inr(bal),
            ], data=r)

            ref = r.get("ref") or ""
            orderid = ref.split("+")[-1] if "+" in ref else ""
            self._invoice_links.append((table_row, vtype, orderid))

        for r in range(self.table.rowCount()):
            for c in (0, 1, 4, 5, 6):
                item = self.table.item(r, c)
                if item:
                    item.setTextAlignment(
                        Qt.AlignmentFlag.AlignRight |
                        Qt.AlignmentFlag.AlignVCenter)

    # ------------------------------------------------------------------ #
    # Add transaction
    # ------------------------------------------------------------------ #
    def _add_transaction(self):
        dlg = _AddTransactionDialog(
            self, self.cid, self.c_name, self.location, self.u_type)
        if not dlg.exec() or not dlg.result_data:
            return
        try:
            db_manager.insert_transaction(dlg.result_data)
        except Exception as exc:
            W.error(self, f"Insert failed: {exc}")
            return
        W.info(self, "Transaction added.")
        self._load_ledger()

    # ------------------------------------------------------------------ #
    # Export
    # ------------------------------------------------------------------ #
    def _on_export(self, kind):
        if not self._ledger_data:
            W.info(self, "Nothing to export.")
            return

        rows = []
        for r in self._ledger_data.get("rows") or []:
            rows.append({
                "date": str(r.get("date") or ""),
                "voucher_type": r.get("voucher_type") or "",
                "ref": r.get("ref") or "",
                "credit": r.get("credit") or 0,
                "debit": r.get("debit") or 0,
                "closing_bal": r.get("closing_bal") or 0,
            })

        columns = [
            ("date", "Date"),
            ("voucher_type", "Voucher Type"),
            ("ref", "Voucher No"),
            ("credit", "Credit"),
            ("debit", "Debit"),
            ("closing_bal", "Balance"),
        ]
        self._generic_export(
            kind, rows, columns,
            filename_stub=f"ledger_{self.c_name}".replace(" ", "_"),
            sql_table="paidhistory",
            sql_cols=["cid", "amount", "bank", "dateofpayment", "purpose"])

    def _generic_export(self, kind, rows, columns,
                        filename_stub, sql_table, sql_cols):
        if not rows:
            W.info(self, "Nothing to export.")
            return

        keys = [k for k, _ in columns]
        headers = [h for _, h in columns]

        # -------- copy --------
        if kind == "copy":
            lines = ["\t".join(headers)]
            for r in rows:
                lines.append("\t".join(str(r.get(k, "")) for k in keys))
            QApplication.clipboard().setText("\n".join(lines))
            W.info(self, f"Copied {len(rows)} rows to clipboard.")
            return

        # -------- print --------
        if kind == "print":
            html = ["<html><body style='font-family:Segoe UI;font-size:10pt;'>",
                    "<table border='1' cellspacing='0' cellpadding='4'"
                    " style='border-collapse:collapse;'>",
                    "<tr style='background:#dd4b39;color:#fff;'>"]
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
            dlg = QPrintPreviewDialog(printer, self)
            dlg.setWindowTitle("Print")
            _apply_brand(dlg)
            dlg.paintRequested.connect(lambda p: doc.print(p))
            dlg.exec()
            return

        # -------- file picker --------
        ext_map = {
            "csv":   ("csv", "CSV Files (*.csv)"),
            "txt":   ("txt", "Text Files (*.txt)"),
            "json":  ("json", "JSON Files (*.json)"),
            "sql":   ("sql", "SQL Files (*.sql)"),
            "excel": ("csv", "Excel Files (*.csv)"),
            "docx":  ("html", "Word Documents (*.html)"),
            "pdf":   ("pdf", "PDF Files (*.pdf)"),
            "png":   ("png", "PNG Images (*.png)"),
        }
        if kind not in ext_map:
            W.info(self, f"Export '{kind}' is not supported.")
            return
        ext, filt = ext_map[kind]

        default = os.path.join(os.path.expanduser("~"),
                               f"{filename_stub}.{ext}")
        fname, _ = QFileDialog.getSaveFileName(
            self, f"Save {ext.upper()}", default, filt)
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
            W.info(self, f"Saved to {fname}")

        elif kind == "txt":
            lines = ["\t".join(headers)]
            for r in rows:
                lines.append("\t".join(str(r.get(k, "")) for k in keys))
            with open(fname, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
            W.info(self, f"Saved to {fname}")

        elif kind == "json":
            data = [{k: r.get(k, "") for k in keys} for r in rows]
            with open(fname, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=str)
            W.info(self, f"Saved to {fname}")

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
            W.info(self, f"Saved to {fname}")

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
            W.info(self, f"Saved to {fname}")

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
            W.info(self, f"Saved to {fname}")

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
            W.info(self, f"Saved to {fname}")