"""
src/rag/reranker.py — Cross-Encoder Re-Ranker
==============================================
Re-scores retrieved chunks using a cross-encoder model, producing more
accurate relevance rankings than bi-encoder (FAISS) alone.

Why re-ranking?
  - FAISS/BM25 retrieve by approximate similarity
  - Cross-encoder reads query + chunk together → much more accurate scoring
  - Better ranking → LLM sees the most relevant chunk first → fewer hallucinations

Model: cross-encoder/ms-marco-MiniLM-L-6-v2
  - Free, local (~70MB, downloads once from HuggingFace)
  - State-of-the-art for passage re-ranking
  - Controlled by ENABLE_RERANKER in .env

Falls back gracefully if:
  - Model not available
  - sentence-transformers not installed
  - ENABLE_RERANKER=false

Usage:
    reranker = Reranker()
    reranked_docs = reranker.rerank(query="refund policy", docs=docs, top_k=3)
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from langchain_core.documents import Document
from src.config import ENABLE_RERANKER, RERANKER_MODEL

logger = logging.getLogger(__name__)


class Reranker:
    """
    Cross-encoder re-ranker for retrieved document chunks.

    If ENABLE_RERANKER=false or the model is unavailable, all methods
    return the original list unchanged (zero-cost passthrough).
    """

    def __init__(self) -> None:
        self._model = None
        self._enabled = ENABLE_RERANKER

        if not self._enabled:
            logger.info("[Reranker] Disabled via ENABLE_RERANKER=false — passthrough mode")
            return

        self._load_model()

    def _load_model(self) -> None:
        """Load cross-encoder model. Logs a warning if unavailable."""
        try:
            from sentence_transformers import CrossEncoder
            self._model = CrossEncoder(RERANKER_MODEL)
            logger.info(f"[Reranker] Loaded model: {RERANKER_MODEL}")
        except ImportError:
            logger.warning("[Reranker] sentence-transformers not installed — falling back to passthrough")
            self._model = None
        except Exception as e:
            logger.warning(f"[Reranker] Failed to load model '{RERANKER_MODEL}': {e} — passthrough mode")
            self._model = None

    def rerank(
        self,
        query: str,
        docs: List[Document],
        top_k: Optional[int] = None,
    ) -> List[Document]:
        """
        Re-score and re-rank documents using the cross-encoder model.

        Args:
            query: The original user query.
            docs: Candidate documents from hybrid retrieval.
            top_k: How many top documents to return. If None, returns all.

        Returns:
            Documents sorted by cross-encoder relevance score (best first).
            If model unavailable, returns docs unchanged.
        """
        if not docs:
            return docs

        if self._model is None:
            # Passthrough — no re-ranking
            return docs[:top_k] if top_k else docs

        try:
            # Build (query, passage) pairs for cross-encoder
            pairs = [(query, doc.page_content) for doc in docs]
            scores = self._model.predict(pairs)

            # Sort docs by score descending
            ranked = sorted(
                zip(scores, docs), key=lambda x: x[0], reverse=True
            )
            result = [doc for _, doc in ranked]

            if top_k:
                result = result[:top_k]

            logger.debug(
                f"[Reranker] Re-ranked {len(docs)} docs → top-{len(result)} | "
                f"query='{query[:60]}' | "
                f"top_score={max(scores):.4f}"
            )
            return result

        except Exception as e:
            logger.warning(f"[Reranker] Re-ranking failed: {e} — returning original order")
            return docs[:top_k] if top_k else docs

    def rerank_with_scores(
        self,
        query: str,
        docs: List[Document],
        top_k: Optional[int] = None,
    ) -> List[tuple]:
        """
        Re-rank and return (Document, score) pairs.
        Score = cross-encoder logit (higher = more relevant).
        """
        if not docs:
            return []

        if self._model is None:
            return [(doc, 0.0) for doc in (docs[:top_k] if top_k else docs)]

        try:
            pairs = [(query, doc.page_content) for doc in docs]
            scores = self._model.predict(pairs)
            ranked = sorted(
                zip(scores, docs), key=lambda x: x[0], reverse=True
            )
            result = [(doc, float(score)) for score, doc in ranked]
            return result[:top_k] if top_k else result
        except Exception as e:
            logger.warning(f"[Reranker] Score re-ranking failed: {e}")
            return [(doc, 0.0) for doc in (docs[:top_k] if top_k else docs)]
