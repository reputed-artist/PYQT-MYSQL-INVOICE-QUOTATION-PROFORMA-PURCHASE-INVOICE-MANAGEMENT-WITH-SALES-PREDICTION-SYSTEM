"""
Title-bar icon test - brand mark on every window + the right icon per message
kind. Headless (offscreen Qt, no display, no database):

    python test_app_icons.py
    python test_app_icons.py --preview %TEMP%\\aura_icons   # dump PNGs

Checks
------
1. the Sales Aura brand mark resolves (`ui.app_icon.title_icon_path()`)
2. `app_icon()` rasterises a non-null pixmap at every title-bar / taskbar size
3. each message kind draws a *different* icon (the point of the feature: a
   confirmation, a warning and an error must not all look the same)
4. `ui.widgets.confirm / success / info / warning / error` put that kind's icon
   on the message-box **title bar** (`windowIcon()`), while the dialog body
   keeps its `setIcon` / green right-tick
5. `apply()` gives any window/dialog the brand icon (login window, splash,
   plain dialogs) and an explicit icon overrides it

Results are written to `icon_test_result.txt` (UTF-8).
"""
import hashlib
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "icon_test_result.txt")
LOG = open(LOG_PATH, "w", encoding="utf-8", buffering=1)

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def log(*args):
    print(*args, file=LOG)
    print(*args)


from PyQt6.QtCore import QBuffer, QByteArray, QIODevice, QCoreApplication, Qt
from PyQt6.QtGui import QColor, QImage
from PyQt6.QtWidgets import QApplication, QDialog, QMessageBox

QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
app = QApplication(sys.argv)

from ui.app_icon import app_icon, apply, title_icon_path
from ui import icons as I
from ui import widgets as W

FAILURES = []


def check(label, ok, detail=""):
    log(f"{'OK  ' if ok else 'FAIL'} {label}"
        f"{(' -> ' + detail) if detail else ''}")
    if not ok:
        FAILURES.append(label)
    return ok


def fingerprint(pm) -> str:
    """Stable hash of a pixmap's PNG bytes ('are these the same image?')."""
    ba = QByteArray()
    buf = QBuffer(ba)
    buf.open(QIODevice.OpenModeFlag.WriteOnly)
    pm.save(buf, "PNG")
    buf.close()
    return hashlib.sha1(bytes(ba)).hexdigest()


def _rgb_image(icon, px=16):
    """An icon rendered at ``px`` as a straight (un-premultiplied) RGB32 image.

    QIcon stores the pixmaps pre-multiplied, so `pixelColor()` on the raw image
    reads a few units darker than the colour that was painted.
    """
    return icon.pixmap(px, px).toImage().convertToFormat(
        QImage.Format.Format_RGB32)


def close_color(a, b, tol=6) -> bool:
    """True when two colours differ by at most ``tol`` per channel."""
    if a.alpha() != b.alpha():
        return False
    return (abs(a.red() - b.red()) <= tol
            and abs(a.green() - b.green()) <= tol
            and abs(a.blue() - b.blue()) <= tol)


# Sample points that hit the disc but miss the white glyph.
_PROBE = ((14, 8), (2, 8), (8, 4), (8, 12), (12, 12))


def same_icon(a, b, px=16) -> bool:
    """True when two QIcons draw the same icon.

    `cacheKey()` is per *instance*, so two separately built icons showing the
    same picture do not share it - the rendered pixels are the reliable test.
    """
    if a is None or b is None:
        return False
    if a.cacheKey() == b.cacheKey():
        return True
    image_a, image_b = _rgb_image(a, px), _rgb_image(b, px)
    if image_a.size() != image_b.size():
        return False
    return all(close_color(image_a.pixelColor(x, y), image_b.pixelColor(x, y))
               for x, y in _PROBE)


# --------------------------------------------------------------------------- #
# 1 + 2. brand mark resolves and rasterises at every size
# --------------------------------------------------------------------------- #
path = title_icon_path()
check("brand mark resolves", bool(path) and os.path.isfile(path or ""),
      os.path.basename(path or "(none)"))

ICON = app_icon()
check("app_icon() is not null", not ICON.isNull())
sizes_ok = []
for size in I._KIND_SIZES:
    sizes_ok.append((size, not ICON.pixmap(size, size).isNull()))
check("app_icon() pixmaps at every size", all(ok for _, ok in sizes_ok),
      ", ".join(f"{s}:{'ok' if ok else 'null'}" for s, ok in sizes_ok))

# --------------------------------------------------------------------------- #
# 3. one distinct icon per message kind
# --------------------------------------------------------------------------- #
KINDS = ("success", "confirm", "info", "warning", "error")
prints = {kind: fingerprint(I.kind_pixmap(kind, 64)) for kind in KINDS}
check("every kind has its own icon", len(set(prints.values())) == len(KINDS),
      ", ".join(prints))

# the success tick must stay the green disc check_pixmap() always drew
check("success kind == check_pixmap()",
      prints["success"] == fingerprint(I.check_pixmap(64)))
check("kind_icon() carries every size",
      all(not I.kind_icon("warning").pixmap(s, s).isNull()
          for s in I._KIND_SIZES))


# --------------------------------------------------------------------------- #
# 4. the message boxes put the kind icon on their title bar
# --------------------------------------------------------------------------- #
RECORDED = []


class _RecordingBox(QMessageBox):
    """QMessageBox that records itself instead of blocking on exec()."""

    def exec(self):                      # noqa: A003 - Qt API name
        RECORDED.append(self)
        return int(QMessageBox.StandardButton.Ok)


REAL_BOX = W.QMessageBox
REAL_KIND_ICON = W.kind_icon
ICONS_GIVEN = {}


def _spy_kind_icon(kind, *args, **kwargs):
    """Record which kind's icon `_box()` asked for."""
    icon = REAL_KIND_ICON(kind, *args, **kwargs)
    ICONS_GIVEN[str(kind).lower()] = icon
    return icon


W.QMessageBox = _RecordingBox
W.kind_icon = _spy_kind_icon
try:
    for helper, kind, expect_std_icon in (
            ("confirm", "confirm", QMessageBox.Icon.Question),
            ("success", "success", QMessageBox.Icon.NoIcon),
            ("info", "info", QMessageBox.Icon.Information),
            ("warning", "warning", QMessageBox.Icon.Warning),
            ("error", "error", QMessageBox.Icon.Critical)):
        RECORDED.clear()
        ICONS_GIVEN.clear()
        getattr(W, helper)(None, f"{helper} message")
        box = RECORDED[-1] if RECORDED else None
        if box is None:
            check(f"{helper}(): title-bar icon", False, "no box recorded")
            continue
        check(f"{helper}(): title-bar icon",
              same_icon(box.windowIcon(), ICONS_GIVEN.get(kind)),
              f"title='{box.windowTitle()}' "
              f"icon built for {'/'.join(ICONS_GIVEN) or 'nothing'}")
        check(f"{helper}(): dialog body icon", box.icon() == expect_std_icon,
              str(box.icon()))
        # the 16 px title-bar bitmap really is the kind's disc colour
        # (x = 14px is inside the disc but clear of the white glyph)
        centre = _rgb_image(box.windowIcon()).pixelColor(14, 8)
        check(f"{helper}(): 16 px disc colour",
              close_color(centre, QColor(I.KIND_COLORS[kind])), centre.name())

    # success() keeps the green right-tick inside the dialog
    RECORDED.clear()
    W.success(None, "invoice generated")
    check("success(): green tick in the dialog body",
          fingerprint(RECORDED[-1].iconPixmap())
          == fingerprint(I.check_pixmap(56)))

    # a box without a kind falls back to the brand app icon
    box = W._box(None, "Neutral", "no kind given", QMessageBox.Icon.NoIcon,
                 QMessageBox.StandardButton.Ok)
    check("no kind -> brand app icon",
          same_icon(box.windowIcon(), app_icon()))
finally:
    W.QMessageBox = REAL_BOX
    W.kind_icon = REAL_KIND_ICON

# --------------------------------------------------------------------------- #
# 5. every window / dialog is branded
# --------------------------------------------------------------------------- #
from ui.login_window import LoginWindow
from ui.splash_screen import SplashScreen

login = LoginWindow(on_success=lambda row: None)
check("login window title bar",
      login.windowIcon().cacheKey() == app_icon().cacheKey(),
      login.windowTitle())

splash = SplashScreen(duration_ms=60000)
check("splash taskbar icon",
      splash.windowIcon().cacheKey() == app_icon().cacheKey())

dlg = QDialog()
dlg.setWindowTitle("Plain dialog")
apply(dlg)
check("apply(window) -> brand icon",
      dlg.windowIcon().cacheKey() == app_icon().cacheKey())
check("apply(dialog) -> system menu hint",
      bool(dlg.windowFlags() & Qt.WindowType.WindowSystemMenuHint))

apply(dlg, I.kind_icon("error"))
check("apply(window, icon) -> explicit icon wins",
      same_icon(dlg.windowIcon(), I.kind_icon("error")))

for obj in (login, splash, dlg):
    obj.deleteLater()
app.processEvents()

# --------------------------------------------------------------------------- #
# optional: dump the icons so they can be eyeballed
# --------------------------------------------------------------------------- #
if "--preview" in sys.argv:
    out = sys.argv[sys.argv.index("--preview") + 1]
    os.makedirs(out, exist_ok=True)
    for kind in KINDS:
        for px in (16, 32, 64):
            I.kind_pixmap(kind, px).save(
                os.path.join(out, f"kind-{kind}-{px:03d}.png"), "PNG")
    for px in (16, 32, 64, 256):
        ICON.pixmap(px, px).save(os.path.join(out, f"brand-{px:03d}.png"),
                                 "PNG")
    log("previews written to", out)

log("")
log(f"Icon test finished - {len(FAILURES)} failure(s)"
    if FAILURES else "Icon test finished - 0 failures")
for name in FAILURES:
    log("  FAILED:", name)

LOG.close()
sys.exit(1 if FAILURES else 0)
