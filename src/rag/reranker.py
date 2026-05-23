
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

    def __init__(self) -> None:
        self._model = None
        self._enabled = ENABLE_RERANKER

        if not self._enabled:
            logger.info("[Reranker] Disabled via ENABLE_RERANKER=false — passthrough mode")
            return

        self._load_model()

    def _load_model(self) -> None:
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
        if not docs:
            return docs

        if self._model is None:
            
            return docs[:top_k] if top_k else docs

        try:
            
            pairs = [(query, doc.page_content) for doc in docs]
            scores = self._model.predict(pairs)

            
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
