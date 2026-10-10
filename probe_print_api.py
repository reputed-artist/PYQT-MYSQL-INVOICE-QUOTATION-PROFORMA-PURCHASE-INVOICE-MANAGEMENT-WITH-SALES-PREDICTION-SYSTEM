import sys
sys.path.insert(0, r"c:\xampp\htdocs\pyqt_app_sqlite")
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWidgets import QApplication
app = QApplication([])
from PyQt6.QtWebEngineCore import QWebEnginePage
import PyQt6.QtCore as C
print("QT:", C.QT_VERSION_STR)
page_methods = [m for m in dir(QWebEnginePage) if "rint" in m.lower()]
view_methods = [m for m in dir(QWebEngineView) if "rint" in m.lower()]
with open(r"c:\xampp\htdocs\pyqt_app_sqlite\probe_out.txt", "w") as f:
    f.write("QT=" + C.QT_VERSION_STR + "\n")
    f.write("PAGE_PRINT_METHODS=" + repr(page_methods) + "\n")
    f.write("VIEW_PRINT_METHODS=" + repr(view_methods) + "\n")
    f.write("has_page_print=" + repr(hasattr(QWebEnginePage, "print")) + "\n")
    f.write("has_view_print=" + repr(hasattr(QWebEngineView, "print")) + "\n")
