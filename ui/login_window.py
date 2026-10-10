import os
import random

from PyQt6.QtCore import Qt, QTimer, QPointF, QSize, QRectF
from PyQt6.QtGui import (QPixmap, QPainter, QColor, QLinearGradient, QPen,
                         QIcon, QPainterPath, QBrush, QPolygonF)
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QLineEdit, QPushButton, QFrame, QCheckBox)

from ui.app_icon import app_icon
from ui.theme import icon
from database import db_manager


# --------------------------------------------------------------------------- #
# App base folder
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
    return os.path.abspath(os.path.join(here, "..", ".."))


APP_BASE   = _app_base_dir()
IMG_DIR    = os.path.join(APP_BASE, "dist", "img")
UPLOAD_DIR = os.path.join(IMG_DIR, "uploads")


# =========================================================================== #
#  ICON PAINTERS  (no reliance on ui.theme glyph names)
# =========================================================================== #

# --------------------------------------------------------------------------- #
# Key icon (for the left of the password input)
# --------------------------------------------------------------------------- #
def _key_icon(color: str = "#888", size: int = 18) -> QIcon:
    """Draw a modern key icon: circular head (bow) + straight shaft + teeth."""
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)

    c = QColor(color)
    stroke = max(1.4, size * 0.09)
    pen = QPen(c)
    pen.setWidthF(stroke)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)

    # work in a 24x24 logical box
    s = size / 24.0
    p.scale(s, s)

    # head: circle outline at (8, 8), radius 5
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawEllipse(QPointF(8, 8), 5, 5)

    # shaft: from (12, 12) down-right to (20, 20)
    p.drawLine(QPointF(11.7, 11.7), QPointF(20, 20))

    # teeth: two short perpendicular segments
    p.drawLine(QPointF(16, 16), QPointF(18, 14))
    p.drawLine(QPointF(18, 18), QPointF(20, 16))

    p.end()
    return QIcon(pm)


# --------------------------------------------------------------------------- #
# Eye icons - four styles
# --------------------------------------------------------------------------- #
EYE_STYLE = "filled"   # "material" | "filled" | "lashes" | "circle"


def _eye_icon(visible: bool, style: str = None,
              color: str = "#666", size: int = 20) -> QIcon:
    """Return an eye QIcon.

    `visible=True`  -> open eye (password shown)
    `visible=False` -> eye-off  (password masked)
    `style`         -> one of "material", "filled", "lashes", "circle"
    """
    style = style or EYE_STYLE
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)

    c = QColor(color)
    stroke = max(1.4, size * 0.09)
    pen = QPen(c)
    pen.setWidthF(stroke)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)

    s = size / 24.0
    p.scale(s, s)

    # helper: almond outline path (top lid + bottom lid meeting at 2,12 and 22,12)
    def _almond() -> QPainterPath:
        path = QPainterPath()
        path.moveTo(2, 12)
        path.quadTo(12, 3, 22, 12)
        path.quadTo(12, 21, 2, 12)
        return path

    # ---------------- material ----------------
    if style == "material":
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(_almond())
        if visible:
            p.setBrush(QBrush(c))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QPointF(12, 12), 2.6, 2.6)
        else:
            p.setPen(pen)
            p.drawLine(QPointF(4, 20), QPointF(20, 4))

    # ---------------- filled ----------------
    elif style == "filled":
        if visible:
            # solid almond, white pupil
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(c))
            p.drawPath(_almond())
            p.setBrush(QBrush(QColor("#ffffff")))
            p.drawEllipse(QPointF(12, 12), 2.6, 2.6)
        else:
            # outline almond + slash (filled reads poorly with a slash)
            p.setPen(pen)
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawPath(_almond())
            p.drawLine(QPointF(4, 20), QPointF(20, 4))

    # ---------------- lashes (open eye with 3 little strokes) ----------------
    elif style == "lashes":
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(_almond())
        # three lashes above the top lid
        p.drawLine(QPointF(12, 3), QPointF(12, 1))
        p.drawLine(QPointF(6, 5),  QPointF(4.5, 3.5))
        p.drawLine(QPointF(18, 5), QPointF(19.5, 3.5))
        if visible:
            p.setBrush(QBrush(c))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QPointF(12, 12), 2.6, 2.6)
        else:
            p.setPen(pen)
            p.drawLine(QPointF(4, 20), QPointF(20, 4))

    # ---------------- circle (simplest: circle outline + dot) ----------------
    elif style == "circle":
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QPointF(12, 12), 8, 8)
        if visible:
            p.setBrush(QBrush(c))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QPointF(12, 12), 3.2, 3.2)
        else:
            p.setPen(pen)
            p.drawLine(QPointF(6, 18), QPointF(18, 6))

    # ---------------- fallback ----------------
    else:
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(_almond())
        if not visible:
            p.drawLine(QPointF(4, 20), QPointF(20, 4))

    p.end()
    return QIcon(pm)


# =========================================================================== #
#  particles.js-style background  (unchanged)
# =========================================================================== #
class ParticleField:
    def __init__(self, count=80, speed=0.4, link_distance=140, dot_radius=2.0):
        self.count = count
        self.speed = speed
        self.link_distance = link_distance
        self.dot_radius = dot_radius
        self._particles = []
        self._size = (0, 0)

    def resize(self, w, h):
        if (w, h) == self._size:
            return
        self._size = (w, h)
        if not self._particles or w <= 0 or h <= 0:
            self._particles = []
            for _ in range(self.count):
                self._particles.append([
                    random.uniform(0, w),
                    random.uniform(0, h),
                    random.uniform(-self.speed, self.speed),
                    random.uniform(-self.speed, self.speed),
                ])

    def step(self):
        w, h = self._size
        if w <= 0 or h <= 0:
            return
        for p in self._particles:
            p[0] += p[2]
            p[1] += p[3]
            if p[0] < 0:
                p[0] = 0; p[2] = abs(p[2])
            elif p[0] > w:
                p[0] = w; p[2] = -abs(p[2])
            if p[1] < 0:
                p[1] = 0; p[3] = abs(p[3])
            elif p[1] > h:
                p[1] = h; p[3] = -abs(p[3])

    def paint(self, painter):
        w, h = self._size
        if w <= 0 or h <= 0 or not self._particles:
            return
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        link2 = self.link_distance * self.link_distance
        n = len(self._particles)
        for i in range(n):
            xi, yi, _, _ = self._particles[i]
            for j in range(i + 1, n):
                xj, yj, _, _ = self._particles[j]
                dx = xi - xj
                dy = yi - yj
                d2 = dx * dx + dy * dy
                if d2 <= link2:
                    alpha = int(80 * (1 - d2 / link2))
                    if alpha > 0:
                        painter.setPen(QPen(QColor(255, 255, 255, alpha), 1))
                        painter.drawLine(QPointF(xi, yi), QPointF(xj, yj))

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(255, 255, 255, 200))
        r = self.dot_radius
        for x, y, _, _ in self._particles:
            painter.drawEllipse(QPointF(x, y), r, r)

        painter.restore()


# =========================================================================== #
#  Login window
# =========================================================================== #
class LoginWindow(QWidget):
    LOGO_CANDIDATES = [
        "login-logo.png",
        "logo.png",
        "AntDev.png",
        "antdev.png",
        "company-logo.png",
    ]

    def __init__(self, on_success):
        super().__init__()
        self.on_success = on_success
        self.admin = None
        self.setWindowTitle("Log in")
        self.setWindowIcon(app_icon())
        # Was setFixedSize(1100, 680), which pinned the login dialog to a size
        # that never matched the dashboard and could not be resized by the
        # user. A minimum size plus the default size keeps the layout sensible
        # while letting the window grow/shrink; main.py opens it maximized.
        # The card is a fixed 400px wide inside stretch factors (2:3) and the
        # particle field re-lays out in resizeEvent, so any size renders fine.
        self.setMinimumSize(900, 600)
        self.resize(1100, 680)

        self._particles = ParticleField(count=80, speed=0.4,
                                        link_distance=140, dot_radius=2.0)
        self._particles.resize(self.width(), self.height())
        self._timer = QTimer(self)
        self._timer.setInterval(30)
        self._timer.timeout.connect(self._tick)
        self._timer.start()

        self.user_edit = None
        self.pass_edit = None
        self.msg = None
        self._build()

    # ------------------------------------------------------------ animation
    def _tick(self):
        self._particles.step()
        self.update()

    def resizeEvent(self, event):
        self._particles.resize(self.width(), self.height())
        super().resizeEvent(event)

    # ------------------------------------------------------------ painting
    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        g = QLinearGradient(0, 0, self.width(), self.height())
        g.setColorAt(0.0, QColor("#667eea"))
        g.setColorAt(0.55, QColor("#3c8dbc"))
        g.setColorAt(1.0, QColor("#00c0ef"))
        p.fillRect(self.rect(), g)
        self._particles.paint(p)
        p.end()

    # ------------------------------------------------------------ logo
    def _resolve_logo(self):
        for name in self.LOGO_CANDIDATES:
            path = os.path.join(IMG_DIR, name)
            if os.path.isfile(path):
                pm = QPixmap(path)
                if not pm.isNull():
                    return pm
        return None

    # ------------------------------------------------------------ UI
    def _build(self):
        outer = QVBoxLayout(self)
        outer.addStretch(2)

        box = QFrame()
        box.setFixedWidth(400)
        box.setStyleSheet(
            "QFrame { background: white; border-radius: 6px;"
            " border-top: 4px solid #3c8dbc; }")
        bl = QVBoxLayout(box)
        bl.setContentsMargins(30, 24, 30, 24)
        bl.setSpacing(14)

        # ---- logo / fallback title ----
        logo_pm = self._resolve_logo()
        if logo_pm is not None:
            logo = QLabel()
            logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
            logo.setStyleSheet("background: transparent; border: none;")
            logo.setPixmap(logo_pm.scaled(
                220, 120,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation))
            bl.addWidget(logo)
        else:
            title_text = "Sign In"
            try:
                admin = db_manager.get_admin() or {}
                title_text = (admin.get("c_name") or admin.get("name")
                              or title_text)
            except Exception:
                pass
            title = QLabel(title_text)
            title.setAlignment(Qt.AlignmentFlag.AlignCenter)
            title.setStyleSheet(
                "font-size: 24px; font-weight: 700; color: #3c8dbc;"
                " background: transparent; border: none;")
            bl.addWidget(title)

        # ---- subtitle ----
        msg_in = QLabel("Sign in to start your session")
        msg_in.setAlignment(Qt.AlignmentFlag.AlignCenter)
        msg_in.setStyleSheet(
            "color: #666; font-size: 13px;"
            " background: transparent; border: none;")
        bl.addWidget(msg_in)

        # ---- inputs ----
        self.user_edit = self._input_user("Username or Email")
        bl.addWidget(self.user_edit)

        # password: hand-drawn key + eye toggle
        self.pass_edit = self._input_password("Password")
        bl.addWidget(self.pass_edit)

        # ---- remember-me ----
        row = QHBoxLayout()
        self.remember = QCheckBox("Remember Me")
        self.remember.setStyleSheet(
            "QCheckBox { color: #555; font-size: 13px; background: transparent; }"
            "QCheckBox::indicator { width: 16px; height: 16px; }")
        row.addWidget(self.remember)
        row.addStretch()
        bl.addLayout(row)

        # ---- error message ----
        self.msg = QLabel("")
        self.msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.msg.setWordWrap(True)
        self.msg.setStyleSheet(
            "background: transparent; border: none; font-size: 13px;")
        bl.addWidget(self.msg)

        # ---- Sign In ----
        btn = QPushButton("Sign In")
        btn.setObjectName("btnInfo")
        btn.setFixedHeight(42)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(self._login)
        self.user_edit.edit.returnPressed.connect(
            lambda: self.pass_edit.edit.setFocus())
        self.pass_edit.edit.returnPressed.connect(self._login)
        bl.addWidget(btn)

        # ---- footer link ----
        forgot = QLabel(
            '<a href="#" style="color:#3c8dbc; text-decoration:none;">'
            'I forgot my password</a>')
        forgot.setAlignment(Qt.AlignmentFlag.AlignCenter)
        forgot.setOpenExternalLinks(False)
        forgot.setStyleSheet("background: transparent; border: none;"
                             " font-size: 12px; padding-top: 4px;")
        bl.addWidget(forgot)

        outer.addWidget(box, 0, Qt.AlignmentFlag.AlignHCenter)
        outer.addStretch(3)

    # ------------------------------------------------------------ inputs
    def _input_user(self, placeholder):
        wrap = QFrame()
        wrap.setStyleSheet(
            "QFrame { background: #f7f9fb; border: 1px solid #d2d6de;"
            " border-radius: 4px; }")
        h = QHBoxLayout(wrap)
        h.setContentsMargins(10, 4, 6, 4)
        h.setSpacing(8)

        ic = QLabel()
        ic.setPixmap(icon("user", "#888", 18).pixmap(18, 18))
        ic.setStyleSheet("background: transparent; border: none;")
        h.addWidget(ic)

        edit = QLineEdit()
        edit.setPlaceholderText(placeholder)
        edit.setFixedHeight(36)
        edit.setStyleSheet(
            "QLineEdit { background: transparent; border: none;"
            " color: #333; font-size: 14px; }")
        wrap.edit = edit
        h.addWidget(edit)
        return wrap

    def _input_password(self, placeholder):
        wrap = QFrame()
        wrap.setStyleSheet(
            "QFrame { background: #f7f9fb; border: 1px solid #d2d6de;"
            " border-radius: 4px; }")
        h = QHBoxLayout(wrap)
        h.setContentsMargins(10, 4, 6, 4)
        h.setSpacing(8)

        # leading key icon (drawn here, not from the theme lib)
        ic = QLabel()
        ic.setPixmap(_key_icon(color="#888", size=18).pixmap(18, 18))
        ic.setStyleSheet("background: transparent; border: none;")
        h.addWidget(ic)

        edit = QLineEdit()
        edit.setPlaceholderText(placeholder)
        edit.setFixedHeight(36)
        edit.setEchoMode(QLineEdit.EchoMode.Password)
        edit.setStyleSheet(
            "QLineEdit { background: transparent; border: none;"
            " color: #333; font-size: 14px; }")
        wrap.edit = edit
        h.addWidget(edit)

        # trailing eye toggle
        toggle = QPushButton()
        toggle.setFlat(True)
        toggle.setFixedSize(30, 30)
        toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        toggle.setIconSize(QSize(20, 20))
        toggle.setStyleSheet(
            "QPushButton { background: transparent; border: none; }"
            "QPushButton:hover { background: #e9eef5; border-radius: 4px; }")

        # default: password hidden -> eye-off
        toggle.setIcon(_eye_icon(visible=False, color="#666", size=20))
        toggle.setToolTip("Show password")

        def _make_toggle(btn, ed):
            def _toggle(_checked=False):
                if ed.echoMode() == QLineEdit.EchoMode.Password:
                    ed.setEchoMode(QLineEdit.EchoMode.Normal)
                    btn.setIcon(_eye_icon(visible=True,
                                          color="#3c8dbc", size=20))
                    btn.setToolTip("Hide password")
                else:
                    ed.setEchoMode(QLineEdit.EchoMode.Password)
                    btn.setIcon(_eye_icon(visible=False,
                                          color="#666", size=20))
                    btn.setToolTip("Show password")
            return _toggle

        toggle.clicked.connect(_make_toggle(toggle, edit))
        h.addWidget(toggle)
        return wrap

    # ------------------------------------------------------------ login
    def _login(self):
        username = self.user_edit.edit.text().strip()
        password = self.pass_edit.edit.text()
        try:
            row = db_manager.authenticate(username, password)
        except Exception as exc:
            self.msg.setText(f"DB error: {exc}")
            self.msg.setStyleSheet(
                "color: #dd4b39; background: transparent; border: none;")
            return
        if row:
            self.admin = row
            self.on_success(row)
        else:
            self.msg.setText("Incorrect username or password!")
            self.msg.setStyleSheet(
                "color: #dd4b39; background: transparent; border: none;")