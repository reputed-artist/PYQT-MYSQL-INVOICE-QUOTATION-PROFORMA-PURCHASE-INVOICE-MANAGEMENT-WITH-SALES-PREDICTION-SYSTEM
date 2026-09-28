"""
Ledger helpers - Python port of CodeIgniter Account_model.php getLedgerDetails
and the getLedgerController FY-detection / FY-summary logic.

Tables (from db.sql):
  account(cid, opening_bal, ...)
  client(cid, u_type, ...)          u_type 0=Customer, 1=Supplier, 2=Dual
  invtest2(cid, totalamount, created, ...)   tax invoices  -> Credit (u_type 0,2)
  purchaseinv2(cid, totalamount, invdate, ...) purchases     -> Debit  (u_type 1,2)
  paidhistory(cid, amount, dateofpayment, ...) receipts      -> Debit (u_type 0) / Credit (u_type 1,2)

FY convention (shared with CodeIgniter): a transaction in April..December belongs
to YEAR-(YEAR+1); a transaction in January..March belongs to (YEAR-1)-YEAR.
"""

from database.db_manager import DB


def get_fys_for_client(cid):
    """Distinct financial years (like '2024-2025') for this client, plus the
    latest detected FY (None if no data). Matches CI SQL_FyDetect logic."""
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
    """u_type: 0=Customer (Sales+Receipts), 1=Supplier (Purchase+Receipts),
    2=Dual (Sales+Purchase+Receipts). From client.u_type, defaults to 0."""
    row = DB.one("SELECT u_type FROM client WHERE cid=%s", (cid,))
    return int(row["u_type"]) if row else 0
