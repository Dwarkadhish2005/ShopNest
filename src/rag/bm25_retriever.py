
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
    return re.findall(r"[a-z0-9]+", text.lower())


class BM25Retriever:

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

    

    def retrieve(self, query: str, k: int = 3) -> List[Document]:
        if not self._docs:
            return []

        tokens = _tokenize(query)
        if not tokens:
            return []

        scores = self._bm25.get_scores(tokens)
        
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

    

    @classmethod
    def from_vectorstore(cls, vectorstore: FAISS) -> "BM25Retriever":
        docs: List[Document] = []
        try:
            
            doc_store = vectorstore.docstore._dict
            for doc_id, doc in doc_store.items():
                docs.append(doc)
        except AttributeError:
            logger.warning("[BM25] Could not access FAISS docstore — BM25 will be empty")

        logger.info(f"[BM25] Loaded {len(docs)} docs from FAISS docstore")
        return cls(docs)
