"""
MODULE 7 — LLM Response Generation (RAG Chain)
================================================
Strict prompt: LLM may ONLY answer from the provided context.
If the answer is not there → "I don't have information about that."

Returns a structured dict so callers can log everything (Phase 4 / Phoenix).
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from langchain.prompts import ChatPromptTemplate

from src.rag.context_assembler import assemble_context, get_sources_summary
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
    """End-to-end RAG chain: retriever → context → LLM → answer."""

    def __init__(self, retriever=None, llm=None):
        # Accept a pre-built LLM (from agent) or create one via the factory
        if llm is None:
            from src.llm import get_llm
            llm = get_llm()
        if retriever is None:
            from src.rag.retriever import ShopNestRetriever
            retriever = ShopNestRetriever()
        
        self.retriever = retriever
        self.llm = llm
        self.chain = _PROMPT | self.llm

    def ask(self, question: str) -> dict:
        """
        Run the full RAG pipeline for one question.

        Returns:
            {
                "question":        str,
                "answer":          str,
                "retrieved_chunks": List[Document],
                "context_used":    str,
                "sources":         str,
            }
        """
        # Module 5: retrieve
        docs = self.retriever.retrieve(question)

        # Module 6: assemble context
        context = assemble_context(docs)
        sources = get_sources_summary(docs)

        # Module 7: generate
        response = self.chain.invoke({
            "context":  context,
            "question": question,
        })

        return {
            "question":         question,
            "answer":           response.content,
            "retrieved_chunks": docs,
            "context_used":     context,
            "sources":          sources,
        }
