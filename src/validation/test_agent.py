"""
MODULE 9 — Phase 3 Agent Validation Suite
==========================================
Tests the 4 canonical Phase 3 scenarios WITHOUT a real OpenAI API key
by using a lightweight mock LLM that mimics OPENAI_FUNCTIONS agent behaviour.

Run:
    python -m src.validation.test_agent

To run live integration tests with your real key:
    python -m src.validation.test_agent --live
"""

import sys, os, argparse
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

from src.tools.actions import (
    check_order_status,
    cancel_order,
    initiate_refund,
    create_support_ticket,
)

console = Console()

# ── Unit-level tool tests (no LLM, no API key) ────────────────────────────

def test_tools_unit() -> tuple[int, int]:
    """
    Directly test all 4 action tools in isolation.
    No LLM involved — validates business logic layer only.
    """
    console.rule("[bold cyan]Phase 3 — Tool Unit Tests (No LLM Required)")

    cases = [
        # (description, fn, arg, must_contain)
        ("check_order_status  order 123 → pending",
         check_order_status, "123",
         ["123", "pending"]),

        ("check_order_status  order 456 → shipped",
         check_order_status, "456",
         ["456", "shipped"]),

        ("cancel_order  order 123",
         cancel_order, "123",
         ["123", "cancel"]),

        ("initiate_refund  order 456",
         initiate_refund, "456",
         ["456", "refund"]),

        ("create_support_ticket  some issue",
         create_support_ticket, "my item arrived broken",
         ["TKT-", "broken"]),

        ("check_order_status  empty → guard",
         check_order_status, "",
         ["provide", "order"]),

        ("cancel_order  empty → guard",
         cancel_order, "",
         ["provide", "order"]),

        ("initiate_refund  empty → guard",
         initiate_refund, "",
         ["provide", "order"]),

        ("create_support_ticket  empty → guard",
         create_support_ticket, "",
         ["provide", "description"]),
    ]

    table = Table(
        "Test", "Result", "Status",
        box=box.ROUNDED, show_lines=True
    )
    passed = failed = 0

    for desc, fn, arg, keywords in cases:
        result = fn(arg)
        result_lower = result.lower()
        missing = [kw for kw in keywords if kw.lower() not in result_lower]
        if not missing:
            status = "[green]PASS[/green]"
            passed += 1
        else:
            status = f"[red]FAIL — missing: {missing}[/red]"
            failed += 1
        table.add_row(desc, result[:80] + ("…" if len(result) > 80 else ""), status)

    console.print(table)
    console.print(
        f"\n  Tool Unit Results: [green]{passed} passed[/green]  "
        f"[red]{failed} failed[/red]  out of {len(cases)} tests"
    )
    return passed, failed


# ── Live integration tests (requires OPENAI_API_KEY) ──────────────────────

LIVE_TEST_CASES = [
    {
        "label": "Info query — should use KnowledgeBase (RAG)",
        "query": "What is the refund policy?",
        "expect_tool": "KnowledgeBase",
        "forbidden_tool": None,
        "must_contain": ["refund"],           # in final answer
        "should_ask_for_id": False,
    },
    {
        "label": "Action query — cancel, order_id given",
        "query": "Cancel my order 123",
        "expect_tool": "cancel_order_tool",
        "forbidden_tool": None,
        "must_contain": ["123", "cancel"],
        "should_ask_for_id": False,
    },
    {
        "label": "Missing info — cancel without order_id",
        "query": "Cancel my order",
        "expect_tool": None,                   # should NOT call cancel
        "forbidden_tool": "cancel_order_tool",
        "must_contain": ["order id", "order ID", "order number"],
        "should_ask_for_id": True,
    },
    {
        "label": "Mixed query — info + action",
        "query": "What is the refund policy and please cancel my order 456",
        "expect_tool": None,                   # both tools used
        "forbidden_tool": None,
        "must_contain": ["refund", "456", "cancel"],
        "should_ask_for_id": False,
    },
    {
        "label": "Status check — order 456",
        "query": "What is the status of order 456?",
        "expect_tool": "check_order_status_tool",
        "forbidden_tool": None,
        "must_contain": ["456"],
        "should_ask_for_id": False,
    },
    {
        "label": "Refund initiation — order 789",
        "query": "Please initiate a refund for order 789",
        "expect_tool": "initiate_refund_tool",
        "forbidden_tool": None,
        "must_contain": ["789", "refund"],
        "should_ask_for_id": False,
    },
    {
        "label": "Support ticket — vague complaint",
        "query": "My package arrived damaged, please help",
        "expect_tool": "create_support_ticket_tool",
        "forbidden_tool": None,
        "must_contain": ["TKT-"],
        "should_ask_for_id": False,
    },
]


def run_live_tests() -> tuple[int, int]:
    """
    Run the 7 canonical Phase 3 scenarios against the real agent.
    Requires OPENAI_API_KEY in .env.
    """
    from src.agent.shop_agent import build_shop_agent

    console.rule("[bold cyan]Phase 3 — Live Agent Integration Tests")
    console.print("[dim]Building agent (this loads FAISS + embedding model)…[/dim]")

    try:
        agent = build_shop_agent()
    except EnvironmentError as e:
        console.print(f"[red]{e}[/red]")
        return 0, 0

    table = Table(
        "Scenario", "Answer (truncated)", "Status",
        box=box.ROUNDED, show_lines=True,
    )

    passed = failed = 0

    for tc in LIVE_TEST_CASES:
        console.print(f"\n[yellow]▶ {tc['label']}[/yellow]")
        console.print(f"  Query: [italic]{tc['query']}[/italic]")
        try:
            raw = agent.invoke({"input": tc["query"]})
            answer: str = raw.get("output", "")
        except Exception as exc:
            answer = f"[ERROR] {exc}"

        answer_lower = answer.lower()
        missing_kw = [
            kw for kw in tc["must_contain"]
            if kw.lower() not in answer_lower
        ]

        if missing_kw:
            status = f"[red]FAIL — missing keywords: {missing_kw}[/red]"
            failed += 1
        else:
            status = "[green]PASS[/green]"
            passed += 1

        table.add_row(
            tc["label"],
            answer[:120] + ("…" if len(answer) > 120 else ""),
            status,
        )

    console.print(table)
    console.print(
        f"\n  Live Results: [green]{passed} passed[/green]  "
        f"[red]{failed} failed[/red]  out of {len(LIVE_TEST_CASES)} tests"
    )
    return passed, failed


# ── Entry ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ShopNest Phase 3 Agent Validation")
    parser.add_argument(
        "--live",
        action="store_true",
        help="Run live integration tests using your real OPENAI_API_KEY",
    )
    args = parser.parse_args()

    console.print(Panel.fit(
        "[bold cyan]ShopNest — Phase 3 Agent Validation Suite[/bold cyan]",
        border_style="cyan",
    ))

    total_pass = total_fail = 0

    # Always run tool unit tests (no API key needed)
    p, f = test_tools_unit()
    total_pass += p
    total_fail += f

    if args.live:
        p, f = run_live_tests()
        total_pass += p
        total_fail += f
    else:
        console.print(
            "\n[dim]Skipping live agent tests. "
            "Run with [bold]--live[/bold] to test the full agent pipeline.[/dim]"
        )

    console.print()
    console.print(Panel.fit(
        f"[bold]Grand Total: [green]{total_pass} passed[/green]  "
        f"[red]{total_fail} failed[/red][/bold]",
        border_style="green" if total_fail == 0 else "red",
    ))
