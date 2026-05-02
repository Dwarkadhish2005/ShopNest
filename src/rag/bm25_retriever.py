"""
src/rag/bm25_retriever.py — BM25 Keyword Retriever
====================================================
Complements FAISS semantic search with classic keyword matching (BM25).

Why BM25?
  - "order #456"        → BM25 finds exact keyword match (FAISS may miss it)
  - "refund policy"     → Semantic handles conceptual meaning
  - Together they cover both sides of retrieval

Implementation:
  - Uses rank_bm25 library (pure Python, no external service)
  - Loads documents from the FAISS index's in-memory docstore
  - Tokenizes with simple whitespace + lowercase (no NLTK dependency)

Usage:
    bm25 = BM25Retriever.from_vectorstore(vs)
    docs = bm25.retrieve("order 456 status", k=3)
"""

from __future__ import annotations

import logging
import re
import sys
from pathlib import Path
from typing import List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS

logger = logging.getLogger(__name__)


def _tokenize(text: str) -> List[str]:
    """Simple tokenizer: lowercase, split on non-alphanumeric chars."""
    return re.findall(r"[a-z0-9]+", text.lower())


class BM25Retriever:
    """
    BM25 keyword retriever built from a list of Documents.

    Parameters
    ----------
    docs : List[Document]
        Documents to index (should be the same set as in FAISS).
    """

    def __init__(self, docs: List[Document]) -> None:
        try:
            from rank_bm25 import BM25Okapi
        except ImportError:
            raise ImportError(
                "rank-bm25 is required for BM25 retrieval.\n"
                "Install it with: pip install rank-bm25"
            )

        self._docs = docs
        tokenized = [_tokenize(doc.page_content) for doc in docs]
        self._bm25 = BM25Okapi(tokenized)
        logger.info(f"[BM25] Indexed {len(docs)} documents")

    # ── Public API ────────────────────────────────────────────────────────────

    def retrieve(self, query: str, k: int = 3) -> List[Document]:
        """
        Retrieve top-k documents by BM25 score.

        Returns an empty list if there are no documents or if BM25 scores
        are all zero (query tokens not found anywhere).
        """
        if not self._docs:
            return []

        tokens = _tokenize(query)
        if not tokens:
            return []

        scores = self._bm25.get_scores(tokens)
        # Pair with docs, sort descending by score, take top-k
        ranked = sorted(
            zip(scores, self._docs), key=lambda x: x[0], reverse=True
        )
        top = [(score, doc) for score, doc in ranked[:k] if score > 0.0]

        if not top:
            logger.debug(f"[BM25] No matching docs for query: '{query[:60]}'")
            return []

        logger.debug(
            f"[BM25] Top scores: {[round(s, 3) for s, _ in top]} | "
            f"query='{query[:60]}'"
        )
        return [doc for _, doc in top]

    def retrieve_with_scores(self, query: str, k: int = 3) -> List[tuple]:
        """Return (Document, bm25_score) pairs for the top-k results."""
        if not self._docs:
            return []

        tokens = _tokenize(query)
        if not tokens:
            return []

        scores = self._bm25.get_scores(tokens)
        ranked = sorted(
            zip(scores, self._docs), key=lambda x: x[0], reverse=True
        )
        return [(doc, score) for score, doc in ranked[:k] if score > 0.0]

    # ── Factory ───────────────────────────────────────────────────────────────

    @classmethod
    def from_vectorstore(cls, vectorstore: FAISS) -> "BM25Retriever":
        """
        Build a BM25Retriever from an existing FAISS vectorstore's docstore.
        Extracts all stored documents without re-embedding them.
        """
        docs: List[Document] = []
        try:
            # FAISS docstore uses an internal dict: {doc_id: Document}
            doc_store = vectorstore.docstore._dict
            for doc_id, doc in doc_store.items():
                docs.append(doc)
        except AttributeError:
            logger.warning("[BM25] Could not access FAISS docstore — BM25 will be empty")

        logger.info(f"[BM25] Loaded {len(docs)} docs from FAISS docstore")
        return cls(docs)
