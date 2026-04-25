"""
MODULE 5 — Retriever
=====================
Wraps the FAISS vector store and exposes a single retrieve() function.

k = 4 by default (configurable via TOP_K in config.py).
Returns the top-k most similar Document objects.
"""

import sys
from pathlib import Path
from typing import List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS

from src.config import TOP_K
from src.rag.vectorstore import load_vectorstore


class ShopNestRetriever:
    """Thin wrapper around FAISS for similarity retrieval."""

    def __init__(self, vectorstore: Optional[FAISS] = None, k: int = TOP_K):
        self._vs = vectorstore or load_vectorstore()
        self.k   = k

    def retrieve(self, query: str) -> List[Document]:
        """
        Embed the query and return the top-k most relevant chunks.
        Each Document carries its full metadata dict.
        """
        return self._vs.similarity_search(query, k=self.k)

    def retrieve_with_scores(self, query: str) -> List[tuple]:
        """Same as retrieve() but also returns similarity scores (for debugging)."""
        return self._vs.similarity_search_with_score(query, k=self.k)
