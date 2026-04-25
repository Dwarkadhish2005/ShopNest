# ShopNest AI Customer Support Agent

An intelligent, LLM-driven customer support system for e-commerce. Built with **LangChain**, **FAISS**, and **OpenAI** — combining Retrieval-Augmented Generation (RAG) with an action-oriented agent.

---

## Architecture

```
User Query
   ↓
LangChain Agent  (OpenAI Functions — LLM-driven reasoning)
   ↓
 ┌─────────────────┬──────────────────┬────────────────────┐
 ↓                 ↓                  ↓                    ↓
KnowledgeBase   check_order_status  cancel_order      initiate_refund
(RAG → FAISS)   check_order_status  cancel_order      create_support_ticket
```

### Modules

| Phase | Module | File | Purpose |
|-------|--------|------|---------|
| 1 | M1+M2 | `src/ingestion/chunker.py` | Document loading, chunking, metadata tagging |
| 1 | M3+M4 | `src/rag/vectorstore.py` | HuggingFace embeddings + FAISS index build/load |
| 2 | M5 | `src/rag/retriever.py` | Similarity search wrapper |
| 2 | M6 | `src/rag/context_assembler.py` | Format retrieved chunks for LLM prompt |
| 2 | M7 | `src/rag/chain.py` | Strict RAG chain (no hallucination) |
| 2 | M8 | `src/validation/test_rag.py` | RAG retrieval validation suite |
| 3 | — | `src/tools/actions.py` | Action tools: cancel, refund, status, ticket |
| 3 | — | `src/agent/shop_agent.py` | LangChain agent with all tools + system prompt |
| 3 | M9 | `src/validation/test_agent.py` | Phase 3 agent validation suite |

---

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Set your OpenAI API key

```bash
# Copy the example and fill in your key
copy .env.example .env
# Edit .env and set OPENAI_API_KEY=sk-...
```

### 3. Build the FAISS index (run once)

```bash
python build_index.py
```

### 4. Run the agent

```bash
# Interactive mode
python agent_query.py

# Single query
python agent_query.py "What is the refund policy?"
python agent_query.py "Cancel my order 123"
```

---

## Test Scenarios

| Query | Expected Behaviour |
|---|---|
| `What is the refund policy?` | Uses **KnowledgeBase** → RAG answer |
| `Cancel my order 123` | Calls **cancel_order_tool** |
| `Cancel my order` | Asks: *"Please provide your order ID"* |
| `What is refund policy and cancel order 123?` | Calls **both** — RAG + cancel |
| `Check status of order 456` | Calls **check_order_status_tool** |
| `Initiate refund for order 789` | Calls **initiate_refund_tool** |
| `My package arrived damaged` | Calls **create_support_ticket_tool** |

---

## Validation

```bash
# Phase 2 — RAG retrieval tests (no API key needed)
python -m src.validation.test_rag

# Phase 3 — Tool unit tests (no API key needed)
python -m src.validation.test_agent

# Phase 3 — Live agent integration tests (requires OPENAI_API_KEY)
python -m src.validation.test_agent --live

# RAG-only CLI (no API key needed)
python query.py --retrieval-only "How long does a refund take?"
```

---

## Project Structure

```
ShopNest/
├── data/                        # Knowledge base documents
│   ├── refund_policy.txt
│   ├── shipping_policy.txt
│   ├── cancellation_policy.txt
│   └── faq.txt
├── faiss_index/                 # Built by build_index.py
│   ├── index.faiss
│   └── index.pkl
├── src/
│   ├── config.py                # Paths, model names, env vars
│   ├── ingestion/
│   │   └── chunker.py           # Document chunker + metadata tagger
│   ├── rag/
│   │   ├── vectorstore.py       # FAISS build + load
│   │   ├── retriever.py         # Similarity search
│   │   ├── context_assembler.py # Context formatter
│   │   └── chain.py             # Strict RAG LLM chain
│   ├── tools/
│   │   └── actions.py           # cancel, refund, status, ticket
│   ├── agent/
│   │   └── shop_agent.py        # LangChain OPENAI_FUNCTIONS agent
│   └── validation/
│       ├── test_rag.py          # Phase 2 retrieval tests
│       └── test_agent.py        # Phase 3 agent validation
├── build_index.py               # One-time FAISS index builder
├── query.py                     # RAG-only CLI
├── agent_query.py               # Agent CLI (Phase 3 entrypoint)
├── requirements.txt
└── .env.example
```

---

## Key Design Decisions

- **LLM-driven routing** — The agent uses `AgentType.OPENAI_FUNCTIONS`. The LLM reads tool descriptions and decides which tools to call. No keyword matching.
- **RAG as a tool** — The knowledge base is wrapped as a `Tool` so the agent can choose it alongside action tools, enabling mixed queries.
- **No hallucination** — The RAG chain uses a strict system prompt; the agent system prompt explicitly forbids inventing data.
- **Missing info handling** — The system prompt instructs the agent to ask for `order_id` if not provided, rather than guessing.
- **Local embeddings** — `all-MiniLM-L6-v2` runs locally (CPU), no embedding API cost.
