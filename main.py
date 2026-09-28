import sys

if sys.platform == "win32":
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            "c4.pyqt.invoice.app"
        )
    except Exception:
        pass

from PyQt6.QtCore import QCoreApplication, Qt

QCoreApplication.setAttribute(
    Qt.ApplicationAttribute.AA_ShareOpenGLContexts, True)

from PyQt6.QtWidgets import QApplication

from ui.splash_screen import SplashScreen
from ui.login_window import LoginWindow
from ui.main_window import MainWindow
from ui.app_icon import app_icon, apply
from ui.theme import QSS


def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(QSS)
    # Brand icon for every title bar / taskbar entry of the app: top-level
    # widgets (dialogs included) inherit the application icon automatically.
    app.setWindowIcon(app_icon())

    state = {"splash": None, "login": None, "main": None}

    splash = SplashScreen(duration_ms=2600)
    apply(splash)
    state["splash"] = splash

    def on_splash_done():
        s = state.get("splash")
        if s is not None:
            s.deleteLater()
        state["splash"] = None

        def on_login_success(admin_row):
            # ================================================ #
            # THE FIX: pass the whole admin row, not 3 keys.
            # ================================================ #
            user = dict(admin_row)

            window = MainWindow(user)
            apply(window)
            state["main"] = window
            window.show()
            state["login"] = None

        login = LoginWindow(on_success=on_login_success)
        apply(login)
        state["login"] = login
        login.show()

    splash.finished.connect(on_splash_done)
    splash.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())