"""
C4 PyQt - Application configuration
Mirrors CodeIgniter .env / app/Config values of the original project.
"""
import os

# ---------------------------------------------------------------------------
# Database (from c:\xampp\htdocs\C4\.env  ->  database.default.*)
# ---------------------------------------------------------------------------
DB_CONFIG = {
    "host": "localhost",
    "port": 3306,
    "user": "root",
    "password": "",
    "database": "db",
    "charset": "utf8mb4",
}

# ---------------------------------------------------------------------------
# Branding (from app/Views/Include/header.php)
# ---------------------------------------------------------------------------
APP_TITLE = "AntDev"
LOGO_MINI = "CT"          # <span class="logo-mini"><b>C</b>T</span>
LOGO_FULL = "AntDev"      # <span class="logo-lg"><b>Ant</b>Dev</span>

# Original project root (used to re-use uploaded pictures / product images)
ORIG_PROJECT_ROOT = r"c:\xampp\htdocs\C4"
ORIG_UPLOAD_DIR = os.path.join(ORIG_PROJECT_ROOT, "public", "uploads")

# Default HSN used by the invoice forms
DEFAULT_HSN = "8443"

# AdminLTE colour palette replicated in ui/theme.py
COLORS = {
    "sidebar_bg": "#222d32",
    "sidebar_hover": "#1e282c",
    "sidebar_link": "#b8c7ce",
    "header_bg": "#3c8dbc",
    "content_bg": "#ecf0f5",
    "box_border": "#f4f4f4",
    "success": "#00a65a",
    "danger": "#dd4b39",
    "warning": "#f39c12",
    "info": "#00c0ef",
    "primary": "#3c8dbc",
    "purple": "#605ca8",
    "navy": "#001f3f",
    "teal": "#39cccc",
    "aqua": "#00c0ef",
    "green": "#00a65a",
    "red": "#dd4b39",
}
