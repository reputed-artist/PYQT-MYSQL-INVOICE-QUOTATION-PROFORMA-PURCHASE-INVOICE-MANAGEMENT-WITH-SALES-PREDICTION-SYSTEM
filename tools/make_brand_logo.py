"""
Sales Aura brand assets - the logo shown on every window title bar / taskbar
entry and on the splash screen.

Run it once (and again whenever the mark changes):

    cd c:\\xampp\\htdocs\\C4\\pyqt_app
    python tools/make_brand_logo.py
    python tools/make_brand_logo.py --preview %TEMP%\\aura   # size previews

It writes two RGBA PNGs next to the other AdminLTE assets:

    dist/img/sales-aura-icon.png   white rounded chip + mark -> title bars
    dist/img/sales-aura.png        mark only, transparent    -> splash screen

Why draw it instead of shipping a bitmap?
-----------------------------------------
The mark is painted with QPainter (vector paths, no font, no external asset),
exactly like every other glyph in this project (`ui/icons.py`,
`ui/theme.py`). It is reproducible, resolution independent and - most
important for a 16 px title-bar icon - the pixmaps are rasterised *at the
final size* instead of being down-scaled from one big bitmap.

The mark itself: a blue -> violet "S" swoosh (Sales), four ascending bars
and the rising arrow of the original logo, in the brand palette used by
`ui/app_icon.py` (_BLUE / _VIOLET).
"""
from __future__ import annotations

import math
import os
import sys

# QPixmap needs a running Qt app; nothing here needs a real display.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import (QBrush, QColor, QGuiApplication, QLinearGradient,
                         QPainter, QPainterPath, QPen, QPixmap)

# All coordinates below live in this design grid (scaled to the target size).
UNIT = 1000.0

# ---- brand palette (matches the logo: cyan -> blue -> violet) ----
CYAN = "#29B6F6"
BLUE = "#1E6FF0"
VIOLET = "#7B3FF2"

# ---- the two brush strokes that build the "S" -----------------------------
# Drawn as variable-width ribbons (see _ribbon): thick in the middle, tapering
# to points at the tips - exactly how the logo's swoosh is shaped.
TOP_BAND_WIDTH = 186.0
TOP_BAND_PROFILE = ((0.00, 0.26), (0.12, 0.70), (0.45, 1.00), (1.00, 0.50))

CRESCENT_WIDTH = 198.0
CRESCENT_PROFILE = ((0.00, 0.20), (0.28, 0.92), (0.55, 1.00), (1.00, 0.24))

# ---- ascending bars: x, top y (the baseline is shared) ----
BAR_W = 92
BAR_BASE = 830.0
BAR_X = (360.0, 480.0, 600.0, 720.0)
BAR_TOP = (700.0, 612.0, 524.0, 436.0)

# The white gap the logo puts between the arrow / bars and the swoosh.
OUTLINE = 18.0

# ---- arrow: tail at the bars, head rising to the top-right corner ----
ARROW_TAIL = QPointF(462.0, 872.0)
ARROW_TIP = QPointF(778.0, 344.0)
HEAD_APEX = QPointF(876.0, 250.0)
HEAD_BASE = QPointF(752.0, 356.0)
HEAD_HALF = 110.0

HALO = OUTLINE
ARROW_WIDTH = 62.0
ARROW_HALO = ARROW_WIDTH + 2 * OUTLINE
HEAD_HALO = OUTLINE


def _linear(x1, y1, x2, y2, stops) -> QLinearGradient:
    grad = QLinearGradient(x1, y1, x2, y2)
    for pos, color in stops:
        grad.setColorAt(pos, QColor(color))
    return grad


def _swoosh_gradients():
    top = _linear(800, 300, 420, 600, [(0.00, CYAN), (1.00, BLUE)])
    crescent = _linear(340, 700, 800, 700,
                       [(0.00, BLUE), (0.50, "#4636DF"), (1.00, VIOLET)])
    return top, crescent


def _bars_gradient() -> QLinearGradient:
    return _linear(BAR_X[0], BAR_BASE, BAR_X[-1] + BAR_W, BAR_TOP[-1],
                   [(0.00, CYAN), (0.45, BLUE), (1.00, VIOLET)])


def _arrow_gradient() -> QLinearGradient:
    return _linear(ARROW_TAIL.x(), ARROW_TAIL.y(),
                   ARROW_TIP.x(), ARROW_TIP.y(),
                   [(0.00, CYAN), (1.00, BLUE)])


def _pen(color, width, cap=Qt.PenCapStyle.RoundCap,
         join=Qt.PenJoinStyle.RoundJoin) -> QPen:
    pen = QPen(QColor(color), width, Qt.PenStyle.SolidLine, cap, join)
    return pen


def _profile_at(profile, t: float) -> float:
    """Linear lookup in a ((t, factor), ...) width profile."""
    for i in range(len(profile) - 1):
        t0, v0 = profile[i]
        t1, v1 = profile[i + 1]
        if t0 <= t <= t1:
            span = t1 - t0
            return v1 if span <= 0 else v0 + (v1 - v0) * (t - t0) / span
    return profile[-1][1]


def _ribbon(centerline: QPainterPath, width: float, profile,
            samples: int = 180) -> QPainterPath:
    """Variable-width band (a 'brush stroke') around ``centerline``.

    The path is *sampled* rather than stroked, because that is the only way
    to taper the two tips to a point - which is what makes the swoosh look
    like the logo's calligraphic stroke instead of a uniform thick line.
    """
    left, right = [], []
    for i in range(samples + 1):
        t = i / samples
        pt = centerline.pointAtPercent(t)
        ang = math.radians(centerline.angleAtPercent(t))
        half = _profile_at(profile, t) * width / 2.0
        nx, ny = math.sin(ang), math.cos(ang)
        left.append(QPointF(pt.x() + nx * half, pt.y() + ny * half))
        right.append(QPointF(pt.x() - nx * half, pt.y() - ny * half))

    band = QPainterPath()
    band.moveTo(left[0])
    for pt in left[1:]:
        band.lineTo(pt)
    for pt in reversed(right):
        band.lineTo(pt)
    band.closeSubpath()
    return band


def _top_band_path() -> QPainterPath:
    """Top band: from the top-right tip, over the top and down into the middle."""
    line = QPainterPath()
    line.moveTo(796.0, 296.0)
    line.cubicTo(700.0, 138.0, 322.0, 148.0, 294.0, 356.0)
    line.cubicTo(268.0, 522.0, 404.0, 588.0, 566.0, 664.0)
    return _ribbon(line, TOP_BAND_WIDTH, TOP_BAND_PROFILE)


def _crescent_path() -> QPainterPath:
    """Bottom crescent: the hammock the bars stand in, rising on the right."""
    line = QPainterPath()
    line.moveTo(336.0, 706.0)
    line.cubicTo(420.0, 902.0, 706.0, 902.0, 792.0, 636.0)
    return _ribbon(line, CRESCENT_WIDTH, CRESCENT_PROFILE)


def _draw_swoosh(p: QPainter) -> None:
    """The 'S' - a blue top band flowing into the violet bottom crescent."""
    top_grad, crescent_grad = _swoosh_gradients()
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QBrush(top_grad))
    p.drawPath(_top_band_path())
    p.setBrush(QBrush(crescent_grad))
    p.drawPath(_crescent_path())


def _bar_rect(x: float, top: float, pad: float = 0.0) -> QRectF:
    """Rounded-rect outline of one bar (``pad`` widens it for the white halo)."""
    return QRectF(x - pad, top - pad, BAR_W + 2 * pad,
                  BAR_BASE - top + 2 * pad)


def _draw_bar_halos(p: QPainter) -> None:
    """White halo behind the bars - the gap the logo leaves over the swoosh."""
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor("#ffffff"))
    for x, top in zip(BAR_X, BAR_TOP):
        r = BAR_W * 0.28
        p.drawRoundedRect(_bar_rect(x, top, HALO), r + HALO, r + HALO)


def _draw_bars(p: QPainter) -> None:
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QBrush(_bars_gradient()))
    for x, top in zip(BAR_X, BAR_TOP):
        r = BAR_W * 0.28
        p.drawRoundedRect(_bar_rect(x, top), r, r)


def _head_points(pad: float = 0.0):
    """((apex), (base-left), (base-right)) of the arrow head, grown by ``pad``."""
    ax, ay = HEAD_APEX.x(), HEAD_APEX.y()
    bx, by = HEAD_BASE.x(), HEAD_BASE.y()
    dx, dy = bx - ax, by - ay                      # apex -> base direction
    length = max(1.0, (dx * dx + dy * dy) ** 0.5)
    ux, uy = dx / length, dy / length              # unit vector
    px, py = -uy, ux                               # perpendicular
    half = HEAD_HALF + pad
    return (QPointF(ax - ux * pad, ay - uy * pad),
            QPointF(bx + px * half, by + py * half),
            QPointF(bx - px * half, by - py * half))


def _head_path(pad: float = 0.0) -> QPainterPath:
    apex, left, right = _head_points(pad)
    path = QPainterPath()
    path.moveTo(apex)
    path.lineTo(left)
    path.lineTo(right)
    path.closeSubpath()
    return path


def _draw_arrow_halos(p: QPainter) -> None:
    """White gap so the arrow stays readable where it crosses the swoosh."""
    pen = _pen("#ffffff", ARROW_HALO)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawLine(ARROW_TAIL, ARROW_TIP)
    p.setPen(_pen("#ffffff", HALO))
    p.setBrush(QColor("#ffffff"))
    p.drawPath(_head_path(HEAD_HALO))


def _draw_arrow(p: QPainter) -> None:
    pen = _pen("#000000", ARROW_WIDTH)
    pen.setBrush(QBrush(_arrow_gradient()))
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawLine(ARROW_TAIL, ARROW_TIP)

    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QBrush(_arrow_gradient()))
    p.drawPath(_head_path())


def draw_mark(p: QPainter, size: int, tile: bool = False) -> None:
    """Paint the whole mark into ``p`` (``size`` = the target pixel size).

    ``tile=True`` puts it on the white rounded chip used by the title-bar /
    taskbar icon; the plain version has a transparent background.
    """
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    p.save()
    p.scale(size / UNIT, size / UNIT)          # paint in UNIT coordinates

    if tile:
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#ffffff"))
        p.drawRoundedRect(QRectF(0.0, 0.0, UNIT, UNIT), UNIT * 0.20,
                          UNIT * 0.20)

    _draw_swoosh(p)
    _draw_bar_halos(p)
    _draw_bars(p)
    _draw_arrow_halos(p)
    _draw_arrow(p)

    p.restore()


def mark_pixmap(size: int = 1024, tile: bool = False) -> QPixmap:
    """The mark as a square RGBA pixmap of exactly ``size`` px."""
    pm = QPixmap(int(size), int(size))
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    draw_mark(p, int(size), tile=tile)
    p.end()
    return pm


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)

    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    img_dir = os.path.join(base, "dist", "img")

    app = QGuiApplication.instance() or QGuiApplication(argv or [""])
    try:
        if "--preview" in argv:
            out = argv[argv.index("--preview") + 1]
            os.makedirs(out, exist_ok=True)
            for px in (16, 20, 24, 32, 48, 64, 128, 256):
                path = os.path.join(out, f"icon-{px:03d}.png")
                mark_pixmap(px, tile=True).save(path, "PNG")
                print("wrote", path)
            for px in (256, 512):
                path = os.path.join(out, f"mark-{px:03d}.png")
                mark_pixmap(px, tile=False).save(path, "PNG")
                print("wrote", path)
            return 0

        os.makedirs(img_dir, exist_ok=True)
        for name, size, tile in (("sales-aura-icon.png", 512, True),
                                 ("sales-aura.png", 1024, False)):
            path = os.path.join(img_dir, name)
            if not mark_pixmap(size, tile=tile).save(path, "PNG"):
                print("FAILED to write", path, file=sys.stderr)
                return 1
            print("wrote", path)
        return 0
    finally:
        del app


if __name__ == "__main__":
    raise SystemExit(main())
