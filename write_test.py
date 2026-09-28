"""Temporary write-path test: insert -> read -> update -> delete a tax invoice.

Cleans up after itself (no test data left in the DB).
Logs to write_test_result.txt (line-buffered) to survive console issues.
"""
import os, traceback

LOG = open(os.path.join(os.path.dirname(__file__), "write_test_result.txt"),
           "w", buffering=1)


def log(*a):
    print(*a, file=LOG)
    print(*a)


from database import db_manager
from datetime import date

# silence modal dialogs (not needed here, but safe)
import ui.widgets  # noqa: F401  (ensures app modules import cleanly)

try:
    # pick any existing client
    clients = db_manager.list_clients()
    assert clients, "No clients in DB to test with"
    cid = clients[0]["cid"]

    orderid = "TESTORD001"
    invid = "TEST/INV/0001"

    # 1. clean any leftovers from a previous run
    db_manager.delete_invoice("tax", orderid)

    master = {"invid": invid, "cid": cid, "orderid": orderid,
              "totalitems": 2, "subtotal": 300, "taxrate": 18,
              "taxamount": 54, "totalamount": 354, "created": date.today()}
    items = [
        {"orderno": 1, "orderid": orderid, "item_name": "Test Item A",
         "item_desc": "desc A", "hsn": 8443, "quantity": 1, "price": 100,
         "total": 100},
        {"orderno": 2, "orderid": orderid, "item_name": "Test Item B",
         "item_desc": "desc B", "hsn": 8443, "quantity": 2, "price": 100,
         "total": 200},
    ]

    log("INSERT:", db_manager.insert_invoice("tax", master, items))

    m2, i2 = db_manager.get_invoice("tax", orderid)
    assert m2 and m2["invid"] == invid, "master read-back failed"
    assert len(i2) == 2, f"expected 2 items, got {len(i2)}"
    log("READ-BACK OK:", m2["invid"], m2["totalamount"],
        [it["item_name"] for it in i2])

    # 2. update: change tax rate, replace items
    master2 = dict(master, taxrate=12, taxamount=36, totalamount=336)
    items2 = [dict(items[0])]
    log("UPDATE:", db_manager.update_invoice("tax", orderid, master2, items2))
    m3, i3 = db_manager.get_invoice("tax", orderid)
    assert m3["taxrate"] == 12 and len(i3) == 1, "update failed"
    log("UPDATE OK: taxrate=", m3["taxrate"], "items=", len(i3))

    # 3. appears in list?
    lst = db_manager.list_invoices("tax", search=invid)
    assert any(r["orderid"] == orderid for r in lst), "list search failed"
    log("LIST SEARCH OK:", len(lst), "match(es)")

    # 4. item report includes it
    rep = db_manager.item_report("tax", item="Test Item A")
    assert any(r["invid"] == invid for r in rep), "item report failed"
    log("ITEM REPORT OK")

    # 5. cleanup
    log("DELETE:", db_manager.delete_invoice("tax", orderid))
    assert db_manager.get_invoice("tax", orderid)[0] is None, "delete failed"
    log("DELETE VERIFIED - no test data left")

    log("WRITE TEST: ALL OK")
except Exception:
    log(traceback.format_exc())
    log("WRITE TEST: FAILED")
    try:
        db_manager.delete_invoice("tax", "TESTORD001")
    except Exception:
        pass
LOG.close()
