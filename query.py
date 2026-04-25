"""
query.py — Interactive CLI
===========================
Test the full RAG pipeline from the command line.

Modes:
  1. Single query:   python query.py "How long does a refund take?"
  2. Interactive:    python query.py
  3. Retrieval only: python query.py --retrieval-only

Shows: answer + retrieved chunks + sources used.
"""

import sys
import argparse
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich import box
from rich.table import Table

from src.rag.vectorstore import load_vectorstore
from src.rag.retriever import ShopNestRetriever
from src.rag.context_assembler import assemble_context

console = Console()


# ── Retrieval-only mode (no LLM, no API key needed) ───────────────────────

def retrieval_only_query(retriever: ShopNestRetriever, question: str) -> None:
    docs = retriever.retrieve_with_scores(question)

    console.print(Panel(f"[bold]{question}[/bold]", title="Query", border_style="cyan"))

    table = Table("Rank", "Score", "Source", "Section", "Preview", box=box.SIMPLE)
    for i, (doc, score) in enumerate(docs, 1):
        meta = doc.metadata
        table.add_row(
            str(i),
            f"{score:.4f}",
            meta.get("source", "?"),
            meta.get("section", "?"),
            doc.page_content[:120].replace("\n", " ") + "…",
        )
    console.print(table)


# ── Full RAG mode ──────────────────────────────────────────────────────────

def full_rag_query(question: str) -> None:
    from src.rag.chain import RAGChain
    chain  = RAGChain()
    result = chain.ask(question)

    console.print(Panel(
        result["answer"],
        title="[bold green]ShopNest Agent Answer[/bold green]",
        border_style="green",
    ))
    console.print(f"[dim]Sources: {result['sources']}[/dim]")
    console.print(f"[dim]Chunks retrieved: {len(result['retrieved_chunks'])}[/dim]")


# ── Interactive loop ───────────────────────────────────────────────────────

def interactive_loop(retrieval_only: bool) -> None:
    console.print(Panel.fit(
        "[bold cyan]ShopNest AI Support — RAG Query CLI[/bold cyan]\n"
        "Type your question. [dim]'debug <query>'[/dim] shows raw chunks. "
        "[dim]'quit'[/dim] exits.",
        border_style="cyan",
    ))

    vs        = load_vectorstore()
    retriever = ShopNestRetriever(vectorstore=vs)

    while True:
        try:
            question = console.input("\n[bold yellow]You:[/bold yellow] ").strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Goodbye![/dim]")
            break

        if not question:
            continue
        if question.lower() in {"quit", "exit", "q"}:
            break

        if question.lower().startswith("debug "):
            retrieval_only_query(retriever, question[6:].strip())
        elif retrieval_only:
            retrieval_only_query(retriever, question)
        else:
            try:
                full_rag_query(question)
            except EnvironmentError as e:
                console.print(f"[red]{e}[/red]")
                console.print("[yellow]Switching to retrieval-only mode.[/yellow]")
                retrieval_only_query(retriever, question)


# ── Entry ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ShopNest RAG Query CLI")
    parser.add_argument("question", nargs="?", help="Single question to answer")
    parser.add_argument("--retrieval-only", action="store_true",
                        help="Skip LLM, show only retrieved chunks")
    args = parser.parse_args()

    if args.question:
        vs        = load_vectorstore()
        retriever = ShopNestRetriever(vectorstore=vs)
        if args.retrieval_only:
            retrieval_only_query(retriever, args.question)
        else:
            full_rag_query(args.question)
    else:
        interactive_loop(retrieval_only=args.retrieval_only)
