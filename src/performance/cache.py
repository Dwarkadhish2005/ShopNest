
from __future__ import annotations

import hashlib
import logging
import threading
import time
from collections import OrderedDict
from typing import Any, Optional

logger = logging.getLogger(__name__)


class ResponseCache:

    def __init__(self, ttl_seconds: int = 300, max_size: int = 256) -> None:
        self.ttl = ttl_seconds
        self.max_size = max_size
        self._store: OrderedDict[str, tuple[float, Any]] = OrderedDict()
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0

    

    def get(self, query: str) -> Optional[Any]:
        key = self._hash(query)
        with self._lock:
            if key not in self._store:
                self._misses += 1
                return None

            timestamp, value = self._store[key]
            if time.monotonic() - timestamp > self.ttl:
                
                del self._store[key]
                self._misses += 1
                logger.debug(f"[Cache] EXPIRED key={key[:8]}")
                return None

            
            self._store.move_to_end(key)
            self._hits += 1
            logger.debug(f"[Cache] HIT key={key[:8]} | hits={self._hits}")
            return value

    def set(self, query: str, value: Any) -> None:
        key = self._hash(query)
        with self._lock:
            if key in self._store:
                self._store.move_to_end(key)
            self._store[key] = (time.monotonic(), value)

            
            while len(self._store) > self.max_size:
                evicted_key, _ = self._store.popitem(last=False)
                logger.debug(f"[Cache] EVICTED key={evicted_key[:8]} (LRU)")

    def invalidate(self, query: Optional[str] = None) -> None:
        with self._lock:
            if query is None:
                count = len(self._store)
                self._store.clear()
                logger.info(f"[Cache] FLUSHED {count} entries")
            else:
                key = self._hash(query)
                if key in self._store:
                    del self._store[key]
                    logger.debug(f"[Cache] INVALIDATED key={key[:8]}")

    def stats(self) -> dict:
        with self._lock:
            total = self._hits + self._misses
            return {
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": round(self._hits / total, 4) if total else 0.0,
                "cached_entries": len(self._store),
                "max_size": self.max_size,
                "ttl_seconds": self.ttl,
            }

    

    @staticmethod
    def _hash(query: str) -> str:
        normalized = query.strip().lower()
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()
