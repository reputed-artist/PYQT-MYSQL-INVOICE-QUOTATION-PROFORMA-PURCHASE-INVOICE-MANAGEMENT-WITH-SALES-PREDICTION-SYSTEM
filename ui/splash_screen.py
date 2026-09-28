"""
Sales Aura — Splash Screen

A polished, animated splash screen with:
  * Aurora-style animated gradient background
  * Particle field + connecting lines (particles.js style)
  * Soft glow behind the logo/title
  * Animated loading progress bar with status text
  * Smooth fade-in on show, fade-out on close
  * Emits `finished` when it's ready to hand over to the login window

Usage:
    from ui.splash_screen import SplashScreen

    splash = SplashScreen(duration_ms=2600)
    splash.finished.connect(start_login)     # called after the splash
    splash.show()
"""
from __future__ import annotations

import math
import os
import random

from PyQt6.QtCore import (Qt, QTimer, QPointF, QRectF, QSize,
                          pyqtSignal)
from PyQt6.QtGui import (QPixmap, QPainter, QColor, QLinearGradient,
                         QRadialGradient, QPen, QFont, QIcon,
                         QPainterPath, QBrush, QFontDatabase)
from PyQt6.QtWidgets import QWidget, QApplication

from ui.app_icon import app_icon, logo_path


# --------------------------------------------------------------------------- #
# Paths
# --------------------------------------------------------------------------- #
def _app_base_dir() -> str:
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


APP_BASE = _app_base_dir()
IMG_DIR = os.path.join(APP_BASE, "dist", "img")

LOGO_CANDIDATES = (
    "sales-aura.png",
    "sales_aura.png",
    "logo.png",
    "login-logo.png",
    "company-logo.png",
)


# --------------------------------------------------------------------------- #
# Palette
# --------------------------------------------------------------------------- #
# BG_TOP       = QColor("#0b1e3a")     # deep navy
# BG_MID       = QColor("#153a6b")     # royal blue
# BG_BOTTOM    = QColor("#00a3c4")     # aqua
# ACCENT       = QColor("#3c8dbc")     # your existing brand blue
# ACCENT_LIGHT = QColor("#00c0ef")     # bright cyan
# ACCENT_GLOW  = QColor(60, 141, 188, 90)
# TEXT_PRIMARY = QColor("#ffffff")
# TEXT_MUTED   = QColor(255, 255, 255, 160)

# --------------------------------------------------------------------------- #
# Black / Premium Palette
# --------------------------------------------------------------------------- #
BG_TOP       = QColor("#050608")
BG_MID       = QColor("#080B10")
BG_BOTTOM    = QColor("#0B1118")

ACCENT       = QColor("#3B82F6")       # modern blue
ACCENT_LIGHT = QColor("#22D3EE")       # cyan
ACCENT_GLOW  = QColor(59, 130, 246, 85)

TEXT_PRIMARY = QColor("#FFFFFF")
TEXT_MUTED   = QColor(255, 255, 255, 155)

# =========================================================================== #
# Particle field (aurora dots)
# =========================================================================== #
class _Particles:
    def __init__(self, count=110, speed=0.55,
                 link_distance=150, dot_radius=1.8):
        self.count = count
        self.speed = speed
        self.link_distance = link_distance
        self.dot_radius = dot_radius
        self._pts: list[list[float]] = []
        self._size = (0, 0)

    def resize(self, w: int, h: int) -> None:
        if (w, h) == self._size:
            return
        self._size = (w, h)
        if not self._pts or w <= 0 or h <= 0:
            self._pts = []
            for _ in range(self.count):
                self._pts.append([
                    random.uniform(0, w),
                    random.uniform(0, h),
                    random.uniform(-self.speed, self.speed),
                    random.uniform(-self.speed, self.speed),
                ])

    def step(self) -> None:
        w, h = self._size
        if w <= 0 or h <= 0:
            return
        for p in self._pts:
            p[0] += p[2]
            p[1] += p[3]
            if p[0] < 0:
                p[0] = 0;  p[2] = abs(p[2])
            elif p[0] > w:
                p[0] = w;  p[2] = -abs(p[2])
            if p[1] < 0:
                p[1] = 0;  p[3] = abs(p[3])
            elif p[1] > h:
                p[1] = h;  p[3] = -abs(p[3])

    def paint(self, painter: QPainter) -> None:
        w, h = self._size
        if w <= 0 or h <= 0 or not self._pts:
            return
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        link2 = self.link_distance * self.link_distance
        n = len(self._pts)
        for i in range(n):
            xi, yi, _, _ = self._pts[i]
            for j in range(i + 1, n):
                xj, yj, _, _ = self._pts[j]
                dx = xi - xj
                dy = yi - yj
                d2 = dx * dx + dy * dy
                if d2 <= link2:
                    alpha = int(70 * (1 - d2 / link2))
                    if alpha > 0:
                        painter.setPen(QPen(
                            QColor(180, 225, 255, alpha), 1))
                        painter.drawLine(QPointF(xi, yi),
                                         QPointF(xj, yj))

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(255, 255, 255, 210))
        r = self.dot_radius
        for x, y, _, _ in self._pts:
            painter.drawEllipse(QPointF(x, y), r, r)

        painter.restore()


# =========================================================================== #
# Aurora wave (drawn behind everything, animated)
# =========================================================================== #
def _aurora_path(w: int, h: int, phase: float,
                 amplitude: float = 26.0,
                 baseline: float = 0.62,
                 frequency: float = 1.6) -> QPainterPath:
    path = QPainterPath()
    path.moveTo(0, h)
    y_base = h * baseline
    steps = 48
    for i in range(steps + 1):
        x = (w / steps) * i
        t = i / steps
        y = y_base + math.sin(t * math.pi * 2 * frequency + phase) * amplitude
        y += math.sin(t * math.pi * 4 * frequency + phase * 0.6) * (amplitude * 0.35)
        if i == 0:
            path.lineTo(x, y)
        else:
            path.lineTo(x, y)
    path.lineTo(w, h)
    path.closeSubpath()
    return path


# =========================================================================== #
# Splash screen
# =========================================================================== #
class SplashScreen(QWidget):
    """Animated splash screen for Sales Aura.

    Emits `finished` once the loading animation is done.
    """
    finished = pyqtSignal()

    def __init__(self, duration_ms: int = 2600, parent=None):
        super().__init__(parent)

        # Frameless, always-on-top, no window chrome, translucent so we
        # can fade with windowOpacity.
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.SplashScreen |
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.setWindowIcon(app_icon())      # taskbar icon (splash is frameless)

        # Size
        self._w, self._h = 720, 460
        self.setFixedSize(self._w, self._h)

        # Center on the primary screen
        try:
            screen = QApplication.primaryScreen().availableGeometry()
            self.move(
                screen.center().x() - self._w // 2,
                screen.center().y() - self._h // 2,
            )
        except Exception:
            pass

        # ---- animation state ----
        self._particles = _Particles()
        self._particles.resize(self._w, self._h)
        self._phase = 0.0
        self._progress = 0.0                    # 0.0 → 1.0
        self._duration_ms = max(800, int(duration_ms))
        self._elapsed_ms = 0
        self._tick_ms = 16                      # ~60 FPS

        self._status_text = "Starting Sales Aura…"
        self._status_steps = [
            (0.00, "Starting Sales Aura…"),
            (0.15, "Loading modules…"),
            (0.35, "Connecting to database…"),
            (0.55, "Preparing dashboard…"),
            (0.75, "Warming up caches…"),
            (0.90, "Almost ready…"),
            (1.00, "Ready"),
        ]

        # ---- logo ----
        self._logo_pm: QPixmap | None = self._resolve_logo()

        # ---- timers ----
        self._timer = QTimer(self)
        self._timer.setInterval(self._tick_ms)
        self._timer.timeout.connect(self._tick)
        self._timer.start()

        # Fade-in via window opacity
        self.setWindowOpacity(0.0)
        self._fade_in = QTimer(self)
        self._fade_in.setInterval(16)
        self._fade_in.timeout.connect(self._do_fade_in)
        self._fade_in.start()

    # ------------------------------------------------------------------ #
    # Logo loader
    # ------------------------------------------------------------------ #
    def _resolve_logo(self) -> QPixmap | None:
        # Shared resolver first (ui.app_icon) so the splash, every title bar and
        # the taskbar always show the very same logo file.
        shared = logo_path()
        if shared:
            pm = QPixmap(shared)
            if not pm.isNull():
                return pm
        for name in LOGO_CANDIDATES:
            path = os.path.join(IMG_DIR, name)
            if os.path.isfile(path):
                pm = QPixmap(path)
                if not pm.isNull():
                    return pm
        return None

    # ------------------------------------------------------------------ #
    # Fade-in / fade-out
    # ------------------------------------------------------------------ #
    def _do_fade_in(self) -> None:
        o = self.windowOpacity()
        if o >= 0.99:
            self.setWindowOpacity(1.0)
            self._fade_in.stop()
            return
        self.setWindowOpacity(min(1.0, o + 0.06))

    def _begin_fade_out(self) -> None:
        self._timer.stop()
        self._fade_out = QTimer(self)
        self._fade_out.setInterval(16)

        def _step():
            o = self.windowOpacity()
            if o <= 0.02:
                self._fade_out.stop()
                self.finished.emit()
                self.close()
                return
            self.setWindowOpacity(max(0.0, o - 0.08))

        self._fade_out.timeout.connect(_step)
        self._fade_out.start()

    # ------------------------------------------------------------------ #
    # Animation tick
    # ------------------------------------------------------------------ #
    def _tick(self) -> None:
        # Move particles
        self._particles.step()

        # Advance aurora phase
        self._phase += 0.045

        # Progress
        self._elapsed_ms += self._tick_ms
        self._progress = min(1.0, self._elapsed_ms / self._duration_ms)

        # Update status text
        for threshold, text in self._status_steps:
            if self._progress >= threshold:
                self._status_text = text

        self.update()

        if self._progress >= 1.0:
            self._begin_fade_out()

    # ------------------------------------------------------------------ #
    # Painting
    # ------------------------------------------------------------------ #
    def paintEvent(self, event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        w, h = self._w, self._h
        rect = QRectF(0, 0, w, h)
        rounded = QPainterPath()
        rounded.addRoundedRect(rect, 14, 14)

        # ---- 1. base vertical gradient ----
        p.save()
        p.setClipPath(rounded)
        grad = QLinearGradient(0, 0, 0, h)
        grad.setColorAt(0.00, BG_TOP)
        grad.setColorAt(0.55, BG_MID)
        grad.setColorAt(1.00, BG_BOTTOM)
        p.fillRect(rect, grad)
        p.restore()

        # ---- 2. aurora waves ----
        p.save()
        p.setClipPath(rounded)
        p.setPen(Qt.PenStyle.NoPen)

        # back wave
        path_back = _aurora_path(w, h, self._phase * 0.7,
                                 amplitude=34, baseline=0.70, frequency=1.4)
        back_grad = QLinearGradient(0, h * 0.4, 0, h)
        back_grad.setColorAt(0.0, QColor(0, 192, 239, 60))
        back_grad.setColorAt(1.0, QColor(0, 192, 239, 0))
        p.setBrush(QBrush(back_grad))
        p.drawPath(path_back)

        # front wave
        path_front = _aurora_path(w, h, self._phase,
                                  amplitude=22, baseline=0.78, frequency=1.8)
        front_grad = QLinearGradient(0, h * 0.5, 0, h)
        front_grad.setColorAt(0.0, QColor(60, 141, 188, 110))
        front_grad.setColorAt(1.0, QColor(60, 141, 188, 0))
        p.setBrush(QBrush(front_grad))
        p.drawPath(path_front)
        p.restore()

        # ---- 3. particles ----
        p.save()
        p.setClipPath(rounded)
        self._particles.paint(p)
        p.restore()

        # ---- 4. soft glow behind logo ----
        p.save()
        p.setClipPath(rounded)
        glow_cx = w // 2
        glow_cy = int(h * 0.36)
        glow = QRadialGradient(QPointF(glow_cx, glow_cy),
                               w * 0.42)
        glow.setColorAt(0.00, ACCENT_GLOW)
        glow.setColorAt(0.55, QColor(60, 141, 188, 30))
        glow.setColorAt(1.00, QColor(60, 141, 188, 0))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(glow))
        p.drawEllipse(QPointF(glow_cx, glow_cy),
                      w * 0.42, w * 0.30)
        p.restore()

        # ---- 5. logo (or animated monogram fallback) ----
        logo_cy = int(h * 0.36)
        if self._logo_pm is not None:
            target_w, target_h = 180, 110
            pm = self._logo_pm.scaled(
                target_w, target_h,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation)
            x = (w - pm.width()) // 2
            y = logo_cy - pm.height() // 2
            p.drawPixmap(x, y, pm)
        else:
            self._draw_monogram(p, w // 2, logo_cy)

        # ---- 6. app title ----
        p.save()
        title_font = QFont()
        title_font.setPointSize(34)
        title_font.setWeight(QFont.Weight.Bold)
        title_font.setLetterSpacing(QFont.SpacingType.PercentageSpacing, 102)
        p.setFont(title_font)

        # Title "Sales Aura" split into two weights for emphasis
        title = "Sales Aura"
        fm = p.fontMetrics()
        total_w = fm.horizontalAdvance(title)
        x = (w - total_w) // 2
        y = int(h * 0.58)

        # subtle text shadow
        p.setPen(QColor(0, 0, 0, 120))
        p.drawText(x + 2, y + 2, title)
        # main text
        p.setPen(TEXT_PRIMARY)
        p.drawText(x, y, title)
        p.restore()

        # ---- 7. tagline ----
        p.save()
        tag_font = QFont()
        tag_font.setPointSize(11)
        tag_font.setLetterSpacing(QFont.SpacingType.PercentageSpacing, 118)
        p.setFont(tag_font)
        p.setPen(TEXT_MUTED)
        tagline = "INVOICES  ·  INSIGHTS  ·  INTELLIGENCE"
        tw = p.fontMetrics().horizontalAdvance(tagline)
        p.drawText((w - tw) // 2, int(h * 0.63), tagline)
        p.restore()

        # ---- 8. progress bar ----
        bar_w = int(w * 0.62)
        bar_h = 6
        bar_x = (w - bar_w) // 2
        bar_y = int(h * 0.78)

        # track
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(255, 255, 255, 40))
        p.drawRoundedRect(QRectF(bar_x, bar_y, bar_w, bar_h),
                          bar_h / 2, bar_h / 2)

        # fill
        fill_w = int(bar_w * self._progress)
        if fill_w > 2:
            bar_grad = QLinearGradient(bar_x, 0, bar_x + bar_w, 0)
            bar_grad.setColorAt(0.00, ACCENT)
            bar_grad.setColorAt(0.60, ACCENT_LIGHT)
            bar_grad.setColorAt(1.00, QColor("#7de3ff"))
            p.setBrush(QBrush(bar_grad))
            p.drawRoundedRect(QRectF(bar_x, bar_y, fill_w, bar_h),
                              bar_h / 2, bar_h / 2)

            # moving highlight
            hl_x = bar_x + fill_w * 0.85
            hl = QRadialGradient(QPointF(hl_x, bar_y + bar_h / 2),
                                 bar_h * 3.2)
            hl.setColorAt(0.0, QColor(255, 255, 255, 220))
            hl.setColorAt(1.0, QColor(255, 255, 255, 0))
            p.setBrush(QBrush(hl))
            p.drawRoundedRect(QRectF(bar_x, bar_y, fill_w, bar_h),
                              bar_h / 2, bar_h / 2)

        # ---- 9. status text ----
        p.save()
        s_font = QFont()
        s_font.setPointSize(10)
        p.setFont(s_font)
        p.setPen(TEXT_MUTED)
        sw = p.fontMetrics().horizontalAdvance(self._status_text)
        p.drawText((w - sw) // 2, bar_y + 30, self._status_text)
        p.restore()

        # ---- 10. footer ----
        p.save()
        f_font = QFont()
        f_font.setPointSize(8)
        p.setFont(f_font)
        p.setPen(QColor(255, 255, 255, 90))
        foot = "© CodeTech Engineers  ·  Sales Aura v1.0"
        fw = p.fontMetrics().horizontalAdvance(foot)
        p.drawText((w - fw) // 2, h - 18, foot)
        p.restore()

        # ---- 11. soft inner border ----
        p.save()
        pen = QPen(QColor(255, 255, 255, 30))
        pen.setWidth(1)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(rect.adjusted(0.5, 0.5, -0.5, -0.5), 14, 14)
        p.restore()

        p.end()

    # ------------------------------------------------------------------ #
    # Fallback monogram — drawn when no logo file is available
    # ------------------------------------------------------------------ #
    def _draw_monogram(self, p: QPainter, cx: int, cy: int) -> None:
        """Draw a glowing 'SA' monogram in place of a missing logo file."""
        size = 120
        # outer ring
        ring_grad = QRadialGradient(QPointF(cx, cy), size * 0.75)
        ring_grad.setColorAt(0.00, QColor(0, 192, 239, 120))
        ring_grad.setColorAt(0.70, QColor(60, 141, 188, 60))
        ring_grad.setColorAt(1.00, QColor(60, 141, 188, 0))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(ring_grad))
        p.drawEllipse(QPointF(cx, cy), size * 0.75, size * 0.75)

        # inner disc
        disc_grad = QLinearGradient(cx - size / 2, cy - size / 2,
                                    cx + size / 2, cy + size / 2)
        disc_grad.setColorAt(0.0, QColor(60, 141, 188, 220))
        disc_grad.setColorAt(1.0, QColor(0, 192, 239, 220))
        p.setBrush(QBrush(disc_grad))
        p.setPen(QPen(QColor(255, 255, 255, 200), 2))
        p.drawEllipse(QPointF(cx, cy), size * 0.45, size * 0.45)

        # monogram "SA"
        p.save()
        f = QFont()
        f.setPointSize(46)
        f.setWeight(QFont.Weight.Bold)
        f.setLetterSpacing(QFont.SpacingType.PercentageSpacing, 96)
        p.setFont(f)
        p.setPen(Qt.PenStyle.NoPen)
        p.setPen(QColor(255, 255, 255))
        text = "SA"
        fm = p.fontMetrics()
        tw = fm.horizontalAdvance(text)
        th = fm.ascent()
        p.drawText(cx - tw // 2, cy + th // 2 - 2, text)
        p.restore()

    # ------------------------------------------------------------------ #
    # Interaction: allow the user to close by clicking or pressing Esc
    # ------------------------------------------------------------------ #
    def mousePressEvent(self, event) -> None:  # noqa: N802
        # Optional: uncomment to let the user skip the splash
        # self._progress = 1.0
        super().mousePressEvent(event)

    def keyPressEvent(self, event) -> None:  # noqa: N802
        if event.key() == Qt.Key.Key_Escape:
            self._begin_fade_out()
        super().keyPressEvent(event)