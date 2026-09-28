"""
Data access layer - Python port of all CodeIgniter models.

Tables are the exact schema from db.sql:
  admin, client, clienttype, products, techsps, account, acc_type,
  bankdetails, paidhistory, invtest/invtest2 (tax), protest/protest2 (proforma),
  quote/quote2, purchaseinv/purchaseinv2, quickquote, delivery_addresses
"""
import pymysql

from datetime import date

from config import DB_CONFIG

_CONN = None


def get_connection():
    """Persistent shared connection (single-threaded UI): avoids the per-query
    connect cost that caused UI freezes; pings/reconnects transparently."""
    global _CONN
    if _CONN is not None:
        try:
            _CONN.ping(reconnect=True)
            return _CONN
        except Exception:
            try:
                _CONN.close()
            except Exception:
                pass
            _CONN = None
    _CONN = pymysql.connect(
        host=DB_CONFIG["host"],
        port=DB_CONFIG["port"],
        user=DB_CONFIG["user"],
        password=DB_CONFIG["password"],
        database=DB_CONFIG["database"],
        charset=DB_CONFIG["charset"],
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True,
        connect_timeout=3,
    )
    return _CONN


_INDEXES_READY = False
_INDEX_CACHE = {}  # (table, column) -> bool, avoids repeated I_S probes


def _indexed(columns=()):
    # True when ensure_dashboard_indexes() already created the given
    # (table, column) secondary indexes; else callers use Python-join fallback.
    # INFORMATION_SCHEMA probes are cached so each dashboard load pays ~1 probe
    # per column, not one per chart function.
    if not _INDEXES_READY:
        return False
    try:
        missing = [c for c in columns if c not in _INDEX_CACHE]
        if missing:
            placeholders = ",".join(["(%s,%s)"] * len(missing))
            rows = DB.query(
                "SELECT TABLE_NAME AS t, COLUMN_NAME AS c"
                " FROM INFORMATION_SCHEMA.STATISTICS"
                " WHERE TABLE_SCHEMA = DATABASE()"
                f" AND (TABLE_NAME, COLUMN_NAME) IN ({placeholders})",
                tuple(x for pair in missing for x in pair))
            have = {(r["t"], r["c"]) for r in rows}
            for c in missing:
                _INDEX_CACHE[c] = c in have
        return all(_INDEX_CACHE.get(c, False) for c in columns)
    except Exception:
        return True  # assume DDL path worked; SQL fallback raises if not


def ensure_dashboard_indexes():
    # The stock db.sql schema ships ONLY primary keys, so every dashboard
    # JOIN on invtest.orderid / invtest2.orderid / products.name /
    # invtest2.created full-scans. First dashboard load creates the missing
    # secondary indexes once (CREATE INDEX IF NOT EXISTS equivalent);
    # afterwards all chart queries run indexed in milliseconds.
    global _INDEXES_READY
    if _INDEXES_READY:
        return
    stmts = [
        ("invtest", "orderid",
         "CREATE INDEX ix_invtest_orderid ON invtest (orderid)"),
        ("invtest2", "orderid",
         "CREATE INDEX ix_invtest2_orderid ON invtest2 (orderid)"),
        ("invtest2", "created",
         "CREATE INDEX ix_invtest2_created ON invtest2 (created)"),
        ("products", "name",
         "CREATE INDEX ix_products_name ON products (name(191))"),
        # reminder-table joins (same no-index problem as invtest):
        ("protest", "orderid",
         "CREATE INDEX ix_protest_orderid ON protest (orderid)"),
        ("protest2", "orderid",
         "CREATE INDEX ix_protest2_orderid ON protest2 (orderid)"),
        ("protest2", "cid",
         "CREATE INDEX ix_protest2_cid ON protest2 (cid)"),
        ("quickquote", "p_id",
         "CREATE INDEX ix_quickquote_pid ON quickquote (p_id)"),
    ]
    for table, column, ddl in stmts:
        try:
            have = DB.query(
                "SELECT COUNT(*) AS n FROM INFORMATION_SCHEMA.STATISTICS"
                " WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s"
                " AND COLUMN_NAME = %s", (table, column))
            if have and int(have[0]["n"] or 0) == 0:
                DB.execute(ddl)
                _INDEX_CACHE[(table, column)] = True
            else:
                _INDEX_CACHE[(table, column)] = bool(
                    have and int(have[0]["n"] or 0) > 0)
        except Exception:
            pass  # best effort - charts have Python-join fallbacks
    _INDEXES_READY = True


class DB:
    """Thin static query helpers (one connection per call)."""

    @staticmethod
    def query(sql, params=None):
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute(sql, params or ())
            return cur.fetchall()

    @staticmethod
    def one(sql, params=None):
        rows = DB.query(sql, params)
        return rows[0] if rows else None

    @staticmethod
    def execute(sql, params=None, return_id=False):
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute(sql, params or ())
            conn.commit()
            return cur.lastrowid if return_id else cur.rowcount

    @staticmethod
    def scalar(sql, params=None, default=0):
        row = DB.one(sql, params)
        if not row:
            return default
        v = next(iter(row.values()), default)
        return v if v is not None else default


# ---------------------------------------------------------------------------
# Document registry (items/master tables per document type)
# ---------------------------------------------------------------------------
DOC_REGISTRY = {
    "tax":      {"items": "invtest",     "master": "invtest2",     "prefix": "INV",
                 "date_col": "created",  "label": "Tax Invoice",
                 "item_cols": ["orderno", "orderid", "item_name", "item_desc",
                               "hsn", "quantity", "price", "total"]},
    "proforma": {"items": "protest",     "master": "protest2",     "prefix": "PI",
                 "date_col": "created",  "label": "Proforma Invoice",
                 "item_cols": ["orderno", "orderid", "item_name", "item_desc",
                               "hsn", "quantity", "price", "total"]},
    "quote":    {"items": "quote",       "master": "quote2",       "prefix": "QT",
                 "date_col": "created",  "label": "Quotation",
                 "item_cols": ["orderno", "orderid", "item_name",
                               "quantity", "price", "total"]},
    "purchase": {"items": "purchaseinv", "master": "purchaseinv2", "prefix": "PUR",
                 "date_col": "invdate",  "label": "Purchase Invoice",
                 "item_cols": ["orderno", "orderid", "item_name", "item_desc",
                               "hsn", "quantity", "price", "total"]},
}


# ---------------------------------------------------------------------------
# Auth  (Login.php / admin table)
# ---------------------------------------------------------------------------
def authenticate(username, password):
    """Return admin row on success, else None (mirrors Login::userlogin)."""
    return DB.one("SELECT * FROM admin WHERE username=%s AND password=%s",
                  (username, password))


def get_admin(admin_id=1):
    return DB.one("SELECT * FROM admin WHERE id=%s", (admin_id,))


# ---------------------------------------------------------------------------
# Clients / Suppliers  (Client_model / Supplier_model - shared `client` table)
# ---------------------------------------------------------------------------
def get_client_types():
    return DB.query("SELECT id, type FROM clienttype ORDER BY id")


def list_clients(search="", u_type=None):
    """List clients filtered by user type.

    `u_type` may be:
        None                       -> all rows (no filter)
        int (0 / 1 / 2)            -> single type
        list / tuple / set of ints -> multiple types via IN (...)
                                      e.g. [0, 2]  Clients + Dual
                                           [1, 2]  Suppliers + Dual

    Used by the Manage-Clients / Suppliers pages, which both show their
    own type PLUS Dual (u_type = 2).
    """
    sql = "SELECT * FROM client"
    where, params = [], []

    if u_type is not None:
        if isinstance(u_type, (list, tuple, set)):
            types = list(u_type)
            if types:
                placeholders = ",".join(["%s"] * len(types))
                where.append(f"u_type IN ({placeholders})")
                params.extend(types)
        else:
            where.append("u_type=%s")
            params.append(u_type)

    if search:
        where.append(
            "(c_name LIKE %s OR mob LIKE %s OR gst LIKE %s OR c_add LIKE %s)")
        params += [f"%{search}%"] * 4

    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY cid DESC"
    return DB.query(sql, params)


def get_client(cid):
    return DB.one("SELECT * FROM client WHERE cid=%s", (cid,))


def insert_client(data):
    return DB.execute(
        "INSERT INTO client (c_name, c_add, mob, country, gst, email, c_type, u_type, created)"
        " VALUES (%(c_name)s, %(c_add)s, %(mob)s, %(country)s, %(gst)s, %(email)s,"
        " %(c_type)s, %(u_type)s, %(created)s)", data, return_id=True)


def update_client(cid, data):
    data = dict(data)
    data["cid"] = cid
    return DB.execute(
        "UPDATE client SET c_name=%(c_name)s, c_add=%(c_add)s, mob=%(mob)s,"
        " country=%(country)s, gst=%(gst)s, email=%(email)s, c_type=%(c_type)s,"
        " u_type=%(u_type)s WHERE cid=%(cid)s", data)


def delete_client(cid):
    return DB.execute("DELETE FROM client WHERE cid=%s", (cid,))


def get_next_client_id():
    return DB.scalar("SELECT COALESCE(MAX(cid), 0) + 1 FROM client")


# ---------------------------------------------------------------------------
# Products  (Product_model)
# ---------------------------------------------------------------------------
def list_products(search="", p_type=None):
    sql = "SELECT * FROM products"
    where, params = [], []
    if p_type:
        where.append("p_type=%s")
        params.append(p_type)
    if search:
        where.append("(name LIKE %s OR description LIKE %s OR hsn LIKE %s)")
        params += [f"%{search}%"] * 3
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY p_id DESC"
    return DB.query(sql, params)


def get_product(p_id):
    return DB.one("SELECT * FROM products WHERE p_id=%s", (p_id,))


def insert_product(data):
    return DB.execute(
        "INSERT INTO products (p_id, name, hsn, description, p_type, cattype,"
        " img_loc, techs, created)"
        " VALUES (%(p_id)s, %(name)s, %(hsn)s, %(description)s, %(p_type)s,"
        " %(cattype)s, %(img_loc)s, %(techs)s, %(created)s)", data, return_id=True)


def update_product(p_id, data):
    data = dict(data)
    data["p_id"] = p_id
    return DB.execute(
        "UPDATE products SET name=%(name)s, hsn=%(hsn)s,"
        " description=%(description)s, p_type=%(p_type)s, cattype=%(cattype)s,"
        " img_loc=%(img_loc)s, techs=%(techs)s WHERE p_id=%(p_id)s", data)


def delete_product(p_id):
    DB.execute("DELETE FROM techsps WHERE p_id=%s", (p_id,))
    return DB.execute("DELETE FROM products WHERE p_id=%s", (p_id,))


def get_next_product_id():
    return DB.scalar("SELECT COALESCE(MAX(p_id), 0) + 1 FROM products")


def get_techsps(p_id):
    return DB.query("SELECT * FROM techsps WHERE p_id=%s", (p_id,))


def insert_techsps(p_id, img_loc, techs, subcat):
    return DB.execute(
        "INSERT INTO techsps (p_id, img_loc, techs, subcat) VALUES (%s,%s,%s,%s)",
        (p_id, img_loc, techs, subcat), return_id=True)


def delete_techsps(tid):
    return DB.execute("DELETE FROM techsps WHERE tid=%s", (tid,))


# ---------------------------------------------------------------------------
# Invoices: Tax / Proforma / Quote / Purchase
# (Taxinv, Proinv, Quote, Purchaseinv controllers + their models)
# ---------------------------------------------------------------------------
def next_invoice_no(doc):
    """Replicates the FY-based generator, e.g. 'INV/24-25/0007'."""
    import datetime
    reg = DOC_REGISTRY[doc]
    today = datetime.date.today()
    if today.month > 3:
        fy = f"{today.year % 100:02d}-{today.year % 100 + 1:02d}"
        fy_start = datetime.date(today.year, 4, 1)
    else:
        fy = f"{today.year % 100 - 1:02d}-{today.year % 100:02d}"
        fy_start = datetime.date(today.year - 1, 4, 1)
    n = DB.scalar(f"SELECT COUNT(*) AS n FROM {reg['master']} WHERE created >= %s",
                  (fy_start,), default=0)
    if n == 0:
        n = DB.scalar(f"SELECT COUNT(*) AS n FROM {reg['master']}", (), default=0)
    return f"{reg['prefix']}/{fy}/{n + 1:04d}"


def insert_invoice(doc, master, items):
    """master: dict for master table; items: list of dicts for items table.

    Note: `orderno` is AUTO_INCREMENT in all items tables (db.sql) so it is
    never inserted - MySQL assigns it; the UI shows row numbers instead.
    """
    reg = DOC_REGISTRY[doc]
    orderid = master["orderid"]
    mcols = ", ".join(master.keys())
    mph = ", ".join(["%s"] * len(master))
    DB.execute(f"INSERT INTO {reg['master']} ({mcols}) VALUES ({mph})",
               tuple(master.values()))
    cols = [c for c in reg["item_cols"]
            if c in items[0] and c != "orderno"]
    icols = ", ".join(cols)
    iph = ", ".join(["%s"] * len(cols))
    for it in items:
        DB.execute(f"INSERT INTO {reg['items']} ({icols}) VALUES ({iph})",
                   tuple(it[c] for c in cols))
    if doc == "tax":
        invalidate_invtest_cache()
    return orderid


def update_invoice(doc, orderid, master, items):
    """Replaces all items for an invoice and updates the master row."""
    reg = DOC_REGISTRY[doc]
    sets = ", ".join(f"{k}=%s" for k in master if k != "orderid")
    params = [v for k, v in master.items() if k != "orderid"]
    DB.execute(f"UPDATE {reg['master']} SET {sets} WHERE orderid=%s",
               tuple(params) + (orderid,))
    DB.execute(f"DELETE FROM {reg['items']} WHERE orderid=%s", (orderid,))
    cols = [c for c in reg["item_cols"]
            if c in items[0] and c != "orderno"]
    icols = ", ".join(cols)
    iph = ", ".join(["%s"] * len(cols))
    for it in items:
        DB.execute(f"INSERT INTO {reg['items']} ({icols}) VALUES ({iph})",
                   tuple(it[c] for c in cols))
    if doc == "tax":
        invalidate_invtest_cache()
    return orderid


def delete_invoice(doc, orderid):
    reg = DOC_REGISTRY[doc]
    DB.execute(f"DELETE FROM {reg['items']} WHERE orderid=%s", (orderid,))
    if doc == "tax":
        invalidate_invtest_cache()
    return DB.execute(f"DELETE FROM {reg['master']} WHERE orderid=%s", (orderid,))


def get_invoice(doc, orderid):
    reg = DOC_REGISTRY[doc]
    master = DB.one(f"SELECT m.*, c.c_name, c.c_add, c.mob, c.gst, c.email,"
                    f" c.country, c.c_type"
                    f" FROM {reg['master']} m LEFT JOIN client c ON c.cid = m.cid"
                    f" WHERE m.orderid=%s", (orderid,))
    items = DB.query(f"SELECT * FROM {reg['items']} WHERE orderid=%s ORDER BY orderno",
                     (orderid,))
    return master, items


def get_delivery_address(invid):
    """`delivery_addresses` row for an invoice (Delivery_model::getdeliverydata).

    The original view matches on `invid` exactly, but the table stores the
    number with a leading space (' INV/24-25/00098'), so the comparison is
    trimmed here - otherwise the delivery block on the print view stays empty.
    """
    if not invid:
        return None
    return DB.one("SELECT * FROM delivery_addresses WHERE TRIM(invid)=TRIM(%s)"
                  " ORDER BY delid LIMIT 1", (invid,))


def list_invoices(doc, start_date=None, end_date=None, search="", client_id=None):
    reg = DOC_REGISTRY[doc]
    dc = reg["date_col"]
    sql = (f"SELECT m.*, c.c_name, c.mob, c.gst, c.c_add FROM {reg['master']} m"
           f" LEFT JOIN client c ON c.cid = m.cid")
    where, params = [], []
    if start_date:
        where.append(f"m.{dc} >= %s")
        params.append(start_date)
    if end_date:
        where.append(f"m.{dc} <= %s")
        params.append(end_date)
    if search:
        where.append("(m.invid LIKE %s OR c.c_name LIKE %s OR c.mob LIKE %s"
                     " OR c.gst LIKE %s OR c.c_add LIKE %s)")
        params += [f"%{search}%"] * 5
    if client_id:
        where.append("m.cid=%s")
        params.append(client_id)
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += f" ORDER BY m.{dc} DESC, m.orderid DESC"
    return DB.query(sql, params)


def get_items(doc, orderid):
    reg = DOC_REGISTRY[doc]
    return DB.query(f"SELECT * FROM {reg['items']} WHERE orderid=%s ORDER BY orderno",
                    (orderid,))


# ---------------------------------------------------------------------------
# Quick Quote  (Quickquote controller/model)
# ---------------------------------------------------------------------------
def next_quickquote_id():
    import datetime
    t = datetime.date.today()
    fy = (f"{t.year % 100:02d}-{t.year % 100 + 1:02d}" if t.month > 3
          else f"{t.year % 100 - 1:02d}-{t.year % 100:02d}")
    n = DB.scalar("SELECT COUNT(*) + 1 AS next_id FROM quickquote")
    return f"QUICKT/{fy}/{n:04d}"


def insert_quickquote(data):
    return DB.execute(
        "INSERT INTO quickquote (sr_no, q_id, p_id, mob, quantity, price, subtotal,"
        " gst, total, created) VALUES (NULL, %(q_id)s, %(p_id)s, %(mob)s,"
        " %(quantity)s, %(price)s, %(subtotal)s, %(gst)s, %(total)s,"
        " %(created)s)",
        data, return_id=True)


def list_quickquotes(start_date=None, end_date=None, search=""):
    sql = ("SELECT q.*, p.name AS product_name, p.hsn FROM quickquote q"
           " LEFT JOIN products p ON p.p_id = q.p_id")
    where, params = [], []
    if start_date:
        where.append("q.created >= %s")
        params.append(start_date)
    if end_date:
        where.append("q.created <= %s")
        params.append(end_date)
    if search:
        where.append("(p.name LIKE %s OR q.mob LIKE %s)")
        params += [f"%{search}%"] * 2
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY q.sr_no DESC"
    return DB.query(sql, params)


def get_quickquote(q_id):
    """One quick quote joined to its product - port of
    Quickquote_model::fulldata($id), which looks the record up by `q_id`."""
    return DB.one(
        "SELECT q.*, p.name AS product_name, p.hsn, p.img_loc, p.cattype"
        " FROM quickquote q LEFT JOIN products p ON p.p_id = q.p_id"
        " WHERE q.q_id=%s ORDER BY q.sr_no DESC LIMIT 1", (q_id,))


def delete_quickquote(sr_no):
    return DB.execute("DELETE FROM quickquote WHERE sr_no=%s", (sr_no,))


# ---------------------------------------------------------------------------
# Transactions / Payments  (Transaction controller -> paidhistory)
# ---------------------------------------------------------------------------
def list_transactions(start_date=None, end_date=None, search=""):
    sql = ("SELECT t.*, c.c_name, c.u_type FROM paidhistory t"
           " LEFT JOIN client c ON c.cid = t.cid")
    where, params = [], []
    if start_date:
        where.append("t.dateofpayment >= %s")
        params.append(start_date)
    if end_date:
        where.append("t.dateofpayment <= %s")
        params.append(end_date)
    if search:
        where.append("(c.c_name LIKE %s OR t.bank LIKE %s OR t.purpose LIKE %s"
                     " OR c.c_add LIKE %s)")
        params += [f"%{search}%"] * 4
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY t.dateofpayment DESC, t.created DESC"
    return DB.query(sql, params)


def insert_transaction(data):
    return DB.execute(
        "INSERT INTO paidhistory (pay_id, cid, amount, bank, dateofpayment, purpose,"
        " created) VALUES (%(pay_id)s, %(cid)s, %(amount)s, %(bank)s,"
        " %(dateofpayment)s, %(purpose)s, %(created)s)", data, return_id=True)


def update_transaction(pay_id, data):
    data = dict(data)
    data["pay_id"] = pay_id
    return DB.execute(
        "UPDATE paidhistory SET cid=%(cid)s, amount=%(amount)s, bank=%(bank)s,"
        " dateofpayment=%(dateofpayment)s, purpose=%(purpose)s WHERE pay_id=%(pay_id)s",
        data)


def delete_transaction(pay_id):
    return DB.execute("DELETE FROM paidhistory WHERE pay_id=%s", (pay_id,))


def next_transaction_id():
    n = DB.scalar("SELECT COUNT(*) + 1 AS n FROM paidhistory")
    return f"PAY/{n:04d}"


def get_banks():
    return DB.query("SELECT * FROM bankdetails ORDER BY bid")


# ---------------------------------------------------------------------------
# Accounts & Ledger  (Account controller / Account_model)
# ---------------------------------------------------------------------------
def get_account_types():
    return DB.query("SELECT * FROM acc_type ORDER BY id")


def list_accounts(search=""):
    sql = ("SELECT a.*, c.c_name, c.c_add, c.mob, c.gst, t.type AS acc_type_name"
           " FROM account a JOIN client c ON c.cid = a.cid"
           " LEFT JOIN acc_type t ON t.id = a.acc_type")
    params = []
    if search:
        sql += " WHERE (c.c_name LIKE %s OR c.mob LIKE %s OR c.c_add LIKE %s OR c.gst LIKE %s)"
        params = [f"%{search}%"] * 4
    sql += " ORDER BY a.aid DESC"
    return DB.query(sql, params)


def insert_account(data):
    return DB.execute(
        "INSERT INTO account (aid, cid, acc_type, opening_bal, created)"
        " VALUES (%(aid)s, %(cid)s, %(acc_type)s, %(opening_bal)s, %(created)s)",
        data, return_id=True)


def delete_account(aid):
    return DB.execute("DELETE FROM account WHERE aid=%s", (aid,))


def get_next_account_id():
    return DB.scalar("SELECT COALESCE(MAX(aid), 0) + 1 FROM account")


def _current_fy_range():
    """(start, end) dates of the running financial year (1 Apr - 31 Mar)."""
    t = date.today()
    y = t.year if t.month >= 4 else t.year - 1
    return f"{y}-04-01", f"{y + 1}-03-31"


def list_account_closing_balances():
    """Closing balance per account (aid -> float) for the CURRENT financial
    year only (1 Apr - 31 Mar), with the exact same sign convention as
    get_ledger_fy, driven by client.u_type:
      u_type 0 (Customer): opening + Sales(credit) - Receipts(debit)
      u_type 1 (Supplier): opening + Receipts(credit) - Purchases(debit)
      u_type 2 (Dual):     opening + Sales + Receipts - Purchases
    Opening balance is always account.opening_bal, as the ledger shows it.
    """
    d0, d1 = _current_fy_range()
    rows = DB.query(
        "SELECT a.aid, "
        "COALESCE(a.opening_bal, 0) + CASE c.u_type "
        "WHEN 0 THEN COALESCE(s.total, 0) - COALESCE(r.total, 0) "
        "WHEN 1 THEN COALESCE(r.total, 0) - COALESCE(p.total, 0) "
        "ELSE COALESCE(s.total, 0) + COALESCE(r.total, 0) - COALESCE(p.total, 0) "
        "END AS closing_bal "
        "FROM account a JOIN client c ON c.cid = a.cid "
        "LEFT JOIN (SELECT cid, SUM(totalamount) AS total FROM invtest2 "
        "           WHERE invtest2.created BETWEEN %s AND %s GROUP BY cid) s"
        "       ON s.cid = a.cid "
        "LEFT JOIN (SELECT cid, SUM(amount) AS total FROM paidhistory "
        "           WHERE paidhistory.dateofpayment BETWEEN %s AND %s GROUP BY cid) r"
        "       ON r.cid = a.cid "
        "LEFT JOIN (SELECT cid, SUM(totalamount) AS total FROM purchaseinv2 "
        "           WHERE purchaseinv2.invdate BETWEEN %s AND %s GROUP BY cid) p"
        "       ON p.cid = a.cid",
        (d0, d1, d0, d1, d0, d1))
    return {r["aid"]: float(r["closing_bal"] or 0) for r in rows}


def get_fys_for_client(cid):
    """Return distinct financial years (like '2024-2025') that have any
    transaction for this client, plus the latest detected FY (None if no data)."""
    sql = (
        "SELECT DISTINCT "
        "CASE WHEN MONTH(t) >= 4 "
        "THEN CONCAT(YEAR(t), '-', YEAR(t)+1) "
        "ELSE CONCAT(YEAR(t)-1, '-', YEAR(t)) END AS fy "
        "FROM ("
        "  SELECT created AS t FROM invtest2 WHERE cid=%s "
        "  UNION ALL SELECT invdate AS t FROM purchaseinv2 WHERE cid=%s "
        "  UNION ALL SELECT dateofpayment AS t FROM paidhistory WHERE cid=%s"
        ") AS u ORDER BY fy DESC")
    rows = DB.query(sql, (cid, cid, cid))
    fys = [r["fy"] for r in rows]
    latest = fys[0] if fys else None
    return fys, latest


def get_client_u_type(cid):
    """Return the u_type (0=Customer, 1=Supplier, 2=Dual) for a client."""
    row = DB.one("SELECT u_type FROM client WHERE cid=%s", (cid,))
    return int(row["u_type"]) if row else 0


def get_ledger_fy(cid, fy, u_type=None):
    """Ledger for one financial year, matching Account.php getLedgerByFY / getLedgerDetails.
              1=Purchase+Receipts (Purchase=debit, Receipt=credit),
              2=Complete (Sales=credit, Purchase=debit, Receipt=credit).
              If None, fetched from client.u_type.
    """
    if u_type is None:
        u_type = get_client_u_type(cid)
    start_year, end_year = fy.split("-")
    start_date = f"{start_year}-04-01"
    end_date = f"{end_year}-03-31"
    opening = float(
        DB.one("SELECT COALESCE(opening_bal, 0) AS opening_bal FROM account WHERE cid=%s",
               (cid,))["opening_bal"] or 0)

    if u_type == 0:
        # Sales = Credit, Receipts = Debit  (Sales and Receipts Ledger)
        rows = DB.query(
            "SELECT "
            "  CASE WHEN X.voucher_type='Receipt' THEN (@s := @s + 1) "
            "       ELSE CONCAT(X.invoice_details, '+', COALESCE(X.orderid, 'N/A')) END AS ref, "
            "  X.debit, X.credit, X.created, X.voucher_type "
            "FROM ("
            "  SELECT invtest2.orderid, invtest2.invid AS invoice_details, "
            "         NULL AS debit, invtest2.totalamount AS credit, "
            "         invtest2.created, 'Sales' AS voucher_type "
            "  FROM invtest2 WHERE invtest2.cid=%s AND invtest2.created BETWEEN %s AND %s "
            "  UNION ALL "
            "  SELECT NULL, NULL, paidhistory.amount, NULL, "
            "         paidhistory.dateofpayment, 'Receipt' "
            "  FROM paidhistory WHERE paidhistory.cid=%s "
            "    AND paidhistory.dateofpayment BETWEEN %s AND %s"
            ") AS X, (SELECT @s := 0) AS init "
            "ORDER BY X.created ASC",
            (cid, start_date, end_date, cid, start_date, end_date))
    elif u_type == 1:
        # Purchases = Debit, Receipts = Credit  (Purchase and Receipts Ledger)
        rows = DB.query(
            "SELECT "
            "  CASE WHEN X.voucher_type='Receipt' THEN (@s := @s + 1) "
            "       ELSE COALESCE(CONCAT(X.invoice_details, '+', X.orderid), 'N/A') END AS ref, "
            "  X.debit, X.credit, X.created, X.voucher_type "
            "FROM ("
            "  SELECT purchaseinv2.orderid, purchaseinv2.invid AS invoice_details, "
            "         purchaseinv2.totalamount AS debit, NULL AS credit, "
            "         purchaseinv2.invdate AS created, 'Purchase' AS voucher_type "
            "  FROM purchaseinv2 WHERE purchaseinv2.cid=%s "
            "    AND purchaseinv2.invdate BETWEEN %s AND %s "
            "  UNION ALL "
            "  SELECT NULL, NULL, NULL AS debit, "
            "         COALESCE(paidhistory.amount, 0) AS credit, "
            "         paidhistory.dateofpayment, 'Receipt' "
            "  FROM paidhistory WHERE paidhistory.cid=%s "
            "    AND paidhistory.dateofpayment BETWEEN %s AND %s"
            ") AS X, (SELECT @s := 0) AS init "
            "ORDER BY X.created ASC",
            (cid, start_date, end_date, cid, start_date, end_date))
    else:
        # u_type == 2 : Complete Ledger (Sales=credit, Purchase=debit, Receipt=credit)
        rows = DB.query(
            "SELECT "
            "  CASE WHEN X.voucher_type='Receipt' THEN (@s := @s + 1) "
            "       WHEN X.voucher_type IN ('Sales', 'Purchase') "
            "       THEN CONCAT(COALESCE(X.invoice_details, 'N/A'), '+', "
            "                   COALESCE(X.orderid, 'N/A')) "
            "       ELSE X.invoice_details END AS ref, "
            "  X.debit, X.credit, X.created, X.voucher_type "
            "FROM ("
            "  SELECT invtest2.orderid, invtest2.invid AS invoice_details, "
            "         NULL AS debit, invtest2.totalamount AS credit, "
            "         invtest2.created, 'Sales' AS voucher_type "
            "  FROM invtest2 WHERE invtest2.cid=%s AND invtest2.created BETWEEN %s AND %s "
            "  UNION ALL "
            "  SELECT purchaseinv2.orderid, purchaseinv2.invid, "
            "         purchaseinv2.totalamount, NULL, "
            "         purchaseinv2.invdate, 'Purchase' "
            "  FROM purchaseinv2 WHERE purchaseinv2.cid=%s "
            "    AND purchaseinv2.invdate BETWEEN %s AND %s "
            "  UNION ALL "
            "  SELECT NULL, NULL, NULL, "
            "         COALESCE(paidhistory.amount, 0), "
            "         paidhistory.dateofpayment, 'Receipt' "
            "  FROM paidhistory WHERE paidhistory.cid=%s "
            "    AND paidhistory.dateofpayment BETWEEN %s AND %s"
            ") AS X, (SELECT @s := 0) AS init "
            "ORDER BY X.created ASC",
            (cid, start_date, end_date,
             cid, start_date, end_date,
             cid, start_date, end_date))

    ledger_rows = []
    # first row: opening balance
    ledger_rows.append({
        "ref": "OPENING BALANCE", "debit": 0.0, "credit": 0.0,
        "date": start_date, "voucher_type": "Opening",
        "opening_bal": opening, "closing_bal": opening,
    })

    total_debit = 0.0
    total_credit = 0.0
    balance = opening
    for r in rows:
        debit = float(r["debit"] or 0)
        credit = float(r["credit"] or 0)
        total_debit += debit
        total_credit += credit
        balance = balance + credit - debit
        ledger_rows.append({
            "ref": r["ref"], "debit": debit, "credit": credit,
            "date": r["created"], "voucher_type": r["voucher_type"],
            "opening_bal": None, "closing_bal": balance,
        })

    # footer row: totals + closing balance
    ledger_rows.append({
        "ref": "Closing Balance", "debit": total_debit, "credit": total_credit,
        "date": None, "voucher_type": "Total",
        "opening_bal": None, "closing_bal": balance,
    })

    return {
        "fy": fy,
        "start_year": start_year,
        "end_year": end_year,
        "opening_balance": opening,
        "total_credit": total_credit,
        "total_debit": total_debit,
        "closing_balance": balance,
        "rows": ledger_rows,
        "u_type": u_type,
    }


# ---------------------------------------------------------------------------
# Reports (Sales / Purchase / Quotation - item, HSN & summary variants)
# ---------------------------------------------------------------------------
def item_report(doc, start_date=None, end_date=None, item=None):
    """Item-wise report: items joined to master (Sale/Purchase/Quote Item Report)."""
    reg = DOC_REGISTRY[doc]
    dc = reg["date_col"]
    sel_desc = ("i.item_desc," if "item_desc" in reg["item_cols"]
                else "'' AS item_desc,")
    sel_hsn = ("i.hsn," if "hsn" in reg["item_cols"] else "8443 AS hsn,")
    sql = (f"SELECT i.item_name, {sel_desc} {sel_hsn} i.quantity, i.price,"
           f" (i.quantity * i.price) AS subtotal, m.invid, c.c_name,"
           f" m.{dc} AS doc_date, m.taxrate, m.taxamount, m.totalamount"
           f" FROM {reg['items']} i JOIN {reg['master']} m ON m.orderid = i.orderid"
           f" LEFT JOIN client c ON c.cid = m.cid")
    where, params = [], []
    if start_date:
        where.append(f"m.{dc} >= %s")
        params.append(start_date)
    if end_date:
        where.append(f"m.{dc} <= %s")
        params.append(end_date)
    if item:
        where.append("i.item_name LIKE %s")
        params.append(f"%{item}%")
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY m.orderid DESC"
    return DB.query(sql, params)


def hsn_report(doc, start_date=None, end_date=None):
    reg = DOC_REGISTRY[doc]
    dc = reg["date_col"]
    sql = (f"SELECT i.hsn, SUM(i.quantity) AS quantity, SUM(i.price) AS price,"
           f" SUM(i.quantity * i.price) AS subtotal"
           f" FROM {reg['items']} i JOIN {reg['master']} m ON m.orderid = i.orderid")
    where, params = [], []
    if start_date:
        where.append(f"m.{dc} >= %s")
        params.append(start_date)
    if end_date:
        where.append(f"m.{dc} <= %s")
        params.append(end_date)
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " GROUP BY i.hsn ORDER BY i.hsn"
    return DB.query(sql, params)


def quickquote_report(start_date=None, end_date=None):
    sql = ("SELECT q.q_id, p.name AS product_name, q.mob, q.quantity, q.price,"
           " q.subtotal, q.gst, q.total, q.created"
           " FROM quickquote q LEFT JOIN products p ON p.p_id = q.p_id")
    where, params = [], []
    if start_date:
        where.append("q.created >= %s")
        params.append(start_date)
    if end_date:
        where.append("q.created <= %s")
        params.append(end_date)
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY q.created DESC"
    return DB.query(sql, params)


# ---------------------------------------------------------------------------
# Dashboard  (Dashboard controller / StatisticsModel)
# ---------------------------------------------------------------------------
def dashboard_stats():
    s = {}
    s["clients"] = DB.scalar("SELECT COUNT(*) AS n FROM client WHERE u_type=0")
    s["suppliers"] = DB.scalar("SELECT COUNT(*) AS n FROM client WHERE u_type=1")
    s["products"] = DB.scalar("SELECT COUNT(*) AS n FROM products")
    s["tax_invoices"] = DB.scalar("SELECT COUNT(*) AS n FROM invtest2")
    s["quotations"] = DB.scalar("SELECT COUNT(*) AS n FROM quote2")
    s["proforma"] = DB.scalar("SELECT COUNT(*) AS n FROM protest2")
    s["purchases"] = DB.scalar("SELECT COUNT(*) AS n FROM purchaseinv2")
    s["sales_amount"] = float(DB.scalar("SELECT COALESCE(SUM(totalamount),0) AS n FROM invtest2"))
    s["purchase_amount"] = float(DB.scalar("SELECT COALESCE(SUM(totalamount),0) AS n FROM purchaseinv2"))
    s["received_amount"] = float(DB.scalar("SELECT COALESCE(SUM(amount),0) AS n FROM paidhistory"))
    s["quotes_amount"] = float(DB.scalar("SELECT COALESCE(SUM(totalamount),0) AS n FROM quote2"))
    return s


def recent_invoices(doc, limit=8):
    reg = DOC_REGISTRY[doc]
    dc = reg["date_col"]
    return DB.query(
        f"SELECT m.invid, c.c_name, m.{dc} AS doc_date, m.totalitems,"
        f" m.subtotal, m.taxrate, m.taxamount, m.totalamount"
        f" FROM {reg['master']} m LEFT JOIN client c ON c.cid = m.cid"
        f" ORDER BY m.{dc} DESC, m.orderid DESC LIMIT %s", (limit,))


def monthly_sales(table_master, date_col, year=None):
    import datetime
    y = year or datetime.date.today().year
    rows = DB.query(
        f"SELECT DATE_FORMAT({date_col}, '%%Y-%%m') AS ym, SUM(totalamount) AS amt"
        f" FROM {table_master} WHERE YEAR({date_col}) = %s GROUP BY ym", (y,))
    m = {r["ym"]: float(r["amt"]) for r in rows}
    return [m.get(f"{y}-{mm:02d}", 0.0) for mm in range(1, 13)]


# --- Donut chart sources (StatisticsModel) -------------------------------
MORRIS_COLORS = ["#0b62a4", "#7a92a3", "#a90329", "#f8b333", "#4da74d",
                 "#afd8f8", "#edc240", "#cb4b16", "#9440ac", "#6b6ecf"]

_JOIN_IX = (("invtest", "orderid"), ("invtest2", "orderid"),
             ("invtest2", "created"), ("products", "name"))


def donut_consumables(start_year, end_year):
    # consumablescount - Consumables qty sold in FY.
    d0, d1 = f"{start_year}-04-01", f"{end_year}-03-31"
    if _indexed(_JOIN_IX):
        try:
            return DB.query(
                "SELECT invtest.item_name AS label, SUM(invtest.quantity) AS value"
                " FROM invtest INNER JOIN invtest2 ON invtest.orderid = invtest2.orderid"
                " INNER JOIN products ON invtest.item_name = products.name"
                " WHERE products.p_type = 'Consumables'"
                " AND invtest2.created BETWEEN %s AND %s"
                " GROUP BY invtest.item_name ORDER BY value DESC LIMIT 6",
                (d0, d1))
        except Exception:
            pass
    # Fallback (no indexes yet / DDL blocked): Python join over cached lines.
    ids = {r["orderid"] for r in DB.query(
        "SELECT orderid FROM invtest2 WHERE created BETWEEN %s AND %s", (d0, d1))}
    if not ids:
        return []
    cons = {r["name"] for r in DB.query(
        "SELECT name FROM products WHERE p_type = 'Consumables'")}
    if not cons:
        return []
    agg = {}
    for ln in _invtest_lines():
        if ln["orderid"] in ids and ln["item_name"] in cons:
            agg[ln["item_name"]] = agg.get(ln["item_name"], 0) + (
                int(ln.get("quantity") or 0))
    return [{"label": k, "value": v}
            for k, v in sorted(agg.items(), key=lambda kv: kv[1],
                               reverse=True)[:6]]


def donut_product_category(start_year, end_year):
    # productcategorycount2 - top Machine products sold in FY (by line count).
    d0, d1 = f"{start_year}-04-01", f"{end_year}-03-31"
    if _indexed(_JOIN_IX):
        try:
            return DB.query(
                "SELECT invtest.item_name AS label, COUNT(invtest.item_name) AS value"
                " FROM invtest INNER JOIN invtest2 ON invtest.orderid = invtest2.orderid"
                " INNER JOIN products ON invtest.item_name = products.name"
                " WHERE products.p_type = 'Machine'"
                " AND invtest2.created BETWEEN %s AND %s"
                " GROUP BY invtest.item_name ORDER BY value DESC LIMIT 5",
                (d0, d1))
        except Exception:
            pass
    # Fallback: Python join over cached lines.
    ids = {r["orderid"] for r in DB.query(
        "SELECT orderid FROM invtest2 WHERE created BETWEEN %s AND %s", (d0, d1))}
    if not ids:
        return []
    mach = {r["name"] for r in DB.query(
        "SELECT name FROM products WHERE p_type = 'Machine'")}
    if not mach:
        return []
    agg = {}
    for ln in _invtest_lines():
        if ln["orderid"] in ids and ln["item_name"] in mach:
            agg[ln["item_name"]] = agg.get(ln["item_name"], 0) + 1
    return [{"label": k, "value": v}
            for k, v in sorted(agg.items(), key=lambda kv: kv[1],
                               reverse=True)[:5]]


def donut_user_category():
    # usercategoryCount - GST / PAN / Adhaar / TIN split
    return DB.query(
        "SELECT CASE WHEN CHAR_LENGTH(gst) = 15 THEN 'GST'"
        " WHEN CHAR_LENGTH(gst) IN (10, 9) THEN 'PAN'"
        " WHEN CHAR_LENGTH(gst) = 12 THEN 'Adhaar' ELSE 'TIN' END AS label,"
        " COUNT(*) AS value FROM client GROUP BY label")


def donut_client_country():
    return DB.query(
        "SELECT country AS label, COUNT(*) AS value FROM client"
        " GROUP BY country")


def donut_billed_clients():
    # docCount - billed vs non-billed clients
    return DB.query(
        "SELECT CASE WHEN t2.cid IS NULL THEN 'Non-Billed Clients'"
        " ELSE 'Billed Clients' END AS label, COUNT(*) AS value"
        " FROM client t1 LEFT JOIN invtest2 t2 ON t1.cid = t2.cid"
        " GROUP BY label")


def donut_doc_count(start_year, end_year):
    # doczCount - documents created in FY. NOTE: the old UNION+WHERE only
    # filtered the LAST leg (quickquote); each leg needs its own date filter.
    d0, d1 = f"{start_year}-04-01", f"{end_year}-03-31"
    rows = DB.query(
        "SELECT 'Proforma Invoice' AS label, COUNT(invid) AS value FROM protest2"
        " WHERE created BETWEEN %s AND %s"
        " UNION ALL SELECT 'Tax Invoice', COUNT(invid) FROM invtest2"
        " WHERE created BETWEEN %s AND %s"
        " UNION ALL SELECT 'Quotation', COUNT(invid) FROM quote2"
        " WHERE created BETWEEN %s AND %s"
        " UNION ALL SELECT 'Quick Quotation', COUNT(q_id) FROM quickquote"
        " WHERE created BETWEEN %s AND %s",
        (d0, d1, d0, d1, d0, d1, d0, d1))
    return sorted(rows, key=lambda r: int(r["value"] or 0), reverse=True)


def donut_client_type():
    # getclienttypecount
    return DB.query(
        "SELECT CASE WHEN u_type = 0 THEN 'Client' WHEN u_type = 1 THEN 'Supplier'"
        " WHEN u_type = 2 THEN 'Dual (Cust/Sup)' ELSE 'Unknown' END AS label,"
        " COUNT(*) AS value FROM client GROUP BY u_type")


_INVTEST_CACHE = None
_INVTEST_TS = 0
_INVTEST_TTL = 600  # 10 min: invtest lines only change via invoice edits


def _invtest_lines():
    # Narrow (orderid,item_name,quantity,price) scan shared by chart fallbacks.
    global _INVTEST_CACHE, _INVTEST_TS
    import time
    now = time.time()
    if _INVTEST_CACHE is None or now - _INVTEST_TS > _INVTEST_TTL:
        _INVTEST_CACHE = DB.query(
            "SELECT orderid, item_name, quantity, price FROM invtest")
        _INVTEST_TS = now
    return _INVTEST_CACHE


def invalidate_invtest_cache():
    global _INVTEST_CACHE, _INVTEST_TS
    _INVTEST_CACHE, _INVTEST_TS = None, 0


# --- Bar charts (StatisticsModel allyearsalesdata / allyeardata) ---------
def fy_sales_chart(start_year, end_year):
    # allyearsalesdata: monthly Turnover/Tax + top Machine item per month (FY).
    # Fast SQL path when dashboard indexes exist; Python-join fallback when
    # DDL was blocked. Top Machine item per month = highest SUM(qty).
    d0, d1 = f"{start_year}-04-01", f"{end_year}-03-31"
    months = DB.query(
        "SELECT YEAR(invtest2.created)*100+MONTH(invtest2.created) AS ym,"
        " MONTH(invtest2.created) AS mon,"
        " SUM(invtest2.totalamount) AS Turnover, SUM(invtest2.taxamount) AS Tax"
        " FROM invtest2"
        " WHERE invtest2.created BETWEEN %s AND %s"
        " GROUP BY ym, mon ORDER BY ym",
        (d0, d1))
    if not months:
        return []
    if _indexed(_JOIN_IX):
        try:
            items = DB.query(
                "SELECT YEAR(invtest2.created)*100+MONTH(invtest2.created) AS ym,"
                " invtest.item_name AS item_name,"
                " SUM(invtest.quantity) AS qty,"
                " SUM(invtest.quantity * invtest.price) AS amt"
                " FROM invtest INNER JOIN invtest2 ON invtest.orderid = invtest2.orderid"
                " INNER JOIN products ON invtest.item_name = products.name"
                " WHERE products.p_type = 'Machine' AND invtest2.created BETWEEN %s AND %s"
                " GROUP BY ym, invtest.item_name",
                (d0, d1))
            best = {}
            for r in items:
                ym = r["ym"]
                key = (int(r["qty"] or 0), float(r["amt"] or 0))
                if ym not in best or key > best[ym][0]:
                    best[ym] = (key, r["item_name"], int(r["qty"] or 0))
            import calendar
            return [{"y": calendar.month_abbr[int(m["mon"])],
                     "a": float(m["Turnover"] or 0), "b": float(m["Tax"] or 0),
                     "c": best[m["ym"]][2] if m["ym"] in best else 0,
                     "label": best[m["ym"]][1] if m["ym"] in best else ""}
                    for m in months]
        except Exception:
            pass
    idmap = {r["orderid"]: r["ym"] for r in DB.query(
        "SELECT orderid, YEAR(created)*100+MONTH(created) AS ym FROM invtest2"
        " WHERE created BETWEEN %s AND %s", (d0, d1))}
    machines = {r["name"] for r in DB.query(
        "SELECT name FROM products WHERE p_type = 'Machine'")}
    best = {}
    if idmap and machines:
        sums = {}
        for ln in _invtest_lines():
            if ln["item_name"] in machines and ln["orderid"] in idmap:
                key = (idmap[ln["orderid"]], ln["item_name"])
                q = int(ln.get("quantity") or 0)
                a = q * float(ln.get("price") or 0)
                qty, amt = sums.get(key, (0, 0.0))
                sums[key] = (qty + q, amt + a)
        for (ym, item), (qty, amt) in sums.items():
            if ym not in best or (qty, amt) > (best[ym][1], best[ym][2]):
                best[ym] = (item, qty, amt)
    import calendar
    out = []
    for m in months:
        b = best.get(m["ym"])
        out.append({"y": calendar.month_abbr[int(m["mon"])],
                    "a": float(m["Turnover"] or 0), "b": float(m["Tax"] or 0),
                    "c": b[1] if b else 0, "label": b[0] if b else ""})
    return out


def annual_turnover_chart():
    # allyeardata: per financial year Turnover/GST + top Machine item (by qty).
    # Fast SQL path when dashboard indexes exist; Python-join fallback when
    # DDL was blocked.
    fy = DB.query(
        "SELECT CONCAT(YEAR(invtest2.created) - IF(MONTH(invtest2.created) < 4, 1, 0), '-',"
        " YEAR(invtest2.created) - IF(MONTH(invtest2.created) < 4, 0, -1)) AS financial_year,"
        " SUM(invtest2.taxamount) AS GST, SUM(invtest2.totalamount) AS Turnover"
        " FROM invtest2"
        " GROUP BY financial_year ORDER BY financial_year DESC")
    if not fy:
        return []
    if _indexed(_JOIN_IX):
        try:
            items = DB.query(
                "SELECT CONCAT(YEAR(invtest2.created) - IF(MONTH(invtest2.created) < 4, 1, 0), '-',"
                " YEAR(invtest2.created) - IF(MONTH(invtest2.created) < 4, 0, -1)) AS financial_year,"
                " invtest.item_name AS item_name, SUM(invtest.quantity) AS qty,"
                " SUM(invtest.quantity * invtest.price) AS amt"
                " FROM invtest INNER JOIN invtest2 ON invtest.orderid = invtest2.orderid"
                " INNER JOIN products ON invtest.item_name = products.name"
                " WHERE products.p_type = 'Machine'"
                " GROUP BY financial_year, invtest.item_name")
            best = {}
            for r in items:
                k = r["financial_year"]
                key = (int(r["qty"] or 0), float(r["amt"] or 0))
                if k not in best or key > best[k][0]:
                    best[k] = (key, r["item_name"], int(r["qty"] or 0))
            return [{"y": r["financial_year"], "a": float(r["Turnover"] or 0),
                     "b": float(r["GST"] or 0),
                     "c": best[r["financial_year"]][2]
                     if r["financial_year"] in best else 0,
                     "label": best[r["financial_year"]][1]
                     if r["financial_year"] in best else ""}
                    for r in fy]
        except Exception:
            pass
    idmap = {r["orderid"]: r["fy"] for r in DB.query(
        "SELECT orderid, CONCAT(YEAR(created) - IF(MONTH(created) < 4, 1, 0), '-',"
        " YEAR(created) - IF(MONTH(created) < 4, 0, -1)) AS fy FROM invtest2")}
    machines = {r["name"] for r in DB.query(
        "SELECT name FROM products WHERE p_type = 'Machine'")}
    best = {}
    if idmap and machines:
        agg = {}
        for ln in _invtest_lines():
            if ln["item_name"] in machines and ln["orderid"] in idmap:
                key = (idmap[ln["orderid"]], ln["item_name"])
                q = int(ln.get("quantity") or 0)
                a = q * float(ln.get("price") or 0)
                qty, amt = agg.get(key, (0, 0.0))
                agg[key] = (qty + q, amt + a)
        for (k, item), (qty, amt) in agg.items():
            if k not in best or (qty, amt) > (best[k][1], best[k][2]):
                best[k] = (item, qty, amt)
    out = []
    for r in fy:
        b = best.get(r["financial_year"])
        out.append({"y": r["financial_year"], "a": float(r["Turnover"] or 0),
                    "b": float(r["GST"] or 0),
                    "c": b[1] if b else 0, "label": b[0] if b else ""})
    return out


def location_tree():
    # gettreechart - top 25 client locations (last comma segment of c_add).
    # Fast SQL path when dashboard indexes exist; Python fallback otherwise
    # (both scan invtest<->invtest2 lines; client.cid is already indexed).
    _LOC_IX = _JOIN_IX + (("client", "cid"), ("invtest2", "cid"))
    if _indexed(_LOC_IX):
        try:
            rows = DB.query(
                "SELECT LOWER(TRIM(SUBSTRING_INDEX(client.c_add, ',', -1))) AS location,"
                " COUNT(*) AS count FROM invtest"
                " INNER JOIN invtest2 ON invtest.orderid = invtest2.orderid"
                " INNER JOIN client ON invtest2.cid = client.cid"
                " GROUP BY location ORDER BY count DESC LIMIT 25")
            return [{"location": str(r["location"] or "").replace("\n", "").replace(
                "\r", "").strip(), "count": int(r["count"])} for r in rows]
        except Exception:
            pass
    cmap = {r["cid"]: r["c_add"] for r in DB.query(
        "SELECT cid, c_add FROM client")}
    idmap = {r["orderid"]: r["cid"] for r in DB.query(
        "SELECT orderid, cid FROM invtest2")}
    if not cmap or not idmap:
        return []
    agg = {}
    for ln in _invtest_lines():
        cid = idmap.get(ln["orderid"])
        addr = cmap.get(cid) if cid is not None else None
        if not addr:
            continue
        loc = addr.rsplit(",", 1)[-1].strip().lower()
        agg[loc] = agg.get(loc, 0) + 1
    return [{"location": k, "count": v}
            for k, v in sorted(agg.items(), key=lambda kv: kv[1],
                               reverse=True)[:25]]


# --- Reminder tables (Dashboard::clientreminder) --------------------------
def client_reminder():
    return DB.query(
        "SELECT protest2.invid, client.c_name, client.mob,"
        " GROUP_CONCAT(protest.item_name SEPARATOR ', ') AS item_name"
        " FROM protest2 INNER JOIN protest ON protest2.orderid = protest.orderid"
        " INNER JOIN client ON protest2.cid = client.cid"
        " GROUP BY protest2.invid, client.c_name, client.mob"
        " ORDER BY protest2.invid DESC LIMIT 7")


def quickquote_reminder():
    return DB.query(
        "SELECT quickquote.q_id, products.name, quickquote.mob, quickquote.quantity,"
        " quickquote.subtotal, quickquote.gst, quickquote.total"
        " FROM quickquote INNER JOIN products ON products.p_id = quickquote.p_id"
        " ORDER BY quickquote.q_id DESC LIMIT 7")


# --- FY stats (footer blocks + FY banner) ---------------------------------
def fy_years(limit=5):
    rows = DB.query(
        "SELECT CASE WHEN MONTH(created) >= 4"
        " THEN CONCAT(YEAR(created), '-', YEAR(created) + 1)"
        " ELSE CONCAT(YEAR(created) - 1, '-', YEAR(created)) END AS financial_year"
        " FROM invtest2 GROUP BY financial_year ORDER BY financial_year DESC LIMIT %s",
        (limit,))
    return [r["financial_year"] for r in rows]


def fy_invoice_stats(start_year, end_year):
    # getInvoiceStatsForFinancialYear
    r = DB.one(
        "SELECT COUNT(invid) AS total_invoices, SUM(totalitems) AS total_items,"
        " SUM(totalamount) AS total_amount, SUM(taxamount) AS total_tax"
        " FROM invtest2 WHERE created >= %s AND created <= %s",
        (f"{start_year}-04-01", f"{end_year}-03-30"))
    return r or {"total_invoices": 0, "total_items": 0,
                 "total_amount": 0, "total_tax": 0}


def current_month_stats():
    # getClientCountForCurrentMonth / getInvoiceTotal / getInvCount / getBounceRate
    import datetime
    t = datetime.date.today()
    month_start = t.replace(day=1)
    prev_start = (month_start - datetime.timedelta(days=1)).replace(day=1)
    next_start = (month_start + datetime.timedelta(days=32)).replace(day=1)

    def turn(a, b):
        return float(DB.scalar(
            "SELECT COALESCE(SUM(totalamount),0) AS n FROM invtest2"
            " WHERE created >= %s AND created < %s", (a, b)) or 0)

    return {
        "clientcount": DB.scalar(
            "SELECT COUNT(*) AS n FROM client WHERE created >= %s AND created < %s",
            (month_start, next_start)) or 0,
        "monthturn": turn(month_start, next_start),
        "invcount": DB.scalar(
            "SELECT COUNT(invid) AS n FROM invtest2 WHERE created >= %s AND created < %s",
            (month_start, next_start)) or 0,
        "bounce_rate": (lambda cur, prev:
                        0.0 if prev == 0 else (cur - prev) / prev * 100)(
            turn(month_start, next_start), turn(prev_start, month_start)),
    }


# ---------------------------------------------------------------------------
# Settings  (Profile controller -> admin + bankdetails)
# ---------------------------------------------------------------------------
def update_admin(admin_id, data):
    """Update only the provided columns of the admin row.

    Pass a dict with any subset of:
        username, name, email, qualification, location, skills,
        c_name, c_add, profession, mob, gst, pan, picture, picturelogo,
        password
    """
    data = dict(data)
    data.pop("id", None)          # never write the PK

    # Allowed columns — protects against typos and SQL injection via keys
    allowed = {
        "username", "name", "email", "qualification", "location",
        "skills", "c_name", "c_add", "profession", "mob", "gst",
        "pan", "picture", "picturelogo", "password",
    }
    cols = [c for c in data.keys() if c in allowed]
    if not cols:
        return 0

    sets = ", ".join(f"{c}=%({c})s" for c in cols)
    params = {c: data[c] for c in cols}
    params["id"] = admin_id
    return DB.execute(f"UPDATE admin SET {sets} WHERE id=%(id)s", params)



def get_bank_details():
    return DB.one("SELECT * FROM bankdetails ORDER BY bid LIMIT 1")


# ---------------------------------------------------------------------------
# Sales Prediction / Repurchase Transactions
# ---------------------------------------------------------------------------
def get_client_invoice_transactions():
    """Fetch all tax invoices joined with client data for BG/NBD repurchase models."""
    return DB.query(
        "SELECT m.orderid, m.invid, m.cid, "
        "COALESCE(c.c_name, CONCAT('Client #', m.cid)) AS client_name, "
        "c.mob, c.gst, m.totalamount, m.created AS invdate "
        "FROM invtest2 m "
        "LEFT JOIN client c ON c.cid = m.cid "
        "WHERE m.created IS NOT NULL "
        "ORDER BY m.created ASC"
    )


def save_bank_details(data):
    existing = get_bank_details()
    if existing:
        data = dict(data)
        data["bid"] = existing["bid"]
        return DB.execute(
            "UPDATE bankdetails SET bname=%(bname)s, ac=%(ac)s, ifsc=%(ifsc)s,"
            " branch=%(branch)s WHERE bid=%(bid)s", data)
    return DB.execute(
        "INSERT INTO bankdetails (bname, ac, ifsc, branch)"
        " VALUES (%(bname)s, %(ac)s, %(ifsc)s, %(branch)s)", data, return_id=True)


# ---------------------------------------------------------------------------
# Client / Product / Supplier Info pages
#   Python port of Client::viewclientinfo + Info layout/getclientinfo.php,
#   Product::viewproductinfo + getproductinfo.php and
#   supplier::viewsupplierinfo + getsupplierinfo.php.
#   Each Info page shows a details box, a per-financial-year summary and one
#   '... Invoice Details' table per document type.
# ---------------------------------------------------------------------------
INFO_DOCS = {
    "client":   [("tax", "Sales Tax Invoice Details"),
                 ("proforma", "Proforma Invoice Details")],
    "supplier": [("purchase", "Purchase Invoice Details"),
                 ("proforma", "Proforma Invoice Details"),
                 ("tax", "Sales Tax Invoice Details")],
    "product":  [("tax", "Sales Tax Invoice Details"),
                 ("proforma", "Proforma Invoice Details")],
}


def _fy_expr(date_col):
    """SQL for the '2024-2025' financial-year label of a date column."""
    return ("CASE WHEN MONTH({0}) >= 4 THEN CONCAT(YEAR({0}), '-',"
            " YEAR({0}) + 1) ELSE CONCAT(YEAR({0}) - 1, '-', YEAR({0}))"
            " END").format(date_col)


def fy_turnover(master, id_col, id_val, date_col="created"):
    """Turnover per financial year ('Turnover as per FY' box)."""
    fy = _fy_expr(date_col)
    return DB.query(
        f"SELECT {fy} AS fy, COUNT(*) AS invoices,"
        f" COALESCE(SUM(totalamount), 0) AS amount"
        f" FROM {master} WHERE {id_col} = %s GROUP BY fy ORDER BY fy DESC",
        (id_val,))


def yearly_item_sold(product_name):
    """'Yearly Sold Item Count' box of the Product Info page."""
    fy = _fy_expr("m.created")
    return DB.query(
        f"SELECT {fy} AS fy, COALESCE(SUM(i.quantity), 0) AS quantity"
        " FROM invtest i JOIN invtest2 m ON m.orderid = i.orderid"
        " WHERE i.item_name = %s GROUP BY fy ORDER BY fy DESC",
        (product_name,))


def info_invoices(kind, key, doc):
    """Rows of a '... Invoice Details' table on an Info page.

    Columns match the original DataTables (Invoice Id, Company Name,
    Location, Item Name, Amount, Created) - Location is the last part of
    the client address and Item Name the comma-joined item list.
    `key` is the client/supplier id, or the product name when kind='product'.
    """
    reg = DOC_REGISTRY[doc]
    master, items, dc = reg["master"], reg["items"], reg["date_col"]
    where = "i.item_name = %s" if kind == "product" else "m.cid = %s"
    return DB.query(
        f"SELECT m.orderid, m.invid, m.{dc} AS created, m.totalamount,"
        f" c.c_name, TRIM(SUBSTRING_INDEX(c.c_add, ',', -1)) AS location,"
        f" GROUP_CONCAT(i.item_name SEPARATOR ', ') AS item_name"
        f" FROM {master} m LEFT JOIN client c ON c.cid = m.cid"
        f" LEFT JOIN {items} i ON i.orderid = m.orderid"
        f" WHERE {where}"
        f" GROUP BY m.orderid, m.invid, m.created, m.totalamount, c.c_name,"
        f" location ORDER BY m.created DESC, m.orderid DESC",
        (key,))


def _sum_amount(rows):
    return sum(float(r["totalamount"] or 0) for r in rows)


def client_info(cid):
    """Client details + FY turnover + tax/proforma invoice rows."""
    client = DB.one("SELECT * FROM client WHERE cid=%s", (cid,))
    if not client:
        return None
    invoices = {doc: info_invoices("client", cid, doc)
                for doc, _title in INFO_DOCS["client"]}
    tax = invoices["tax"]
    return {
        "details": client,
        "fy": fy_turnover("invtest2", "cid", cid),
        "invoices": invoices,
        "total_invoices": len(tax),
        "total_amount": _sum_amount(tax),
    }


def supplier_info(cid):
    """Supplier details + FY turnover + purchase/proforma/tax rows."""
    client = DB.one("SELECT * FROM client WHERE cid=%s", (cid,))
    if not client:
        return None
    invoices = {doc: info_invoices("supplier", cid, doc)
                for doc, _title in INFO_DOCS["supplier"]}
    purchase = invoices["purchase"]
    return {
        "details": client,
        "fy": fy_turnover("purchaseinv2", "cid", cid, "invdate"),
        "invoices": invoices,
        "total_invoices": len(purchase),
        "total_amount": _sum_amount(purchase),
    }


def product_info(p_id):
    """Product details + tech specs + yearly sold + tax/proforma rows."""
    product = DB.one("SELECT * FROM products WHERE p_id=%s", (p_id,))
    if not product:
        return None
    name = product["name"]
    yearly = yearly_item_sold(name)
    return {
        "details": product,
        "tech": get_techsps(p_id),
        "yearly": yearly,
        "invoices": {doc: info_invoices("product", name, doc)
                     for doc, _title in INFO_DOCS["product"]},
        "total_sold": sum(float(r["quantity"] or 0) for r in yearly),
    }