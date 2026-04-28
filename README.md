# ShopNest AI Customer Support Agent

An intelligent, LLM-driven customer support system tailored for e-commerce environments. Built with **LangChain**, **FAISS**, and **OpenAI**, it seamlessly combines robust Retrieval-Augmented Generation (RAG) with an action-oriented agent capable of performing automated tasks.

---

## 🏗️ Architecture

The ShopNest Agent follows a modular and scalable architecture that routes user queries seamlessly between knowledge retrieval (RAG) and actionable tools via an LLM reasoning engine.

```text
User Query
   │
   ▼
LangChain Agent (OpenAI Functions — LLM-driven reasoning & planning)
   │
   ├───────────────────┬──────────────────────┬──────────────────────┐
   ▼                   ▼                      ▼                      ▼
KnowledgeBase       check_order_status     cancel_order         initiate_refund
(RAG → FAISS)       Tool Action            Tool Action          create_support_ticket
```

### Components overview:
1. **RAG Pipeline (KnowledgeBase):** Answers policy-based questions (FAQs, shipping, refunds) using vectorized context from domain documents.
2. **Tool Bindings:** Allows the Agent to take explicit actions based on user intent (e.g. canceling an order, checking status).
3. **Agent Core:** An LLM utilizing OpenAI function calling to intelligently decide *when* to search knowledge and *when* to execute a tool, or both.

---

## 🚀 Phase-Wise Breakdown & "Why it was used"

The project was constructed in distinct phases to ensure reliability, testability, and accurate grounding.

### Phase 1: Ingestion & Vectorization
**Goal:** Prepare unstructured domain knowledge (text files) for rapid semantic search.
* **Modules Used:** `chunker.py`, `vectorstore.py`
* **Technologies:** LangChain Text Splitters, HuggingFace Embeddings, FAISS.
* **Why this approach?** E-commerce policies can be lengthy. We use Recursive Character Text Splitting to chunk documents while preserving semantic meaning. FAISS (Facebook AI Similarity Search) is utilized because it provides a lightweight, exceptionally fast, and local vector index without the overhead of deploying a dedicated vector database container. HuggingFace standard embeddings offer excellent baseline semantic representation locally, saving API costs.

### Phase 2: RAG Pipeline (Retrieval-Augmented Generation)
**Goal:** Retrieve the most relevant information and enforce strict LLM answering (zero hallucination).
* **Modules Used:** `retriever.py`, `context_assembler.py`, `chain.py`, `test_rag.py`
* **Technologies:** LangChain Retrievers, PromptTemplates.
* **Why this approach?** Standard LLMs hallucinate when asked hyper-specific domain questions. By injecting retrieved FAISS context directly into the prompt (`chain.py`), we force the model to answer *only* using provided context. The modular separation of `retriever` and `context_assembler` allows for isolated unit testing (`test_rag.py`) to ensure retrieval accuracy before introducing the LLM token costs.

### Phase 3: Agent & Tool Integration
**Goal:** Evolve the system from a passive Q&A bot into an active Agent capable of fulfilling user requests.
* **Modules Used:** `actions.py`, `shop_agent.py`, `test_agent.py`
* **Technologies:** LangChain Agents, OpenAI Function Calling, Pydantic (strict schema validation).
* **Why this approach?** Support queries often mix knowledge questions ("What is the refund policy?") with actionable requests ("Cancel my order 123"). An Agent dynamically routes these requests. OpenAI function calling guarantees the LLM provides correctly formatted arguments (e.g., extracting `order_id` as integers). We built mock tools (`actions.py`) to simulate backend order management systems securely.

---

## 🛠️ Modules Directory

| Phase | Module | File | Purpose |
|-------|--------|------|---------|
| 1 | M1+M2 | `src/ingestion/chunker.py` | Document loading, recursive chunking, metadata tagging |
| 1 | M3+M4 | `src/rag/vectorstore.py` | HuggingFace embedding application + local FAISS index execution |
| 2 | M5 | `src/rag/retriever.py` | Abstraction wrapper for similarity search algorithms |
| 2 | M6 | `src/rag/context_assembler.py` | Formats retrieved embedding chunks into clean text for prompts |
| 2 | M7 | `src/rag/chain.py` | Strict RAG chain design enforcing context-only answers |
| 2 | M8 | `src/validation/test_rag.py` | RAG retrieval validation suite (no LLM required) |
| 3 | — | `src/tools/actions.py` | Simulated backend API tools (cancel, refund, status, ticket) |
| 3 | — | `src/agent/shop_agent.py` | LangChain ReAct agent integrating tools with custom system prompts |
| 3 | M9 | `src/validation/test_agent.py` | Phase 3 agent validation suite (unit + live integration) |

---

## ⚡ Quick Start

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
This parses the `/data` folder and generates the local vector store.
```bash
python build_index.py
```

### 4. Run the Agent

```bash
# Interactive Chat mode
python agent_query.py

# Single queries
python agent_query.py "What is the refund policy?"
python agent_query.py "Cancel my order 123"
```

---

## 🧪 Test Scenarios

The agent is designed to handle complex, multi-intent queries effortlessly.

| User Query | Expected Agent Behaviour |
|---|---|
| `What is the refund policy?` | Routes to **KnowledgeBase** → Retrieves context → RAG generation |
| `Cancel my order 123` | Invokes **cancel_order_tool(order_id=123)** |
| `Cancel my order` | Agent detects missing param, asks: *"Please provide your order ID"* |
| `What is refund policy and cancel order 123?` | Multi-step: Routes to **KnowledgeBase**, then invokes **cancel_order_tool** |
| `Check status of order 456` | Invokes **check_order_status_tool(order_id=456)** |
| `Initiate refund for order 789` | Invokes **initiate_refund_tool(order_id=789)** |
| `My package arrived damaged` | Invokes **create_support_ticket_tool(issue="damaged package")** |

---

## 🌐 Phase 4: Production Layer (Implemented)

Phase 4 turns the project into a usable application stack with backend APIs, session memory, browser UI, and runtime telemetry.

### Final Phase 4 Architecture

```text
Frontend (HTML/CSS/JS)
            ↓
FastAPI (API Layer)
            ↓
LangChain Agent Executor
    ↙                   ↘
RAG (FAISS)         Action Tools
```

### 1) FastAPI Backend (API Layer)

Implemented under `src/api/`.

- `src/api/main.py`
   - `POST /chat` accepts user messages, calls the agent, and returns structured response + telemetry.
   - `GET /health` readiness endpoint.
   - `GET /sessions/{session_id}` returns stored chat history for that session.
   - `DELETE /sessions/{session_id}` clears memory for a session.
- `src/api/service.py`
   - Central service that invokes the agent and coordinates memory + telemetry capture.

### 2) Conversation Memory (Context Awareness)

Implemented via in-process memory store:

- `src/memory/session_store.py`
   - Thread-safe session dictionary with bounded history (`max_turns`).
   - Persists prior user/assistant messages per `session_id`.
   - Trims old messages to keep memory efficient.
- Agent prompt upgraded to accept optional `chat_history`.

### 3) Frontend UI (Simple HTML/CSS/JS)

Implemented at `src/api/static/`.

- `index.html` modern single-page chat UI.
- `styles.css` responsive visual theme for desktop/mobile.
- `app.js` session-aware chat client:
   - Stores `session_id` in `localStorage`.
   - Sends requests to `/chat`.
   - Renders assistant responses and telemetry JSON.

### 4) Observability (Telemetry + Phoenix-ready)

Implemented with callback-level tracing and logging:

- `src/observability/callbacks.py`
   - Captures tool calls, tool latency, llm call count, and llm errors.
- `src/observability/phoenix.py`
   - Best-effort Phoenix initialization (safe fallback when packages are not installed).
- API responses include request telemetry payload for each call.

### 5) Deployment-ready Structure

New runtime entrypoint:

- `run_api.py` to launch uvicorn with env-driven host/port.

New config/env controls:

- `API_HOST`, `API_PORT`
- `LOG_LEVEL`
- `ENABLE_PHOENIX`
- `PHOENIX_COLLECTOR_ENDPOINT` (optional)

---

## ▶️ Run Phase 4 App

```bash
pip install -r requirements.txt
python build_index.py
python run_api.py
```

Then open:

```text
http://127.0.0.1:8000/
```

### API Example

```bash
curl -X POST "http://127.0.0.1:8000/chat" ^
   -H "Content-Type: application/json" ^
   -d "{\"message\":\"Cancel my order 123\",\"session_id\":\"demo-session\"}"
```

---

## 🛡️ Validation & Testing

Run unit and integration tests to verify pipeline integrity.

```bash
# Phase 2 — RAG retrieval tests (Local, no API key needed)
python -m src.validation.test_rag

# Phase 3 — Tool unit schema tests (Local, no API key needed)
python -m src.validation.test_agent

# Phase 3 — Live agent integration tests (requires OPENAI_API_KEY)
python -m src.validation.test_agent --live

# RAG-only CLI query test (Local, no API key needed)
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
│   ├── api/
│   │   ├── main.py              # FastAPI app + endpoints
│   │   ├── service.py           # Agent orchestration for API
│   │   ├── schemas.py           # Request/response models
│   │   └── static/              # Browser UI (HTML/CSS/JS)
│   ├── memory/
│   │   └── session_store.py     # Session-scoped conversation history
│   ├── observability/
│   │   ├── callbacks.py         # Tool + LLM telemetry callbacks
│   │   └── phoenix.py           # Optional Phoenix tracing bootstrap
│   └── validation/
│       ├── test_rag.py          # Phase 2 retrieval tests
│       └── test_agent.py        # Phase 3 agent validation
├── build_index.py               # One-time FAISS index builder
├── query.py                     # RAG-only CLI
├── agent_query.py               # Agent CLI (Phase 3 entrypoint)
├── run_api.py                   # FastAPI entrypoint (Phase 4)
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
