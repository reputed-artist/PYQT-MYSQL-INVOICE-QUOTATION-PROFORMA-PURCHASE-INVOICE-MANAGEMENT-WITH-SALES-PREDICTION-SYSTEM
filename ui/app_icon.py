"""
Application / window icon (title bar + taskbar) shared by every window.

Why this module exists
----------------------
Windows draws the *window icon* on the left of every title bar. Nothing in the
app ever called ``setWindowIcon()``, so the login window, the dashboard and all
dialogs showed Qt's stock "unidentified" icon instead of a brand icon.

Resolution order
----------------
1. ``C4_APP_ICON`` (environment variable) - overrides everything.
2. The **Sales Aura brand mark** (``dist/img/sales-aura-icon.png``, drawn by
   ``tools/make_brand_logo.py``) - what every title bar / taskbar entry shows.
3. The company logo stored on the `admin` row, then ``APP_ICON_NAMES`` inside
   this project's ``dist/img`` (``dist/img/uploads`` included) - the folder
   every other asset lookup uses - and the PHP project's ``public/dist/img``.
4. A vector mark drawn with QPainter (Sales Aura style: blue -> violet rounded
   tile, ascending bars and an up arrow) so a branded icon always exists, even
   before the PNG is dropped in.

Simply save the logo as ``pyqt_app/dist/img/appicon.png`` (or
``dist/img/Sales Aura.png``) and it is picked up automatically everywhere,
because the drawn mark is only a fallback.

The icons are rasterised at the standard sizes and added to the QIcon, so the
16 px title-bar copy stays crisp instead of being down-scaled from 1000+ px.
"""
import os

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import (QColor, QIcon, QLinearGradient, QPainter,
                         QPainterPath, QPen, QPixmap)

from config import ORIG_PROJECT_ROOT

# File names looked up (first hit wins), in both projects' image folders.
APP_ICON_NAMES = (
    "logo.png", "Logo.png", "login-logo.png", "company-logo.png",
    "AntDev.png", "antdev.png", "Backup-Logo.png", "backup-logo.png",
    "appicon.png", "app_icon.png", "AppIcon.png", "AppIcon.ico",
    "Sales Aura.png", "Sales-Aura.png", "sales-aura.png",
    "salesaura.png", "sales_aura.png", "aura.png",
)

# Sales Aura brand mark - looked up BEFORE the company logo, so every window
# title bar / taskbar entry shows the product logo even after another company
# logo is uploaded in Settings (`C4_APP_ICON` still overrides everything).
# "sales-aura-icon.png" is the square chip version (see tools/make_brand_logo.py).
BRAND_ICON_NAMES = (
    "sales-aura-icon.png", "sales_aura_icon.png", "Sales Aura Icon.png",
    "sales-aura.png", "sales_aura.png", "salesaura.png", "Sales Aura.png",
)

# The plain mark (no chip) - what the splash screen draws.
BRAND_LOGO_NAMES = (
    "sales-aura.png", "sales_aura.png", "salesaura.png", "Sales Aura.png",
)

# Sizes rasterised into the QIcon (title bar 16, taskbar 32/48, pickers 256).
_SIZES = (16, 20, 24, 32, 48, 64, 128, 256)

# Sales Aura palette (blue -> violet) matching the logo.
_BLUE = "#2f7ef7"
_VIOLET = "#7b3ff2"


def _app_base_dir() -> str:
    """Walk up until the folder that holds ``dist/`` is found (like theme.py)."""
    here = os.path.dirname(os.path.abspath(__file__))
    cur = here
    for _ in range(6):
        if os.path.isdir(os.path.join(cur, "dist")):
            return cur
        parent = os.path.dirname(cur)
        if parent == cur:
            break
        cur = parent
    return os.path.abspath(os.path.join(here, ".."))


_PYQT_BASE = _app_base_dir()


def _search_dirs():
    """Image folders searched for the logo, nearest project first."""
    pyqt_img = os.path.join(_PYQT_BASE, "dist", "img")
    php_img = os.path.join(ORIG_PROJECT_ROOT, "public", "dist", "img")
    dirs = [
        pyqt_img,
        os.path.join(pyqt_img, "uploads"),
        php_img,
        os.path.join(php_img, "uploads"),
        os.path.join(ORIG_PROJECT_ROOT, "public", "img"),
    ]
    seen = []
    for d in dirs:
        if d not in seen:
            seen.append(d)
    return seen


def _db_logo_name():
    """Try to read the company logo filename (picturelogo) from the admin table."""
    try:
        from database import db_manager
        admin = db_manager.get_admin()
        if admin:
            for k in ("picturelogo", "logo", "c_logo"):
                val = (admin.get(k) or "").strip()
                if val:
                    return val
    except Exception:
        pass
    return None


def brand_path():
    """Absolute path of the Sales Aura brand mark, or ``None``.

    ``C4_APP_ICON`` still wins, so the mark can be swapped without touching
    the project.
    """
    env = os.environ.get("C4_APP_ICON", "").strip()
    if env and os.path.isfile(env):
        return env

    for folder in _search_dirs():
        for name in BRAND_ICON_NAMES:
            path = os.path.join(folder, name)
            if os.path.isfile(path):
                return path
    return None


def title_icon_path():
    """Logo file for the *window* icon (title bar, taskbar, alt-tab).

    The Sales Aura mark wins over the company logo so every window of the app
    is branded the same way; `logo_path()` (company logo -> legacy names ->
    drawn mark) remains the fallback chain.
    """
    return brand_path() or logo_path()


def logo_path():
    """Absolute path of the logo file to use, or ``None`` (-> drawn mark).

    Resolution order: ``C4_APP_ICON`` (environment variable) -> the Sales Aura
    brand mark (what the splash screen draws) -> the company logo stored on
    the `admin` row -> the known logo file names in either project.
    """
    env = os.environ.get("C4_APP_ICON", "").strip()
    if env and os.path.isfile(env):
        return env

    dirs = _search_dirs()

    # 1. Sales Aura brand mark (splash screen / large logo)
    for name in BRAND_LOGO_NAMES:
        for folder in dirs:
            path = os.path.join(folder, name)
            if os.path.isfile(path):
                return path

    # 2. Company logo from database
    db_logo = _db_logo_name()
    if db_logo:
        for folder in dirs:
            path = os.path.join(folder, db_logo)
            if os.path.isfile(path):
                return path

    # 3. Known brand / logo file names
    for folder in dirs:
        for name in APP_ICON_NAMES:
            path = os.path.join(folder, name)
            if os.path.isfile(path):
                return path
    return None


def _rounded(pm: QPixmap, size: int, radius: float = 0.20) -> QPixmap:
    """Round the corners of a square pixmap so a flat logo tile looks native."""
    out = QPixmap(size, size)
    out.fill(Qt.GlobalColor.transparent)
    p = QPainter(out)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    path = QPainterPath()
    path.addRoundedRect(QRectF(0, 0, size, size), size * radius, size * radius)
    p.setClipPath(path)
    p.drawPixmap(0, 0, pm)
    p.end()
    return out


def _scaled_from_file(path: str):
    """Pre-scaled (rounded) pixmaps for every icon size; [] when unreadable."""
    src = QPixmap(path)
    if src.isNull():
        return []
    out = []
    for size in _SIZES:
        pm = src.scaled(size, size,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation)
        if pm.width() != size or pm.height() != size:
            # centre a non-square logo on a transparent square canvas
            canvas = QPixmap(size, size)
            canvas.fill(Qt.GlobalColor.transparent)
            p = QPainter(canvas)
            p.drawPixmap((size - pm.width()) // 2,
                         (size - pm.height()) // 2, pm)
            p.end()
            pm = canvas
        out.append(_rounded(pm, size))
    return out


def _drawn_mark(size: int) -> QPixmap:
    """Fallback 'Sales Aura' mark: gradient tile + ascending bars + up arrow."""
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)

    s = float(size)

    # ---- rounded tile with the brand gradient ----
    grad = QLinearGradient(0, 0, s, s)
    grad.setColorAt(0.0, QColor(_BLUE))
    grad.setColorAt(1.0, QColor(_VIOLET))
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(grad)
    radius = s * 0.22
    p.drawRoundedRect(QRectF(s * 0.02, s * 0.02, s * 0.96, s * 0.96),
                      radius, radius)

    # ---- ascending bars (white, slightly translucent) ----
    bar_w = s * 0.115
    base_y = s * 0.79
    x = s * 0.19
    for h in (0.20, 0.30, 0.40, 0.50):
        p.setBrush(QColor(255, 255, 255, 232))
        p.drawRoundedRect(QRectF(x, base_y - s * h, bar_w, s * h),
                          bar_w * 0.35, bar_w * 0.35)
        x += bar_w + s * 0.055

    # ---- rising arrow drawn over the bars ----
    pen = QPen(QColor("#ffffff"), max(1.6, s * 0.085), Qt.PenStyle.SolidLine,
               Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawLine(QPointF(s * 0.25, base_y - s * 0.02), QPointF(s * 0.70, s * 0.30))

    head = QPainterPath()
    head.moveTo(s * 0.57, s * 0.19)
    head.lineTo(s * 0.85, s * 0.15)
    head.lineTo(s * 0.77, s * 0.43)
    head.closeSubpath()
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor("#ffffff"))
    p.drawPath(head)

    p.end()
    return pm


_ICON = None


def app_icon() -> QIcon:
    """The application icon (brand mark file when present, drawn mark otherwise)."""
    global _ICON
    if _ICON is not None:
        return _ICON

    icon = QIcon()
    path = title_icon_path()
    if path:
        for pm in _scaled_from_file(path):
            icon.addPixmap(pm)
    if icon.isNull():
        for size in _SIZES:
            icon.addPixmap(_drawn_mark(size))

    _ICON = icon
    return icon


def reload_icon() -> QIcon:
    """Forget the cached icon (call after a new company logo is uploaded)."""
    global _ICON
    _ICON = None
    return app_icon()


def apply(widget, icon=None):
    """Set the brand icon on one window or dialog (title bar + taskbar icon).

    ``icon`` - a QIcon to use instead of the app icon. That is how the message
    boxes get the icon that matches their kind (see `ui.icons.kind_icon()`:
    tick for success, question mark for a confirmation, "!" for a warning,
    cross for an error).

    On Windows, top-level QDialogs without min/max buttons have their title bar
    icons suppressed by the Windows Desktop Window Manager (DWM). This helper
    sets the window icon and ensures the window hints allow DWM to render it.
    """
    if widget is None:
        return widget

    try:
        widget.setWindowIcon(icon if icon is not None else app_icon())
    except Exception:
        pass

    try:
        from PyQt6.QtWidgets import QDialog
        flags = widget.windowFlags()
        is_dialog = bool(flags & Qt.WindowType.Dialog) or isinstance(widget, QDialog)
        has_minmax = bool(flags & Qt.WindowType.WindowMinMaxButtonsHint)
        if is_dialog and not has_minmax:
            widget.setWindowFlags(flags | Qt.WindowType.WindowSystemMenuHint | Qt.WindowType.WindowMinMaxButtonsHint)
        elif not bool(flags & Qt.WindowType.WindowSystemMenuHint):
            widget.setWindowFlags(flags | Qt.WindowType.WindowSystemMenuHint)
    except Exception:
        pass

    return widget
