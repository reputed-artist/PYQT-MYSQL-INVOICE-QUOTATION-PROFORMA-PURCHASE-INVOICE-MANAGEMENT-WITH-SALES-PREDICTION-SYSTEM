# utils/paths.py
"""
Path helpers that work both from source and from a PyInstaller bundle.

Frozen layout assumed: PyInstaller built with
    --contents-directory "."
so sys._MEIPASS == the folder containing Sales Aura.exe.
"""
import os
import sys


def _is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def app_root() -> str:
    """
    Folder containing the deployed app (exe + its read-only data folders).

    - Frozen : sys._MEIPASS (== exe folder when built with --contents-directory ".")
    - Source : project root
    """
    if _is_frozen():
        base = getattr(sys, "_MEIPASS", None)
        if base and os.path.isdir(base):
            return base
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def resource_path(*parts: str) -> str:
    """Read-only assets shipped with the app."""
    return os.path.join(app_root(), *parts)


def user_data_dir() -> str:
    """
    Writable per-user folder for the SQLite DB, uploads, logs, backups.
    Created on demand. Never touched by the installer.
    """
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA") \
               or os.path.expanduser("~")
    elif sys.platform == "darwin":
        base = os.path.expanduser("~/Library/Application Support")
    else:
        base = os.environ.get("XDG_DATA_HOME") \
               or os.path.expanduser("~/.local/share")
    d = os.path.join(base, "Sales Aura")
    os.makedirs(d, exist_ok=True)
    return d


def user_subdir(*parts: str) -> str:
    """A named subfolder inside user_data_dir(). Created on demand."""
    d = os.path.join(user_data_dir(), *parts)
    os.makedirs(d, exist_ok=True)
    return d


def user_db_path(db_name: str = "sales_aura.db") -> str:
    """
    Absolute path to the LIVE SQLite DB. Always under
        %LOCALAPPDATA%\\Sales Aura\\database\\<db_name>
    The parent folder is created if missing.
    """
    db_dir = user_subdir("database")
    return os.path.join(db_dir, db_name)


def bundled_seed_db(seed_name: str = "sales_aura.db") -> str:
    """
    Path to the SEED DB shipped with the app.
    Looks under  <app_root>\\data\\<seed_name>  first, then
    <app_root>\\database\\<seed_name>  (either is fine — the config
    just needs to know which one you actually ship).
    """
    for sub in ("data", "database"):
        p = resource_path(sub, seed_name)
        if os.path.isfile(p):
            return p
    # Fall back to the primary location so callers get a path even if missing
    return resource_path("data", seed_name)