"""
Facebook Scraper page - PyQt6 UI on top of utils/fb_scraper/.

Tabs:
  * Simple Post  -> comments + images from one post
  * Page Posts   -> posts + comments from a Page
  * Group Posts  -> posts + comments from a Group

All scrapers run in a background QThread; the UI never freezes.
"""
import os
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QLineEdit, QSpinBox, QTabWidget,
                             QPlainTextEdit, QFrame, QFileDialog, QMessageBox)

from ui import widgets as W
from ui.app_icon import apply as _apply_brand
from utils.fb_scraper_worker import (ScraperWorker,
                                     make_simple_post_task,
                                     make_page_posts_task,
                                     make_group_posts_task)


class FacebookScraperPage(QWidget):
    title = "Facebook Scraper"

    def __init__(self, main):
        super().__init__()
        self.main = main
        self._worker = None

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)

        lay.addWidget(W.PageHeader(
            "Facebook Scraper",
            breadcrumb="Tools > Facebook Scraper"))

        card = QFrame()
        card.setStyleSheet(
            "QFrame { background:#ffffff; border:1px solid #d2d6de;"
            " border-top:3px solid #3c8dbc; border-radius:3px; }")
        cl = QVBoxLayout(card)
        cl.setContentsMargins(14, 12, 14, 12)
        cl.setSpacing(10)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_simple_tab(), "Simple Post")
        self.tabs.addTab(self._build_page_tab(), "Page Posts")
        self.tabs.addTab(self._build_group_tab(), "Group Posts")
        cl.addWidget(self.tabs)

        # ---- shared log area ----
        log_lbl = QLabel("Log")
        log_lbl.setStyleSheet(
            "font-size:13px; font-weight:600; color:#444;"
            " background:transparent; border:none;")
        cl.addWidget(log_lbl)

        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setFixedHeight(180)
        self.log.setStyleSheet(
            "QPlainTextEdit { background:#0f172a; color:#e5e7eb;"
            " font-family:Consolas,monospace; font-size:11pt;"
            " border:1px solid #d2d6de; border-radius:3px; padding:6px; }")
        cl.addWidget(self.log)

        lay.addWidget(card, 1)

    # ------------------------------------------------------------------ #
    def _build_simple_tab(self):
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(8, 8, 8, 8)
        v.setSpacing(8)

        v.addWidget(QLabel(
            "Enter the URL of a Facebook post (or its numeric post_id)."))
        self.simple_input = QLineEdit()
        self.simple_input.setPlaceholderText(
            "https://www.facebook.com/.../posts/1234567890")
        v.addWidget(self.simple_input)

        self.simple_run = QPushButton("Scrape Comments")
        self.simple_run.setObjectName("btnSuccess")
        self.simple_run.setFixedHeight(34)
        self.simple_run.clicked.connect(self._run_simple)
        v.addWidget(self.simple_run)
        v.addStretch()
        return w

    def _build_page_tab(self):
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(8, 8, 8, 8)
        v.setSpacing(8)

        v.addWidget(QLabel("Enter the URL of a Facebook Page "
                           "(or its numeric page_id)."))
        self.page_input = QLineEdit()
        self.page_input.setPlaceholderText(
            "https://www.facebook.com/YourPage")
        v.addWidget(self.page_input)

        row = QHBoxLayout()
        row.addWidget(QLabel("Posts to fetch:"))
        self.page_count = QSpinBox()
        self.page_count.setRange(1, 200)
        self.page_count.setValue(10)
        row.addWidget(self.page_count)
        row.addStretch()
        v.addLayout(row)

        self.page_run = QPushButton("Scrape Page Posts")
        self.page_run.setObjectName("btnSuccess")
        self.page_run.setFixedHeight(34)
        self.page_run.clicked.connect(self._run_page)
        v.addWidget(self.page_run)
        v.addStretch()
        return w

    def _build_group_tab(self):
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(8, 8, 8, 8)
        v.setSpacing(8)

        v.addWidget(QLabel("Enter the URL of a Facebook Group "
                           "(or its numeric group_id)."))
        self.group_input = QLineEdit()
        self.group_input.setPlaceholderText(
            "https://www.facebook.com/groups/YourGroup")
        v.addWidget(self.group_input)

        row = QHBoxLayout()
        row.addWidget(QLabel("Posts to fetch:"))
        self.group_count = QSpinBox()
        self.group_count.setRange(1, 200)
        self.group_count.setValue(10)
        row.addWidget(self.group_count)
        row.addStretch()
        v.addLayout(row)

        self.group_run = QPushButton("Scrape Group Posts")
        self.group_run.setObjectName("btnSuccess")
        self.group_run.setFixedHeight(34)
        self.group_run.clicked.connect(self._run_group)
        v.addWidget(self.group_run)
        v.addStretch()
        return w

    # ------------------------------------------------------------------ #
    # Log helpers
    # ------------------------------------------------------------------ #
    def _clear_log(self):
        self.log.clear()

    def _append_log(self, line: str):
        self.log.appendPlainText(str(line))
        # auto-scroll
        sb = self.log.verticalScrollBar()
        sb.setValue(sb.maximum())

    # ------------------------------------------------------------------ #
    # Dispatch
    # ------------------------------------------------------------------ #
    def _start(self, task, run_btn):
        if self._worker and self._worker.isRunning():
            QMessageBox.information(self, "Busy",
                                    "A scrape is already running.")
            return
        self._clear_log()
        run_btn.setEnabled(False)
        self._worker = ScraperWorker(task, self)
        self._worker.log.connect(self._append_log)
        self._worker.done.connect(
            lambda ok, msg, folder: self._finish(ok, msg, folder, run_btn))
        self._worker.start()

    def _finish(self, ok, msg, folder, run_btn):
        run_btn.setEnabled(True)
        self._append_log("")
        self._append_log(f"{'✅' if ok else '❌'} {msg}")
        if folder and os.path.isdir(folder):
            self._append_log(f"📁 Output folder: {folder}")
            # open the folder in the OS file explorer
            QDesktopServices.openUrl(QUrl.fromLocalFile(folder))
        self._worker = None

    # ------------------------------------------------------------------ #
    # Button handlers
    # ------------------------------------------------------------------ #
    def _run_simple(self):
        val = self.simple_input.text().strip()
        if not val:
            QMessageBox.warning(self, "Missing input", "Enter a URL or ID.")
            return
        is_url = val.startswith("http")
        task = make_simple_post_task(val, is_url=is_url)
        self._start(task, self.simple_run)

    def _run_page(self):
        val = self.page_input.text().strip()
        if not val:
            QMessageBox.warning(self, "Missing input", "Enter a URL or ID.")
            return
        is_url = val.startswith("http")
        task = make_page_posts_task(val, self.page_count.value(),
                                    is_url=is_url)
        self._start(task, self.page_run)

    def _run_group(self):
        val = self.group_input.text().strip()
        if not val:
            QMessageBox.warning(self, "Missing input", "Enter a URL or ID.")
            return
        is_url = val.startswith("http")
        task = make_group_posts_task(val, self.group_count.value(),
                                     is_url=is_url)
        self._start(task, self.group_run)