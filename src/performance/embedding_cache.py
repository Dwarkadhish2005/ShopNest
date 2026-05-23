
from __future__ import annotations

import hashlib
import logging
import threading
from collections import OrderedDict
from typing import List

from langchain_huggingface import HuggingFaceEmbeddings

logger = logging.getLogger(__name__)


class CachedEmbeddings:

    def __init__(self, base: HuggingFaceEmbeddings, max_size: int = 512) -> None:
        self._base = base
        self.max_size = max_size
        self._cache: OrderedDict[str, List[float]] = OrderedDict()
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0

    

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        results: List[List[float]] = []
        to_embed_indices: List[int] = []
        to_embed_texts: List[str] = []

        for i, text in enumerate(texts):
            key = self._hash(text)
            cached = self._get(key)
            if cached is not None:
                results.append(cached)
            else:
                results.append(None)           
                to_embed_indices.append(i)
                to_embed_texts.append(text)

        
        if to_embed_texts:
            fresh = self._base.embed_documents(to_embed_texts)
            for idx, vec in zip(to_embed_indices, fresh):
                key = self._hash(texts[idx])
                self._put(key, vec)
                results[idx] = vec

        return results

    def embed_query(self, text: str) -> List[float]:
        key = self._hash(text)
        cached = self._get(key)
        if cached is not None:
            return cached

        vec = self._base.embed_query(text)
        self._put(key, vec)
        return vec

    def stats(self) -> dict:
        with self._lock:
            total = self._hits + self._misses
            return {
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": round(self._hits / total, 4) if total else 0.0,
                "cached_embeddings": len(self._cache),
                "max_size": self.max_size,
            }

    

    def _get(self, key: str) -> List[float] | None:
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
                self._hits += 1
                logger.debug(f"[EmbedCache] HIT key={key[:8]}")
                return self._cache[key]
            self._misses += 1
            return None

    def _put(self, key: str, vector: List[float]) -> None:
        with self._lock:
            self._cache[key] = vector
            self._cache.move_to_end(key)
            while len(self._cache) > self.max_size:
                evicted, _ = self._cache.popitem(last=False)
                logger.debug(f"[EmbedCache] EVICTED key={evicted[:8]}")

    @staticmethod
    def _hash(text: str) -> str:
        return hashlib.sha256(text.strip().encode("utf-8")).hexdigest()
