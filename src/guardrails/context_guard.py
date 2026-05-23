
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List, Optional, Tuple

from langchain_core.documents import Document

logger = logging.getLogger(__name__)




_MAX_L2_DISTANCE: float = 1.5      
_MIN_CHUNKS_REQUIRED: int = 1      
_MIN_CONTENT_LENGTH: int = 20      


@dataclass
class ContextGuardResult:
    is_sufficient: bool
    fallback_message: Optional[str] = None
    reason: Optional[str] = None
    passing_chunks: int = 0
    best_score: Optional[float] = None


class ContextGuard:

    FALLBACK_MSG = (
        "I don't have enough information in our knowledge base to answer that "
        "confidently. Please contact our support team at support@shopnest.com "
        "or call our helpline for accurate assistance."
    )

    def __init__(
        self,
        max_distance: float = _MAX_L2_DISTANCE,
        min_chunks: int = _MIN_CHUNKS_REQUIRED,
    ):
        self.max_distance = max_distance
        self.min_chunks = min_chunks

    def evaluate(
        self,
        docs_with_scores: List[Tuple[Document, float]],
    ) -> ContextGuardResult:
        if not docs_with_scores:
            logger.warning("[ContextGuard] WEAK — no documents retrieved")
            return ContextGuardResult(
                is_sufficient=False,
                fallback_message=self.FALLBACK_MSG,
                reason="no_documents",
                passing_chunks=0,
            )

        
        passing = [
            (doc, score)
            for doc, score in docs_with_scores
            if score <= self.max_distance
            and len(doc.page_content.strip()) >= _MIN_CONTENT_LENGTH
        ]

        best_score = min(score for _, score in docs_with_scores)

        if len(passing) < self.min_chunks:
            logger.warning(
                f"[ContextGuard] WEAK — only {len(passing)}/{len(docs_with_scores)} "
                f"chunks passed threshold (best L2={best_score:.4f}, max={self.max_distance})"
            )
            return ContextGuardResult(
                is_sufficient=False,
                fallback_message=self.FALLBACK_MSG,
                reason=f"weak_retrieval:{len(passing)}_chunks_passed",
                passing_chunks=len(passing),
                best_score=best_score,
            )

        logger.debug(
            f"[ContextGuard] SUFFICIENT — {len(passing)} chunks passed "
            f"(best L2={best_score:.4f})"
        )
        return ContextGuardResult(
            is_sufficient=True,
            passing_chunks=len(passing),
            best_score=best_score,
        )

    def evaluate_docs(self, docs: List[Document]) -> ContextGuardResult:
        if not docs:
            return ContextGuardResult(
                is_sufficient=False,
                fallback_message=self.FALLBACK_MSG,
                reason="no_documents",
                passing_chunks=0,
            )

        passing = [
            doc for doc in docs
            if len(doc.page_content.strip()) >= _MIN_CONTENT_LENGTH
        ]

        if len(passing) < self.min_chunks:
            return ContextGuardResult(
                is_sufficient=False,
                fallback_message=self.FALLBACK_MSG,
                reason=f"insufficient_content:{len(passing)}_chunks",
                passing_chunks=len(passing),
            )

        return ContextGuardResult(is_sufficient=True, passing_chunks=len(passing))
