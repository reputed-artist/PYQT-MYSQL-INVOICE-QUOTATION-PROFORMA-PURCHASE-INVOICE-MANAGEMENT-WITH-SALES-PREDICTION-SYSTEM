"""Icon action buttons for table rows (drawn white icons on coloured buttons).

Icons are vector-drawn with QPainter (no font / emoji dependency, so they look
identical on every platform) and rasterised at the *final* pixel size instead of
being down-scaled - that keeps the strokes solid white rather than fading into
the button colour.

The same painters build the **message-kind icons** (`kind_pixmap()` /
`kind_icon()`): a tinted disc + white glyph per dialog kind, which is what the
message boxes put on their *title bar* (tick = success, ? = confirmation,
! = warning, x = error, i = info).
"""
from PyQt6.QtWidgets import QPushButton
from PyQt6.QtCore import QSize, QRectF, Qt, QPointF
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QPen, QPainterPath

from config import COLORS


def _stroke_width(rect):
    """Pen width that stays ~2px solid at the rendered size."""
    return max(1.8, rect.width() * 0.17)


def _paint_edit(p, r):
    """Pen / pencil glyph (fa-pencil)."""
    p.setPen(QPen(QColor("#ffffff"), _stroke_width(r), Qt.PenStyle.SolidLine,
                  Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    w, h = r.width(), r.height()
    # pencil barrel with a pointed tip
    path = QPainterPath()
    path.moveTo(w * 0.70, h * 0.08)
    path.lineTo(w * 0.92, h * 0.30)
    path.lineTo(w * 0.34, h * 0.88)
    path.lineTo(w * 0.06, h * 0.94)
    path.lineTo(w * 0.12, h * 0.66)
    path.closeSubpath()
    p.drawPath(path)
    # nib line between tip and barrel
    p.drawLine(QPointF(w * 0.60, h * 0.18), QPointF(w * 0.82, h * 0.40))


def _paint_delete(p, r):
    """Trash bin glyph (fa-trash)."""
    p.setPen(QPen(QColor("#ffffff"), _stroke_width(r), Qt.PenStyle.SolidLine,
                  Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    w, h = r.width(), r.height()
    # lid
    p.drawLine(QPointF(w * 0.04, h * 0.20), QPointF(w * 0.96, h * 0.20))
    # handle
    path = QPainterPath()
    path.moveTo(w * 0.34, h * 0.20)
    path.lineTo(w * 0.34, h * 0.05)
    path.lineTo(w * 0.66, h * 0.05)
    path.lineTo(w * 0.66, h * 0.20)
    p.drawPath(path)
    # body (tapered)
    body = QPainterPath()
    body.moveTo(w * 0.16, h * 0.32)
    body.lineTo(w * 0.26, h * 0.96)
    body.lineTo(w * 0.74, h * 0.96)
    body.lineTo(w * 0.84, h * 0.32)
    p.drawPath(body)
    # ribs - only when there is room for them to stay legible
    if r.width() >= 20:
        p.drawLine(QPointF(w * 0.42, h * 0.46), QPointF(w * 0.45, h * 0.84))
        p.drawLine(QPointF(w * 0.58, h * 0.46), QPointF(w * 0.55, h * 0.84))


def _paint_view(p, r):
    """Eye glyph (fa-eye) - view icon."""
    p.setPen(QPen(QColor("#ffffff"), _stroke_width(r), Qt.PenStyle.SolidLine,
                  Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    w, h = r.width(), r.height()
    # eye outline (two arcs meeting at the corners)
    path = QPainterPath()
    path.moveTo(w * 0.04, h * 0.50)
    path.quadTo(w * 0.50, h * 0.02, w * 0.96, h * 0.50)
    path.quadTo(w * 0.50, h * 0.98, w * 0.04, h * 0.50)
    path.closeSubpath()
    p.drawPath(path)
    # pupil (circle)
    p.drawEllipse(QPointF(w * 0.50, h * 0.50), w * 0.16, h * 0.16)


def _paint_check(p, r):
    """Right-tick glyph (fa-check) - the 'saved / generated' confirmation."""
    p.setPen(QPen(QColor("#ffffff"), _stroke_width(r), Qt.PenStyle.SolidLine,
                  Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    p.setBrush(Qt.BrushStyle.NoBrush)
    w, h = r.width(), r.height()
    path = QPainterPath()
    path.moveTo(r.left() + w * 0.04, r.top() + h * 0.56)
    path.lineTo(r.left() + w * 0.37, r.top() + h * 0.92)
    path.lineTo(r.left() + w * 0.98, r.top() + h * 0.12)
    p.drawPath(path)


def _dot(p, r, fx, fy):
    """Filled white dot - the foot of the '?' and '!' glyphs."""
    radius = _stroke_width(r) * 0.58
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor("#ffffff"))
    p.drawEllipse(QPointF(r.left() + r.width() * fx,
                          r.top() + r.height() * fy), radius, radius)


def _paint_question(p, r):
    """Question mark glyph - 'are you sure?' confirmations."""
    p.setPen(QPen(QColor("#ffffff"), _stroke_width(r), Qt.PenStyle.SolidLine,
                  Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    p.setBrush(Qt.BrushStyle.NoBrush)
    w, h = r.width(), r.height()
    hook = QPainterPath()
    hook.moveTo(r.left() + w * 0.18, r.top() + h * 0.30)
    hook.cubicTo(r.left() + w * 0.20, r.top() + h * 0.00,
                 r.left() + w * 0.82, r.top() - h * 0.02,
                 r.left() + w * 0.80, r.top() + h * 0.32)
    hook.cubicTo(r.left() + w * 0.78, r.top() + h * 0.54,
                 r.left() + w * 0.50, r.top() + h * 0.50,
                 r.left() + w * 0.50, r.top() + h * 0.70)
    p.drawPath(hook)
    _dot(p, r, 0.50, 0.96)


def _paint_exclaim(p, r):
    """Exclamation mark glyph - warnings."""
    p.setPen(QPen(QColor("#ffffff"), _stroke_width(r), Qt.PenStyle.SolidLine,
                  Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    w, h = r.width(), r.height()
    p.drawLine(QPointF(r.left() + w * 0.50, r.top() + h * 0.02),
               QPointF(r.left() + w * 0.50, r.top() + h * 0.64))
    _dot(p, r, 0.50, 0.96)


def _paint_cross(p, r):
    """X glyph - errors / critical failures."""
    p.setPen(QPen(QColor("#ffffff"), _stroke_width(r), Qt.PenStyle.SolidLine,
                  Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    w, h = r.width(), r.height()
    p.drawLine(QPointF(r.left() + w * 0.06, r.top() + h * 0.06),
               QPointF(r.left() + w * 0.94, r.top() + h * 0.94))
    p.drawLine(QPointF(r.left() + w * 0.94, r.top() + h * 0.06),
               QPointF(r.left() + w * 0.06, r.top() + h * 0.94))


def _paint_info(p, r):
    """Lower-case 'i' glyph - information messages."""
    p.setPen(QPen(QColor("#ffffff"), _stroke_width(r), Qt.PenStyle.SolidLine,
                  Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    w, h = r.width(), r.height()
    p.drawLine(QPointF(r.left() + w * 0.50, r.top() + h * 0.34),
               QPointF(r.left() + w * 0.50, r.top() + h * 0.98))
    _dot(p, r, 0.50, 0.08)


_PAINTERS = {"edit": _paint_edit, "delete": _paint_delete, "view": _paint_view,
             "check": _paint_check}

# Rendered icon size in pixels (also the rasterisation size - no down-scaling).
ICON_PX = 16


def vector_icon(name: str, color: str = "#ffffff", size: int = ICON_PX) -> QIcon:
    """Vector-drawn icon (pen = edit, bin = delete, eye = view) - font independent.

    The glyph is rasterised at `size` so the strokes stay crisp and fully white.
    """
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    _PAINTERS.get(name, _paint_delete)(p, QRectF(size * 0.16, size * 0.16,
                                                 size * 0.68, size * 0.68))
    p.end()
    return QIcon(pm)


def icon_button(kind, object_name, tooltip=""):
    """Square button with a solid white drawn icon
    (pen = edit, bin = delete, eye = view, tick = check).

    kind: "edit" | "delete" | "view" | "check"
    """
    b = QPushButton()
    b.setIcon(vector_icon(kind, "#ffffff", ICON_PX))
    b.setIconSize(QSize(ICON_PX, ICON_PX))
    b.setObjectName(object_name)
    b.setFixedSize(30, 26)
    b.setToolTip(tooltip or ("Edit" if kind == "edit" else "Delete"))
    return b


def check_pixmap(size=64, bg="#00a65a", fg="#ffffff") -> QPixmap:
    """Green disc with a white right-tick - the confirmation icon.

    Used as `QMessageBox.setIconPixmap()` by `ui.widgets.success()` so every
    'generated / saved / updated' dialog shows a tick instead of the stock
    information glyph. Vector-drawn like the row-action icons, so it stays
    crisp at any dialog scale. Thin wrapper over `kind_pixmap("success", ...)`.
    """
    return kind_pixmap("success", size, bg, fg)


# --------------------------------------------------------------------------- #
# Message kinds (title bar icons for the message boxes)
# --------------------------------------------------------------------------- #
# kind -> disc colour, taken from the AdminLTE palette in config.COLORS.
KIND_COLORS = {
    "success": COLORS["success"],      # green  + tick
    "confirm": COLORS["primary"],      # blue   + ?
    "question": COLORS["primary"],
    "info": COLORS["info"],            # aqua   + i
    "warning": COLORS["warning"],      # amber  + !
    "error": COLORS["danger"],         # red    + x
    "critical": COLORS["danger"],
}

KIND_GLYPHS = {
    "success": _paint_check,
    "confirm": _paint_question,
    "question": _paint_question,
    "info": _paint_info,
    "warning": _paint_exclaim,
    "error": _paint_cross,
    "critical": _paint_cross,
}

# Sizes rasterised into `kind_icon()` (16 = title bar, 32/48 = taskbar).
_KIND_SIZES = (16, 20, 24, 32, 48, 64, 128)


def kind_pixmap(kind, size=64, bg=None, fg="#ffffff") -> QPixmap:
    """Coloured disc + white glyph for one message kind.

    kind: ``"success"`` (tick) | ``"confirm"`` / ``"question"`` (?) |
    ``"info"`` (i) | ``"warning"`` (!) | ``"error"`` / ``"critical"`` (x).
    An unknown kind falls back to the information glyph on the brand blue.

    ``bg`` overrides the disc colour, ``fg`` is kept for API compatibility
    (the glyphs are drawn white, like every other icon in this module).
    """
    kind = str(kind or "").lower()
    glyph = KIND_GLYPHS.get(kind, _paint_info)
    disc = bg or KIND_COLORS.get(kind, COLORS["primary"])

    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)

    # filled disc + slightly darker rim
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(disc))
    p.drawEllipse(QRectF(size * 0.03, size * 0.03,
                         size * 0.94, size * 0.94))
    p.setPen(QPen(QColor(0, 0, 0, 38), max(1.0, size * 0.03)))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawEllipse(QRectF(size * 0.03, size * 0.03,
                         size * 0.94, size * 0.94))

    # white glyph, same box the success tick always used
    p.setPen(Qt.PenStyle.NoPen)
    glyph(p, QRectF(size * 0.24, size * 0.24, size * 0.52, size * 0.52))

    p.end()
    return pm


def kind_icon(kind, size=None, bg=None, fg="#ffffff") -> QIcon:
    """`kind_pixmap()` as a QIcon (the title-bar icon of a message box).

    Without ``size`` a pixmap is added for every standard icon size, so the
    16 px title-bar copy and the 32 px taskbar / alt-tab copy are both crisp
    instead of one bitmap being scaled around.
    """
    icon = QIcon()
    for px in ([size] if size else _KIND_SIZES):
        icon.addPixmap(kind_pixmap(kind, px, bg, fg))
    return icon


def check_icon(size=ICON_PX, bg="#00a65a", fg="#ffffff") -> QIcon:
    """`check_pixmap()` as a QIcon (buttons / menu items)."""
    return kind_icon("success", size, bg, fg)


