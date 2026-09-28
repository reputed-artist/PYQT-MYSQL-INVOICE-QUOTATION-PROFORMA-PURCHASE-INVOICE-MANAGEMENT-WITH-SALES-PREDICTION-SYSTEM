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
        with _LOCK:
            e = self._data.get(key)
            if e is None:
                return default
            if not e.valid():
                del self._data[key]
                return default
            return e.value

    def set(self, key: str, value: Any, ttl: Optional[float] = 300) -> None:
        with _LOCK:
            self._data[key] = _Entry(value, ttl)
            self._save()

    def invalidate(self, key: str) -> None:
        with _LOCK:
            self._data.pop(key, None)
            self._save()

    def invalidate_all(self) -> None:
        with _LOCK:
            self._data.clear()
            self._save()

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
        if not self._persist_path:
            return
        try:
            os.makedirs(os.path.dirname(self._persist_path), exist_ok=True)
            payload = {k: (e.value, e.expires_at)
                       for k, e in self._data.items() if e.valid()}
            tmp = self._persist_path + ".tmp"
            with open(tmp, "wb") as f:
                pickle.dump(payload, f, protocol=pickle.HIGHEST_PROTOCOL)
            os.replace(tmp, self._persist_path)
        except Exception:
            pass  # never crash on cache write


_MISSING = object()

# Global cache instance used across the app.
cache = TTLCache(persist_path=_CACHE_FILE)