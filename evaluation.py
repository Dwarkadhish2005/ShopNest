
import os
import sys
import json
import uuid
import warnings
from typing import List, Dict
from pathlib import Path


warnings.filterwarnings("ignore")


os.environ["ENABLE_PHOENIX"] = "true"
os.environ["PHOENIX_PROJECT_NAME"] = "shopnest-evaluation"


sys.path.insert(0, str(Path(__file__).resolve().parent))

try:
    from rich.console import Console
    from rich.table import Table
except ImportError:
    print("Please install rich: `pip install rich`")
    sys.exit(1)

from src.api.service import ShopNestService
from src.llm import get_llm
from src.observability.phoenix import init_phoenix

console = Console()


init_phoenix(
    enable_phoenix=True,
    project_name=os.environ["PHOENIX_PROJECT_NAME"],
    endpoint=os.environ.get("PHOENIX_COLLECTOR_ENDPOINT", "http://127.0.0.1:6006/v1/traces")
)


try:
    service = ShopNestService()
    eval_llm = get_llm()
except Exception as e:
    console.print(f"[red]Error initializing service/LLM. Is your .env configured?[/red]\n{e}")
    sys.exit(1)


TEST_QUERIES = [
    
    {"query": "What is the refund policy?", "expected": "Explain the general refund policy conditions."},
    {"query": "Can I return an item after 10 days?", "expected": "Clarify the number of days allowed for returns based on policy."},
    {"query": "How long does shipping take?", "expected": "Provide shipping timelines."},
    {"query": "Where are you located?", "expected": "Provide location details if in FAQ."},
    
    
    {"query": "Check the status of my order ORD-123", "expected": "Call check_order_status and return 'pending'."},
    {"query": "Cancel my order 123", "expected": "Call cancel_order and confirm cancellation."},
    {"query": "Initiate a refund for order 123", "expected": "Call initiate_refund and confirm."},
    {"query": "Create a support ticket for a broken screen", "expected": "Call create_support_ticket and return a ticket ID."},
    
    
    {"query": "What is the refund policy and also cancel order 123", "expected": "Provide refund policy info AND confirm cancellation of order 123."},
    {"query": "Cancel my order", "expected": "Ask the user to provide an order ID since it's missing."}
]

def evaluate_with_llm(query: str, expected: str, actual: str, tools_used: List[str]) -> dict:
    
    prompt = f"""
    You are an expert AI system evaluator.
    Evaluate the AI's response based on the following criteria:
    
    1. Query: "{query}"
    2. Expected Behavior/Answer: "{expected}"
    3. Actual Answer: "{actual}"
    4. Tools Invoked by AI: {tools_used}
    
    Rate the following from 1 to 5 (5 is best):
    - "accuracy": Does the actual answer correctly fulfill the expected behavior? (1-5)
    - "hallucination": Is the answer grounded natively? (5 = fully grounded, no hallucination. 1 = completely made up).
    - "retrieval_quality": Did the AI use the correct tools to get the answer? If policy/context was needed, did it call 'knowledge_base'? If an action was needed, did it call an action tool? (1-5)
    
    Respond EXACTLY with valid JSON only. Format:
    { 
        "accuracy": 5,
        "hallucination": 5,
        "retrieval_quality": 5,
        "reasoning": "brief explanation"
    } 
    """
    
    from langchain_core.messages import HumanMessage
    response = eval_llm.invoke([HumanMessage(content=prompt)])
    content = response.content.strip()
    
    
    if content.startswith("```json"):
        content = content[7:-3].strip()
    elif content.startswith("```"):
        content = content[3:-3].strip()
        
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return {
            "accuracy": 0, "hallucination": 0, "retrieval_quality": 0, 
            "reasoning": "Failed to parse JSON evaluation."
        }

def run_evaluation():
    console.print(f"\n[bold cyan]=== Starting ShopNest Evaluation Suite ({len(TEST_QUERIES)} Test Cases) ===[/bold cyan]")
    console.print("Traces will be sent to Phoenix project: 'shopnest-evaluation'\n")
    
    table = Table(title="Evaluation Results", show_header=True, header_style="bold magenta")
    table.add_column("ID", justify="center")
    table.add_column("Query", width=35)
    table.add_column("Acc", justify="center")
    table.add_column("Hall", justify="center")
    table.add_column("Retr", justify="center")
    table.add_column("Reasoning", width=40)
    
    total_acc, total_hall, total_retr = 0, 0, 0
    
    for i, test in enumerate(TEST_QUERIES, 1):
        session_id = f"eval-sess-{uuid.uuid4().hex[:8]}"
        query = test["query"]
        expected = test["expected"]
        
        console.print(f"[dim]Running {i}/{len(TEST_QUERIES)}:[/dim] {query}")
        
        
        try:
            result_payload = service.ask(session_id=session_id, message=query)
            actual_response = result_payload["response"]
            telemetry = result_payload.get("telemetry", {})
        except Exception as e:
            actual_response = f"Error during execution: {str(e)}"
            telemetry = {}
        
        
        tool_events = telemetry.get("tool_events", [])
        
        
        tools_used = []
        for t in tool_events:
            if hasattr(t, "name"):
                tools_used.append(t.name)
            elif isinstance(t, dict):
                tools_used.append(t.get("name", "unknown"))
                
        
        eval_result = evaluate_with_llm(query, expected, actual_response, tools_used)
        
        acc = eval_result.get("accuracy", 0)
        hall = eval_result.get("hallucination", 0)
        retr = eval_result.get("retrieval_quality", 0)
        reasoning = eval_result.get("reasoning", "No reason provided")
        
        total_acc += acc
        total_hall += hall
        total_retr += retr
        
        
        acc_str = f"[green]{acc}[/green]" if acc >= 4 else f"[{'yellow' if acc == 3 else 'red'}]{acc}[/]"
        hall_str = f"[green]{hall}[/green]" if hall >= 4 else f"[red]{hall}[/red]"
        retr_str = f"[green]{retr}[/green]" if retr >= 4 else f"[red]{retr}[/red]"
        
        table.add_row(str(i), query, acc_str, hall_str, retr_str, reasoning)
        
    console.print("\n")
    console.print(table)
    
    
    avg_acc = total_acc / len(TEST_QUERIES)
    avg_hall = total_hall / len(TEST_QUERIES)
    avg_retr = total_retr / len(TEST_QUERIES)
    
    console.print("\n[bold cyan]=== Evaluation Summary ===[/bold cyan]")
    console.print(f"Average Accuracy:          [bold]{avg_acc:.2f} / 5.00[/bold]")
    console.print(f"Avoidance of Hallucination:[bold]{avg_hall:.2f} / 5.00[/bold]")
    console.print(f"Average Retrieval Quality: [bold]{avg_retr:.2f} / 5.00[/bold]\n")
    
    console.print("[bold green]Evaluation complete![/bold green] Open your Phoenix UI to explore traces.")
    console.print("[dim]If Phoenix isn't running, start it with: 'python -m phoenix.server.main serve'[/dim]")

if __name__ == "__main__":
    run_evaluation()