"""
src/agent/shop_agent.py — ShopNest Decision Agent
===================================================
Uses the modern LangChain create_tool_calling_agent pattern.
Provider is controlled by LLM_PROVIDER in .env:

  LLM_PROVIDER=groq    → uses ChatGroq (FREE ✅)
  LLM_PROVIDER=openai  → uses ChatOpenAI (paid)

Default: groq
"""
import sys
import concurrent.futures
from pathlib import Path
sys.path.insert(0 , str(Path(__file__).resolve().parent.parent.parent))
from langchain_classic.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from src.llm import get_llm
from src.tools.actions import check_order_status , cancel_order , initiate_refund , create_support_ticket
from src.rag.chain import RAGChain
from src.guardrails.input_guard import InputGuard
from src.guardrails.tool_guard import ToolGuard

def build_shop_agent() -> AgentExecutor:
    llm = get_llm()
    rag_chain = RAGChain(llm=llm)
    tool_guard = ToolGuard()

    # ── Tool 1: RAG Knowledge Base ─────────────────────────────────────────
    @tool
    def knowledge_base(query: str) ->str:
        """Answer policy and FAQ questions using the ShopNest knowledge base."""
        # Use ThreadPoolExecutor to run the blocking ask() call for concurrency, if preferred
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(rag_chain.ask, query)
            result = future.result()
        return result["answer"]

    # ── Tool 2: Check Order Status ─────────────────────────────────────────    
    @tool
    def check_order_status_tool(order_id: str) -> str:
        """Check current status for a given order_id."""
        res = tool_guard.validate_order_id(order_id)
        if not res.valid:
            return res.reason
        return check_order_status(res.sanitized_value)

    # ── Tool 3: Cancel Order ───────────────────────────────────────────────
    @tool
    def cancel_order_tool(order_id: str) -> str:
        """Cancel an order by order_id."""
        res = tool_guard.validate_destructive_action("cancel_order", order_id)
        if not res.valid:
            return res.reason
        return cancel_order(res.sanitized_value)

    # ── Tool 4: Initiate Refund ────────────────────────────────────────────    
    @tool
    def initiate_refund_tool(order_id: str) -> str:
        """Initiate a refund for the given order_id."""
        res = tool_guard.validate_destructive_action("initiate_refund", order_id)
        if not res.valid:
            return res.reason
        return initiate_refund(res.sanitized_value)
    
    # ── Tool 5: Create Support Ticket ──────────────────────────────────────
    @tool 
    def create_support_ticket_tool(issue: str) -> str:
        """Create a support ticket for the provided issue description."""
        res = tool_guard.validate_issue_text(issue)
        if not res.valid:
            return res.reason
        return create_support_ticket(res.sanitized_value)
    
    tools = [knowledge_base , check_order_status_tool , cancel_order_tool , initiate_refund_tool , create_support_ticket_tool]

    # ── System Prompt ──────────────────────────────────────────────────────
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a helpful customer support agent for ShopNest, an e-commerce platform.

Your goal is to help users by providing information OR performing actions using tools.

RULES:
1. INFORMATIONAL QUERIES: If the user asks about policies, FAQs, shipping timelines, \
refund procedures, or anything starting with "What is...", "How do I..." → use the \
knowledge_base tool.

2. ACTION QUERIES: If the user asks to check order status, cancel an order, get a refund, \
or raise a complaint → use the matching action tool.

3. MISSING INFORMATION: If an action requires an order_id but the user didn't provide one, \
DO NOT call the tool. Ask politely: "Could you please provide your order ID?"

4. MIXED QUERIES: If the user asks both an informational question AND an action \
(e.g. "What is the refund policy and cancel my order 123"), fulfill BOTH — \
call knowledge_base AND the action tool.

5. NO HALLUCINATION: Only state facts from tool results. Never invent order statuses, \
refund amounts, or policy details.

6. FRIENDLY TONE: Combine tool responses into a single, natural, helpful reply."""),
    MessagesPlaceholder(variable_name="chat_history", optional=True),
        ("human", "{input}"),
        ("placeholder", "{agent_scratchpad}"),
    ])
    # ── Build Modern Agent ─────────────────────────────────────────────────
    agent = create_tool_calling_agent(llm=llm , tools=tools , prompt=prompt)
    return AgentExecutor(agent=agent , tools=tools,verbose=True,max_iterations=5,return_intermediate_steps=False)

class ShopAgent:
    """Wrapper class that includes Layer 1 InputGuard and holds the AgentExecutor."""
    def __init__(self):
        self.input_guard = InputGuard()
        self.executor = build_shop_agent()
    
    def invoke(self, inputs: dict, **kwargs) -> dict:
        guard_result = self.input_guard.check(inputs.get("input", ""))
        if not guard_result.is_valid:
            return {"output": guard_result.rejection_message}
            
        return self.executor.invoke(inputs, **kwargs)
