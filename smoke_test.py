"""Temporary smoke test: construct every page against the live DB (offscreen)."""
import sys, os, traceback

LOG = open(os.path.join(os.path.dirname(__file__), "smoke_result.txt"), "w",
           encoding="utf-8", buffering=1)


def log(*a):
    print(*a, file=LOG)
    print(*a)


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

sys.stdout.reconfigure(encoding="utf-8")

from PyQt6.QtCore import QCoreApplication, Qt
from PyQt6.QtWidgets import QApplication

# Same QtWebEngine requirement as main.py: the attribute has to be set before
# the QApplication exists, otherwise the invoice pages cannot be imported.
QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)

app = QApplication(sys.argv)

from database import db_manager
try:
    row = db_manager.authenticate("admin@gmail.com", "admin@123")
    log("AUTH:", "OK" if row else "FAILED")
    admin = row or {"id": 1, "name": "Test", "username": "x"}
except Exception as exc:
    log("DB not reachable, using dummy admin:", exc)
    admin = {"id": 1, "name": "Test", "username": "x"}

from ui.main_window import MainWindow
from ui.login_window import LoginWindow

# make error dialogs non-blocking during the smoke test
import ui.widgets as _W
_orig_err = _W.error


def _log_err(*a, **k):
    """Log UI errors; while inside an except block also log the traceback so
    page-level refresh failures are easy to locate."""
    log("UI ERROR DIALOG:", a)
    tb = traceback.format_exc()
    if tb and "Traceback" in tb:
        log(tb)


_W.error = _log_err
_W.confirm = lambda *a, **k: True

# ---- login window (construct + simulate a real login) ----
fired = []


def on_success(admin_row):
    fired.append(admin_row)


lw = LoginWindow(on_success)
lw.user_edit.edit.setText("admin@gmail.com")
lw.pass_edit.edit.setText("admin@123")
lw._login()
log("LOGIN FLOW:", "OK" if fired else "FAILED")

w = MainWindow(fired[0] if fired else admin)
log("MAIN WINDOW OK")

# layout check: header must span full width at top; sidebar at left below it
from PyQt6.QtWidgets import QFrame
w.resize(1360, 800)
w.show()
app.processEvents()
cw = w.centralWidget()
hdr = cw.findChild(QFrame, "HeaderBar")
side = cw.findChild(QFrame, "Sidebar")
side_pos = side.mapTo(cw, side.rect().topLeft())   # relative to central
log("HEADER geom:", hdr.geometry(), "central w:", cw.width())
log("SIDEBAR pos in central:", side_pos)
ok_header = (hdr.geometry().x() == 0 and hdr.geometry().y() == 0
             and hdr.geometry().width() >= cw.width() - 5)
ok_side = (side_pos.x() == 0 and side_pos.y() >= 52)
log("LAYOUT:", "OK (header top, sidebar left)" if ok_header and ok_side
    else "WRONG")

keys = ["dashboard", "clients", "suppliers", "products", "accounts",
        "account_types", "tax_gen", "tax_list", "proforma_list",
        "quote_list", "purchase_list", "purchase_gen", "quote_gen",
        "proforma_gen", "quickquote", "transaction", "sale_item_report",
        "sale_hsn_report", "sale_report", "purchase_item_report",
        "purchase_hsn_report", "purchase_report", "quote_item_report",
        "quote_report", "quickquote_report", "proforma_item_report",
        "proforma_report", "sales_prediction", "settings"]
failed = []
for key in keys:
    try:
        w.navigate(key)
        log("PAGE", key, "OK")
    except Exception:
        tb = traceback.format_exc()
        failed.append((key, tb))
        log("PAGE", key, "FAILED:")
        log(tb)

log("FAILED COUNT:", len(failed))

# ---- dashboard refresh regression check ----
# The dashboard builds its info boxes / recap box / donuts inside a
# QScrollArea.  If the scroll area is never wired into the page layout the
# child QLabels are orphaned and collected, which used to raise
# "wrapped C/C++ object of type QLabel has been deleted" on refresh().
try:
    dash = w._pages["dashboard"]
    dash.refresh()
    app.processEvents()
    app.processEvents()
    vals = [b.value_label.text() for b in dash.infoboxes.values()]
    log("DASHBOARD REFRESH: OK, info-box values =", vals)
    log("DASHBOARD INFOBOXES ALIVE:",
        "OK" if all(v not in (None, "") for v in vals) else "FAILED")
    # a second refresh must be equally stable (widgets reused, not rebuilt)
    dash.refresh()
    app.processEvents()
    log("DASHBOARD SECOND REFRESH: OK")
except Exception:
    log("DASHBOARD REFRESH FAILED:")
    log(traceback.format_exc())

# ---- pagination behaviour check (clients table) ----
# The master pages render their DataTables chrome through
# ui/pages/master_pages.py (DTTopBar / DTFooter / _TableState), i.e.
# cl.top.page_size, cl.footer and cl._state - NOT widgets.Paginator.  The
# buttons below are the real ones the user clicks.
from PyQt6.QtWidgets import QPushButton


def _flush():
    """Let queued repaints/layout passes settle before inspecting the table."""
    app.processEvents()
    app.processEvents()


def click_page_btn(footer, label):
    """Click the page button (~label~) that is currently painted.

    DTFooter._rebuild_nav() takes the stale buttons back out of its layout
    before adding the new ones, so scanning the layout only ever sees the
    buttons that are live right now.
    """
    for i in range(footer._nav.count()):
        wdg = footer._nav.itemAt(i).widget()
        if (isinstance(wdg, QPushButton) and wdg.text() == str(label)
                and wdg.isEnabled()):
            wdg.click()
            return True
    return False


cl = w._pages.get("clients")
if cl is not None and hasattr(cl, "footer"):
    _flush()
    cl.refresh()
    _flush()
    footer = cl.footer
    n_rows = cl.table.rowCount()
    sr1 = cl.table.item(0, 0).text() if n_rows else "(empty)"
    log(f"CLIENTS: {len(cl._rows)} records, page shows {n_rows} rows, "
        f"first Sr No = {sr1}, pages = {footer._total}")

    # 1) click the actual "2" button
    if click_page_btn(footer, 2):
        _flush()
        n2 = cl.table.rowCount()
        sr2 = cl.table.item(0, 0).text() if n2 else "(empty)"
        log(f"CLICK PAGE 2 -> shows {n2} rows, first Sr No = {sr2}, "
            f"active page = {footer._current}")
        log("CLICK PAGE 2 CHANGES DATA:",
            "OK" if sr2 != sr1 and sr2 == "11" else "FAILED")
    else:
        log("CLICK PAGE 2: button not found")

    # 2) click "3"
    if click_page_btn(footer, 3):
        _flush()
        sr3 = cl.table.item(0, 0).text() if cl.table.rowCount() else "(empty)"
        log(f"CLICK PAGE 3 -> first Sr No = {sr3}, "
            f"active page = {footer._current}")
        log("CLICK PAGE 3 CHANGES DATA:",
            "OK" if sr3 == "21" else "FAILED")

    # 3) click "1" to return
    if click_page_btn(footer, 1):
        _flush()
        sr_back = (cl.table.item(0, 0).text()
                   if cl.table.rowCount() else "(empty)")
        log(f"CLICK PAGE 1 -> first Sr No = {sr_back}")
        log("CLICK PAGE 1 CHANGES DATA:",
            "OK" if sr_back == "1" else "FAILED")

    # 4) Next / Prev buttons  ("\u00bb" = next, "\u00ab" = previous)
    before = footer._current
    if click_page_btn(footer, "\u00bb"):
        _flush()
        log("NEXT BUTTON:",
            "OK" if footer._current == before + 1 else "FAILED",
            f"(page {footer._current}, first Sr No = "
            f"{cl.table.item(0, 0).text()})")
    if click_page_btn(footer, "\u00ab"):
        _flush()
        log("PREV BUTTON:", "OK" if footer._current == before else "FAILED",
            f"(page {footer._current})")

    # 5) rows-per-page selector - the real "Show [N] entries" combo
    cl.top.page_size.setCurrentIndex(cl.top.page_size.findData(20))
    _flush()
    log("PER-PAGE=20 rows shown:", cl.table.rowCount())

    # 6) Last page
    if click_page_btn(footer, footer._total):
        _flush()
        log(f"LAST BUTTON -> page {footer._current} of {footer._total}, "
            f"rows = {cl.table.rowCount()}")
    else:
        log("LAST BUTTON: button not found")
else:
    log("PAGINATION CHECKS SKIPPED:",
        "no clients page" if cl is None
        else "ClientsPage has no DTFooter `footer` attribute")

# ---- Info pages (client / product / supplier) ----
try:
    clients = db_manager.list_clients("", 0)
    suppliers = db_manager.list_clients("", 1)
    products = db_manager.list_products()
    targets = [("client", clients[0]["cid"]), ("supplier", suppliers[0]["cid"]),
               ("product", products[0]["p_id"])]
    for kind, info_id in targets:
        w.open_info(kind, info_id)
        app.processEvents()
        app.processEvents()
        page = w._pages[f"info_{kind}_{info_id}"]
        doc = db_manager.INFO_DOCS[kind][0][0]
        entry = [e for e in page._docs if e[0] == doc][0]
        log(f"INFO {kind} #{info_id}: {len(entry[3])} invoice rows, table "
            f"{entry[1].rowCount()} visible, summary = "
            f"'{page.sub_label.text()[:70]}'")
        # info tables append a bold totals row (DataTable.apply_totals_row),
        # so the visible page slice is rowCount() - 1.
        expected = min(10, len(entry[3])) + 1
        log(f"INFO {kind} TABLES:",
            "OK" if entry[1].rowCount() == expected else "FAILED")
    log("INFO PAGES: OK")
except Exception:
    log("INFO PAGES FAILED:")
    log(traceback.format_exc())

log("SMOKE TEST DONE")
LOG.close()
