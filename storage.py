"""
Thread-safe JSON file storage with file-level locking to prevent race conditions.
Uses a lock file to ensure atomic read-modify-write operations.

Optimization: in-memory cache with write-time invalidation.
Reads within the same process that don't cross a write boundary are served
from memory — eliminates redundant disk I/O + JSON parsing.

Thread safety is preserved because:
- Python's GIL ensures dict reads/writes are atomic.
- The cache dirty flag is only set inside the file lock.
- For this single-process CLI tool, no cross-process caching issues exist.
"""
import json
import os
import time
import threading
from typing import Optional

DATA_FILE = os.path.join(os.path.dirname(__file__), "data.json")
LOCK_FILE = DATA_FILE + ".lock"


class FileLock:
    """Cross-platform file lock using a lock file with exponential backoff."""

    def __init__(self, lock_path: str, max_retries: int = 50, base_delay: float = 0.01):
        self.lock_path = lock_path
        self.max_retries = max_retries
        self.base_delay = base_delay
        self._lock_file: Optional[object] = None
        self._thread_lock = threading.Lock()

    def acquire(self) -> None:
        """Acquire the file lock with exponential backoff."""
        with self._thread_lock:
            delay = self.base_delay
            for _ in range(self.max_retries):
                try:
                    self._lock_file = open(self.lock_path, "x")
                    self._lock_file.close()
                    return
                except FileExistsError:
                    time.sleep(delay)
                    delay = min(delay * 1.5, 0.5)
            # Last resort: remove stale lock and try once more
            try:
                os.remove(self.lock_path)
            except OSError:
                pass
            self._lock_file = open(self.lock_path, "x")
            self._lock_file.close()

    def release(self) -> None:
        """Release the file lock."""
        with self._thread_lock:
            try:
                if self._lock_file:
                    self._lock_file.close()
                    self._lock_file = None
                os.remove(self.lock_path)
            except OSError:
                pass


_file_lock = FileLock(LOCK_FILE)

# --- In-memory cache ---
_cache: Optional[dict] = None
_cache_dirty: bool = True  # Start dirty so first read hits disk


def _load_data() -> dict:
    """Load all data from the JSON file."""
    if not os.path.exists(DATA_FILE):
        return {"events": [], "registrations": []}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_data(data: dict) -> None:
    """Save all data to the JSON file atomically."""
    tmp = DATA_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp, DATA_FILE)


def read_data() -> dict:
    """
    Thread-safe read of all data with in-memory caching.
    First call reads from disk; subsequent calls return cached copy
    until a write invalidates the cache.
    """
    global _cache, _cache_dirty

    # Fast path: return cached data if clean (no lock needed for read)
    if not _cache_dirty and _cache is not None:
        return _cache

    # Slow path: read from disk
    _file_lock.acquire()
    try:
        # Double-check after acquiring lock — another thread may have refreshed
        if not _cache_dirty and _cache is not None:
            return _cache
        _cache = _load_data()
        _cache_dirty = False
        return _cache
    finally:
        _file_lock.release()


def write_data(data: dict) -> None:
    """Thread-safe write of all data. Invalidates the cache."""
    global _cache, _cache_dirty
    _file_lock.acquire()
    try:
        _save_data(data)
        _cache = data
        _cache_dirty = False
    finally:
        _file_lock.release()


def atomic_update(operation) -> any:
    """
    Execute an operation atomically: read data, apply operation, write back.
    Invalidates the in-memory cache on write so the next read picks up changes.
    """
    global _cache, _cache_dirty
    _file_lock.acquire()
    try:
        data = _load_data()
        result = operation(data)
        _save_data(data)
        # Update cache with the written data — no need for next read to hit disk
        _cache = data
        _cache_dirty = False
        return result
    finally:
        _file_lock.release()
