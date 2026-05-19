"""
src/rag/chain.py — LLM Response Generation (RAG Chain)
========================================================
Phase 5 upgrade: Full advanced retrieval pipeline:

    query
      → InputGuard (reject off-domain)
      → MultiQueryRetriever (1 query → N variations)
      → HybridRetriever (FAISS semantic + BM25 keyword, parallel)
      → Reranker (cross-encoder re-scoring, optional)
      → ContextGuard (reject weak retrieval → fallback)
      → LLM (strict RAG prompt)

Falls back gracefully at each stage if components are unavailable.
Strict prompt: LLM may ONLY answer from provided context.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import logging
from typing import Optional

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.language_models import BaseLanguageModel

from src.rag.context_assembler import assemble_context, get_sources_summary
from src.guardrails.context_guard import ContextGuard
from src.config import TOP_K

logger = logging.getLogger(__name__)

# ── Strict RAG Prompt ──────────────────────────────────────────────────────

_SYSTEM_PROMPT = """You are a helpful and professional customer support agent for ShopNest, an e-commerce platform.

STRICT RULES:
1. Answer ONLY using the context below. Do NOT use outside knowledge.
2. If the answer is NOT in the context, respond exactly:
   "I don't have information about that in our current policies. Please contact support@shopnest.com for help."
3. Be concise, clear, and friendly.
4. Never make up order status, timelines, or policies.

CONTEXT:
{context}
"""

_HUMAN_PROMPT = "Customer question: {question}"

_PROMPT = ChatPromptTemplate.from_messages([
    ("system", _SYSTEM_PROMPT),
    ("human",  _HUMAN_PROMPT),
])


# ── RAG Chain ──────────────────────────────────────────────────────────────

class RAGChain:
    """
    End-to-end RAG chain with Phase 5 advanced retrieval pipeline.

    Pipeline stages:
      1. MultiQueryRetriever  — expands 1 query to N variations
      2. HybridRetriever      — FAISS semantic + BM25 keyword (parallel)
      3. Reranker             — cross-encoder re-scoring (if enabled)
      4. ContextGuard         — rejects weak retrieval before LLM
      5. LLM                  — strict context-only generation
    """

    def __init__(self, retriever=None, llm: Optional[BaseLanguageModel] = None):
        # Accept a pre-built LLM (from agent) or create one via the factory
        if llm is None:
            from src.llm import get_llm
            llm = get_llm()

        self.llm = llm
        self.chain = _PROMPT | self.llm
        self.context_guard = ContextGuard()

        # ── Build advanced retrieval pipeline ─────────────────────────────
        self._retriever = self._build_retriever(retriever, llm)

    def _build_retriever(self, base_retriever, llm):
        """
        Attempt to build the full hybrid + multi-query retriever pipeline.
        Falls back to base_retriever → ShopNestRetriever on any failure.
        """
        try:
            from src.rag.vectorstore import load_vectorstore
            from src.rag.hybrid_retriever import HybridRetriever
            from src.rag.multi_query import MultiQueryRetriever
            from src.rag.reranker import Reranker

            vs = load_vectorstore()
            hybrid = HybridRetriever(vectorstore=vs)
            reranker = Reranker()

            # Wrap hybrid with reranker in a thin adapter
            class RerankedHybrid:
                def __init__(self, hybrid, reranker, top_k):
                    self._hybrid = hybrid
                    self._reranker = reranker
                    self._top_k = top_k

                def retrieve(self, query: str, k: int = None) -> list:
                    k = k or self._top_k
                    docs = self._hybrid.retrieve(query, k=k * 2)  # fetch 2× for reranker
                    return self._reranker.rerank(query, docs, top_k=k)

                def retrieve_with_scores(self, query: str, k: int = None) -> list:
                    k = k or self._top_k
                    docs_with_scores = self._hybrid.retrieve_with_scores(query, k=k * 2)
                    docs = [d for d, _ in docs_with_scores]
                    reranked = self._reranker.rerank(query, docs, top_k=k)
                    return [(doc, 0.0) for doc in reranked]  # scores not meaningful post-rerank

            reranked_hybrid = RerankedHybrid(hybrid, reranker, TOP_K)

            # Wrap with multi-query for best recall
            multi_query = MultiQueryRetriever(
                retriever=reranked_hybrid,
                llm=llm,
            )
            logger.info("[RAGChain] ✓ Full pipeline: MultiQuery → Hybrid(FAISS+BM25) → Reranker")
            return multi_query

        except Exception as e:
            logger.warning(
                f"[RAGChain] Advanced pipeline failed ({e}), "
                "falling back to base ShopNestRetriever"
            )
            if base_retriever is not None:
                return base_retriever
            from src.rag.retriever import ShopNestRetriever
            return ShopNestRetriever()

    def ask(self, question: str) -> dict:
        """
        Run the full RAG pipeline for one question.

        Returns:
            {
                "question":          str,
                "answer":            str,
                "retrieved_chunks":  List[Document],
                "context_used":      str,
                "sources":           str,
                "context_sufficient": bool,
                "pipeline":          str,
            }
        """
        # ── Stage 1: Retrieve (multi-query + hybrid + rerank) ──────────────
        try:
            docs = self._retriever.retrieve(question, k=TOP_K)
        except TypeError:
            # Some retrievers don't accept k kwarg
            docs = self._retriever.retrieve(question)

        # ── Stage 2: Context Guard ─────────────────────────────────────────
        guard_result = self.context_guard.evaluate_docs(docs)

        if not guard_result.is_sufficient:
            logger.warning(
                f"[RAGChain] ContextGuard triggered: {guard_result.reason} | "
                f"query='{question[:60]}'"
            )
            return {
                "question":           question,
                "answer":             guard_result.fallback_message,
                "retrieved_chunks":   docs,
                "context_used":       "",
                "sources":            "",
                "context_sufficient": False,
                "pipeline":           "context_guard_fallback",
            }

        # ── Stage 3: Assemble context ──────────────────────────────────────
        context = assemble_context(docs)
        sources = get_sources_summary(docs)

        # ── Stage 4: LLM generation ────────────────────────────────────────
        response = self.chain.invoke({
            "context":  context,
            "question": question,
        })

        return {
            "question":           question,
            "answer":             response.content,
            "retrieved_chunks":   docs,
            "context_used":       context,
            "sources":            sources,
            "context_sufficient": True,
            "pipeline":           "hybrid_multiquery_reranker",
        }
