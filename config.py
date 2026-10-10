# config.py
"""
C4 PyQt — Application configuration.
Local SQLite storage configuration.
"""
import os
import shutil
import sys

from utils.paths import (
    app_root,
    bundled_seed_db,
    resource_path,
    user_data_dir,
    user_subdir,
    user_db_path,
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

APP_DIR_NAME = "Sales Aura"
DB_NAME      = "sales_aura.db"

# ---------------------------------------------------------------------------
# Writable locations (always under %LOCALAPPDATA%\Sales Aura on Windows)
# ---------------------------------------------------------------------------
UPLOAD_DIR = user_subdir("uploads")
BACKUP_DIR = user_subdir("backups")
PDF_DIR    = user_subdir("pdf")
LOG_DIR    = user_subdir("logs")
DB_DIR     = user_subdir("database")

# Read-only asset folder inside the bundle
BUNDLE_IMG_DIR = resource_path("dist", "img")


def is_frozen() -> bool:
    """True when running from a PyInstaller-built exe."""
    return bool(getattr(sys, "frozen", False))


def _ensure_dir(path: str) -> str:
    try:
        os.makedirs(path, exist_ok=True)
    except Exception:
        pass
    return path


# ---------------------------------------------------------------------------
# Database — live path + one-time seed copy
# ---------------------------------------------------------------------------
def get_db_path() -> str:
    """
    Absolute path to the LIVE database.

    Always writable, always under %LOCALAPPDATA%\\Sales Aura\\database\\.
    Same path whether frozen or running from source (so a dev DB and a
    production DB never collide — dev uses its own copy).
    """
    if is_frozen():
        return user_db_path(DB_NAME)
    # Running from source: keep the dev DB beside the project
    return os.path.join(BASE_DIR, "data", DB_NAME)


def initialize_database() -> str:
    """
    Return the live DB path, creating it once from the bundled seed
    if it does not exist yet. Safe to call on every startup.
    """
    target = get_db_path()
    _ensure_dir(os.path.dirname(target))

    if os.path.exists(target):
        return target

    # Locate the seed DB that shipped with the app
    if is_frozen():
        bundled_db = bundled_seed_db(DB_NAME)
    else:
        bundled_db = os.path.join(BASE_DIR, "data", DB_NAME)

    if not os.path.isfile(bundled_db):
        # The seed is missing — create an empty DB. The app's
        # init_sqlite_database() will build the schema on first query.
        try:
            open(target, "a").close()
        except Exception:
            pass
        return target

    try:
        shutil.copy2(bundled_db, target)
    except Exception:
        # Fall back to an empty DB rather than refusing to start
        try:
            open(target, "a").close()
        except Exception:
            pass
    return target


# Live DB path — computed once at import time.
DB_FILE = initialize_database()

# Settings → Backup destination
BACKUP_DIR = _ensure_dir(os.path.join(os.path.dirname(DB_FILE), "backups"))

# ---------------------------------------------------------------------------
# DSN-style config consumed by db_manager
# ---------------------------------------------------------------------------
DB_CONFIG = {
    "engine":   "sqlite",
    "database": DB_FILE,
}

# ---------------------------------------------------------------------------
# Branding
# ---------------------------------------------------------------------------
APP_TITLE = "AntDev"
LOGO_MINI = "CT"
LOGO_FULL = "AntDev"

ORIG_PROJECT_ROOT = r"c:\xampp\htdocs\C4"
ORIG_UPLOAD_DIR   = os.path.join(ORIG_PROJECT_ROOT, "public", "uploads")

DEFAULT_HSN = "8443"

COLORS = {
    "sidebar_bg":    "#222d32",
    "sidebar_hover": "#1e282c",
    "sidebar_link":  "#b8c7ce",
    "header_bg":     "#3c8dbc",
    "content_bg":    "#ecf0f5",
    "box_border":    "#f4f4f4",
    "success":       "#00a65a",
    "danger":        "#dd4b39",
    "warning":       "#f39c12",
    "info":          "#00c0ef",
    "primary":       "#3c8dbc",
    "purple":        "#605ca8",
    "navy":          "#001f3f",
    "teal":          "#39cccc",
    "aqua":          "#00c0ef",
    "green":         "#00a65a",
    "red":           "#dd4b39",
}