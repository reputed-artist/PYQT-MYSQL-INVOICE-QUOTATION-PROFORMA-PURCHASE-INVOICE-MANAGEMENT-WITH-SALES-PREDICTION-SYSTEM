"""
Printable invoice generator - port of the 'print' views
(print taxinv.php / print proinv.php / print quote.php / print purchaseinv.php /
printquickq.php).

Builders
--------
`build_tax_invoice_html()`       - A4 GST invoice  (tax / proforma)
`build_purchase_invoice_html()`  - A4 purchase invoice
`build_quotation_html()`         - 2-page styled quotation  (print quote.php)
`build_quick_quotation_html()`   - 2-page quick quotation   (printquickq.php)

The *View* dialog and the *Print Preview* dialog use `QWebEngineView` so the
rendered output matches the PHP/PDF view pixel-for-pixel.

Image resolution
----------------
`_find_image()` looks in `<pyqt_app_base>/dist/img/<basename>` FIRST
(same rule the working quickquote_page.py uses), then falls back to other
folders in the PyQt project and the PHP project.

`_quote_product_images()` also falls back to a **product-name lookup**
against `db_manager.list_products()` if the item dict has no `img_loc` —
so quotations work even when the item query doesn't return that column.
"""
import base64
import mimetypes
import os
import textwrap
import traceback
from datetime import date, datetime
from html import escape

from PyQt6.QtCore import Qt, QUrl, QMarginsF
from PyQt6.QtGui import QTextDocument, QPageSize, QPageLayout
from PyQt6.QtPrintSupport import QPrinter, QPrintPreviewDialog
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout,
                             QPushButton, QFileDialog)

from config import ORIG_PROJECT_ROOT
from database import db_manager
from utils.helpers import money, number_to_words


def _msg(kind, parent, title, text):
    """Kind-aware message box: ``kind`` is a `ui.widgets` helper name
    ("success" / "info" / "warning" / "error"), so the dialog title bar gets
    the matching icon (tick / "i" / "!" / "x").

    `ui.widgets` is imported on use - this module stays importable without
    pulling in the whole UI package.
    """
    from ui import widgets
    return getattr(widgets, kind)(parent, text, title)


def _brand(widget):
    """Give a dialog the brand icon on its title bar (`ui.app_icon.apply`)."""
    try:
        from ui.app_icon import apply
        apply(widget)
    except Exception:
        pass
    return widget


# --------------------------------------------------------------------------- #
# App base folder  (…/pyqt_app/)
#
# Walks up from this module's file location to find the folder that
# contains a `dist/` sub-directory - exactly what quickquote_page.py does.
# --------------------------------------------------------------------------- #
def _app_base_dir() -> str:
    here = os.path.dirname(os.path.abspath(__file__))
    cur = here
    for _ in range(6):
        if os.path.isdir(os.path.join(cur, "dist")):
            return cur
        parent = os.path.dirname(cur)
        if parent == cur:
            break
        cur = parent
    # Fallback: walk up 3 levels (…/utils/invoice_print.py -> …/)
    return os.path.abspath(os.path.join(here, "..", ".."))


_PYQT_BASE = _app_base_dir()
_IMG_DIR = os.path.join(_PYQT_BASE, "dist", "img")


def _asset_dir(*parts):
    for base in (_PYQT_BASE, ORIG_PROJECT_ROOT):
        path = os.path.join(base, *parts)
        if os.path.isdir(path):
            return path
    return os.path.join(_PYQT_BASE, *parts)


def _all_asset_dirs(*parts):
    seen = []
    for base in (_PYQT_BASE, ORIG_PROJECT_ROOT):
        path = os.path.join(base, *parts)
        if os.path.isdir(path) and path not in seen:
            seen.append(path)
    return seen


def _img_data_uri(path):
    if not path or not os.path.isfile(path):
        return None
    try:
        with open(path, "rb") as f:
            raw = f.read()
    except OSError:
        return None
    mime = mimetypes.guess_type(path)[0] or "image/png"
    b64 = base64.b64encode(raw).decode("ascii")
    return f"data:{mime};base64,{b64}"


def _find_image(img_loc, debug=False, label=""):
    """Locate an image by its `img_loc` value.

    PRIMARY: <pyqt_app_base>/dist/img/<basename>
    Then fallbacks inside the PyQt project and the PHP project.
    """
    if not img_loc:
        if debug:
            print(f"[img] {label}: img_loc is empty")
        return None

    img_loc = str(img_loc).strip()
    if not img_loc:
        if debug:
            print(f"[img] {label}: img_loc is blank")
        return None

    # 1. Absolute path
    if os.path.isabs(img_loc) and os.path.isfile(img_loc):
        if debug:
            print(f"[img] {label}: absolute -> {img_loc}")
        return img_loc

    rel = img_loc.replace("\\", "/").lstrip("/")
    rel_parts = rel.split("/")
    basename = rel_parts[-1]

    # --- PRIMARY: <base>/dist/img/<basename> ------------------------------
    p = os.path.join(_IMG_DIR, basename)
    if os.path.isfile(p):
        if debug:
            print(f"[img] {label}: found (primary dist/img) -> {p}")
        return p

    p_full = os.path.join(_IMG_DIR, *rel_parts)
    if os.path.isfile(p_full):
        if debug:
            print(f"[img] {label}: found (primary dist/img full) -> {p_full}")
        return p_full

    p2 = os.path.join(_PYQT_BASE, *rel_parts)
    if os.path.isfile(p2):
        if debug:
            print(f"[img] {label}: found (app_base) -> {p2}")
        return p2

    # --- Fallback folders inside the PyQt project -------------------------
    primary_dirs = [
        os.path.join(_PYQT_BASE, "public", "dist", "img"),
        os.path.join(_PYQT_BASE, "dist"),
        os.path.join(_PYQT_BASE, "uploads"),
        os.path.join(_PYQT_BASE, "public", "uploads"),
        os.path.join(_PYQT_BASE, "images"),
        os.path.join(_PYQT_BASE, "public", "images"),
        os.path.join(_PYQT_BASE, "public", "img"),
        os.path.join(_PYQT_BASE, "img"),
    ]
    for d in primary_dirs:
        p_full = os.path.join(d, *rel_parts)
        if os.path.isfile(p_full):
            if debug:
                print(f"[img] {label}: found (fallback) -> {p_full}")
            return p_full
        p_base = os.path.join(d, basename)
        if os.path.isfile(p_base):
            if debug:
                print(f"[img] {label}: found (fallback basename) -> {p_base}")
            return p_base

    # --- Fallback folders inside the PHP project --------------------------
    secondary_dirs = []
    for prefix in (
        ("dist", "img"), ("public", "dist", "img"),
        ("uploads"), ("public", "uploads"),
        ("images"), ("public", "images"),
        ("public", "img"), ("img"),
        ("static", "uploads"), ("media"),
    ):
        secondary_dirs.extend(_all_asset_dirs(*prefix))

    for d in secondary_dirs:
        p_full = os.path.join(d, *rel_parts)
        if os.path.isfile(p_full):
            if debug:
                print(f"[img] {label}: found (php) -> {p_full}")
            return p_full
        p_base = os.path.join(d, basename)
        if os.path.isfile(p_base):
            if debug:
                print(f"[img] {label}: found (php basename) -> {p_base}")
            return p_base

    if debug:
        print(f"[img] {label}: NOT FOUND for {img_loc!r}")
        print(f"[img] {label}: primary folder -> {_IMG_DIR}"
              f"  exists={os.path.isdir(_IMG_DIR)}")
        if os.path.isdir(_IMG_DIR):
            try:
                files = os.listdir(_IMG_DIR)
                print(f"[img] {label}: {len(files)} files in dist/img, e.g.")
                for f in files[:10]:
                    print(f"[img]     {f}")
            except OSError:
                pass
    return None


# --------------------------------------------------------------------------- #
# Product lookup helper (fallback for img_loc / techs / hsn)
# --------------------------------------------------------------------------- #
_PRODUCT_CACHE = None


def _load_products():
    """Fetch all products once and cache them."""
    global _PRODUCT_CACHE
    if _PRODUCT_CACHE is None:
        try:
            _PRODUCT_CACHE = db_manager.list_products() or []
        except Exception:
            _PRODUCT_CACHE = []
    return _PRODUCT_CACHE


def _lookup_product_by_name(name):
    """Return the product dict whose name matches exactly (case-insensitive)."""
    if not name:
        return None
    needle = str(name).strip().lower()
    for p in _load_products():
        if (p.get("name") or "").strip().lower() == needle:
            return p
    return None


# --------------------------------------------------------------------------- #
# Generic fallback
# --------------------------------------------------------------------------- #
def build_invoice_html(doc, master, items, admin=None, bank=None):
    admin = admin or db_manager.get_admin()
    bank = bank or db_manager.get_bank_details() or {}
    label = {"tax": "TAX INVOICE", "proforma": "PROFORMA INVOICE",
             "quote": "QUOTATION", "purchase": "PURCHASE INVOICE"}[doc]
    c_name = master.get("c_name", "") or ""
    c_add = master.get("c_add", "") or ""
    c_gst = master.get("gst", "") or ""
    invid = master.get("invid", "")
    date_ = str(master.get("created") or master.get("invdate") or "")
    subtotal = float(master.get("subtotal") or 0)
    taxrate = float(master.get("taxrate") or 0)
    taxamount = float(master.get("taxamount") or 0)
    total = float(master.get("totalamount") or 0)

    rows_html = ""
    for i, it in enumerate(items, 1):
        qty = float(it.get("quantity") or 0)
        price = float(it.get("price") or 0)
        rows_html += f"""
        <tr>
          <td align="center">{i}</td>
          <td>{it.get('item_name', '')}</td>
          <td>{it.get('item_desc', '') or ''}</td>
          <td align="center">{it.get('hsn', '')}</td>
          <td align="right">{qty:g}</td>
          <td align="right">{money(price)}</td>
          <td align="right">{money(qty * price)}</td>
        </tr>"""

    return f"""
    <html><body style="font-family:'Segoe UI'; font-size:11pt; color:#222;">
    <h2 style="margin:0">{admin.get('c_name', '')}</h2>
    <div>{admin.get('c_add', '')}</div>
    <hr/>
    <h1 style="color:#3c8dbc">{label}</h1>
    <div><b>{invid}</b> &mdash; {date_}</div>
    <div>To: {c_name}<br/>{c_add}<br/>GST: {c_gst}</div>
    <table width="100%" border="1" cellspacing="0" cellpadding="4"
           style="border-collapse:collapse; margin-top:10px;">
      <tr style="background:#3c8dbc; color:#fff">
        <th>#</th><th>Item</th><th>Description</th><th>HSN</th>
        <th>Qty</th><th>Price</th><th>Total</th>
      </tr>
      {rows_html}
    </table>
    <p><b>Subtotal:</b> {money(subtotal)}<br/>
       <b>GST ({taxrate:g}%):</b> {money(taxamount)}<br/>
       <b>Grand Total:</b> {money(total)}</p>
    <p><b>Amount in words:</b> {number_to_words(int(round(total)))} Rupees Only</p>
    </body></html>
    """


# --------------------------------------------------------------------------- #
# Faithful A4 invoice constants
# --------------------------------------------------------------------------- #
INVOICE_PRINT_DOCS = ("tax", "proforma", "purchase", "quote", "quickq")

_PRINT_TITLE = {"tax": "Tax Invoice", "proforma": "Proforma Invoice",
                "purchase": "Purchase Invoice", "quote": "Quotation",
                "quickq": "Quick Quotation"}
_PRINT_STICKER = {"tax": "sticker Letter black Pad.png",
                  "proforma": "sticker Letter colorpad.png",
                  "quote": "sticker Letter colorpad.png",
                  "quickq": "sticker Letter colorpad.png"}

_LR = "border-left:1px solid black;border-right:1px solid black;"
_BR = "border-right:1px solid black;border-bottom:1px solid black;"
_R  = "border-right:1px solid black;"
_L  = "border-left:1px solid black;"
_TB = "border:1px solid black;border-top:0px;"
_TD = "border:1px solid black;"
_LB = "border-left:1px solid black;border-bottom:1px solid black;"
_TR = "border-top:1px solid black;border-right:1px solid black;"


def _h(value):
    return escape(str(value if value is not None else ""), quote=False)


def _n2(value):
    try:
        return f"{float(value or 0):,.2f}"
    except (TypeError, ValueError):
        return "0.00"


def _dmy(value):
    if isinstance(value, datetime):
        value = value.date()
    if isinstance(value, date):
        return value.strftime("%d-%b-%Y")
    text = str(value or "").strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(text[:len(fmt) + 2], fmt) \
                .strftime("%d-%b-%Y")
        except ValueError:
            continue
    return text


def _wrap_address(text, width=40, keep=4):
    wrapped = []
    for para in (str(text or "").splitlines() or [""]):
        wrapped.extend(textwrap.wrap(para, width=width, break_long_words=True,
                                     break_on_hyphens=False,
                                     replace_whitespace=False) or [""])
    while len(wrapped) < keep:
        wrapped.append("")
    wrapped = [_h(line) for line in wrapped]
    wrapped[keep - 1] = "<br/>".join(wrapped[keep - 1:])
    return wrapped[:keep]


def _tax_id_line(country, gst):
    code = str(gst or "").strip()
    up = code.upper()
    if country == "India":
        if len(code) == 10:
            return f"Pan : {up}"
        if len(code) == 12:
            return f"Adhaar : {up}"
        if len(code) == 15:
            return f"GSTIN/UIN : {up}"
    elif country == "Nepal":
        if len(code) == 15:
            return f"Exim Code : {up}"
        if len(code) == 9:
            return f"Nepal Pan : {up}"
    return ""


# =========================================================================== #
# Tax / Purchase shared builders
# =========================================================================== #
def _build_item_rows(master, items, c_type, taxrate, taxamount,
                     subtotal, totalamount, last_hsn):
    total_items = len(items)
    rows = []
    for n, it in enumerate(items, 1):
        rows.append(
            f'<tr height="21">'
            f'<td height="25" style="{_LR}" align="center">{n}</td>'
            f'<td colspan="2" style="{_R}">&nbsp;{_h(it.get("item_name"))}</td>'
            f'<td style="{_R}"><div align="center">{_h(it.get("hsn"))}</div></td>'
            f'<td style="{_R}"><div align="center">{_n2(it.get("quantity"))}</div></td>'
            f'<td style="{_R}"><div align="center">{_n2(it.get("price"))}</div></td>'
            f'<td style="{_R}"><div align="center"> No. </div></td>'
            f'<td style="{_R}"><div align="center">{_n2(it.get("total"))}</div></td>'
            f'</tr>')
        if it.get("item_desc"):
            rows.append(
                f'<tr height="21">'
                f'<td height="25" style="{_LR}"><div align="center"></div></td>'
                f'<td colspan="2" style="{_R}padding-left:20px;">&nbsp;'
                f'({_h(it.get("item_desc"))})</td>'
                f'<td style="{_R}"><div align="center"></div></td>'
                f'<td style="{_R}"><div align="center"></div></td>'
                f'<td style="{_R}"><div align="center"></div></td>'
                f'<td style="{_R}"><div align="center"></div></td>'
                f'<td style="{_R}"><div align="center"></div></td>'
                f'</tr>')

    if total_items > 1:
        for tail in ("------------------", _n2(subtotal)):
            rows.append(
                f'<tr height="18">'
                f'<td height="10" style="{_LR}">&nbsp;</td>'
                f'<td colspan="2" style="{_R}"> &nbsp;</td>'
                f'<td style="{_R}"><div align="center"></div></td>'
                f'<td style="{_R}"><div align="center"></div></td>'
                f'<td style="{_R}"><div align="center"></div></td>'
                f'<td style="{_R}"><div align="center"></div></td>'
                f'<td style="{_R}"><div align="center">{tail}</div></td>'
                f'</tr>')

    filler_count = {1: 9, 2: 7, 3: 4, 4: 3, 5: 4}.get(
        total_items, 2 if total_items > 5 else 0)
    for _ in range(filler_count):
        rows.append(
            f'<tr height="21">'
            f'<td height="21" style="{_LR}">&nbsp;</td>'
            f'<td colspan="2" style="{_R}">&nbsp;</td>'
            f'<td style="{_R}"><div align="center"></div></td>'
            f'<td style="{_R}"><div align="center"></div></td>'
            f'<td style="{_R}"><div align="center"></div></td>'
            f'<td style="{_R}"><div align="center"></div></td>'
            f'<td style="{_R}"><div align="center"></div></td>'
            f'</tr>')

    if c_type == "IGST":
        labels = [(f"IGST&nbsp; ({taxrate:g} % )", taxamount)]
    elif c_type == "Loc":
        labels = [(f"CGST&nbsp;({taxrate / 2:g} %)", taxamount / 2),
                  (f"SGST&nbsp;({taxrate / 2:g} %)", taxamount / 2)]
    else:
        labels = []

    pad = "&nbsp;" * 54
    for label, amount in labels:
        rows.append(
            f'<tr height="22">'
            f'<td height="22" style="{_LR}">&nbsp;</td>'
            f'<td colspan="2" style="{_R}">' + pad +
            f'<em><strong>{label}</strong></em></td>'
            f'<td style="{_R}"></td>'
            f'<td style="{_R}"></td>'
            f'<td style="{_R}"></td>'
            f'<td style="{_R}">&nbsp;</td>'
            f'<td style="{_R}"><div align="center"><b>{_n2(amount)}</b></div></td>'
            f'</tr>')

    rows.append(
        f'<tr height="20">'
        f'<td height="20" style="{_TB}">&nbsp;</td>'
        f'<td colspan="2" style="{_BR}">&nbsp;</td>'
        f'<td style="{_BR}">&nbsp;</td>'
        f'<td style="{_BR}">&nbsp;</td>'
        f'<td style="{_BR}">&nbsp;</td>'
        f'<td style="{_BR}">&nbsp;</td>'
        f'<td style="{_BR}"><div align="center"></div></td>'
        f'</tr>')

    rows.append(
        f'<tr height="22">'
        f'<td height="22" style="{_TB}">&nbsp;</td>'
        f'<td colspan="2" style="{_BR}"><div align="right" style="padding-right:4px;">'
        f'<strong>Total</strong></div></td>'
        f'<td style="{_BR}">&nbsp;</td>'
        f'<td style="{_BR}"><div align="center">{total_items:.2f}</div></td>'
        f'<td style="{_BR}">&nbsp;</td>'
        f'<td style="{_BR}"><div align="center">No</div></td>'
        f'<td style="{_BR}"><div align="center"><b>{_n2(totalamount)}</b></div></td>'
        f'</tr>')

    rows.append(
        f'<tr height="22">'
        f'<td colspan="7" height="22" style="{_L}">Amount Chargeable&nbsp;&nbsp;&nbsp;(in words):</td>'
        f'<td style="{_R}"><div align="center">E.&amp; O.E.</div></td>'
        f'</tr>')
    rows.append(
        f'<tr height="27">'
        f'<td colspan="8" height="27" style="{_TB}"><strong>Indian Rupees '
        f'{number_to_words(int(round(totalamount)))}  Only</strong>&nbsp;</td>'
        f'</tr>')

    return "".join(rows)


def _build_tax_summary(c_type, taxrate, taxamount, subtotal, totalamount,
                       last_hsn):
    out = []
    if c_type == "IGST":
        out.append(
            f'<tr height="20">'
            f'<td colspan="3" rowspan="2" height="30" style="{_TB}">'
            f'<div align="center">HSN /SAC</div></td>'
            f'<td width="93" height="30" rowspan="2" style="{_BR}">'
            f'<div align="center" style="padding-right:2px">Taxable Value</div></td>'
            f'<td colspan="2" style="{_BR}">'
            '&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; &nbsp;&nbsp; Integrated Tax</td>'
            f'<td colspan="2" style="{_R}"><div align="center">Total&nbsp;</div></td>'
            f'</tr>'
            f'<tr height="15">'
            f'<td height="20" style="{_BR}">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; Rate&nbsp;</td>'
            f'<td height="20" style="{_BR}"><div align="center">Amount</div></td>'
            f'<td height="20" colspan="3" style="{_BR}"><div align="center">Amount</div></td>'
            f'</tr>'
            f'<tr height="29">'
            f'<td colspan="3" height="29" style="{_TB}">'
            f'<div align="center">{last_hsn}</div></td>'
            f'<td style="{_BR}"><div align="center">{_n2(subtotal)}</div></td>'
            f'<td style="{_BR}"><div align="center">{taxrate:g} % </div></td>'
            f'<td style="{_BR}"><div align="center">{_n2(taxamount)}</div></td>'
            f'<td colspan="2" style="{_BR}"><div align="center">{_n2(totalamount)}</div></td>'
            f'</tr>'
            f'<tr height="24">'
            f'<td colspan="3" height="24" style="{_TB}">'
            f'<div align="center"><strong>Total</strong></div></td>'
            f'<td style="{_BR}"><div align="center"><strong>{_n2(subtotal)}</strong></div></td>'
            f'<td style="{_BR}"><div align="center"></div></td>'
            f'<td style="{_BR}"><div align="center"><strong>{_n2(taxamount)}</strong></div></td>'
            f'<td colspan="2" style="{_BR}"><div align="center"><strong>{_n2(totalamount)}</strong></div></td>'
            f'</tr>'
            f'<tr height="34">'
            f'<td colspan="8" height="27" style="{_TB}">Tax Amount (in words) :&nbsp; '
            f'<strong>Indian Rupees {number_to_words(int(round(taxamount)))} Only&nbsp;</strong></td>'
            f'</tr>')
    elif c_type == "Loc":
        half = _n2(taxamount / 2)
        half_rate = f"{taxrate / 2:g} %"
        out.append(
            f'<tr height="20">'
            f'<td colspan="2" rowspan="2" height="45" style="{_TB}">'
            f'<div align="center">HSN /SAC</div></td>'
            f'<td rowspan="2" width="115" style="border-right:1px solid black;border-bottom:1px solid black;">'
            f'<div align="center">Taxable    Value</div></td>'
            f'<td colspan="2" style="border-bottom:1px solid black;border-right:1px solid black;">'
            f'<div align="center">Central Tax</div></td>'
            f'<td colspan="2" style="border-bottom:1px solid black;border-right:1px solid black;">'
            f'<div align="center">State Tax</div></td>'
            f'<td style="border-bottom:1px solid black;border-right:1px solid black;">'
            f'<div align="center">Total&nbsp;</div></td>'
            f'</tr>'
            f'<tr height="25">'
            f'<td height="25" style="border-bottom:1px solid black;border-right:1px solid black;">'
            f'<div align="center">Rate</div></td>'
            f'<td style="border-bottom:1px solid black;border-right:1px solid black;">'
            f'<div align="center">Amount</div></td>'
            f'<td style="border-bottom:1px solid black;border-right:1px solid black;">'
            f'<div align="center">Rate</div></td>'
            f'<td style="border-bottom:1px solid black;border-right:1px solid black;">'
            f'<div align="center">Amount</div></td>'
            f'<td style="border-bottom:1px solid black;border-right:1px solid black;">'
            f'<div align="center">Tax</div></td>'
            f'</tr>'
            f'<tr height="25">'
            f'<td colspan="2" height="25" style="{_TB}">'
            f'<div align="center">{last_hsn}</div></td>'
            f'<td style="border-bottom:1px solid black;border-right:1px solid black;">'
            f'<div align="center">{_n2(subtotal)}</div></td>'
            f'<td style="border-bottom:1px solid black;border-right:1px solid black;">'
            f'<div align="center">{half_rate}</div></td>'
            f'<td style="border-bottom:1px solid black;border-right:1px solid black;">'
            f'<div align="center">{half}</div></td>'
            f'<td style="border-bottom:1px solid black;border-right:1px solid black;">'
            f'<div align="center">{half_rate}</div></td>'
            f'<td style="border-bottom:1px solid black;border-right:1px solid black;">'
            f'<div align="center">{half}</div></td>'
            f'<td style="border-bottom:1px solid black;border-right:1px solid black;">'
            f'<div align="center"><p>{_n2(taxamount)}</p></div></td>'
            f'</tr>'
            f'<tr height="24">'
            f'<td colspan="2" height="24" style="{_TB}">'
            f'<div align="center"><strong>Total</strong></div></td>'
            f'<td style="border-bottom:1px solid black;border-right:1px solid black;">'
            f'<div align="center"><strong>{_n2(subtotal)}</strong></div></td>'
            f'<td style="border-bottom:1px solid black;border-right:1px solid black;">'
            f'<div align="center"></div></td>'
            f'<td style="border-bottom:1px solid black;border-right:1px solid black;">'
            f'<div align="center"><strong>{half}</strong></div></td>'
            f'<td style="border-bottom:1px solid black;border-right:1px solid black;">'
            f'<div align="center"></div></td>'
            f'<td style="border-bottom:1px solid black;border-right:1px solid black;">'
            f'<div align="center"><strong>{half}</strong></div></td>'
            f'<td style="border-bottom:1px solid black;border-right:1px solid black;">'
            f'<div align="center"><strong>{_n2(taxamount)}</strong></div></td>'
            f'</tr>'
            f'<tr height="34">'
            f'<td colspan="8" height="27" style="{_TB}"><strong>Tax Amount (in words) :&nbsp; '
            f'Indian Rupees {number_to_words(int(round(taxamount)))} Only&nbsp;</strong></td>'
            f'</tr>')
    return "".join(out)


# =========================================================================== #
# TAX / PROFORMA INVOICE
# =========================================================================== #
def build_tax_invoice_html(doc, master, items, admin=None, banks=None,
                           delivery=None):
    admin = admin or db_manager.get_admin() or {}
    if banks is None:
        banks = db_manager.get_banks() or []
    items = list(items or [])

    title = _PRINT_TITLE.get(doc, "Tax Invoice")
    sticker = _PRINT_STICKER.get(doc, _PRINT_STICKER["tax"])
    invid = _h(master.get("invid") or "")
    c_name = _h(master.get("c_name") or "")
    inv_date = _dmy(master.get("created") or master.get("invdate"))
    mob = _h(master.get("mob") or "")
    tax_id = _h(_tax_id_line((master.get("country") or "").strip(),
                             master.get("gst")))
    c_type = (master.get("c_type") or "").strip()
    subtotal = float(master.get("subtotal") or 0)
    taxrate = float(master.get("taxrate") or 0)
    taxamount = float(master.get("taxamount") or 0)
    totalamount = float(master.get("totalamount") or 0)
    company = _h(admin.get("c_name") or "")
    addr = _wrap_address(master.get("c_add"))
    delivery = delivery or None
    last_hsn = _h(items[-1].get("hsn")) if items else ""

    parts = []
    parts.append(f"""<html><head><meta charset="utf-8"><style>
      @page {{ size: A4 portrait; margin: 0; }}
      html, body {{ margin:0; padding:0; background:#ffffff; }}
      body {{ font-family:calibri, 'Segoe UI', Arial, sans-serif;
              font-size:10pt; color:#000000; }}
      td {{ padding-left:2px; }}
      table {{ border-collapse:collapse; }}
      img {{ image-rendering: -webkit-optimize-contrast; }}
      page {{ display:block; width:21cm; height:29.7cm; background:white;
              margin:0; padding:0; }}
    </style></head><body>
    <page size="A4">
    <table width="816" height="1056" cellpadding="0" cellspacing="0"
           style="font-family:calibri; margin-top:10px;" align="center">
      <col width="31" /><col width="201" /><col width="61" /><col width="87" />
      <col width="72" /><col width="77" /><col width="57" /><col width="73" />

      <tr height="13">
        <td height="13" colspan="8" style="{_TD}">
          <img src="{sticker}" height="200px" width="870px"/></td>
      </tr>

      <tr height="26">
        <td colspan="8" height="24"
            style="border:1px solid black;border-bottom:0px;font-size:20px;">
          <div style="float: left">
            <b>&nbsp; GSTIN:&nbsp; {_h(admin.get('gst'))} </b>
            <strong style="font-size:24px; margin-left: 100px;">{title}</strong>
            <b style="padding-left:120px;">&nbsp; IEC:&nbsp; {_h(admin.get('pan'))} </b>
          </div></td>
      </tr>
      <tr height="13">
        <td height="13" colspan="8" style="{_TD}">&nbsp;</td>
      </tr>

      <tr height="20">
        <td colspan="3" height="20"
            style="border:1px solid black;border-bottom:0px;">&nbsp; Buyer</td>
        <td colspan="2" style="{_TR}">Invoice No.</td>
        <td colspan="3" style="{_TR}">Dated</td>
      </tr>
      <tr height="20">
        <td colspan="3" height="20" style="{_LR}">&nbsp; To,</td>
        <td colspan="2" style="{_BR}"><b>{invid}</b></td>
        <td colspan="3" style="{_BR}"><b>{inv_date}</b></td>
      </tr>
      <tr height="24">
        <td colspan="3" height="24" style="{_LR}">&nbsp;
          <strong style="font-size: 18px;">M/s. {c_name}</strong></td>
        <td colspan="2" style="{_R}">Buyer's Order No.</td>
        <td colspan="3" style="{_R}">Dated</td>
      </tr>
      <tr height="23">
        <td colspan="3" height="24" style="{_LR}padding-left:10px;">{addr[0]}</td>
        <td colspan="2" style="{_BR}">&nbsp;</td>
        <td colspan="3" style="{_BR}">&nbsp;</td>
      </tr>
      <tr height="23">
        <td colspan="3" height="24" style="{_LR}padding-left:10px;">{addr[1]}</td>
        <td colspan="2" style="{_R}">Dispatch through</td>
        <td colspan="3" style="{_R}">Mode/Terms of Payment</td>
      </tr>
      <tr height="23">
        <td colspan="3" height="24" style="{_LR}padding-left:10px;">{addr[2]}</td>
        <td colspan="2" style="{_BR}"><strong></strong></td>
        <td colspan="3" style="{_BR}"><b>NEFT</b></td>
      </tr>
      <tr style="border-left:1px solid black; border-bottom: 0px;">
        <td colspan="3" style="{_LR}padding-left:10px;">{addr[3]}</td>
        <td colspan="5" style="border-left:1px solid black;border-right:1px solid black;">{
          'Delivery Address' if delivery else 'Terms of Delivery'}</td>
      </tr>
      <tr height="23">
        <td colspan="3" height="23" style="{_LR}">
          <strong>&nbsp; Mob    : {mob}</strong></td>
        <td colspan="5" style="{_R}"><b>{
          'M/s.' + _h(delivery.get('name')) if delivery else ''}</b></td>
      </tr>
      <tr height="23">
        <td colspan="3" height="23" style="{_LR}"><strong>&nbsp; {tax_id}</strong></td>
        <td colspan="5" style="{_R}">{
          _h(delivery.get('address')) if delivery else ''}</td>
      </tr>
      <tr height="13">
        <td colspan="3" height="13" style="{_TB}"></td>
        <td height="15" colspan="5" style="{_BR}"><b>{
          'Mob: ' + _h(delivery.get('mob')) if delivery else ''}</b></td>
      </tr>
    """)

    parts.append(f"""
      <tr height="35">
        <td height="35" width="38" style="{_TB}">
          <div align="center"><strong>Sr. No.</strong></div></td>
        <td colspan="2" style="{_BR}">
          <div align="center"><strong>Description of Goods</strong></div></td>
        <td style="{_BR}"><div align="center"><strong>HSN/SAC</strong></div></td>
        <td width="114" style="{_BR}"><div align="center"><strong>Quantity</strong></div></td>
        <td width="94" style="{_BR}"><div align="center"><strong>Rate</strong></div></td>
        <td width="37" style="{_BR}"><div align="center"><strong>per</strong></div></td>
        <td width="102" style="{_BR}"><div align="center"><strong>Amount</strong></div></td>
      </tr>
    """)

    parts.append(_build_item_rows(master, items, c_type, taxrate, taxamount,
                                  subtotal, totalamount, last_hsn))
    parts.append(_build_tax_summary(c_type, taxrate, taxamount, subtotal,
                                    totalamount, last_hsn))

    parts.append(
        f'<tr height="15">'
        f'<td colspan="8" height="20" style="{_LR}">&nbsp;Proprietorship\'s PAN : '
        f'{_h(admin.get("pan"))}</td>'
        f'</tr>'
        f'<tr height="20" style="{_LR}"></tr>')

    bank_count = len(banks)
    if bank_count > 1:
        parts.append(
            f'<tr height="20">'
            f'<td colspan="4" height="20" style="{_L}padding-left:5px;">'
            f'<u>Bank Details</u></td>'
            f'<td colspan="4" height="20" style="{_R}padding-left:5px;">'
            f'<u>Bank Details</u></td>'
            f'</tr>')
    else:
        parts.append(
            f'<tr height="20" style="{_R}">'
            f'<td colspan="4" height="20" style="{_L}padding-left:5px;">'
            f'<u>Bank Details</u></td>'
            f'</tr>')

    for i in range(0, bank_count, 2):
        pair = banks[i:i + 2]
        rows_b = [
            ("Bank Name: ", "bname", False),
            ("A/C No: ", "ac", False),
            ("IFSC Code: ", "ifsc", True),
        ]
        for prefix, key, with_branch in rows_b:
            left_html = prefix + str(pair[0].get(key) or "")
            if with_branch:
                left_html += " & " + "Branch: " + str(pair[0].get("branch") or "")
            if len(pair) > 1:
                right_html = prefix + str(pair[1].get(key) or "")
                if with_branch:
                    right_html += " & " + "Branch: " + str(pair[1].get("branch") or "")
                right_cell = (f'<td colspan="4" style="{_R}padding-left:5px;">'
                              f'{_h(right_html)}</td>')
            else:
                right_cell = f'<td colspan="4" style="{_R}"></td>'
            parts.append(
                f'<tr height="20">'
                f'<td colspan="4" height="20" style="{_L}padding-left:5px;">'
                f'{_h(left_html)}</td>{right_cell}</tr>')

    parts.append(f'<tr height="20" style="{_LR}"></tr>')

    parts.append(
        f'<tr height="20">'
        f'<td colspan="8" height="20" style="{_LR}"><u>Declaration&nbsp;&nbsp;</u></td>'
        f'</tr>'
        f'<tr height="24">'
        f'<td height="24" colspan="4" style="{_L}">We    declare that this invoice shows the actual price of the&nbsp;</td>'
        f'<td colspan="4" style="border:1px solid black;border-bottom:0px;">'
        f'<div align="right" style="padding-right:10px;"><strong>for {company}</strong></div></td>'
        f'</tr>'
        f'<tr height="29">'
        f'<td height="29" colspan="3" style="{_L}">goods described and that all particulars are true and correct.</td>'
        f'<td>&nbsp;</td>'
        f'<td colspan="4" style="{_LR}"><div align="right"></div></td>'
        f'</tr>'
        f'<tr height="19">'
        f'<td height="19" colspan="4" style="{_LB}">&nbsp;</td>'
        f'<td colspan="4" style="border:1px solid black;border-top: 0px; padding-right:10px;">'
        f'<div align="right">Authorised    Signatory</div></td>'
        f'</tr>'
        f'<tr height="5">'
        f'<td colspan="8" height="5"><div align="center"></div></td>'
        f'</tr>'
        f'<tr height="20">'
        f'<td height="20" colspan="8"><div align="center">This is a Computer    Generated Invoice</div></td>'
        f'</tr>')

    parts.append("</table></page></body></html>")
    return "".join(parts)


# =========================================================================== #
# PURCHASE INVOICE
# =========================================================================== #
def build_purchase_invoice_html(master, items, admin=None, buyer=None):
    admin = admin or db_manager.get_admin() or {}
    items = list(items or [])

    title = "Purchase Invoice"
    invid = _h(master.get("invid") or "")
    c_name = _h(master.get("c_name") or "")
    inv_date = _dmy(master.get("invdate") or master.get("created"))
    mob = _h(master.get("mob") or "")
    tax_id = _h(_tax_id_line((master.get("country") or "").strip(),
                             master.get("gst")))
    c_type = (master.get("c_type") or "").strip()
    subtotal = float(master.get("subtotal") or 0)
    taxrate = float(master.get("taxrate") or 0)
    taxamount = float(master.get("taxamount") or 0)
    totalamount = float(master.get("totalamount") or 0)
    company = _h(admin.get("c_name") or "")
    company_addr = _wrap_address(admin.get("c_add") or "")
    company_mob = _h(admin.get("mob") or "")
    company_gst = _h(admin.get("gst") or "")
    addr = _wrap_address(master.get("c_add"))
    last_hsn = _h(items[-1].get("hsn")) if items else ""

    parts = []
    parts.append(f"""<html><head><meta charset="utf-8"><style>
      @page {{ size: A4 portrait; margin: 0; }}
      html, body {{ margin:0; padding:0; background:#ffffff; }}
      body {{ font-family:calibri, 'Segoe UI', Arial, sans-serif;
              font-size:10pt; color:#000000; }}
      td {{ padding-left:2px; }}
      table {{ border-collapse:collapse; }}
      img {{ image-rendering: -webkit-optimize-contrast; }}
      page {{ display:block; width:21cm; height:29.7cm; background:white;
              margin:0; padding:0; }}
    </style></head><body>
    <page size="A4">
    <table width="816" height="1056" cellpadding="0" cellspacing="0"
           style="font-family:calibri; margin-top:10px;" align="center">
      <col width="31" /><col width="201" /><col width="61" /><col width="87" />
      <col width="72" /><col width="77" /><col width="57" /><col width="73" />

      <tr height="13"></tr>

      <tr height="26">
        <td colspan="8" height="24"
            style="border:1px solid black;border-bottom:0px;font-size:20px;">
          <div style="text-align: center;">
            <strong style="font-size:24px;text-align: center;">{title}</strong>
          </div></td>
      </tr>
      <tr height="13">
        <td height="13" colspan="8" style="{_TD}">&nbsp;</td>
      </tr>

      <tr height="20">
        <td colspan="3" height="20"
            style="border:1px solid black;border-bottom:0px;">&nbsp; Supplier</td>
        <td colspan="2" style="{_TR}">Invoice No.</td>
        <td colspan="3" style="{_TR}">Dated</td>
      </tr>
      <tr height="20">
        <td colspan="3" height="20" style="{_LR}">&nbsp;
          <strong style="font-size: 18px;">M/s. {c_name}</strong></td>
        <td colspan="2" style="{_BR}"><b>{invid}</b></td>
        <td colspan="3" style="{_BR}"><b>{inv_date}</b></td>
      </tr>
      <tr height="24">
        <td colspan="3" height="24" style="{_LR}">&nbsp; {addr[0]}</td>
        <td colspan="2" style="{_R}">Buyer's Order No.</td>
        <td colspan="3" style="{_R}">Dated</td>
      </tr>
      <tr height="23">
        <td colspan="3" height="24" style="{_LR}padding-left:10px;">{addr[1]}</td>
        <td colspan="2" style="{_BR}">&nbsp;</td>
        <td colspan="3" style="{_BR}">&nbsp;</td>
      </tr>
      <tr height="23">
        <td colspan="3" height="24" style="{_LR}padding-left:10px;">{addr[2]}</td>
        <td colspan="2" style="{_R}">Dispatch through</td>
        <td colspan="3" style="{_R}">Mode/Terms of Payment</td>
      </tr>
      <tr height="23">
        <td colspan="3" height="24"
            style="{_LR}padding-left:10px;border-bottom:1px solid black;">
          {addr[3]}
          {f'<b>Mob:{mob}<b></b></b><br/>' if mob else ''}
          {tax_id}
        </td>
        <td colspan="2" style="{_BR}"><strong></strong></td>
        <td colspan="3" style="{_BR}"><b>NEFT</b></td>
      </tr>
      <tr style="border-left:1px solid black; border-bottom: 0px;">
        <td colspan="3" style="{_LR}padding-left:10px;">
          Buyer.<br/>
          <b>M/s. {company}</b><br/>
          {company_addr[0]}<br/>
          {company_addr[1]}
        </td>
        <td colspan="5" style="border-left:1px solid black;border-right:1px solid black;">Terms of Delivery</td>
      </tr>
      <tr height="23">
        <td colspan="3" height="23" style="{_LR}">
          <strong>&nbsp;&nbsp;<b>Mob:{company_mob}<b></b></b></strong></td>
        <td colspan="5" style="{_R}"><b></b></td>
      </tr>
      <tr height="23">
        <td colspan="3" height="23" style="{_LR}"><strong>&nbsp; {_h(company_gst)}</strong></td>
        <td colspan="5" style="{_R}"></td>
      </tr>
      <tr height="13">
        <td colspan="3" height="13" style="{_TB}"></td>
        <td height="15" colspan="5" style="{_BR}"><b></b></td>
      </tr>
    """)

    parts.append(f"""
      <tr height="35">
        <td height="35" width="38" style="{_TB}">
          <div align="center"><strong>Sr. No.</strong></div></td>
        <td colspan="2" style="{_BR}">
          <div align="center"><strong>Description of Goods</strong></div></td>
        <td style="{_BR}"><div align="center"><strong>HSN/SAC</strong></div></td>
        <td width="114" style="{_BR}"><div align="center"><strong>Quantity</strong></div></td>
        <td width="94" style="{_BR}"><div align="center"><strong>Rate</strong></div></td>
        <td width="37" style="{_BR}"><div align="center"><strong>per</strong></div></td>
        <td width="102" style="{_BR}"><div align="center"><strong>Amount</strong></div></td>
      </tr>
    """)

    parts.append(_build_item_rows(master, items, c_type, taxrate, taxamount,
                                  subtotal, totalamount, last_hsn))
    parts.append(_build_tax_summary(c_type, taxrate, taxamount, subtotal,
                                    totalamount, last_hsn))
    parts.append(
        f'<tr height="15">'
        f'<td colspan="8" height="20" style="{_LR}">&nbsp;</td>'
        f'</tr>')

    parts.append(
        f'<tr height="20">'
        f'<td colspan="8" height="20" style="{_LR}"><u>Declaration&nbsp;&nbsp;</u></td>'
        f'</tr>'
        f'<tr height="24">'
        f'<td height="24" colspan="4" style="{_L}">We    declare that this invoice shows the actual price of the&nbsp;</td>'
        f'<td colspan="4" style="border:1px solid black;border-bottom:0px;">'
        f'<div align="right" style="padding-right:10px;"><strong>for {c_name}</strong></div></td>'
        f'</tr>'
        f'<tr height="29">'
        f'<td height="29" colspan="3" style="{_L}">goods described and that all particulars are true and correct.</td>'
        f'<td>&nbsp;</td>'
        f'<td colspan="4" style="{_LR}"><div align="right"></div></td>'
        f'</tr>'
        f'<tr height="19">'
        f'<td height="19" colspan="4" style="{_LB}">&nbsp;</td>'
        f'<td colspan="4" style="border:1px solid black;border-top: 0px; padding-right:10px;">'
        f'<div align="right">Authorised    Signatory</div></td>'
        f'</tr>'
        f'<tr height="5">'
        f'<td colspan="8" height="5"><div align="center"></div></td>'
        f'</tr>'
        f'<tr height="20">'
        f'<td height="20" colspan="8"><div align="center">This is a Computer    Generated Invoice</div></td>'
        f'</tr>')

    parts.append("</table></page></body></html>")
    return "".join(parts)


# =========================================================================== #
# STYLED QUOTATION  (print quote.php / Dompdf view)
# =========================================================================== #
_QUOTATION_CSS = """
* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; }
body {
    background: #ffffff;
    font-family: Arial, Helvetica, sans-serif;
    color: #1f2937;
    font-size: 14px;
    line-height: 1.5;
}
.quotation-page {
    width: 100%;
    padding: 13mm 15mm 15mm 15mm;
    position: relative;
    background: linear-gradient(135deg, #ffffff 0%, #f8fbff 48%, #eef5ff 100%);
    border-top: 6px solid #172554;
}
.page-break { page-break-before: always; }

.company-header { width: 100%; padding-bottom: 10px; }
.company-logo img { display: block; width: 100%; max-width: 100%; height: auto; }
.header-line {
    width: 100%; height: 4px; margin-top: 10px;
    background: #2563eb; border-radius: 4px;
}
.quote-meta-table {
    width: 100%; border-collapse: collapse;
    margin-top: 14px; margin-bottom: 22px;
    font-size: 15px; line-height: 1.5; color: #111827;
}
.quote-meta-table td { padding: 0; vertical-align: middle; }
.quote-reference { text-align: left; width: 50%; }
.quote-date { text-align: right; width: 50%; }

.customer-details {
    width: 100%; margin-bottom: 25px;
    font-size: 15px; line-height: 1.55; color: #111827;
}
.to-label { margin-bottom: 3px; }
.customer-name-old { font-size: 15px; font-weight: bold; margin-bottom: 2px; }
.customer-address-old { font-size: 14px; line-height: 1.55; color: #374151; }

.attention {
    width: 100%; text-align: center; font-size: 15px; line-height: 1.5;
    margin-top: 8px; margin-bottom: 20px;
}

.subject-section { width: 100%; margin-top: 10px; margin-bottom: 22px; }
.subject-label {
    font-size: 11px; line-height: 1.4; color: #6b7280;
    text-transform: uppercase; letter-spacing: 0.7px;
    font-weight: bold; margin-bottom: 5px;
}
.subject { font-size: 16px; line-height: 1.4; font-weight: bold; color: #111827; }
.subject-line {
    width: 80px; height: 4px; margin-top: 8px;
    background: #2563eb; border-radius: 5px;
}
.introduction {
    margin-top: 10px; margin-bottom: 18px;
    font-size: 14px; line-height: 1.6; color: #374151;
}

.quotation-table {
    width: 100%; border-collapse: collapse;
    margin-top: 12px; border: 1px solid #cbd5e1;
    font-size: 13px; line-height: 1.45;
}
.quotation-table thead th {
    background: #172554; color: #ffffff; padding: 12px 10px;
    font-size: 11px; line-height: 1.4; text-transform: uppercase;
    letter-spacing: 0.5px; font-weight: bold; border: none;
}
.quotation-table tbody td {
    border-right: 1px solid #e5e7eb; border-bottom: 1px solid #e5e7eb;
    padding: 10px 9px; vertical-align: top; font-size: 13px; line-height: 1.45;
}
.quotation-table tbody tr:last-child td { border-bottom: none; }
.quotation-table tbody td:last-child { border-right: none; }
.quotation-table tbody tr.even-row { background: #eff6ff; }
.quotation-table tbody tr { page-break-inside: avoid; }
.sr { width: 7%; text-align: center; font-size: 13px; font-weight: bold; }
.description { width: 58%; }
.qty { width: 12%; text-align: center; }
.amount { width: 23%; text-align: right; }
.item-name {
    font-size: 14px; line-height: 1.4; font-weight: bold;
    color: #111827; margin-bottom: 8px;
}
.item-description { font-size: 13px; line-height: 1.45; }
.item-description ul { margin: 5px 0 0 18px; padding: 0; }
.item-description li {
    margin-bottom: 5px; font-size: 13px; line-height: 1.45; color: #4b5563;
}
.qty strong { font-size: 14px; line-height: 1.4; }
.qty-label { font-size: 10px; line-height: 1.3; color: #9ca3af; margin-top: 3px; }
.amount strong {
    font-size: 13px; line-height: 1.4; color: #111827; white-space: nowrap;
}

.totals-wrapper-table { width: 100%; border-collapse: collapse; margin-top: 14px; }
.totals-spacer { width: 60%; }
.totals-box { width: 40%; min-width: 260px; vertical-align: top; }
.totals-inner {
    width: 100%; border-collapse: collapse;
    border: 1px solid #cbd5e1; font-size: 13px;
}
.total-row td {
    padding: 9px 13px; border-bottom: 1px solid #e5e7eb;
    background: #ffffff; font-size: 13px; line-height: 1.4;
}
.total-label { color: #6b7280; font-weight: 600; text-align: left; }
.total-value { color: #111827; font-weight: bold; text-align: right; }
.grand-total-row td {
    padding: 12px 13px; background: #172554; color: #ffffff;
    font-size: 15px; line-height: 1.4; font-weight: bold; border-bottom: none;
}
.grand-total-row .total-value { color: #ffffff; font-size: 16px; }

.continued {
    margin-top: 35px; text-align: right;
    color: #6b7280; font-size: 12px; line-height: 1.4;
}

.section-title {
    font-size: 15px; line-height: 1.4; font-weight: bold;
    color: #172554; padding-bottom: 9px; margin-bottom: 15px;
    border-bottom: 3px solid #2563eb;
}

.product-image-box {
    text-align: left;
    padding: 10px 0 20px 25px;
    margin-bottom: 20px;
    background: transparent;
    page-break-inside: avoid;
}
.product-image-box img {
    display: block;
    width: 400px;
    height: 300px;
    object-fit: contain;
}
.product-image-name {
    font-size: 14px;
    line-height: 1.4;
    font-weight: bold;
    color: #111827;
    margin-top: 8px;
    margin-left: 30px;
}
.terms { margin-top: 22px; }
.terms p { margin: 8px 0; font-size: 14px; line-height: 1.55; color: #374151; }
.terms strong { color: #111827; }

.bank-section { margin-top: 25px; }
.bank-grid-table {
    width: 100%; border-collapse: separate; border-spacing: 0; margin-top: 12px;
}
.bank-card-cell { width: 50%; vertical-align: top; padding: 6px; }
.bank-card {
    border: 1px solid #cbd5e1; border-radius: 6px; padding: 12px;
    font-size: 13px; line-height: 1.7; background: #ffffff;
    page-break-inside: avoid;
}
.bank-name {
    font-size: 14px; line-height: 1.4; font-weight: bold;
    margin-bottom: 5px; color: #172554;
}
.bank-label { color: #6b7280; }

.closing {
    margin-top: 25px; font-size: 14px; line-height: 1.6; color: #374151;
}
.closing p { margin: 8px 0; }

.signature { margin-top: 25px; font-size: 14px; line-height: 1.6; }
.signature-line { margin: 12px 0; font-size: 18px; line-height: 1.4; color: #555; }
.signature-name { font-size: 14px; line-height: 1.5; font-weight: bold; color: #111827; }
.mobile { float: right; font-size: 14px; font-weight: bold; }

@page { size: A4; margin: 0; }
"""


def _split_lines(text, width=45):
    out = []
    for para in (str(text or "").splitlines() or [""]):
        out.extend(textwrap.wrap(para, width=width,
                                 break_long_words=True,
                                 break_on_hyphens=False) or [""])
    return out


def _quote_item_rows(items):
    extra_name = None
    extra_total = 0.0
    rows = []
    idx = 0

    extra_names = {"Courier", "Freight Charges", "Wooden Packing",
                   "Packing and forwarding"}

    for it in items:
        name = str(it.get("item_name") or "")
        if name in extra_names:
            extra_name = name
            try:
                extra_total = float(it.get("total") or 0)
            except (TypeError, ValueError):
                extra_total = 0.0
            continue

        idx += 1
        row_class = "even-row" if idx % 2 == 0 else ""

        # techs may come from the item OR be looked up from the product
        techs = str(it.get("techs") or "")
        if not techs:
            p = _lookup_product_by_name(name)
            if p:
                techs = str(p.get("techs") or "")

        features = [f.strip() for f in techs.split(";") if f.strip()]

        features_html = ""
        if features:
            lis = "".join(f"<li>{_h(f)}</li>" for f in features)
            features_html = (f'<div class="item-description">'
                             f'<ul>{lis}</ul></div>')

        qty = it.get("quantity")
        total = it.get("total")
        try:
            total_fmt = f"{float(total or 0):,.2f}"
        except (TypeError, ValueError):
            total_fmt = "0.00"

        rows.append(
            f'<tr class="{row_class}">'
            f'<td class="sr">{idx}</td>'
            f'<td class="description">'
            f'<div class="item-name">{_h(name)}</div>'
            f'{features_html}'
            f'</td>'
            f'<td class="qty"><strong>{_h(qty)}</strong>'
            f'<div class="qty-label">No.</div></td>'
            f'<td class="amount"><strong>&#8377; {total_fmt}</strong></td>'
            f'</tr>')

    return "".join(rows), extra_name, extra_total


def _quote_product_images(items, debug=False):
    """Build the product image boxes for page 2.

    If an item has no `img_loc`, we look up the matching product by name
    (via db_manager.list_products()) and use its img_loc.
    """
    boxes = []
    for it in items:
        name = it.get("item_name") or ""
        img = it.get("img_loc")

        # ---- fallback: lookup product by name ---------------------------
        if not img and name:
            p = _lookup_product_by_name(name)
            if p:
                img = p.get("img_loc")
                if debug:
                    print(f"[quote] resolved img_loc for {name!r} "
                          f"via product lookup -> {img!r}")

        if not img:
            if debug:
                print(f"[quote] no img_loc for {name!r}, skipping")
            continue

        path = _find_image(img, debug=debug, label=f"quote item={name!r}")
        if not path:
            continue
        uri = _img_data_uri(path)
        if not uri:
            continue
        boxes.append(
            f'<div class="product-image-box">'
            f'<img src="{uri}" alt="{_h(name)}"/>'
            f'<div class="product-image-name">{_h(name)}</div>'
            f'</div>')
    return "".join(boxes)


def _quote_bank_cards(banks):
    if not banks:
        return ""
    rows = []
    for i in range(0, len(banks), 2):
        pair = banks[i:i + 2]
        cells = []
        for b in pair:
            cells.append(
                f'<td class="bank-card-cell"><div class="bank-card">'
                f'<div><span class="bank-label">Account Name:</span> Codetech Engineers</div>'
                f'<div class="bank-name"><span class="bank-label">Bank Name:</span> '
                f'{_h(b.get("bname") or "")}</div>'
                f'<div><span class="bank-label">A/C No:</span> {_h(b.get("ac") or "")}</div>'
                f'<div><span class="bank-label">IFSC:</span> {_h(b.get("ifsc") or "")}</div>'
                f'<div><span class="bank-label">Branch:</span> {_h(b.get("branch") or "")}</div>'
                f'</div></td>')
        if len(pair) == 1:
            cells.append('<td class="bank-card-cell"></td>')
        rows.append(f'<tr>{"".join(cells)}</tr>')
    return "".join(rows)


def build_quotation_html(master, items, admin=None, banks=None,
                         cattype="", base_url="", debug=False):
    admin = admin or db_manager.get_admin() or {}
    if banks is None:
        banks = db_manager.get_banks() or []
    items = list(items or [])

    if debug:
        print("=" * 60)
        print(f"[quotation] build called with {len(items)} item(s)")
        for i, it in enumerate(items):
            print(f"[quotation]   item[{i}] keys     = {sorted(it.keys())}")
            print(f"[quotation]   item[{i}].img_loc  = {it.get('img_loc')!r}")
            print(f"[quotation]   item[{i}].item_name = {it.get('item_name')!r}")
        print("=" * 60)

    invid = _h(master.get("invid") or "")
    c_name = _h(master.get("c_name") or "")
    c_add = master.get("c_add") or ""
    quote_date = _dmy(master.get("created") or master.get("invdate"))
    taxrate = float(master.get("taxrate") or 18)
    taxamount = float(master.get("taxamount") or 0)
    totalamount = float(master.get("totalamount") or 0)

    logo_path = _find_image(_PRINT_STICKER["quote"], debug=debug, label="logo")
    logo_html = ""
    if logo_path:
        uri = _img_data_uri(logo_path)
        if uri:
            logo_html = f'<img src="{uri}" alt="CodeTech Engineers"/>'

    addr_lines = _split_lines(c_add, width=45)
    addr_html = "".join(f"{_h(line)}<br/>" for line in addr_lines if line.strip())

    items_html, extra_name, extra_total = _quote_item_rows(items)
    extra_row = ""
    if extra_name:
        extra_row = (
            f'<tr class="total-row">'
            f'<td class="total-label">{_h(extra_name)}</td>'
            f'<td class="total-value">&#8377; {extra_total:,.2f}</td>'
            f'</tr>')

    tax_row = (
        f'<tr class="total-row">'
        f'<td class="total-label">GST {taxrate:,.2f}%</td>'
        f'<td class="total-value">&#8377; {taxamount:,.2f}</td>'
        f'</tr>')

    grand_row = (
        f'<tr class="grand-total-row">'
        f'<td>TOTAL</td>'
        f'<td class="total-value">&#8377; {totalamount:,.2f}</td>'
        f'</tr>')

    product_images = _quote_product_images(items, debug=debug)
    bank_cards = _quote_bank_cards(banks)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Quotation - {invid}</title>
<style>{_QUOTATION_CSS}</style>
</head>
<body>

<!-- ===================== PAGE 1 ===================== -->
<div class="quotation-page">
  <div class="company-header">
    <div class="company-logo">{logo_html}</div>
    <div class="header-line"></div>
  </div>

  <table class="quote-meta-table">
    <tr>
      <td class="quote-reference"><strong>Ref.: {invid}</strong></td>
      <td class="quote-date"><strong>Date: {quote_date}</strong></td>
    </tr>
  </table>

  <div class="customer-details">
    <div class="to-label">To,</div>
    <div class="customer-name-old"><strong>M/s. {c_name}</strong></div>
    <div class="customer-address-old">{addr_html}</div>
  </div>

  <div class="attention"><strong>Kind Attn.: Mr.</strong></div>

  <div class="subject-section">
    <div class="subject-label">Subject</div>
    <div class="subject">Quotation for {_h(cattype)} Batch Coding Machines</div>
    <div class="subject-line"></div>
  </div>

  <div class="introduction">
    Dear Sir/Madam,
    <br/><br/>
    We are pleased to submit our quotation for the following
    batch coding machine as per your requirement.
  </div>

  <table class="quotation-table">
    <thead>
      <tr>
        <th class="sr">#</th>
        <th class="description">Description</th>
        <th class="qty">Qty.</th>
        <th class="amount">Amount<br/><small>EXW INR</small></th>
      </tr>
    </thead>
    <tbody>
      {items_html}
    </tbody>
  </table>

  <table class="totals-wrapper-table">
    <tr>
      <td class="totals-spacer"></td>
      <td class="totals-box">
        <table class="totals-inner">
          {extra_row}
          {tax_row}
          {grand_row}
        </table>
      </td>
    </tr>
  </table>

  <div class="continued"><strong>Continued on next page...</strong></div>
</div>

<!-- ===================== PAGE 2 ===================== -->
<div class="quotation-page page-break">

  <div class="section-title">Product Details</div>
  {product_images}

  <div class="terms">
    <div class="section-title">Terms &amp; Conditions</div>
    <p><strong>A.</strong> Above prices are Ex-Works Ahmedabad. Transportation charges are extra.</p>
    <p><strong>B. Payment Terms:</strong> 50% Advance along with confirmed P.O. and balance 50% against Proforma Invoice before dispatch after inspection.</p>
    <p><strong>C. Delivery:</strong> Within 3&ndash;4 weeks from the date of receipt of confirmed P.O. along with advance.</p>
    <p><strong>D. Installation:</strong> Installation will be provided free of cost from our side.</p>
    <p><strong>E.</strong> The design and prices are subject to change for any changes/additions in the above specifications.</p>
    <p><strong>F. Warranty:</strong> 1 year from the date of delivery against manufacturing defects. The warranty covers free replacement of defective parts, if any.</p>
    <p><strong>G.</strong> Order once placed cannot be cancelled under any circumstances. In case of cancellation, the entire amount of advance payment will stand forfeited.</p>
  </div>

  <div class="bank-section">
    <div class="section-title">Bank Details</div>
    <table class="bank-grid-table">{bank_cards}</table>
  </div>

  <div class="closing">
    <p>We hope that the above offer is technically in line with your requirement.</p>
    <p>Thanking you and looking forward to receiving your valuable Purchase Order.</p>
  </div>

  <div class="signature">
    <div>Yours truly,</div>
    <div style="margin-top:15px;"><strong>From CodeTech Engineers</strong></div>
    <div class="signature-line">-----sd------</div>
    <div class="signature-name">
      Kamlesh Chavda
      <span class="mobile">Mob.: +91-9737693302</span>
    </div>
  </div>

</div>

</body>
</html>
"""


# =========================================================================== #
# QUICK QUOTATION  (printquickq.php)
# =========================================================================== #
_QUICK_QUOTATION_CSS = """
* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; background: #ffffff; }
body {
    font-family: 'Segoe UI', Arial, Helvetica, sans-serif;
    color: #1f2937;
    font-size: 15px;
    line-height: 1.5;
}
page {
    background: #ffffff;
    display: block;
    margin: 0 auto;
    width: 21cm;
    min-height: 29.7cm;
    box-shadow: 0 0 0.5cm rgba(0,0,0,0.5);
    page-break-after: always;
}
page:last-child { page-break-after: auto; }

.qk-sticker {
    margin: 20px 0 0 20px;
    display: block;
    width: 100%;
    max-width: calc(100% - 40px);
    height: auto;
}
.qk-rule { border-bottom: 5px solid #000; width: 100%; }

.qk-ref-line {
    margin: 26px 0 0 52px;
    font-size: 15px;
    font-weight: bold;
}
.qk-ref-line .qk-date {
    float: right;
    margin-right: 60px;
    font-weight: bold;
    font-size: 15px;
}

.qk-to {
    margin: 26px 0 0 50px;
    font-size: 15px;
    line-height: 1.7;
}
.qk-to b { font-size: 15px; }

.qk-attn {
    text-align: center;
    font-size: 15px;
    margin: 22px 0 0 0;
    font-weight: bold;
}
.qk-sub {
    text-align: center;
    font-size: 15px;
    margin: 22px 0 0 0;
    font-weight: bold;
}
.qk-quote-for {
    margin: 22px 0 0 65px;
    font-size: 15px;
    font-weight: bold;
    text-decoration: underline;
}

.qk-table {
    border-collapse: collapse;
    margin: 22px 0 0 65px;
    width: calc(100% - 130px);
}
.qk-table, .qk-table td {
    border: 3px solid #000;
}
.qk-table td {
    padding: 6px 8px;
    vertical-align: top;
    font-size: 14px;
    line-height: 1.5;
}
.qk-table tr.qk-head td { text-align: center; height: 40px; }

.qk-desc-cell {
    padding: 10px 8px 10px 8px !important;
    height: 195px;
}
.qk-item-name {
    font-weight: bold;
    text-decoration: underline;
    display: inline-block;
    margin-bottom: 6px;
}
.qk-desc-cell ul {
    margin: 6px 0 0 22px;
    padding: 0;
}
.qk-desc-cell li {
    margin-bottom: 4px;
    line-height: 1.5;
    font-size: 14px;
}
.qk-qty-cell, .qk-amt-cell {
    text-align: center;
    font-weight: bold;
}
.qk-total-label {
    text-align: right;
    padding-right: 20px !important;
    font-weight: bold;
}
.qk-total-value {
    text-align: center;
    font-weight: bold;
}

.qk-continued {
    text-align: right;
    margin: 30px 70px 0 0;
    font-size: 15px;
    font-weight: bold;
}

.qk-product-title {
    margin: 30px 0 0 65px;
    font-size: 15px;
    font-weight: bold;
    text-decoration: underline;
}
.qk-product-img-box {
    margin: 25px 0 0 25px;
    display: inline-block;
    vertical-align: top;
}
.qk-product-img-box img {
    display: block;
    height: 300px;
    width: 400px;
    object-fit: contain;
}
.qk-product-img-name {
    margin: 8px 0 0 30px;
    font-size: 15px;
    font-weight: bold;
}

.qk-terms-title {
    margin: 30px 0 0 55px;
    font-size: 18px;
    font-weight: bold;
    text-decoration: underline;
}
.qk-terms {
    margin: 20px 40px 0 55px;
    font-size: 15px;
    line-height: 1.55;
}
.qk-terms p { margin: 6px 0; }

.qk-sign {
    margin: 30px 0 40px 70px;
    font-size: 15px;
    line-height: 1.6;
}
.qk-sign .qk-from { font-weight: bold; }
.qk-sign .qk-sd   { margin-left: 25px; }
.qk-sign .qk-name { font-weight: bold; }
.qk-sign .qk-mob  { float: right; margin-right: 10px; font-weight: bold; }

@page { size: A4; margin: 0; }
"""


def _quickq_items_from_master(master, items):
    if items:
        base = dict(items[0])
    else:
        base = {}

    for key in ("q_id", "name", "img_loc", "techs", "hsn", "mob",
                "quantity", "subtotal", "gst", "total", "created"):
        if not base.get(key) and master.get(key):
            base[key] = master[key]

    if not base.get("q_id"):
        base["q_id"] = master.get("invid") or master.get("q_id") or ""
    return base


def _quickq_tech_items(techs):
    text = str(techs or "")
    return [t.strip() for t in text.split(";") if t.strip()]


def build_quick_quotation_html(master, items, admin=None, banks=None,
                               cattype="", base_url="", debug=False):
    admin = admin or db_manager.get_admin() or {}
    if banks is None:
        banks = db_manager.get_banks() or []

    dv = _quickq_items_from_master(master, items)

    q_id = _h(dv.get("q_id") or "")
    name = _h(dv.get("name") or "")
    img_loc = str(dv.get("img_loc") or "").strip()
    techs = dv.get("techs") or ""

    # fallback: lookup product by name for img_loc / techs
    if (not img_loc or not techs) and name:
        p = _lookup_product_by_name(dv.get("name") or "")
        if p:
            if not img_loc:
                img_loc = str(p.get("img_loc") or "").strip()
            if not techs:
                techs = p.get("techs") or ""

    quantity = dv.get("quantity")
    subtotal = float(dv.get("subtotal") or 0)
    gst = float(dv.get("gst") or 0)
    total = float(dv.get("total") or 0)
    mob = _h(dv.get("mob") or "")
    today = _dmy(dv.get("created") or date.today())

    logo_path = _find_image(_PRINT_STICKER["quickq"], debug=debug, label="logo")
    logo_uri = _img_data_uri(logo_path) if logo_path else ""
    logo_html = (f'<img class="qk-sticker" src="{logo_uri}" alt="logo"/>'
                 if logo_uri else "")

    tech_items = _quickq_tech_items(techs)
    tech_lis = "".join(f"<li>{_h(t)}</li>" for t in tech_items)

    def _fmt_php(v):
        try:
            return f"{int(round(float(v or 0))):,}"
        except (TypeError, ValueError):
            return "0"

    qty_txt = f"{_h(quantity)} No." if quantity not in (None, "") else "No."
    subtotal_txt = f"{_fmt_php(subtotal)}=00"
    gst_txt = f"{_fmt_php(gst)}=00"
    total_txt = f"{_fmt_php(total)}=00"

    product_img_html = ""
    if img_loc:
        p = _find_image(img_loc, debug=debug, label=f"quickq={name!r}")
        uri = _img_data_uri(p) if p else None
        if uri:
            product_img_html = (
                f'<div class="qk-product-img-box">'
                f'<img src="{uri}" alt="{name}"/>'
                f'<div class="qk-product-img-name">{name}</div>'
                f'</div>')

    bank_rows = []
    bank_count = len(banks)
    for i in range(0, bank_count, 2):
        left = banks[i]
        right = banks[i + 1] if i + 1 < bank_count else None

        left_name = f'<b>Bank Name: </b>{_h(left.get("bname") or "")}'
        left_ac = f'<b>A/C No: </b>{_h(left.get("ac") or "")}'
        left_ifsc = (f'<b>IFSC Code: </b>{_h(left.get("ifsc") or "")}'
                     f' &amp; <b>Branch: </b>{_h(left.get("branch") or "")}')

        if right:
            right_name = f'<b>Bank Name: </b>{_h(right.get("bname") or "")}'
            right_ac = f'<b>A/C No: </b>{_h(right.get("ac") or "")}'
            right_ifsc = (f'<b>IFSC Code: </b>{_h(right.get("ifsc") or "")}'
                          f' &amp; <b>Branch: </b>{_h(right.get("branch") or "")}')
        else:
            right_name = right_ac = right_ifsc = ""

        bank_rows.append(
            f'<div style="display:flex; gap:20px;">'
            f'<div style="flex:1;">{left_name}</div>'
            f'<div style="flex:1;">{right_name}</div>'
            f'</div>'
            f'<div style="display:flex; gap:20px;">'
            f'<div style="flex:1;">{left_ac}</div>'
            f'<div style="flex:1;">{right_ac}</div>'
            f'</div>'
            f'<div style="display:flex; gap:20px;">'
            f'<div style="flex:1;">{left_ifsc}</div>'
            f'<div style="flex:1;">{right_ifsc}</div>'
            f'</div>')
    bank_html = "".join(bank_rows)

    page1 = f"""
    <page size="A4">
      {logo_html}
      <div class="qk-rule"></div>

      <p class="qk-ref-line">
        <b>Ref.: {q_id}</b>
        <span class="qk-date"><b>Date: {today}</b></span>
      </p>

      <p class="qk-to">
        To,<br/>
        <b>M/s.</b><br/>
        <b>{mob}</b>
      </p>

      <p class="qk-attn"><b>Kind Attn.: Mr.</b></p>

      <p class="qk-sub"><b>Sub.: Batch Coding Machines</b></p>

      <p class="qk-quote-for">
        <b>Quotation for {_h(cattype)} Batch Coding Machines</b>
      </p>

      <table class="qk-table">
        <tr class="qk-head">
          <td width="60"><strong>Sr. no.</strong></td>
          <td width="350"><strong>Description</strong></td>
          <td width="100"><strong>Qty.</strong></td>
          <td width="140"><strong>Total Amount</strong><br/>
                          <strong>EXW</strong><br/>
                          <strong>(INR)</strong></td>
        </tr>
        <tr>
          <td class="qk-qty-cell">1</td>
          <td class="qk-desc-cell">
            <span class="qk-item-name">{name}</span>
            <ul>{tech_lis}</ul>
          </td>
          <td class="qk-qty-cell">{qty_txt}</td>
          <td class="qk-amt-cell">{subtotal_txt}</td>
        </tr>
        <tr>
          <td colspan="3" class="qk-total-label"><b>GST 18%</b></td>
          <td class="qk-total-value">{gst_txt}</td>
        </tr>
        <tr>
          <td colspan="3" class="qk-total-label"><b>Total</b></td>
          <td class="qk-total-value">{total_txt}</td>
        </tr>
      </table>

      <p class="qk-continued"><b>Continued....</b></p>
    </page>
    """

    page2 = f"""
    <page size="A4">
      <div class="qk-product-title"><u>Product Image :</u></div>
      {product_img_html}

      <div class="qk-terms-title"><u>Terms and Conditions :</u></div>

      <div class="qk-terms">
        <p><strong>A.</strong> Above prices are Ex-works Ahmedabad. Transport Charges extra.</p>
        <p><strong>B. Payment Terms :</strong> 50% Advance along with confirmed P.O. &amp; balance 50 % against Proforma Invoice before dispatch after inspection.</p>
        <p><strong>C. Delivery: </strong> Within 3 -4 Weeks from the date of receipt of confirmed P.O. along with Advance.</p>
        <p><strong>D. Installation:</strong> It will be free of cost from our side.</p>
        <p><strong>E.</strong> The design and prices are subject to change for any changes/ additions in the above specifications.</p>
        <p><strong>F. Warranty: </strong> 1 Year from the date of delivery against any manufacturing defects. The warranty covers free replacement of defective part if any.</p>
        <p><strong>G.</strong> Order once placed cannot be cancelled under any circumstances. In case of order being cancelled, then the entire amount of Advance payment will stand as forfeited.</p>
        <p><strong>H. Bank Details</strong></p>
        {bank_html}
      </div>

      <div class="qk-sign">
        <p>We hope that the offer is technically in line with your requirement.</p>
        <p>Thanking you and looking for your valuable Purchase Order.</p>
        <p>Yours truly,</p>
        <p class="qk-from">From CodeTech Engineers,</p>
        <p class="qk-sd">-----sd------</p>
        <p><span class="qk-name">Kamlesh Chavda</span>
           <span class="qk-mob">Mob.: +91-9737693302</span></p>
      </div>
    </page>
    """

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Print Quick Quotation - {q_id}</title>
<style>{_QUICK_QUOTATION_CSS}</style>
</head>
<body>
{page1}
{page2}
</body>
</html>
"""


def _embed_sticker(html, doc):
    sticker = _PRINT_STICKER.get(doc)
    if not sticker:
        return html
    path = _find_image(sticker)
    if not path:
        return html
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("ascii")
    return html.replace(f'src="{sticker}"',
                        f'src="data:image/png;base64,{b64}"')


# --------------------------------------------------------------------------- #
# Print helper
# --------------------------------------------------------------------------- #
def _print_web_page(page, printer, parent=None):
    from PyQt6.QtCore import QEventLoop
    loop = QEventLoop()
    result = {"ok": False}

    def _done(success):
        result["ok"] = bool(success)
        loop.quit()

    page.print(printer, _done)
    loop.exec()


# --------------------------------------------------------------------------- #
# Public entry points
# --------------------------------------------------------------------------- #
def _build_html_for_doc(doc, master, items, cattype="", base_url="",
                        debug=False):
    if doc in ("tax", "proforma"):
        delivery = db_manager.get_delivery_address(master.get("invid"))
        return build_tax_invoice_html(
            doc, master, items,
            admin=db_manager.get_admin(),
            banks=db_manager.get_banks(),
            delivery=delivery)
    if doc == "purchase":
        return build_purchase_invoice_html(
            master, items, admin=db_manager.get_admin())
    if doc == "quote":
        return build_quotation_html(
            master, items,
            admin=db_manager.get_admin(),
            banks=db_manager.get_banks(),
            cattype=cattype,
            base_url=base_url,
            debug=debug)
    if doc == "quickq":
        return build_quick_quotation_html(
            master, items,
            admin=db_manager.get_admin(),
            banks=db_manager.get_banks(),
            cattype=cattype,
            base_url=base_url,
            debug=debug)
    return None


def _top_level_widget(widget):
    if widget is None:
        return None
    w = widget
    while w.parent() is not None:
        w = w.parent()
    return w


def show_invoice_view(parent, doc, master, items, title="", cattype="",
                      debug=False):
    if doc not in INVOICE_PRINT_DOCS:
        return False

    base_url = QUrl.fromLocalFile(_PYQT_BASE + os.sep).toString()
    try:
        html = _build_html_for_doc(doc, master, items,
                                   cattype=cattype, base_url=base_url,
                                   debug=debug)
    except Exception:
        traceback.print_exc()
        _msg("error", parent, "Error",
             "Failed to build the document HTML.\nSee the terminal for details.")
        return False

    if html is None:
        return False

    if doc in ("tax", "proforma"):
        html = _embed_sticker(html, doc)

    invid = str(master.get("invid") or master.get("q_id") or "").strip()

    top = _top_level_widget(parent) or parent

    dlg = QDialog(top)
    dlg.setWindowTitle(title or f"View - {_PRINT_TITLE.get(doc, 'Document')}"
                              f"{(' ' + invid) if invid else ''}")
    dlg.resize(950, 1000)
    dlg.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
    _brand(dlg)                                 # brand mark on the title bar

    lay = QVBoxLayout(dlg)
    lay.setContentsMargins(8, 8, 8, 8)
    lay.setSpacing(6)

    view = QWebEngineView(dlg)
    try:
        from PyQt6.QtWebEngineCore import QWebEngineSettings
        view.settings().setAttribute(
            QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls,
            True)
        view.settings().setAttribute(
            QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls,
            True)
    except Exception:
        pass

    view.setHtml(html, baseUrl=QUrl.fromLocalFile(_PYQT_BASE + os.sep))
    lay.addWidget(view, 1)

    bar = QHBoxLayout()
    bar.addStretch(1)

    pdf_btn = QPushButton("Save PDF")
    pdf_btn.setObjectName("btnDefault")
    pdf_btn.setEnabled(False)

    print_btn = QPushButton("Print")
    print_btn.setObjectName("btnPrimary")
    print_btn.setEnabled(False)

    close_btn = QPushButton("Close")
    close_btn.setObjectName("btnDefault")
    close_btn.clicked.connect(dlg.close)

    def _on_load_finished(ok):
        pdf_btn.setEnabled(ok)
        print_btn.setEnabled(ok)
        if debug:
            print(f"[view] WebEngine loadFinished: ok={ok}")

    view.loadFinished.connect(_on_load_finished)

    def _save_pdf():
        default = os.path.join(os.path.expanduser("~"),
                               f"{invid or doc}.pdf")
        fname, _ = QFileDialog.getSaveFileName(
            dlg, "Save as PDF", default, "PDF Files (*.pdf)")
        if not fname:
            return
        if not fname.lower().endswith(".pdf"):
            fname += ".pdf"
        page = view.page()
        page.pdfPrintingFinished.connect(
            lambda path, ok: _msg(
                "success" if ok else "error", dlg, "Save PDF",
                f"Saved to:\n{path}" if ok else "Failed to save PDF."))
        page.printToPdf(fname, QPageSize(QPageSize.PageSizeId.A4))

    def _print():
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
        printer.setPageMargins(QMarginsF(8, 6, 8, 6),
                               QPageLayout.Unit.Millimeter)
        preview = QPrintPreviewDialog(printer, dlg)
        preview.setWindowTitle("Print Preview")
        _brand(preview)                         # brand mark on the title bar
        preview.paintRequested.connect(
            lambda pr: _print_web_page(view.page(), pr, preview))
        preview.exec()

    pdf_btn.clicked.connect(_save_pdf)
    print_btn.clicked.connect(_print)

    bar.addWidget(pdf_btn)
    bar.addWidget(print_btn)
    bar.addWidget(close_btn)
    lay.addLayout(bar)

    if not hasattr(top, "_invoice_view_dialogs"):
        top._invoice_view_dialogs = []
    top._invoice_view_dialogs.append(dlg)

    def _forget(_obj=None, _top=top, _dlg=dlg):
        try:
            _top._invoice_view_dialogs.remove(_dlg)
        except (ValueError, AttributeError):
            pass
    dlg.destroyed.connect(_forget)

    dlg.show()
    return True


def show_quick_quotation_preview(parent, master, items=None, cattype="",
                                 debug=False):
    if items is None:
        items = []
    return show_invoice_view(parent, "quickq", master, items,
                             cattype=cattype, debug=debug)


def show_print_preview(parent, doc, master, items, cattype="", debug=False):
    if doc in INVOICE_PRINT_DOCS:
        return show_invoice_view(parent, doc, master, items,
                                 cattype=cattype, debug=debug)

    printer = QPrinter(QPrinter.PrinterMode.HighResolution)
    preview = QPrintPreviewDialog(printer, parent)
    preview.setWindowTitle("Print Preview")
    _brand(preview)                             # brand mark on the title bar
    doc_html = QTextDocument()
    doc_html.setHtml(build_invoice_html(doc, master, items))

    def render(printer_):
        doc_html.print_(printer_)

    preview.paintRequested.connect(render)
    preview.exec()


# --------------------------------------------------------------------------- #
# Ledger
# --------------------------------------------------------------------------- #
def build_ledger_html(client_name, fy, data, admin=None):
    from utils.helpers import money as _money
    admin = admin or db_manager.get_admin()
    fy_text = f"FY {data['start_year']} - {data['end_year']}"

    rows_html = ""
    for row in data["rows"]:
        if row["voucher_type"] == "Opening":
            rows_html += (
                f"<tr><td>{row['date']}</td><td>OPENING BALANCE</td>"
                f"<td>Opening</td><td align='right'></td><td align='right'></td>"
                f"<td align='right'>{_money(row['opening_bal'])}</td></tr>")
        elif row["voucher_type"] == "Total":
            rows_html += (
                "<tr style='background:#f0f4f8; font-weight:bold'>"
                "<td></td><td>TOTAL</td><td>Closing Balance</td>"
                f"<td align='right'>{_money(row['debit'])}</td>"
                f"<td align='right'>{_money(row['credit'])}</td>"
                f"<td align='right'>{_money(row['closing_bal'])}</td></tr>")
        else:
            debit = _money(row["debit"]) if row["debit"] else "-"
            credit = _money(row["credit"]) if row["credit"] else "-"
            rows_html += (
                f"<tr><td>{row['date']}</td><td>{row['ref']}</td>"
                f"<td>{row['voucher_type']}</td>"
                f"<td align='right'>{debit}</td>"
                f"<td align='right'>{credit}</td>"
                f"<td align='right'>{_money(row['closing_bal'])}</td></tr>")

    return f"""
    <html><body style="font-family:'Segoe UI'; font-size:10pt; color:#222;">
    <table width="100%" cellpadding="4">
      <tr>
        <td width="60%">
          <h2 style="margin:0">{admin.get('c_name', '')}</h2>
          <div>{admin.get('c_add', '')}</div>
          <div>Mobile: {admin.get('mob', '')}</div>
        </td>
        <td width="40%" align="right">
          <h1 style="margin:0; color:#3c8dbc">LEDGER STATEMENT</h1>
          <div style="font-size:12pt"><b>{client_name}</b></div>
          <div>{fy_text}</div>
        </td>
      </tr>
    </table>
    <hr/>
    <table width="100%" border="0.6" cellspacing="0" cellpadding="4"
           style="border-collapse:collapse">
      <tr style="background:#3c8dbc; color:#fff">
        <th>Date</th><th width="30%">Ref / Description</th><th>Voucher</th>
        <th>Debit</th><th>Credit</th><th>Balance</th>
      </tr>
      {rows_html}
    </table>
    </body></html>
    """


def show_ledger_print_preview(parent, client_name, fy, data):
    html = build_ledger_html(client_name, fy, data)
    printer = QPrinter(QPrinter.PrinterMode.HighResolution)
    preview = QPrintPreviewDialog(printer, parent)
    preview.setWindowTitle(f"Print Ledger - {client_name} ({fy})")
    _brand(preview)                             # brand mark on the title bar
    doc_html = QTextDocument()
    doc_html.setHtml(html)

    def render(printer_):
        doc_html.print_(printer_)

    preview.paintRequested.connect(render)
    preview.exec()