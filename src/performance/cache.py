"""
src/performance/cache.py — Response Cache
==========================================
TTL-based thread-safe in-memory cache for full RAG/agent responses.

Why this matters:
  - Repeated questions (e.g., "what is your refund policy") hit the cache
    instead of making LLM API calls → faster + cheaper
  - TTL ensures stale answers expire (default 5 min)

Usage:
    cache = ResponseCache(ttl_seconds=300, max_size=256)
    result = cache.get("what is the refund policy")
    if result is None:
        result = run_expensive_query(...)
        cache.set("what is the refund policy", result)
"""

from __future__ import annotations

import hashlib
import logging
import threading
import time
from collections import OrderedDict
from typing import Any, Optional

logger = logging.getLogger(__name__)


class ResponseCache:
    """
    Thread-safe LRU cache with TTL expiry for RAG / agent responses.

    Parameters
    ----------
    ttl_seconds : int
        Time-to-live for each cached entry in seconds (default: 300 = 5 min).
    max_size : int
        Maximum number of entries to hold in the cache (LRU eviction).
    """

    def __init__(self, ttl_seconds: int = 300, max_size: int = 256) -> None:
        self.ttl = ttl_seconds
        self.max_size = max_size
        self._store: OrderedDict[str, tuple[float, Any]] = OrderedDict()
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0

    # ── Public API ────────────────────────────────────────────────────────────

    def get(self, query: str) -> Optional[Any]:
        """
        Retrieve cached value for a query string.

        Returns None if not found or if the entry has expired.
        """
        key = self._hash(query)
        with self._lock:
            if key not in self._store:
                self._misses += 1
                return None

            timestamp, value = self._store[key]
            if time.monotonic() - timestamp > self.ttl:
                # Expired — evict it
                del self._store[key]
                self._misses += 1
                logger.debug(f"[Cache] EXPIRED key={key[:8]}")
                return None

            # Cache hit — move to end (most recently used)
            self._store.move_to_end(key)
            self._hits += 1
            logger.debug(f"[Cache] HIT key={key[:8]} | hits={self._hits}")
            return value

    def set(self, query: str, value: Any) -> None:
        """Store a value in the cache for the given query string."""
        key = self._hash(query)
        with self._lock:
            if key in self._store:
                self._store.move_to_end(key)
            self._store[key] = (time.monotonic(), value)

            # Evict oldest entry if over capacity
            while len(self._store) > self.max_size:
                evicted_key, _ = self._store.popitem(last=False)
                logger.debug(f"[Cache] EVICTED key={evicted_key[:8]} (LRU)")

    def invalidate(self, query: Optional[str] = None) -> None:
        """
        Invalidate a specific query's cache entry, or flush the entire cache
        if query is None.
        """
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
        """Return cache performance statistics."""
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

    # ── Internal ──────────────────────────────────────────────────────────────

    @staticmethod
    def _hash(query: str) -> str:
        """Normalize and hash a query string for use as a cache key."""
        normalized = query.strip().lower()
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()
