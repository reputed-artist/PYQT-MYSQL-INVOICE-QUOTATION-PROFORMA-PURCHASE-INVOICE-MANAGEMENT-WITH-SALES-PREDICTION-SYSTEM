#!/usr/bin/env python3
"""
Build db.sqlite from MySQL dump (db.sql) + enhancement script (enhance.sql).
Usage:  python build_sqlite.py
Output: db.sqlite
"""
import re, sqlite3, os

MYSQL_DUMP = "db.sql"
ENHANCE_SQL = "enhance.sql"
OUTPUT_DB = "sales_aura.db"


def mysql_to_sqlite(sql: str) -> str:
    # Remove MySQL conditional comments /*!...*/;
    sql = re.sub(r'/\*![\s\S]*?\*/;?', '', sql)

    # Remove SET statements
    sql = re.sub(r'^\s*SET\s+[^;]*;\s*$', '', sql, flags=re.M | re.I)

    # Remove START TRANSACTION / COMMIT
    sql = re.sub(r'^\s*START\s+TRANSACTION\s*;\s*$', '', sql, flags=re.M | re.I)
    sql = re.sub(r'^\s*COMMIT\s*;\s*$', '', sql, flags=re.M | re.I)

    # Backticks -> double quotes
    sql = sql.replace('`', '"')

    # Strip ENGINE / CHARSET / COLLATE from CREATE TABLE
    sql = re.sub(r'\)\s*ENGINE\s*=\s*\w+[^;]*;', ');', sql, flags=re.I)
    sql = re.sub(r'DEFAULT\s+CHARSET\s*=\s*\w+', '', sql, flags=re.I)
    sql = re.sub(r'COLLATE\s*=?\s*\w+', '', sql, flags=re.I)
    sql = re.sub(r'CHARACTER\s+SET\s+\w+', '', sql, flags=re.I)

    # --- Handle AUTO_INCREMENT ---
    # Case 1: Inline in column definition (rare in this dump)
    sql = re.sub(
        r'(\w+)\s+int\(\d+\)\s+NOT\s+NULL\s+AUTO_INCREMENT',
        r'\1 INTEGER PRIMARY KEY AUTOINCREMENT',
        sql, flags=re.I)

    # Case 2: via ALTER TABLE ... MODIFY ... AUTO_INCREMENT
    # -> Extract the PK column and mark it for inline injection.
    alter_pat = re.compile(
        r'ALTER\s+TABLE\s+(\w+)\s+MODIFY\s+(\w+)\s+int\(\d+\)\s+NOT\s+NULL\s+AUTO_INCREMENT[^;]*;',
        re.I)

    pk_cols = {}  # table -> column
    for m in alter_pat.finditer(sql):
        pk_cols[m.group(1).lower()] = m.group(2)
    sql = alter_pat.sub('', sql)

    # Case 3: ALTER TABLE ... ADD PRIMARY KEY
    pk_pat = re.compile(
        r'ALTER\s+TABLE\s+(\w+)\s+ADD\s+PRIMARY\s+KEY\s*\(\s*"?(\w+)"?\s*\)\s*;',
        re.I)
    for m in pk_pat.finditer(sql):
        pk_cols.setdefault(m.group(1).lower(), m.group(2))
    sql = pk_pat.sub('', sql)

    # Case 4: ALTER TABLE ... ADD KEY / INDEX
    sql = re.sub(r'ALTER\s+TABLE\s+\w+\s+ADD\s+(KEY|INDEX|UNIQUE)[^;]*;', '', sql, flags=re.I)

    # Now inject PRIMARY KEY AUTOINCREMENT into CREATE TABLE if needed
    def fix_create(match):
        table = match.group(1)
        body = match.group(2)
        pk = pk_cols.get(table.lower())
        if pk and 'AUTOINCREMENT' not in body.upper():
            # Replace the pk column's type with INTEGER PRIMARY KEY AUTOINCREMENT
            body = re.sub(
                rf'("{pk}")\s+INTEGER\s+NOT\s+NULL',
                r'\1 INTEGER PRIMARY KEY AUTOINCREMENT',
                body, flags=re.I)
            body = re.sub(
                rf'("{pk}")\s+INTEGER(?!\s+PRIMARY)',
                r'\1 INTEGER PRIMARY KEY AUTOINCREMENT',
                body, flags=re.I)
            if 'AUTOINCREMENT' not in body.upper():
                # If pk column had no NOT NULL (like some tables), handle alt pattern
                body = re.sub(
                    rf'("{pk}")\s+INTEGER',
                    r'\1 INTEGER PRIMARY KEY AUTOINCREMENT',
                    body, count=1, flags=re.I)
        return f'CREATE TABLE "{table}" ({body});'

    sql = re.sub(
        r'CREATE\s+TABLE\s+"?(\w+)"?\s*\(([\s\S]*?)\)\s*;',
        fix_create, sql, flags=re.I)

    # Type conversions
    sql = re.sub(r'\bdouble\b', 'REAL', sql, flags=re.I)
    sql = re.sub(r'\btinyint\(\d+\)', 'INTEGER', sql, flags=re.I)
    sql = re.sub(r'\bint\(\d+\)', 'INTEGER', sql, flags=re.I)
    sql = re.sub(r'\bdatetime\b', 'TEXT', sql, flags=re.I)
    sql = re.sub(r'\bdate\b', 'TEXT', sql, flags=re.I)
    sql = re.sub(r'\bvarchar\(\d+\)', 'TEXT', sql, flags=re.I)

    return sql


def split_sql(sql: str):
    """Split SQL into statements, respecting single-quoted strings."""
    stmts, buf, in_str, esc = [], [], False, False
    for ch in sql:
        if esc:
            buf.append(ch); esc = False; continue
        if ch == '\\' and in_str:
            buf.append(ch); esc = True; continue
        if ch == "'":
            in_str = not in_str
            buf.append(ch); continue
        if ch == ';' and not in_str:
            s = ''.join(buf).strip()
            if s: stmts.append(s)
            buf = []
        else:
            buf.append(ch)
    s = ''.join(buf).strip()
    if s: stmts.append(s)
    return stmts


def main():
    if not os.path.exists(MYSQL_DUMP):
        print(f"❌ Missing: {MYSQL_DUMP}")
        return

    raw = open(MYSQL_DUMP, encoding='utf-8', errors='replace').read()
    converted = mysql_to_sqlite(raw)

    if os.path.exists(ENHANCE_SQL):
        enh = open(ENHANCE_SQL, encoding='utf-8', errors='replace').read()
        converted += "\n" + mysql_to_sqlite(enh)

    open('converted.sql', 'w', encoding='utf-8').write(converted)

    if os.path.exists(OUTPUT_DB):
        os.remove(OUTPUT_DB)

    conn = sqlite3.connect(OUTPUT_DB)
    cur = conn.cursor()
    ok = err = 0
    for i, stmt in enumerate(split_sql(converted), 1):
        try:
            cur.execute(stmt)
            ok += 1
        except sqlite3.Error as e:
            err += 1
            print(f"⚠️  #{i}: {e}\n   {stmt[:140]}...")
    conn.commit()

    # Report
    print(f"\n✅ {OUTPUT_DB} created  ({ok} ok / {err} errors)")
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    print("📋 Tables:", ", ".join(r[0] for r in cur.fetchall()))
    conn.close()


if __name__ == "__main__":
    main()