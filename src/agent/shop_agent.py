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
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.tools import tool, Tool
from langchain_core.prompts import ChatPromptTemplate

from src.llm import get_llm
from src.tools.actions import check_order_status, cancel_order, initiate_refund, create_support_ticket
from src.rag.chain import RAGChain


def build_shop_agent() -> AgentExecutor:
    """
    Builds the ShopNest decision agent combining:
      - KnowledgeBase tool  (RAG over FAISS)
      - check_order_status  (action)
      - cancel_order        (action)
      - initiate_refund     (action)
      - create_support_ticket (action)

    The LLM (Groq / OpenAI) reads tool descriptions and decides
    which tools to call — NO hardcoded keyword routing.
    """
    llm = get_llm()
    rag_chain = RAGChain(llm=llm)

    # ── Tool 1: RAG Knowledge Base ─────────────────────────────────────────
    @tool
    def knowledge_base(query: str) -> str:
        """
        Use this tool to answer ANY informational question about ShopNest's
        policies: shipping, refund, cancellation, returns, FAQs.
        Use this whenever the user asks 'What is...', 'How do I...', or 
        anything about policies, timelines, or procedures.
        """
        result = rag_chain.ask(query)
        return result["answer"]

    # ── Tool 2: Check Order Status ─────────────────────────────────────────
    @tool
    def check_order_status_tool(order_id: str) -> str:
        """
        Check the current shipping or delivery status of a customer's order.
        Call this when the user asks about their order status or tracking.
        Requires: order_id (e.g. '123', 'ORD-456').
        """
        return check_order_status(order_id)

    # ── Tool 3: Cancel Order ───────────────────────────────────────────────
    @tool
    def cancel_order_tool(order_id: str) -> str:
        """
        Cancel an existing order for the customer.
        Call this when the user explicitly requests a cancellation.
        Requires: order_id. If not provided, ask the user for it first.
        """
        return cancel_order(order_id)

    # ── Tool 4: Initiate Refund ────────────────────────────────────────────
    @tool
    def initiate_refund_tool(order_id: str) -> str:
        """
        Initiate a refund for a returned or cancelled order.
        Call this when the user asks for a refund or money back.
        Requires: order_id. If not provided, ask the user for it first.
        """
        return initiate_refund(order_id)

    # ── Tool 5: Create Support Ticket ──────────────────────────────────────
    @tool
    def create_support_ticket_tool(issue: str) -> str:
        """
        Create a customer support ticket for complaints, damaged items,
        missing packages, or any issue that needs human review.
        Requires: a clear description of the issue.
        """
        return create_support_ticket(issue)

    tools = [
        knowledge_base,
        check_order_status_tool,
        cancel_order_tool,
        initiate_refund_tool,
        create_support_ticket_tool,
    ]

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
        ("human", "{input}"),
        ("placeholder", "{agent_scratchpad}"),
    ])

    # ── Build Modern Agent ─────────────────────────────────────────────────
    agent = create_tool_calling_agent(llm=llm, tools=tools, prompt=prompt)

    return AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
        max_iterations=5,
        return_intermediate_steps=False,
    )