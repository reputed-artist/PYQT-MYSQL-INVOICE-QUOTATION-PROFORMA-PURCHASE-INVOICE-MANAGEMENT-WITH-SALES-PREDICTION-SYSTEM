"""
MySQL -> SQLite compatibility helpers.

The project was originally written against MySQL (pymysql + CodeIgniter
models).  The SQL in ``database/db_manager.py`` is therefore written in MySQL
dialect.  Rather than rewriting ~200 queries by hand - and risking silent
behaviour changes - this module adapts the dialect at the boundary:

* ``rewrite_sql()``  - placeholder (``%s`` / ``%(name)s`` -> ``?`` / ``:name``)
                      and ``GROUP_CONCAT(x SEPARATOR ', ')`` translation.
* ``register()``     - registers MySQL scalar functions (``YEAR``, ``MONTH``,
                      ``DATE_FORMAT``, ``CONCAT``, ``IF``, ``SUBSTRING_INDEX``,
                      ``CHAR_LENGTH`` ...) on an sqlite3 connection.
* ``register_adapters()`` - ``datetime`` adapters so ``datetime.date`` /
                      ``datetime.datetime`` bind like they did under pymysql.
* ``converters``     - ``DATE`` / ``DATETIME`` column converters, so values
                      come back as ``datetime`` objects exactly like MySQL
                      (the UI relies on ``isinstance(v, date)``).

Keeping this in one place means the rest of the app (UI included) is untouched.
"""
import re
import sqlite3
import datetime


# --------------------------------------------------------------------------- #
#  Parameter placeholders
# --------------------------------------------------------------------------- #
# Matches either  %(name)s  (dict params)  or  %s  (sequence params).
# Any other '%' inside the SQL (e.g. LIKE wildcards baked into a literal) is
# left untouched because the scanner below only rewrites outside string quotes.
_PLACEHOLDER_RE = re.compile(r"%\((?P<name>\w+)\)s|%s")


def _match_paren(sql, open_idx):
    """Index of the ')' matching the '(' at *open_idx* (-1 if unbalanced)."""
    depth = 0
    i = open_idx
    n = len(sql)
    while i < n:
        ch = sql[i]
        if ch in ("'", '"', "`"):
            quote = ch
            i += 1
            while i < n:
                if sql[i] == quote:
                    if i + 1 < n and sql[i + 1] == quote:   # doubled escape
                        i += 2
                        continue
                    break
                if sql[i] == "\\" and i + 1 < n:
                    i += 2
                    continue
                i += 1
        elif ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return -1


def _rewrite_placeholders(sql, named):
    """Translate pymysql placeholders into sqlite3 placeholders.

    *named* - True  -> ``%(foo)s`` becomes ``:foo`` (dict params)
    *named* - False -> ``%s`` becomes ``?``        (tuple/list params)

    String literals are skipped so a ``%`` inside quotes is never mangled.
    """
    out = []
    i = 0
    n = len(sql)
    quote = None
    while i < n:
        ch = sql[i]
        if quote:
            out.append(ch)
            if ch == quote:
                if i + 1 < n and sql[i + 1] == quote:      # doubled escape
                    out.append(sql[i + 1])
                    i += 2
                    continue
                quote = None
            elif ch == "\\" and i + 1 < n:
                out.append(sql[i + 1])
                i += 2
                continue
            i += 1
            continue
        if ch in ("'", '"', "`"):
            quote = ch
            out.append(ch)
            i += 1
            continue
        if ch == "%":
            m = _PLACEHOLDER_RE.match(sql, i)
            if m:
                name = m.group("name")
                out.append(":" + name if (named and name) else "?")
                i = m.end()
                continue
            out.append(ch)
            i += 1
            continue
        out.append(ch)
        i += 1
    return "".join(out)


# --------------------------------------------------------------------------- #
#  GROUP_CONCAT(... SEPARATOR ', ')
# --------------------------------------------------------------------------- #
# SQLite's group_concat() takes the separator as a second argument instead of
# a SEPARATOR keyword, so  GROUP_CONCAT(x SEPARATOR ', ')  ->  group_concat(x, ', ')
_GROUP_CONCAT_RE = re.compile(r"group_concat\s*\(", re.IGNORECASE)
_SEPARATOR_RE = re.compile(r"\s*SEPARATOR\s+('(?:[^']|'')*')\s*$",
                            re.IGNORECASE | re.DOTALL)


def _rewrite_group_concat(sql):
    """MySQL  GROUP_CONCAT(x SEPARATOR ', ')  ->  SQLite  group_concat(x, ', ')

    The MySQL keyword sits *inside* the parentheses, so the inner expression is
    split on a trailing ``SEPARATOR '...'``.
    """
    pos = 0
    while True:
        m = _GROUP_CONCAT_RE.search(sql, pos)
        if not m:
            return sql
        open_idx = m.end() - 1
        close_idx = _match_paren(sql, open_idx)
        if close_idx < 0:
            return sql
        inner = sql[open_idx + 1:close_idx]
        sep = _SEPARATOR_RE.search(inner)
        if not sep:
            pos = open_idx + 1
            continue
        value_expr = inner[:sep.start()].rstrip()
        new_call = f"group_concat({value_expr}, {sep.group(1)})"
        sql = sql[:m.start()] + new_call + sql[close_idx + 1:]
        pos = m.start() + len(new_call)


def rewrite_sql(sql, named=False, interpolate=True):
    """Full MySQL -> SQLite statement translation used by ``DB.*``."""
    if interpolate:
        # pymysql ran ``query % args`` whenever parameters were supplied, which
        # collapsed every '%%' to '%'.  Several DATE_FORMAT calls in this
        # project are written as '%%Y-%%m' for exactly that reason, so the
        # collapse has to be reproduced to keep them working.
        sql = sql.replace("%%", "%")
    sql = _rewrite_group_concat(sql)
    return _rewrite_placeholders(sql, named)


# --------------------------------------------------------------------------- #
#  MySQL scalar functions
# --------------------------------------------------------------------------- #
def _coerce(value):
    """Best-effort conversion of a sqlite value to a date/datetime object."""
    if isinstance(value, (datetime.datetime, datetime.date)):
        return value
    if isinstance(value, bytes):
        value = value.decode("utf-8", "replace")
    if isinstance(value, str):
        s = value.strip()
        m = re.match(r"^(\d{4})-(\d{1,2})-(\d{1,2})"
                     r"(?:[ T](\d{1,2}):(\d{2})(?::(\d{2}))?)?", s)
        if m:
            y, mo, d = int(m[1]), int(m[2]), int(m[3])
            hh, mi, ss = int(m[4] or 0), int(m[5] or 0), int(m[6] or 0)
            try:
                if hh or mi or ss:
                    return datetime.datetime(y, mo, d, hh, mi, ss)
                return datetime.date(y, mo, d)
            except ValueError:
                return None
    return None


def _as_date(value):
    d = _coerce(value)
    return d.date() if isinstance(d, datetime.datetime) else d


def _fn_year(value):
    d = _as_date(value)
    return d.year if d else None


def _fn_month(value):
    d = _as_date(value)
    return d.month if d else None


def _fn_day(value):
    d = _as_date(value)
    return d.day if d else None


def _fn_iso_date(value):
    d = _as_date(value)
    return d.isoformat() if d else None


_MONTHS = ["January", "February", "March", "April", "May", "June", "July",
           "August", "September", "October", "November", "December"]
_DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday",
         "Friday", "Saturday", "Sunday"]


def _fn_date_format(value, fmt):
    """MySQL DATE_FORMAT - supports the specifiers used by this project."""
    d = _coerce(value)
    if d is None:
        return None
    dt, dd = (d, d.date()) if isinstance(d, datetime.datetime) else (None, d)
    out = []
    i = 0
    fmt = "" if fmt is None else str(fmt)
    while i < len(fmt):
        ch = fmt[i]
        if ch != "%" or i + 1 >= len(fmt):
            out.append(ch)
            i += 1
            continue
        code = fmt[i + 1]
        i += 2
        if code == "Y":
            out.append(f"{dd.year:04d}")
        elif code == "y":
            out.append(f"{dd.year % 100:02d}")
        elif code == "m":
            out.append(f"{dd.month:02d}")
        elif code == "c":
            out.append(str(dd.month))
        elif code == "d":
            out.append(f"{dd.day:02d}")
        elif code == "e":
            out.append(str(dd.day))
        elif code == "M":
            out.append(_MONTHS[dd.month - 1])
        elif code == "b":
            out.append(_MONTHS[dd.month - 1][:3])
        elif code == "W":
            out.append(_DAYS[dd.weekday()])
        elif code == "a":
            out.append(_DAYS[dd.weekday()][:3])
        elif code == "H":
            out.append(f"{dt.hour:02d}" if dt else "00")
        elif code == "i":
            out.append(f"{dt.minute:02d}" if dt else "00")
        elif code == "s":
            out.append(f"{dt.second:02d}" if dt else "00")
        elif code == "p":
            out.append("AM" if (dt.hour if dt else 0) < 12 else "PM")
        elif code == "%":
            out.append("%")
        else:
            out.append("%" + code)
    return "".join(out)


def _fn_concat(*args):
    """MySQL CONCAT - returns NULL if any argument is NULL."""
    parts = []
    for a in args:
        if a is None:
            return None
        if isinstance(a, bytes):
            a = a.decode("utf-8", "replace")
        parts.append(a if isinstance(a, str) else str(a))
    return "".join(parts)


def _fn_concat_ws(sep, *args):
    if sep is None:
        return None
    if isinstance(sep, bytes):
        sep = sep.decode("utf-8", "replace")
    out = []
    for a in args:
        if a is None:
            continue
        if isinstance(a, bytes):
            a = a.decode("utf-8", "replace")
        out.append(a if isinstance(a, str) else str(a))
    return str(sep).join(out)


def _fn_if(cond, if_true, if_false):
    return if_true if cond else if_false


def _fn_ifnull(value, default):
    return default if value is None else value


def _fn_char_length(value):
    if value is None:
        return None
    if isinstance(value, bytes):
        value = value.decode("utf-8", "replace")
    return len(str(value))


def _fn_substring_index(text, delim, count):
    """MySQL SUBSTRING_INDEX(text, delim, count).

    count > 0 -> everything before the count-th occurrence (from the left)
    count < 0 -> everything after the |count|-th occurrence (from the right)
    """
    if text is None or delim is None:
        return None
    if isinstance(text, bytes):
        text = text.decode("utf-8", "replace")
    if isinstance(delim, bytes):
        delim = delim.decode("utf-8", "replace")
    text, delim = str(text), str(delim)
    if delim == "":
        return text
    try:
        count = int(count)
    except (TypeError, ValueError):
        return None
    if count == 0:
        return ""
    if count > 0:
        idx = -1
        for _ in range(count):
            idx = text.find(delim, idx + 1)
            if idx < 0:
                return text
        return text[:idx]
    idx = len(text)
    for _ in range(-count):
        idx = text.rfind(delim, 0, idx)
        if idx < 0:
            return text
    return text[idx + len(delim):]


def _fn_curdate():
    return datetime.date.today().isoformat()


def _fn_now():
    return datetime.datetime.now().replace(microsecond=0).isoformat(sep=" ")


def _fn_random():
    import random
    return random.random()


# --------------------------------------------------------------------------- #
#  Registration
# --------------------------------------------------------------------------- #
_FUNCTIONS = (
    ("YEAR", 1, _fn_year),
    ("MONTH", 1, _fn_month),
    ("DAY", 1, _fn_day),
    ("DATE", 1, _fn_iso_date),
    ("DATE_FORMAT", 2, _fn_date_format),
    ("TIME_FORMAT", 2, _fn_date_format),
    ("CONCAT", -1, _fn_concat),
    ("CONCAT_WS", -1, _fn_concat_ws),
    ("IF", 3, _fn_if),
    ("IFNULL", 2, _fn_ifnull),
    ("CHAR_LENGTH", 1, _fn_char_length),
    ("CHARACTER_LENGTH", 1, _fn_char_length),
    ("SUBSTRING_INDEX", 3, _fn_substring_index),
    ("CURDATE", 0, _fn_curdate),
    ("NOW", 0, _fn_now),
    ("RAND", 0, _fn_random),
)


def register(conn):
    """Attach the MySQL-compatible function set to a sqlite3 connection."""
    for name, narg, fn in _FUNCTIONS:
        conn.create_function(name, narg, fn, deterministic=True)


def register_adapters():
    """Bind ``date``/``datetime`` like pymysql did (ISO strings).

    Python 3.12 deprecated the implicit sqlite3 date adapters, so the app
    registers its own explicitly.  Values are converted back to ``datetime``
    objects by the DATE/DATETIME converters registered below.
    """
    sqlite3.register_adapter(datetime.date, lambda d: d.isoformat())
    sqlite3.register_adapter(datetime.datetime,
                             lambda d: d.isoformat(sep=" "))


def _decode(value):
    return (value.decode("utf-8", "replace")
            if isinstance(value, bytes) else value)


def _convert_date(value):
    d = _coerce(_decode(value))
    if isinstance(d, datetime.datetime):
        d = d.date()
    return d if d is not None else value


def _convert_datetime(value):
    d = _coerce(_decode(value))
    if isinstance(d, datetime.datetime):
        return d
    if isinstance(d, datetime.date):
        return datetime.datetime(d.year, d.month, d.day)
    return value


def register_converters():
    """Map SQLite ``DATE``/``DATETIME`` declared types to Python objects."""
    sqlite3.register_converter("date", _convert_date)
    sqlite3.register_converter("datetime", _convert_datetime)
    sqlite3.register_converter("timestamp", _convert_datetime)


def configure(conn):
    """One-stop setup: adapters, converters, functions and pragmas."""
    register_adapters()
    register_converters()
    register(conn)
    cur = conn.cursor()
    cur.execute("PRAGMA journal_mode = WAL")
    cur.execute("PRAGMA synchronous = NORMAL")
    cur.execute("PRAGMA foreign_keys = ON")
    cur.execute("PRAGMA busy_timeout = 5000")
    cur.close()
    return conn



