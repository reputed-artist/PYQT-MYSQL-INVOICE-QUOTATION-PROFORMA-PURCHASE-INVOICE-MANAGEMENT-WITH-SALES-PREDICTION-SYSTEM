import sys
from PyQt6.QtCore import (
    Qt, QTimer, QPropertyAnimation,
    QEasingCurve, pyqtProperty
)
from PyQt6.QtGui import QPainter, QColor, QFont
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel,
    QVBoxLayout, QProgressBar, QGraphicsDropShadowEffect
)


class AuraLogo(QWidget):
    """Simple animated Sales Aura logo."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._glow = 0.0
        self.setFixedSize(110, 110)

        self.animation = QPropertyAnimation(self, b"glow")
        self.animation.setDuration(1800)
        self.animation.setStartValue(0.0)
        self.animation.setEndValue(1.0)
        self.animation.setEasingCurve(
            QEasingCurve.Type.InOutSine
        )
        self.animation.setLoopCount(-1)
        self.animation.start()

    def getGlow(self):
        return self._glow

    def setGlow(self, value):
        self._glow = value
        self.update()

    glow = pyqtProperty(float, getGlow, setGlow)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        cx = self.width() // 2
        cy = self.height() // 2

        # --------------------------------
        # Aura rings
        # --------------------------------
        for i in range(3):
            alpha = int(35 - (i * 8) + self._glow * 8)

            radius = 43 + i * 9 + int(self._glow * 4)

            painter.setPen(
                QColor(60, 141, 188, max(alpha, 8))
            )

            painter.drawEllipse(
                cx - radius,
                cy - radius,
                radius * 2,
                radius * 2
            )

        # --------------------------------
        # Main circle
        # --------------------------------
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#3c8dbc"))

        painter.drawEllipse(
            cx - 34,
            cy - 34,
            68,
            68
        )

        # --------------------------------
        # Upward sales graph
        # --------------------------------
        painter.setPen(
            QColor("#ffffff")
        )

        painter.setBrush(Qt.BrushStyle.NoBrush)

        from PyQt6.QtCore import QPointF

        points = [
            QPointF(cx - 22, cy + 14),
            QPointF(cx - 9, cy + 3),
            QPointF(cx + 1, cy + 9),
            QPointF(cx + 22, cy - 16),
        ]

        for i in range(len(points) - 1):
            painter.drawLine(
                points[i],
                points[i + 1]
            )

        # Arrow head
        painter.drawLine(
            QPointF(cx + 22, cy - 16),
            QPointF(cx + 11, cy - 17)
        )

        painter.drawLine(
            QPointF(cx + 22, cy - 16),
            QPointF(cx + 21, cy - 27)
        )


class SalesAuraSplash(QWidget):

    def __init__(self):
        super().__init__()

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint
        )

        self.setAttribute(
            Qt.WidgetAttribute.WA_TranslucentBackground
        )

        self.setFixedSize(600, 360)

        # --------------------------------
        # Main container
        # --------------------------------
        container = QWidget(self)

        container.setGeometry(
            10, 10,
            580, 340
        )

        container.setStyleSheet("""
            QWidget {
                background: #f7f9fb;
                border-radius: 18px;
            }
        """)

        # Shadow
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(35)
        shadow.setOffset(0, 8)
        shadow.setColor(
            QColor(0, 0, 0, 45)
        )

        container.setGraphicsEffect(shadow)

        # --------------------------------
        # Layout
        # --------------------------------
        layout = QVBoxLayout(container)

        layout.setContentsMargins(
            40, 25, 40, 25
        )

        layout.setSpacing(5)

        # --------------------------------
        # Logo
        # --------------------------------
        logo = AuraLogo()

        layout.addWidget(
            logo,
            alignment=Qt.AlignmentFlag.AlignCenter
        )

        # --------------------------------
        # Product name
        # --------------------------------
        title = QLabel("SALES AURA")

        title.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        title.setStyleSheet("""
            QLabel {
                color: #263238;
                font-size: 30px;
                font-weight: 700;
                letter-spacing: 2px;
                background: transparent;
            }
        """)

        layout.addWidget(title)

        # --------------------------------
        # Tagline
        # --------------------------------
        tagline = QLabel(
            "Smarter Sales. Clearer Decisions."
        )

        tagline.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        tagline.setStyleSheet("""
            QLabel {
                color: #78909c;
                font-size: 14px;
                background: transparent;
            }
        """)

        layout.addWidget(tagline)

        # --------------------------------
        # Spacer
        # --------------------------------
        layout.addSpacing(12)

        # --------------------------------
        # Loading bar
        # --------------------------------
        self.progress = QProgressBar()

        self.progress.setRange(0, 100)
        self.progress.setValue(0)

        self.progress.setTextVisible(False)

        self.progress.setFixedHeight(4)

        self.progress.setStyleSheet("""
            QProgressBar {
                background: #e6ebef;
                border: none;
                border-radius: 2px;
            }

            QProgressBar::chunk {
                background: #3c8dbc;
                border-radius: 2px;
            }
        """)

        layout.addWidget(self.progress)

        # --------------------------------
        # Loading text
        # --------------------------------
        self.loading = QLabel(
            "Starting Sales Aura..."
        )

        self.loading.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        self.loading.setStyleSheet("""
            QLabel {
                color: #90a4ae;
                font-size: 11px;
                background: transparent;
            }
        """)

        layout.addWidget(self.loading)

        # --------------------------------
        # Footer
        # --------------------------------
        footer = QLabel(
            "© 2026 Sales Aura"
        )

        footer.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        footer.setStyleSheet("""
            QLabel {
                color: #b0bec5;
                font-size: 10px;
                background: transparent;
            }
        """)

        layout.addStretch()

        layout.addWidget(footer)

        # --------------------------------
        # Progress animation
        # --------------------------------
        self.progress_value = 0

        self.timer = QTimer(self)
        self.timer.timeout.connect(
            self.update_progress
        )

        self.timer.start(30)

    def update_progress(self):

        self.progress_value += 1

        self.progress.setValue(
            self.progress_value
        )

        if self.progress_value < 30:
            self.loading.setText(
                "Initializing..."
            )

        elif self.progress_value < 60:
            self.loading.setText(
                "Loading modules..."
            )

        elif self.progress_value < 85:
            self.loading.setText(
                "Preparing workspace..."
            )

        else:
            self.loading.setText(
                "Almost ready..."
            )

        if self.progress_value >= 100:

            self.timer.stop()

            QTimer.singleShot(
                400,
                self.close
            )

    def showEvent(self, event):
        super().showEvent(event)

        # Center on screen
        screen = QApplication.primaryScreen()
        geometry = screen.availableGeometry()

        x = (
            geometry.x()
            + (geometry.width() - self.width()) // 2
        )

        y = (
            geometry.y()
            + (geometry.height() - self.height()) // 2
        )

        self.move(x, y)


if __name__ == "__main__":

    app = QApplication(sys.argv)

    # Global font
    app.setFont(
        QFont("Segoe UI", 10)
    )

    splash = SalesAuraSplash()

    splash.show()

    sys.exit(
        app.exec()
    )