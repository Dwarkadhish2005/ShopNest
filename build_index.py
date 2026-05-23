import os, sys
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule

from src.ingestion.chunker import chunk_all_documents
from src.rag.vectorstore import build_and_save_vectorstore

console = Console()


def main():
    console.print(Panel.fit(
        "[bold cyan]ShopNest - RAG Index Builder[/bold cyan]\n"
        "Modules 1 -> 2 -> 3 -> 4",
        border_style="cyan",
    ))

    
    console.print(Rule("[bold]Step 1 — Chunking + Metadata Tagging[/bold]"))
    docs = chunk_all_documents()

    if not docs:
        console.print("[red]No chunks produced. Check data/ directory.[/red]")
        sys.exit(1)

    
    console.print("\n[dim]Sample chunk metadata:[/dim]")
    for doc in docs[:3]:
        console.print(f"  {doc.metadata}")

    
    console.print(Rule("[bold]Step 2 — Embedding + FAISS Build[/bold]"))
    build_and_save_vectorstore(docs)

    console.print(Panel.fit(
        "[bold green]Index built successfully![/bold green]\n"
        "Run  [cyan]python query.py[/cyan]  to start querying.",
        border_style="green",
    ))


if __name__ == "__main__":
    main()
