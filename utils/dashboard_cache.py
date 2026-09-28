"""
Cached wrappers around every db_manager call the dashboard uses.

The dashboard makes ~12 DB calls per load. With 1000+ clients and hundreds
of invoices, this is slow. This module caches each result for a TTL that
matches its volatility:

    - dashboard_stats           ->  5 min  (KPIs, changes on any save)
    - current_month_stats       ->  5 min
    - monthly_sales             -> 10 min  (per year, keyed)
    - fy_main_chart             ->  5 min  (per FY, keyed)
    - fy_sales_chart            ->  5 min  (per FY, keyed)
    - annual_turnover           -> 10 min
    - location_tree             -> 10 min
    - donut_*                   -> 10 min  (per FY where relevant)
    - top_products_sold         ->  5 min  (per FY, keyed)
    - client_reminder           ->  2 min  (changes as proformas come in)
    - quickquote_reminder       ->  2 min
    - recent_invoices           ->  2 min  (per doc, keyed)
    - recent_reports            ->  not cached (runs on demand)

Any write to a document (invoice / proforma / quote / purchase / payment)
should call `invalidate_dashboard()` to force a refresh on next load.
"""
from database import db_manager
from utils.cache import cache


# --------------------------------------------------------------------- TTLs
TTL_KPI = 300            #  5 min
TTL_CHART = 600          # 10 min
TTL_FAST = 120           #  2 min


# ------------------------------------------------------------------- getters
def get_dashboard_stats():
    return cache.get("dash.stats")


def get_current_month_stats():
    return cache.get("dash.month")


def get_monthly_sales(year):
    return cache.get(f"dash.monthly_sales::{year}")


def get_fy_main_chart(sy, ey):
    return cache.get(f"dash.fy_main::{sy}-{ey}")


def get_fy_sales_chart(sy, ey):
    return cache.get(f"dash.fy_sales::{sy}-{ey}")


def get_annual_turnover():
    return cache.get("dash.annual")


def get_location_tree():
    return cache.get("dash.locations")


def get_donut(key, sy=None, ey=None):
    k = f"dash.donut.{key}"
    if sy is not None and ey is not None:
        k += f"::{sy}-{ey}"
    return cache.get(k)


def get_top_products(sy, ey):
    return cache.get(f"dash.top_products::{sy}-{ey}")


def get_client_reminder():
    return cache.get("dash.reminder.clients")


def get_quickquote_reminder():
    return cache.get("dash.reminder.quickquote")


def get_recent_invoices(doc, limit=8):
    return cache.get(f"dash.recent::{doc}::{limit}")


# ------------------------------------------------------------------- fillers
def fill_all(year, sy, ey):
    """Run every dashboard query once and cache the results.

    Called by the dashboard page when the cache is cold or after a manual
    refresh. Any exception in an individual call is swallowed and stored
    as an empty value, so a single broken query doesn't blank the page.
    """
    def safe(fn, default):
        try:
            return fn()
        except Exception:
            return default

    cache.set("dash.stats", safe(db_manager.dashboard_stats, {}),
              ttl=TTL_KPI)
    cache.set("dash.month", safe(db_manager.current_month_stats, {}),
              ttl=TTL_KPI)
    cache.set(f"dash.monthly_sales::{year}",
              safe(lambda: db_manager.monthly_sales("invtest2", "created",
                                                    year), [0] * 12),
              ttl=TTL_CHART)
    cache.set(f"dash.fy_main::{sy}-{ey}",
              safe(lambda: db_manager.fy_invoice_stats(sy, ey), {}),
              ttl=TTL_KPI)
    cache.set(f"dash.fy_sales::{sy}-{ey}",
              safe(lambda: db_manager.fy_sales_chart(sy, ey), []),
              ttl=TTL_CHART)
    cache.set("dash.annual",
              safe(db_manager.annual_turnover_chart, []),
              ttl=TTL_CHART)
    cache.set("dash.locations",
              safe(db_manager.location_tree, []),
              ttl=TTL_CHART)
    cache.set(f"dash.top_products::{sy}-{ey}",
              safe(lambda: db_manager.top_products_sold(sy, ey), []),
              ttl=TTL_KPI)
    cache.set("dash.reminder.clients",
              safe(db_manager.client_reminder, []),
              ttl=TTL_FAST)
    cache.set("dash.reminder.quickquote",
              safe(db_manager.quickquote_reminder, []),
              ttl=TTL_FAST)
    cache.set("dash.recent::tax::8",
              safe(lambda: db_manager.recent_invoices("tax", 8), []),
              ttl=TTL_FAST)

    # Donuts — keyed by FY where applicable
    donuts = {
        "consumables":      lambda: db_manager.donut_consumables(sy, ey),
        "client_type":      db_manager.donut_user_category,
        "country":          db_manager.donut_client_country,
        "product_category": lambda: db_manager.donut_product_category(sy, ey),
        "billed":           db_manager.donut_billed_clients,
        "docs":             lambda: db_manager.donut_doc_count(sy, ey),
        "client_type2":     db_manager.donut_client_type,
    }
    for key, fn in donuts.items():
        k = f"dash.donut.{key}"
        if key in ("consumables", "product_category", "docs"):
            k += f"::{sy}-{ey}"
        cache.set(k, safe(fn, []), ttl=TTL_CHART)


# ---------------------------------------------------------------- invalidation
def invalidate_dashboard():
    """Call this after any save/delete that affects dashboard numbers.

    Invoices, proformas, quotes, purchases, payments, clients, products,
    accounts — anything that could change a KPI or chart.
    """
    cache.invalidate_all()