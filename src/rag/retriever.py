"""
MODULE 5 — Retriever
=====================
Wraps the FAISS vector store and exposes retrieve() functionality.

Supports dynamic TOP_K based on query length.
Returns the top-k most similar Document objects or tuples with scores.
"""

import sys
from pathlib import Path
from typing import List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS

from src.config import TOP_K, TOP_K_MIN, TOP_K_MAX
from src.rag.vectorstore import load_vectorstore


class ShopNestRetriever:
    def __init__(self, vectorstore: Optional[FAISS] = None, k: Optional[int] = None):
        self._vs = vectorstore or load_vectorstore()
        self.k = k

    def _get_dynamic_k(self, query: str) -> int:
        """Calculate dynamic k based on query length if static k is not provided."""
        if self.k is not None:
            return self.k
            
        word_count = len(query.split())
        if word_count < 5:
            return TOP_K_MIN
        elif word_count > 15:
            return TOP_K_MAX
        return TOP_K

    def retrieve(self, query: str) -> List[Document]:
        """Retrieve top documents matching the query."""
        k = self._get_dynamic_k(query)
        return self._vs.similarity_search(query, k=k)

    def retrieve_with_scores(self, query: str) -> List[Tuple[Document, float]]:
        """Retrieve top documents with their similarity scores."""
        k = self._get_dynamic_k(query)
        return self._vs.similarity_search_with_score(query, k=k)
