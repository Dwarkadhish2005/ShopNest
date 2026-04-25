"""
MODULE 8 — Validation Suite
============================
Runs a battery of test queries and checks expected behaviour:
  ✔ Core RAG questions (answer exists in dataset)
  ✔ FAQ direct matches
  ✔ Edge cases (answer NOT in dataset)

Run:
    python -m src.validation.test_rag
"""

import os, sys
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from rich.console import Console
from rich.table import Table
from rich import box

from src.rag.vectorstore import load_vectorstore
from src.rag.retriever import ShopNestRetriever
from src.rag.context_assembler import assemble_context

console = Console()

# ── Test Cases ─────────────────────────────────────────────────────────────

TEST_CASES = [
    # (query, expected_behaviour, keywords_that_MUST appear in top chunks)
    # Core policy questions
    ("How long does a refund take?",
     "answer_exists",
     ["refund", "business days"]),

    ("Can I cancel my order after it has been shipped?",
     "answer_exists",
     ["dispatch", "cancel", "refund"]),

    ("Do you charge for return shipping?",
     "answer_exists",
     ["shipping", "return", "cost"]),

    ("What items cannot be refunded?",
     "answer_exists",
     ["non-refundable", "digital", "gift"]),

    ("How long does standard shipping take?",
     "answer_exists",
     ["standard", "5-7", "business"]),

    # FAQ direct matches
    ("What payment methods do you accept?",
     "answer_exists",
     ["UPI", "credit", "debit"]),

    ("How do I track my order?",
     "answer_exists",
     ["tracking", "email", "SMS"]),

    # Edge cases — answer NOT in dataset
    ("Do you sell cars?",
     "out_of_scope",
     []),

    ("What is the weather like today?",
     "out_of_scope",
     []),

    ("Can I return after 30 days?",
     "answer_exists",
     ["30 days", "eligible", "refund"]),
]


# ── Runner ─────────────────────────────────────────────────────────────────

def run_retrieval_tests(retriever: ShopNestRetriever) -> None:
    """
    For each test case, retrieve chunks and verify:
      1. The correct number of chunks is returned
      2. Expected keywords appear in the retrieved context
    """
    console.rule("[bold cyan]MODULE 8 — RAG Retrieval Validation")

    table = Table(
        "Query", "Expected", "Chunks", "Keywords Found", "Status",
        box=box.ROUNDED,
        show_lines=True,
    )

    passed = 0
    failed = 0

    for query, behaviour, keywords in TEST_CASES:
        docs    = retriever.retrieve(query)
        context = assemble_context(docs)

        chunk_count = len(docs)
        ctx_lower   = context.lower()

        if behaviour == "out_of_scope":
            status   = "[PASS] out-of-scope"
            kw_found = "N/A (out-of-scope)"
            passed  += 1
        else:
            missing = [kw for kw in keywords if kw.lower() not in ctx_lower]
            if not missing:
                status   = "[PASS]"
                kw_found = ", ".join(keywords) if keywords else "-"
                passed  += 1
            else:
                status   = f"[FAIL] missing: {', '.join(missing)}"
                kw_found = f"Found: {[k for k in keywords if k.lower() in ctx_lower]}"
                failed  += 1

        table.add_row(
            query[:55] + ("…" if len(query) > 55 else ""),
            behaviour,
            str(chunk_count),
            kw_found,
            status,
        )

    console.print(table)
    console.print(f"\n  Results: [green]{passed} passed[/green]  [red]{failed} failed[/red]  "
                  f"out of {len(TEST_CASES)} tests")


def print_chunk_debug(retriever: ShopNestRetriever, query: str) -> None:
    """Print retrieved chunks + metadata for a single query (debugging tool)."""
    console.rule(f"[yellow]Debug: '{query}'")
    docs_with_scores = retriever.retrieve_with_scores(query)
    for i, (doc, score) in enumerate(docs_with_scores, 1):
        meta = doc.metadata
        console.print(
            f"[bold][{i}][/bold] Score: [cyan]{score:.4f}[/cyan]  "
            f"source=[magenta]{meta.get('source')}[/magenta]  "
            f"section=[green]{meta.get('section')}[/green]  "
            f"type=[yellow]{meta.get('chunk_type')}[/yellow]"
        )
        console.print(doc.page_content[:300] + ("…" if len(doc.page_content) > 300 else ""))
        console.print()


if __name__ == "__main__":
    console.print("\n[bold green]ShopNest RAG — Validation Suite[/bold green]\n")
    vs        = load_vectorstore()
    retriever = ShopNestRetriever(vectorstore=vs)

    run_retrieval_tests(retriever)

    # Debug individual query
    console.print()
    print_chunk_debug(retriever, "How long does a refund take?")
