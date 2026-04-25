"""
agent_query.py — Interactive CLI for ShopNest Decision Agent
===========================
Test the full Agent pipeline from the command line (Phase 3).

Modes:
  1. Single query:   python agent_query.py "Cancel order 123"
  2. Interactive:    python agent_query.py
"""

import sys
import argparse
from pathlib import Path

# Add project root to sys path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from rich.console import Console
from rich.panel import Panel

from src.agent.shop_agent import build_shop_agent

console = Console()

def agent_query(agent, question: str) -> None:
    try:
        response = agent.invoke({"input": question})["output"]
        console.print(Panel(
            response,
            title="[bold green]ShopNest Agent Answer[/bold green]",
            border_style="green",
        ))
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")

def interactive_loop() -> None:
    console.print(Panel.fit(
        "[bold cyan]ShopNest Decision Agent CLI[/bold cyan]\n"
        "Type your question (informational, action, mixed).\n"
        "[dim]'quit'[/dim] exits.",
        border_style="cyan",
    ))

    try:
        agent = build_shop_agent()
    except EnvironmentError as e:
        console.print(f"[red]{e}[/red]")
        sys.exit(1)

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

        agent_query(agent, question)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ShopNest Agent CLI")
    parser.add_argument("question", nargs="?", help="Single question to answer")
    args = parser.parse_args()

    if args.question:
        agent = build_shop_agent()
        agent_query(agent, args.question)
    else:
        interactive_loop()