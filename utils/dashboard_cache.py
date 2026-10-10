"""
dashboard_cache.py

Thread-safe in-memory cache for dashboard queries.

Public API
----------
cached(key, ttl, loader, default=..., on_error=None) -> value
get(key, default=None) -> value
set(key, value, ttl=TTL_CHART) -> None
invalidate(prefix="") -> None
warm_many(tasks, progress=None) -> None
fill_all(year, fy_start, fy_end, progress=None) -> None
stats() -> dict
"""
from __future__ import annotations

import threading
import time
from typing import Any, Callable, Iterable, Optional, Tuple

# --------------------------------------------------------------------- #
# TTL buckets
# --------------------------------------------------------------------- #
TTL_KPI:   float = 20.0
TTL_CHART: float = 60.0
TTL_FAST:  float = 20.0

_LOCK = threading.RLock()
_STORE: dict[str, Tuple[float, Any]] = {}


# --------------------------------------------------------------------- #
# Core API
# --------------------------------------------------------------------- #
def _fresh(entry: Optional[Tuple[float, Any]]) -> bool:
    return entry is not None and entry[0] > time.time()


def get(key: str, default: Any = None) -> Any:
    with _LOCK:
        entry = _STORE.get(key)
        if _fresh(entry):
            return entry[1]
    return default


def set(key: str, value: Any, ttl: float = TTL_CHART) -> None:
    with _LOCK:
        _STORE[key] = (time.time() + float(ttl), value)


def invalidate(prefix: str = "") -> None:
    with _LOCK:
        if not prefix:
            _STORE.clear()
            return
        for k in [k for k in _STORE if k.startswith(prefix)]:
            _STORE.pop(k, None)


def cached(key: str,
           ttl: float,
           loader: Callable[[], Any],
           default: Any = None,
           on_error: Optional[Callable[[Exception], None]] = None) -> Any:
    with _LOCK:
        entry = _STORE.get(key)
        if _fresh(entry):
            return entry[1]

    try:
        value = loader()
    except Exception as exc:
        if on_error is not None:
            try:
                on_error(exc)
            except Exception:
                pass
        return default

    with _LOCK:
        _STORE[key] = (time.time() + float(ttl), value)
    return value


# --------------------------------------------------------------------- #
# Warm-up (used by prefetch thread)
# --------------------------------------------------------------------- #
def warm_many(
    tasks: Iterable[Tuple[str, float, Callable[[], Any]]],
    progress: Optional[Callable[[int, int, str], None]] = None,
) -> None:
    tasks = list(tasks)
    total = len(tasks)
    for i, (key, ttl, loader) in enumerate(tasks, 1):
        try:
            value = loader()
        except Exception:
            value = None
        with _LOCK:
            _STORE[key] = (time.time() + float(ttl), value)
        if progress is not None:
            try:
                progress(i, total, key)
            except Exception:
                pass


# --------------------------------------------------------------------- #
# fill_all — the ONE function main.py's prefetch thread calls
# --------------------------------------------------------------------- #
def fill_all(
    year: int,
    fy_start: int,
    fy_end: int,
    progress: Optional[Callable[[int, int, str], None]] = None,
) -> None:
    """
    Warm every key DashboardPage.refresh() reads.

    Parameters
    ----------
    year      : calendar year used by the Monthly Recap Report combo
    fy_start  : start year of the currently-selected financial year
    fy_end    : end year of the same FY (= fy_start + 1)
    progress  : optional callback(done, total, key) after each query
    """
    from database import db_manager  # local import to avoid cycles

    # Ensure dashboard indexes exist BEFORE any query. This DDL can take
    # seconds on a cold DB, so it MUST run on the worker thread.
    try:
        db_manager.ensure_dashboard_indexes()
    except Exception:
        pass

    tasks: list[Tuple[str, float, Callable[[], Any]]] = []

    # ---- KPIs ----
    tasks.append(("dash.stats", TTL_KPI, db_manager.dashboard_stats))
    tasks.append(("dash.month", TTL_KPI, db_manager.current_month_stats))

    # ---- Monthly sales for the current year ----
    tasks.append((
        f"dash.monthly_sales::{year}",
        TTL_CHART,
        lambda y=year: db_manager.monthly_sales("invtest2", "created", y),
    ))

    # ---- Recent invoices / reminders ----
    tasks.append((
        "dash.recent::tax::8",
        TTL_FAST,
        lambda: db_manager.recent_invoices("tax", 8),
    ))
    tasks.append((
        "dash.reminder.clients",
        TTL_FAST,
        db_manager.client_reminder,
    ))
    tasks.append((
        "dash.reminder.quickquote",
        TTL_FAST,
        db_manager.quickquote_reminder,
    ))

    # ---- Donuts (non-FY-scoped) ----
    tasks.append((
        "dash.donut.client_type",
        TTL_CHART,
        db_manager.donut_user_category,
    ))
    tasks.append((
        "dash.donut.country",
        TTL_CHART,
        db_manager.donut_client_country,
    ))
    tasks.append((
        "dash.donut.billed",
        TTL_CHART,
        db_manager.donut_billed_clients,
    ))
    tasks.append((
        "dash.donut.client_type2",
        TTL_CHART,
        db_manager.donut_client_type,
    ))

    # ---- Donuts (FY-scoped) ----
    tasks.append((
        f"dash.donut.consumables::{fy_start}-{fy_end}",
        TTL_CHART,
        lambda s=fy_start, e=fy_end: db_manager.donut_consumables(s, e),
    ))
    tasks.append((
        f"dash.donut.product_category::{fy_start}-{fy_end}",
        TTL_CHART,
        lambda s=fy_start, e=fy_end: db_manager.donut_product_category(s, e),
    ))
    tasks.append((
        f"dash.donut.docs::{fy_start}-{fy_end}",
        TTL_CHART,
        lambda s=fy_start, e=fy_end: db_manager.donut_doc_count(s, e),
    ))

    # ---- FY bar chart ----
    tasks.append((
        f"dash.fy_sales::{fy_start}-{fy_end}",
        TTL_CHART,
        lambda s=fy_start, e=fy_end: db_manager.fy_sales_chart(s, e),
    ))

    warm_many(tasks, progress=progress)


# --------------------------------------------------------------------- #
# Diagnostic
# --------------------------------------------------------------------- #
def stats() -> dict:
    with _LOCK:
        return {k: (v[1] if _fresh(v) else "<stale>")
                for k, v in _STORE.items()}