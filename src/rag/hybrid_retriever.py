"""
src/rag/hybrid_retriever.py — Hybrid Retriever (FAISS + BM25)
==============================================================
Merges semantic search (FAISS) and keyword search (BM25) using
Reciprocal Rank Fusion (RRF).

Why Hybrid?
  - Semantic alone: misses exact keyword matches
  - BM25 alone: misses conceptual/synonym matches
  - Together with RRF: the best of both worlds

Reciprocal Rank Fusion formula:
    RRF_score(doc) = Σ  1 / (k + rank_in_list_i)
  where k=60 is a smoothing constant (standard value from literature).

Both retrievers run in parallel via ThreadPoolExecutor for speed.

Usage:
    hybrid = HybridRetriever(vectorstore=vs)
    docs = hybrid.retrieve("refund policy for damaged items", k=5)
"""

from __future__ import annotations

import logging
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS

from src.rag.bm25_retriever import BM25Retriever
from src.config import TOP_K

logger = logging.getLogger(__name__)

# RRF smoothing constant — standard value from the original paper
_RRF_K = 60


def _rrf_score(rank: int, k: int = _RRF_K) -> float:
    """Reciprocal Rank Fusion score for a document at position `rank` (0-indexed)."""
    return 1.0 / (k + rank + 1)


class HybridRetriever:
    """
    Hybrid retriever combining FAISS (semantic) + BM25 (keyword) with
    Reciprocal Rank Fusion merging.

    Parameters
    ----------
    vectorstore : FAISS
        Loaded FAISS vectorstore.
    bm25 : Optional[BM25Retriever]
        Pre-built BM25 retriever. If None, builds one from vectorstore.
    semantic_weight : float
        Weight for semantic scores in RRF (default 1.0).
    keyword_weight : float
        Weight for BM25 scores in RRF (default 1.0).
    """

    def __init__(
        self,
        vectorstore: FAISS,
        bm25: Optional[BM25Retriever] = None,
        semantic_weight: float = 1.0,
        keyword_weight: float = 1.0,
    ) -> None:
        self._vs = vectorstore
        self._bm25 = bm25 or BM25Retriever.from_vectorstore(vectorstore)
        self.semantic_weight = semantic_weight
        self.keyword_weight = keyword_weight

    def retrieve(self, query: str, k: int = TOP_K) -> List[Document]:
        """
        Run hybrid retrieval and return the top-k fused documents.

        Runs FAISS and BM25 in parallel, then merges via RRF.
        """
        # Fetch more candidates before merging (2× to ensure diversity)
        fetch_k = max(k * 2, 6)

        semantic_docs: List[Document] = []
        keyword_docs: List[Document] = []

        # ── Parallel retrieval ────────────────────────────────────────────────
        with ThreadPoolExecutor(max_workers=2) as executor:
            future_semantic = executor.submit(
                self._vs.similarity_search, query, k=fetch_k
            )
            future_keyword = executor.submit(
                self._bm25.retrieve, query, k=fetch_k
            )
            for future in as_completed([future_semantic, future_keyword]):
                try:
                    if future is future_semantic:
                        semantic_docs = future.result()
                    else:
                        keyword_docs = future.result()
                except Exception as e:
                    logger.warning(f"[HybridRetriever] Retrieval error: {e}")

        logger.debug(
            f"[HybridRetriever] semantic={len(semantic_docs)}, "
            f"keyword={len(keyword_docs)} | query='{query[:60]}'"
        )

        # ── RRF Fusion ────────────────────────────────────────────────────────
        fused = self._rrf_merge(semantic_docs, keyword_docs)
        result = fused[:k]

        logger.debug(f"[HybridRetriever] Returning {len(result)} fused docs")
        return result

    def retrieve_with_scores(self, query: str, k: int = TOP_K) -> List[tuple]:
        """
        Run hybrid retrieval and return (Document, rrf_score) pairs.
        Higher RRF score = better match.
        """
        fetch_k = max(k * 2, 6)

        semantic_docs: List[Document] = []
        keyword_docs: List[Document] = []

        with ThreadPoolExecutor(max_workers=2) as executor:
            future_semantic = executor.submit(
                self._vs.similarity_search, query, k=fetch_k
            )
            future_keyword = executor.submit(
                self._bm25.retrieve, query, k=fetch_k
            )
            for future in as_completed([future_semantic, future_keyword]):
                try:
                    if future is future_semantic:
                        semantic_docs = future.result()
                    else:
                        keyword_docs = future.result()
                except Exception as e:
                    logger.warning(f"[HybridRetriever] Score retrieval error: {e}")

        scored = self._rrf_merge_scored(semantic_docs, keyword_docs)
        return scored[:k]

    # ── Internal: RRF Merging ─────────────────────────────────────────────────

    def _doc_key(self, doc: Document) -> str:
        """Unique key for a document — uses content hash for deduplication."""
        return doc.page_content[:200]  # first 200 chars as proxy

    def _rrf_merge(
        self,
        semantic_docs: List[Document],
        keyword_docs: List[Document],
    ) -> List[Document]:
        """Merge two ranked lists via RRF, return deduplicated sorted docs."""
        scores: Dict[str, float] = {}
        doc_map: Dict[str, Document] = {}

        for rank, doc in enumerate(semantic_docs):
            key = self._doc_key(doc)
            scores[key] = scores.get(key, 0.0) + self.semantic_weight * _rrf_score(rank)
            doc_map[key] = doc

        for rank, doc in enumerate(keyword_docs):
            key = self._doc_key(doc)
            scores[key] = scores.get(key, 0.0) + self.keyword_weight * _rrf_score(rank)
            doc_map[key] = doc

        ranked_keys = sorted(scores.keys(), key=lambda k: scores[k], reverse=True)
        return [doc_map[k] for k in ranked_keys]

    def _rrf_merge_scored(
        self,
        semantic_docs: List[Document],
        keyword_docs: List[Document],
    ) -> List[tuple]:
        """Same as _rrf_merge but returns (Document, rrf_score) tuples."""
        scores: Dict[str, float] = {}
        doc_map: Dict[str, Document] = {}

        for rank, doc in enumerate(semantic_docs):
            key = self._doc_key(doc)
            scores[key] = scores.get(key, 0.0) + self.semantic_weight * _rrf_score(rank)
            doc_map[key] = doc

        for rank, doc in enumerate(keyword_docs):
            key = self._doc_key(doc)
            scores[key] = scores.get(key, 0.0) + self.keyword_weight * _rrf_score(rank)
            doc_map[key] = doc

        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return [(doc_map[k], score) for k, score in ranked]
