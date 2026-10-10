"""
Tiny TTL cache with disk persistence.

Usage:
    from utils.cache import cache

    @cache.cached("dashboard.stats", ttl=300)
    def expensive():
        return db_manager.dashboard_stats()

    # Or manually:
    cache.set("dashboard.stats", value, ttl=300)
    value = cache.get("dashboard.stats")   # None if expired
    cache.invalidate("dashboard.stats")
    cache.invalidate_all()
"""
from __future__ import annotations

import json
import os
import pickle
import threading
import time
from functools import wraps
from typing import Any, Callable, Optional

# Cache file lives next to your app so it survives restarts.
_APP_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CACHE_DIR = os.path.join(_APP_BASE, ".cache")
_CACHE_FILE = os.path.join(_CACHE_DIR, "dashboard.pkl")

_LOCK = threading.RLock()
# Depth counter for TTLCache.batch(): while > 0 the cache suppresses disk
# writes so a multi-key fill costs a single pickle at the end.
_BATCH = [0]


class _Entry:
    __slots__ = ("value", "expires_at")

    def __init__(self, value: Any, ttl: Optional[float]):
        self.value = value
        self.expires_at = (time.time() + ttl) if ttl else None

    def valid(self) -> bool:
        return self.expires_at is None or time.time() < self.expires_at


class TTLCache:
    """Simple thread-safe in-memory cache with optional disk persistence."""

    def __init__(self, persist_path: Optional[str] = None):
        self._data: dict[str, _Entry] = {}
        self._persist_path = persist_path
        if persist_path:
            self._load()

    # ------------------------------------------------------------------ API
    def get(self, key: str, default=None) -> Any:
        # NOTE: _data is only ever mutated under _LOCK, and every read is a
        # plain dict lookup, so the lock is held for a few microseconds here.
        # The expensive part (pickling to disk) happens in _save() with the
        # lock released - otherwise a UI-thread cache.get() would block for
        # the whole duration of a background thread's disk write.
        with _LOCK:
            e = self._data.get(key)
            if e is None:
                return default
            if not e.valid():
                del self._data[key]
                return default
            return e.value

    def set(self, key: str, value: Any, ttl: Optional[float] = 300,
            persist: bool = True) -> None:
        """Store `value` under `key` for `ttl` seconds.

        `persist=False` updates memory only, so a caller that writes many keys
        in a row (e.g. the dashboard prefetch) pays for ONE disk write via
        flush() instead of one per key.
        """
        with _LOCK:
            self._data[key] = _Entry(value, ttl)
            do_save = persist and not _BATCH[0]
        if do_save:
            self._save()

    def flush(self) -> None:
        """Write the in-memory cache to disk now."""
        self._save()

    def invalidate(self, key: str) -> None:
        with _LOCK:
            self._data.pop(key, None)
            do_save = not _BATCH[0]
        if do_save:
            self._save()

    def invalidate_all(self) -> None:
        with _LOCK:
            self._data.clear()
            do_save = not _BATCH[0]
        if do_save:
            self._save()

    def batch(self):
        """Context manager: suppress disk writes until the block exits.

        Used when a caller fills many keys at once (the splash-screen
        dashboard prefetch writes ~15), turning N pickles into one.
        """
        return _Batch()

    def has(self, key: str) -> bool:
        return self.get(key, _MISSING) is not _MISSING

    # ------------------------------------------------------------ decorator
    def cached(self, key: str, ttl: Optional[float] = 300,
               key_args: bool = False):
        """Decorator: cache the function result under `key` for `ttl` seconds.

        If `key_args` is True, the positional args are appended to the key,
        e.g. key="chart" + ("2024",) -> "chart::2024".
        """
        def deco(fn: Callable):
            @wraps(fn)
            def wrapper(*args, **kwargs):
                k = key
                if key_args and args:
                    k = key + "::" + "::".join(str(a) for a in args)
                hit = self.get(k, _MISSING)
                if hit is not _MISSING:
                    return hit
                value = fn(*args, **kwargs)
                self.set(k, value, ttl=ttl)
                return value
            return wrapper
        return deco

    # ------------------------------------------------------ persistence
    def _load(self) -> None:
        if not self._persist_path or not os.path.isfile(self._persist_path):
            return
        try:
            with open(self._persist_path, "rb") as f:
                payload = pickle.load(f)
            with _LOCK:
                self._data = {}
                for k, (value, expires_at) in payload.items():
                    e = _Entry(value, None)
                    e.expires_at = expires_at
                    if e.valid():
                        self._data[k] = e
        except Exception:
            # Corrupt cache — ignore and start fresh
            self._data = {}

    def _save(self) -> None:
        """Snapshot under the lock, then write to disk with the lock released.

        Keeping the (potentially slow) pickle + file replace outside _LOCK is
        what stops a background flush from blocking a UI-thread cache.get().
        """
        if not self._persist_path:
            return
        try:
            with _LOCK:
                payload = {k: (e.value, e.expires_at)
                           for k, e in self._data.items() if e.valid()}
            os.makedirs(os.path.dirname(self._persist_path), exist_ok=True)
            tmp = self._persist_path + ".tmp"
            with open(tmp, "wb") as f:
                pickle.dump(payload, f, protocol=pickle.HIGHEST_PROTOCOL)
            os.replace(tmp, self._persist_path)
        except Exception:
            pass  # never crash on cache write


class _Batch:
    """Context manager toggling the module-level batch flag (depth counted)."""

    def __enter__(self):
        _BATCH[0] += 1
        return self

    def __exit__(self, *exc):
        _BATCH[0] = max(0, _BATCH[0] - 1)
        if _BATCH[0] == 0:
            try:
                cache.flush()      # one flush for the whole batch
            except Exception:
                pass
        return False


_MISSING = object()

# Global cache instance used across the app.
cache = TTLCache(persist_path=_CACHE_FILE)