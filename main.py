import sys

if sys.platform == "win32":
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            "c4.pyqt.invoice.app"
        )
    except Exception:
        pass

# ===========================================================================
# PATCH 1: WebEngine safe-mode env (must be set BEFORE any PyQt import)
# ===========================================================================
import os
os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS",
                      "--disable-gpu --disable-software-rasterizer")
os.environ.setdefault("QT_OPENGL", "software")

from PyQt6.QtCore import (QCoreApplication, Qt, QThread, QTimer,
                          QSharedMemory)
from PyQt6.QtWidgets import QApplication, QMessageBox

QCoreApplication.setAttribute(
    Qt.ApplicationAttribute.AA_ShareOpenGLContexts, True)

# ===========================================================================
# PATCH 2: initialize QtWebEngine BEFORE QApplication is constructed
# ===========================================================================
try:
    from PyQt6 import QtWebEngineQuick
    QtWebEngineQuick.initialize()
except Exception:
    pass

from ui.splash_screen import SplashScreen
from ui.login_window import LoginWindow
from ui.main_window import MainWindow
from ui.app_icon import app_icon, apply
from ui.theme import QSS
from utils import dashboard_cache


# ===========================================================================
# SINGLE-INSTANCE GUARD
# ---------------------------------------------------------------------------
# Only one Sales Aura may run at a time. Uses a named Qt shared-memory
# segment as a mutex. The key MUST match AppMutex in the .iss file
# ("SalesAuraMutex2026").
# ===========================================================================
_SINGLE_INSTANCE_KEY = "SalesAuraMutex2026"
_shared_mem = None     # module-level reference — MUST NOT be garbage-collected


def _ensure_single_instance(app: QApplication) -> bool:
    """
    Return True if this is the first instance (continue startup).

    If another Sales Aura is already running, show a friendly message and
    return False so main() can exit cleanly without launching any windows.
    """
    global _shared_mem

    _shared_mem = QSharedMemory(_SINGLE_INSTANCE_KEY)

    # If a previous process crashed while holding the segment, it may still
    # be attached — try to detach first so we don't get a false positive.
    _shared_mem.attach()
    _shared_mem.detach()

    if _shared_mem.create(1):
        return True   # first instance

    # Another instance is running
    QMessageBox.information(
        None,
        "Sales Aura",
        "Sales Aura is already running.\n\n"
        "Please use the existing window.",
    )
    return False


# ===========================================================================
#  Background dashboard prefetch
# ===========================================================================
# Set to False to silence the [PREFETCH] console logs once everything works.
PREFETCH_DEBUG = True


def _dbg(*args):
    if PREFETCH_DEBUG:
        try:
            print("[PREFETCH]", *args, flush=True)
        except Exception:
            pass


class _PrefetchThread(QThread):
    """
    Runs dashboard_cache.fill_all() off the UI thread.

    Emits `progress(done, total, key)` after each query and
    `finished_all(ok)` once the warm-up is complete.
    """

    from PyQt6.QtCore import pyqtSignal as _sig
    progress = _sig(int, int, str)
    finished_all = _sig(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("dashboard-prefetch")
        self.done = False
        self.total = 0
        self.completed = 0

    def run(self):
        import time
        t0 = time.time()
        ok = True
        try:
            from datetime import date
            today = date.today()
            year = today.year
            fy_start = today.year
            fy_end = today.year + 1

            _dbg(f"start  year={year}  fy={fy_start}-{fy_end}")

            def _progress(done, total, key):
                self.completed = done
                self.total = total
                try:
                    self.progress.emit(done, total, key)
                except Exception:
                    pass
                _dbg(f"  {done}/{total}  {key}")

            dashboard_cache.fill_all(
                year, fy_start, fy_end,
                progress=_progress,
            )

            elapsed = time.time() - t0
            keys = list(dashboard_cache.stats().keys()) \
                if hasattr(dashboard_cache, "stats") else []
            _dbg(f"done   {elapsed:.2f}s  keys={len(keys)}")
            if keys:
                _dbg(f"       {keys}")
        except Exception as exc:
            ok = False
            _dbg(f"FAILED: {exc!r}")
            try:
                import traceback
                traceback.print_exc()
            except Exception:
                pass
        finally:
            self.done = True
            try:
                self.finished_all.emit(ok)
            except Exception:
                pass


# Hard ceiling: never keep the splash held longer than this.
PREFETCH_HOLD_MAX_MS = 20000


# ===========================================================================
# PATCH 3: Warm heavy subsystems on the GUI thread before the event loop
# ===========================================================================
def _warm_heavy_subsystems():
    """Best-effort warm-up of subsystems used by the invoice preview button."""
    try:
        from PyQt6.QtPrintSupport import QPrinter
        _ = QPrinter()
    except Exception:
        pass
    try:
        from utils import invoice_print  # noqa: F401
        _ = invoice_print
    except Exception:
        pass
    try:
        from ui.pages import invoice_pages  # noqa: F401
        _ = invoice_pages
    except Exception:
        pass
    try:
        from ui.pages import master_pages  # noqa: F401
        _ = master_pages
    except Exception:
        pass
    try:
        from ui.pages import info  # noqa: F401
        _ = info
    except Exception:
        pass
    try:
        from PyQt6.QtWebEngineWidgets import QWebEngineView  # noqa: F401
        _ = QWebEngineView
    except Exception:
        pass


# --------------------------------------------------------------------------- #
# Helper: strict progress check for SplashScreen
# --------------------------------------------------------------------------- #
def _splash_progress_full(splash):
    """Return True only if the splash has genuinely reached 100%."""
    if splash is None:
        return True

    v = getattr(splash, "_progress", None)
    if isinstance(v, (int, float)):
        if v <= 1.0001:
            return v >= 0.999
        return v >= 99.9

    for attr in ("progress", "_value", "value",
                 "_progress_value", "progress_value"):
        v = getattr(splash, attr, None)
        if isinstance(v, (int, float)):
            if v <= 1.0001:
                return v >= 0.999
            return v >= 99.9

    return False


def _on_logout(window, state):
    """Full teardown on logout so the NEXT login starts clean."""
    try:
        for dlg in list(getattr(window, "_invoice_view_dialogs", []) or []):
            try:
                dlg.close()
                dlg.deleteLater()
            except Exception:
                pass
    except Exception:
        pass
    try:
        window.deleteLater()
    except Exception:
        pass
    state["main"] = None

    def _relogin(admin_row):
        user = dict(admin_row)
        nxt = MainWindow(user)
        apply(nxt)
        state["main"] = nxt
        nxt.set_logout_callback(lambda: _on_logout(nxt, state))
        nxt.showMaximized()
        state["login"] = None

    from ui.login_window import LoginWindow as _LoginWindow
    from ui.app_icon import apply as _apply
    login = _LoginWindow(on_success=_relogin)
    _apply(login)
    state["login"] = login
    login.showMaximized()


def main():
    app = QApplication(sys.argv)

    # -----------------------------------------------------------------------
    # SINGLE INSTANCE: only one Sales Aura may run at a time.
    # If another instance is already running, show a message and exit.
    # -----------------------------------------------------------------------
    if not _ensure_single_instance(app):
        return 0

    app.setStyleSheet(QSS)
    app.setWindowIcon(app_icon())

    # ---- PATCH 3: warm-up before any window opens ----
    _warm_heavy_subsystems()

    state = {"splash": None, "login": None, "main": None, "prefetch": None}

    # =======================================================================
    # SPLASH — held until BOTH: progress==100% AND prefetch done (or ceiling)
    # =======================================================================
    splash = SplashScreen(duration_ms=2600)
    apply(splash)
    state["splash"] = splash

    # Put the splash into "hold" mode immediately.
    splash.hold()

    # Start the prefetch worker in parallel with the splash animation.
    prefetch = _PrefetchThread()
    prefetch.start()
    state["prefetch"] = prefetch

    # Optional: bridge prefetch progress into the splash's status text
    def _on_prefetch_progress(done, total, key):
        try:
            s = state.get("splash")
            if s is not None and hasattr(s, "_status_text"):
                # Optional cosmetic: show "Preparing dashboard… 3/14"
                pass
        except Exception:
            pass

    prefetch.progress.connect(_on_prefetch_progress)

    # ---- Poll every 120 ms: close only when both conditions hold ----------
    hold_deadline = [False]
    hold_timer = QTimer()
    hold_timer.setInterval(120)

    def poll_prefetch():
        p = state.get("prefetch")
        prefetch_done = (p is None) or bool(getattr(p, "done", False))
        progress_full = _splash_progress_full(state.get("splash"))

        if (prefetch_done and progress_full) or hold_deadline[0]:
            hold_timer.stop()
            ceiling.stop()
            s = state.get("splash")
            if s is not None:
                s.release_finish()

    hold_timer.timeout.connect(poll_prefetch)
    hold_timer.start()

    # Hard ceiling: never hold the splash longer than PREFETCH_HOLD_MAX_MS
    ceiling = QTimer()
    ceiling.setSingleShot(True)
    ceiling.setInterval(PREFETCH_HOLD_MAX_MS)
    ceiling.timeout.connect(lambda: hold_deadline.__setitem__(0, True))
    ceiling.start()

    # ---- Splash teardown → login window ----------------------------------
    def on_splash_done():
        s = state.get("splash")
        if s is not None:
            try:
                s.deleteLater()
            except Exception:
                pass
        state["splash"] = None

        def on_login_success(admin_row):
            user = dict(admin_row)

            window = MainWindow(user)
            apply(window)
            state["main"] = window
            window.set_logout_callback(
                lambda: _on_logout(window, state))
            window.showMaximized()
            state["login"] = None

        login = LoginWindow(on_success=on_login_success)
        apply(login)
        state["login"] = login
        login.showMaximized()

    splash.finished.connect(on_splash_done)
    splash.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())