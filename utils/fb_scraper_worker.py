"""
Background workers for the Facebook scraper.

Runs the requests-based scraper from `utils/fb_scraper/` in a QThread,
emitting log lines and final results so the PyQt UI stays responsive.
"""
import os
import sys
import importlib.util
import traceback
from PyQt6.QtCore import QThread, pyqtSignal


# Make sure the fb_scraper package is importable regardless of cwd
_HERE = os.path.dirname(os.path.abspath(__file__))
_FB_DIR = os.path.join(_HERE, "fb_scraper")
if _FB_DIR not in sys.path:
    sys.path.insert(0, _FB_DIR)


# Both the application entry point (project root ``main.py``) and the scraper
# (``utils/fb_scraper/main.py``) are called "main", so a plain ``import main``
# can resolve to the wrong file and blow up with
#     AttributeError: module 'main' has no attribute 'extract_post_id_from_url'
# Load the scraper's ``main.py`` from its explicit path instead. Its own
# ``from comment_scraper import ...`` style imports still resolve through
# ``sys.path`` above, so the sibling modules stay shared - required because the
# tasks below monkey-patch them (``post_scraper.USER_ID = ...`` must hit the
# very module object ``fetch_posts`` reads its globals from).
_FB_MAIN_MODULE = "fb_scraper_main"


def _load_fb_main():
    """The ``utils/fb_scraper/main.py`` module (imported once, then cached)."""
    module = sys.modules.get(_FB_MAIN_MODULE)
    if module is None:
        spec = importlib.util.spec_from_file_location(
            _FB_MAIN_MODULE, os.path.join(_FB_DIR, "main.py"))
        module = importlib.util.module_from_spec(spec)
        sys.modules[_FB_MAIN_MODULE] = module
        spec.loader.exec_module(module)
    return module


class ScraperWorker(QThread):
    """Generic worker that runs a callable in a background thread."""

    log = pyqtSignal(str)              # progress line
    done = pyqtSignal(bool, str, str)  # ok, message, output_folder

    def __init__(self, task, parent=None):
        super().__init__(parent)
        self._task = task              # callable(log_emit) -> (ok, msg, folder)

    def run(self):
        try:
            ok, msg, folder = self._task(self.log.emit)
        except Exception:
            traceback.print_exc()
            ok, msg, folder = False, "Unhandled exception — see terminal.", ""
        self.done.emit(ok, msg, folder)


# --------------------------------------------------------------------------- #
# Task factories — one per scraper mode
# --------------------------------------------------------------------------- #
def _build_env():
    """Load cookies + proxy from .env into the fb_scraper modules."""
    from dotenv import load_dotenv
    load_dotenv(os.path.join(_FB_DIR, ".env"))


def make_simple_post_task(post_url_or_id, is_url=True):
    """Scrape comments from a single post (mirrors scrape_simple_post())."""
    def task(log):
        _build_env()
        fb_main = _load_fb_main()         # utils/fb_scraper/main.py

        log(f"📘 Simple Post scraper starting…")

        # ----- resolve post_id -----
        if is_url:
            log(f"  Extracting post ID from URL: {post_url_or_id}")
            post_id = fb_main.extract_post_id_from_url(post_url_or_id)
        else:
            post_id = str(post_url_or_id).strip()

        if not post_id:
            return False, "Could not determine post ID.", ""

        log(f"  Post ID = {post_id}")
        log(f"  Fetching comments…")

        comments, post_info = fb_main.fetch_comments_for_post(post_id)

        post_data = {
            "post_id": post_id,
            "type": "simple_post",
            "post_info": post_info,
        }

        # Save under <project>/simple_post/<post_id>/
        out_root = os.path.join(os.getcwd(), "fb_output")
        os.makedirs(out_root, exist_ok=True)
        os.chdir(out_root)                     # fb_main saves relative to cwd
        fb_main.save_post_data("simple_post", post_id, post_data, comments)

        folder = os.path.join(out_root, "simple_post", post_id)
        log(f"  ✅ Saved to {folder}")
        return True, f"Fetched {len(comments)} comments.", folder
    return task


def make_page_posts_task(page_url_or_id, count, is_url=True):
    """Scrape posts + comments from a Page."""
    def task(log):
        _build_env()
        fb_main = _load_fb_main()
        import post_scraper

        log("📘 Page Posts scraper starting…")

        if is_url:
            log(f"  Extracting page ID from URL: {page_url_or_id}")
            page_id = fb_main.extract_user_id_from_url(page_url_or_id)
        else:
            page_id = str(page_url_or_id).strip()

        if not page_id:
            return False, "Could not determine page ID.", ""

        log(f"  Page ID = {page_id}")
        post_scraper.USER_ID = page_id
        post_scraper.BASE_HEADERS["referer"] = (
            f"https://www.facebook.com/profile.php?id={page_id}")

        log(f"  Fetching up to {count} posts…")
        posts = fb_main.fetch_page_posts(count)
        log(f"  Found {len(posts)} posts. Fetching comments…")

        out_root = os.path.join(os.getcwd(), "fb_output")
        os.makedirs(out_root, exist_ok=True)
        os.chdir(out_root)

        for i, post in enumerate(posts, 1):
            pid = post.get("post_id")
            if not pid:
                continue
            log(f"  [{i}/{len(posts)}] comments for {pid}")
            try:
                comments, _ = fb_main.fetch_comments_for_post(pid)
                fb_main.save_post_data("page_post", pid, post, comments)
            except Exception as exc:
                log(f"     ⚠️ {exc}")

        folder = os.path.join(out_root, "page_post")
        log(f"  ✅ Saved under {folder}")
        return True, f"Scraped {len(posts)} posts.", folder
    return task


def make_group_posts_task(group_url_or_id, count, is_url=True):
    """Scrape posts + comments from a Group."""
    def task(log):
        _build_env()
        fb_main = _load_fb_main()
        import group_post_scraper_v2

        log("📘 Group Posts scraper starting…")

        if is_url:
            log(f"  Extracting group ID from URL: {group_url_or_id}")
            group_id = fb_main.extract_group_id_from_url(group_url_or_id)
        else:
            group_id = str(group_url_or_id).strip()

        if not group_id:
            return False, "Could not determine group ID.", ""

        log(f"  Group ID = {group_id}")
        group_post_scraper_v2.GROUP_ID = group_id
        group_post_scraper_v2.HEADERS["referer"] = (
            f"https://www.facebook.com/groups/{group_id}/")

        log(f"  Fetching up to {count} posts…")
        posts = fb_main.fetch_group_posts(count)
        log(f"  Found {len(posts)} posts. Fetching comments…")

        out_root = os.path.join(os.getcwd(), "fb_output")
        os.makedirs(out_root, exist_ok=True)
        os.chdir(out_root)

        for i, post in enumerate(posts, 1):
            pid = post.get("post_id")
            if not pid:
                continue
            log(f"  [{i}/{len(posts)}] comments for {pid}")
            try:
                comments, _ = fb_main.fetch_comments_for_post(pid)
                fb_main.save_post_data("group_post", pid, post, comments)
            except Exception as exc:
                log(f"     ⚠️ {exc}")

        folder = os.path.join(out_root, "group_post")
        log(f"  ✅ Saved under {folder}")
        return True, f"Scraped {len(posts)} posts.", folder
    return task