"""
Data migration and initialization from db.sql into SQLite.
"""
import os
import re
import sqlite3
from database.schema_sqlite import SQLITE_TABLES, SECONDARY_INDEXES

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_SQL_PATH = os.path.join(BASE_DIR, "db.sql")

# Rows that could not be imported from db.sql (kept for diagnostics only).
SEED_ERRORS = []


def extract_inserts_from_sql(sql_content):
    """Parse MySQL INSERT statements from db.sql into (table, columns, rows).

    A regex is not enough here: the dump contains values with ``;`` and
    parentheses *inside* quoted strings (e.g. the long product ``techs``
    descriptions), so the statements are located with a quote-aware scanner.
    """
    results = []
    i = 0
    n = len(sql_content)
    upper = sql_content.upper()
    while True:
        start = upper.find("INSERT INTO", i)
        if start < 0:
            break
        i = start + 11
        # table name (optionally back-ticked)
        m = re.match(r"\s*`?(\w+)`?", sql_content[i:])
        if not m:
            continue
        table = m.group(1).lower()
        i += m.end()
        # column list
        while i < n and sql_content[i] in " \t\r\n":
            i += 1
        if i >= n or sql_content[i] != "(":
            continue
        close = _find_char_outside_quotes(sql_content, i, "(", ")")
        if close < 0:
            break
        cols_str = sql_content[i + 1:close]
        cols = [c.strip().strip("`") for c in cols_str.split(",")]
        i = close + 1
        # VALUES keyword
        m = re.match(r"\s*VALUES", sql_content[i:], re.IGNORECASE)
        if not m:
            continue
        i += m.end()
        # statement terminator: the first ';' outside any string literal
        end = _find_char_outside_quotes(sql_content, i, ";", ";")
        if end < 0:
            break
        rows = _parse_sql_tuples(sql_content[i:end])
        results.append((table, cols, rows))
        i = end + 1
    return results


def _find_char_outside_quotes(text, start, opener, closer):
    """Index of the *closer* matching *opener*, ignoring quoted sections.

    When opener == closer (e.g. searching for a bare ';') the first occurrence
    outside quotes is returned.
    """
    depth = 0
    i = start
    n = len(text)
    while i < n:
        ch = text[i]
        if ch in ("'", '"', "`"):
            quote = ch
            i += 1
            while i < n:
                if text[i] == "\\" and i + 1 < n:
                    i += 2
                    continue
                if text[i] == quote:
                    if i + 1 < n and text[i + 1] == quote:   # doubled escape
                        i += 2
                        continue
                    break
                i += 1
            i += 1
            continue
        if opener == closer:
            if ch == closer:
                return i
            i += 1
            continue
        if ch == opener:
            depth += 1
        elif ch == closer:
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return -1


def _parse_sql_tuples(val_block):
    """State-machine parser for MySQL VALUES tuples.

    Quoting is tracked per value so a quoted empty string ``''`` (an empty
    ``quote2.note``) is not mistaken for NULL.
    """
    tuples = []
    current_tuple = []
    current_val = []
    was_quoted = False
    in_str = False
    str_char = None
    escaped = False
    in_tuple = False

    i = 0
    n = len(val_block)
    while i < n:
        ch = val_block[i]
        if not in_tuple:
            if ch == '(':
                in_tuple = True
                current_tuple = []
                current_val = []
                was_quoted = False
            i += 1
            continue

        if in_str:
            if escaped:
                current_val.append(ch)
                escaped = False
            elif ch == '\\':
                escaped = True
            elif ch == str_char:
                if i + 1 < n and val_block[i + 1] == str_char:
                    current_val.append(str_char)
                    i += 1
                else:
                    in_str = False
            else:
                current_val.append(ch)
            i += 1
            continue

        if ch in ("'", '"'):
            in_str = True
            str_char = ch
            escaped = False
            was_quoted = True
            i += 1
            continue

        if ch == ',':
            current_tuple.append(
                _cast_sql_val("".join(current_val), was_quoted))
            current_val = []
            was_quoted = False
            i += 1
            continue

        if ch == ')':
            current_tuple.append(
                _cast_sql_val("".join(current_val), was_quoted))
            tuples.append(current_tuple)
            in_tuple = False
            current_tuple = []
            current_val = []
            was_quoted = False
            i += 1
            continue

        current_val.append(ch)
        i += 1

    return tuples


def _cast_sql_val(raw_val, was_quoted=False):
    """Convert a raw MySQL literal into a Python value for sqlite3 binding.

    Only an *unquoted* NULL (or an empty token) becomes None - a quoted empty
    string ``''`` must stay an empty string, otherwise a NOT NULL column such
    as ``quote2.note`` rejects the row.  Unquoted numbers are converted so the
    target column keeps its SQLite type affinity.
    """
    raw = "" if raw_val is None else raw_val.strip()
    if not was_quoted:
        if raw == "" or raw.upper() == "NULL":
            return None
        if re.fullmatch(r"[+-]?\d+", raw):
            return int(raw)
        if re.fullmatch(r"[+-]?\d*\.\d+([eE][+-]?\d+)?", raw):
            return float(raw)
    return raw


def init_sqlite_database(db_path, sql_dump_path=None, conn=None):
    """Create all SQLite tables, seed from db.sql when fresh, add indexes.

    Safe to call repeatedly: every statement is IF NOT EXISTS / INSERT OR
    IGNORE, and the seed data is only loaded while the database is empty.
    When *conn* is given (the shared app connection) it is reused, otherwise a
    short-lived connection is opened for the work.
    """
    os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
    sql_dump_path = sql_dump_path or DB_SQL_PATH

    own = conn is None
    if own:
        from database import sqlite_compat
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        sqlite_compat.configure(conn)
    cur = conn.cursor()

    # 1. Create tables
    for _, ddl in SQLITE_TABLES:
        cur.execute(ddl)

    # 2. Seed from the MySQL dump while the database is still empty
    cur.execute("SELECT COUNT(*) FROM admin")
    admin_count = cur.fetchone()[0]

    if admin_count == 0 and os.path.exists(sql_dump_path):
        with open(sql_dump_path, "r", encoding="utf-8", errors="ignore") as f:
            dump_content = f.read()

        inserts = extract_inserts_from_sql(dump_content)
        known_tables = {name for name, _ in SQLITE_TABLES}
        for table, cols, rows in inserts:
            if table not in known_tables or not rows:
                continue
            col_names = ", ".join(f'"{c}"' for c in cols)
            placeholders = ", ".join(["?"] * len(cols))
            insert_sql = (f'INSERT OR IGNORE INTO "{table}" ({col_names}) '
                          f"VALUES ({placeholders})")
            # One bad row must not cost us the whole table, so fall back to a
            # per-row insert and report anything that still fails.
            try:
                cur.executemany(insert_sql, rows)
            except Exception:
                for r in rows:
                    try:
                        cur.execute(insert_sql, r)
                    except Exception as exc:
                        SEED_ERRORS.append(f"{table}: {exc}")

    # 3. Create secondary indexes
    for idx_sql in SECONDARY_INDEXES:
        try:
            cur.execute(idx_sql)
        except Exception:
            pass

    if not conn.in_transaction:
        conn.commit()
    if own:
        conn.close()
    return conn
