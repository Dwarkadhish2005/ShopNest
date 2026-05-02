"""
src/guardrails/context_guard.py — Context Guard (Layer 2)
==========================================================
Evaluates the quality of retrieved chunks BEFORE the LLM sees them.
If retrieval is weak (low scores, too few chunks) → forces a safe fallback
response instead of letting the LLM hallucinate.

Usage:
    guard = ContextGuard()
    result = guard.evaluate(docs_with_scores)
    if not result.is_sufficient:
        return result.fallback_message
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List, Optional, Tuple

from langchain_core.documents import Document

logger = logging.getLogger(__name__)

# ── Thresholds ────────────────────────────────────────────────────────────────
# FAISS returns L2 distance (lower = more similar).
# A distance > MAX_L2_DISTANCE means the chunk is too dissimilar.
_MAX_L2_DISTANCE: float = 1.5      # cosine-normalised embeddings → L2 ∈ [0, 2]
_MIN_CHUNKS_REQUIRED: int = 1      # at least 1 chunk must pass the threshold
_MIN_CONTENT_LENGTH: int = 20      # ignore empty / trivial chunks


@dataclass
class ContextGuardResult:
    is_sufficient: bool
    fallback_message: Optional[str] = None
    reason: Optional[str] = None
    passing_chunks: int = 0
    best_score: Optional[float] = None


class ContextGuard:
    """
    Layer-2 Safety Guard: detects weak retrieval and prevents hallucination
    by forcing a transparent fallback response.

    Works with FAISS similarity_search_with_score() which returns (doc, L2_distance).
    Lower L2 distance = better match (0.0 = identical).
    """

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
        """
        Evaluate retrieved docs quality.

        Args:
            docs_with_scores: List of (Document, L2_distance) from FAISS.
                              Lower distance = better match.

        Returns:
            ContextGuardResult — is_sufficient=False triggers fallback.
        """
        if not docs_with_scores:
            logger.warning("[ContextGuard] WEAK — no documents retrieved")
            return ContextGuardResult(
                is_sufficient=False,
                fallback_message=self.FALLBACK_MSG,
                reason="no_documents",
                passing_chunks=0,
            )

        # Filter chunks that pass score + content-length threshold
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
        """
        Convenience method when scores are not available.
        Checks only chunk count and content length.
        """
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
