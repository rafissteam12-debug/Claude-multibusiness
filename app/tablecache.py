"""Parse an upload once: a small in-memory cache of parsed tables (review H1).

Holds at most a few tables for a few minutes so upload -> propose -> convert does not parse the same
file three times. Cell values live only in process memory and are dropped with the upload.
"""
from __future__ import annotations

import threading
import time
from collections import OrderedDict

MAX_ENTRIES = 4
TTL_SECONDS = 15 * 60


class TableCache:
    def __init__(self, max_entries: int = MAX_ENTRIES, ttl: float = TTL_SECONDS):
        self.max, self.ttl = max_entries, ttl
        self._d: OrderedDict[str, tuple[float, object]] = OrderedDict()
        self._lock = threading.Lock()

    def get(self, key: str):
        with self._lock:
            item = self._d.get(key)
            if not item:
                return None
            if time.monotonic() - item[0] > self.ttl:
                self._d.pop(key, None)
                return None
            self._d.move_to_end(key)
            return item[1]

    def put(self, key: str, table) -> None:
        with self._lock:
            self._d[key] = (time.monotonic(), table)
            self._d.move_to_end(key)
            while len(self._d) > self.max:
                self._d.popitem(last=False)

    def drop(self, key: str) -> None:
        with self._lock:
            self._d.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._d.clear()


table_cache = TableCache()


def read_cached(upload_id: str, path, filename: str):
    """The parsed Table of an upload (raises mapping.TableReadError like read_table)."""
    import mapping
    from pathlib import Path

    t = table_cache.get(upload_id)
    if t is None:
        t = mapping.read_table(Path(path).read_bytes(), filename)
        table_cache.put(upload_id, t)
    return t
