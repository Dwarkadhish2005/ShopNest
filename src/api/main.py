from __future__ import annotations

import logging
import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from langchain_core.messages import AIMessage, HumanMessage

from src.api.schemas import ChatRequest, ChatResponse, HistoryMessage, SessionHistoryResponse
from src.api.service import ShopNestService
from src.observability.phoenix import init_phoenix, is_phoenix_enabled
from src.config import (
    ENABLE_PHOENIX,
    LOG_LEVEL,
    PHOENIX_PROJECT_NAME,
    PHOENIX_COLLECTOR_ENDPOINT,
    PHOENIX_API_KEY,
    PHOENIX_CAPTURE_LLM_DETAILS
)

# ── Configure Logging ──────────────────────────────────────────────────────
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s [%(name)s] - %(message)s",
)
logger = logging.getLogger(__name__)

# ── Initialize FastAPI App ─────────────────────────────────────────────────
app = FastAPI(
    title="ShopNest AI API", 
    version="4.0.0",
    description="Enterprise-grade customer support AI with Phoenix observability"
)

# ── Initialize Phoenix Tracing (safe no-op if disabled or fails) ───────────
phoenix_enabled = init_phoenix(
    enable_phoenix=ENABLE_PHOENIX,
    project_name=PHOENIX_PROJECT_NAME,
    endpoint=PHOENIX_COLLECTOR_ENDPOINT,
    api_key=PHOENIX_API_KEY or None,
)

# ── Initialize Service ─────────────────────────────────────────────────────
try:
    service = ShopNestService(max_turns=12)
    logger.info("✓ ShopNest service initialized successfully")
except Exception as e:
    logger.exception("Failed to initialize ShopNest service")
    raise

# ── CORS Middleware ───────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Static Files ───────────────────────────────────────────────────────────
STATIC_DIR = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# ── API Endpoints ──────────────────────────────────────────────────────────

@app.get("/", include_in_schema=False)
def root() -> FileResponse:
    """Serve the frontend UI."""
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health")
def health() -> dict:
    """Health check endpoint."""
    return {
        "status": "ok",
        "service": "shopnest-api",
        "version": "4.0.0",
        "phoenix_enabled": is_phoenix_enabled(),
    }


@app.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest) -> ChatResponse:
    """
    Main chat endpoint for customer support queries.
    
    Supports optional session management and returns telemetry data.
    """
    session_id = payload.session_id or f"sess-{uuid.uuid4().hex[:12]}"

    try:
        result = service.ask(
            session_id=session_id, 
            message=payload.message,
            capture_llm_details=PHOENIX_CAPTURE_LLM_DETAILS
        )
        return ChatResponse(
            session_id=session_id,
            response=result["response"],
            latency_ms=result["latency_ms"],
            telemetry=result["telemetry"],
        )
    except Exception as exc:
        logger.exception(f"Chat request failed | session={session_id}")
        raise HTTPException(
            status_code=500, 
            detail=f"Agent failure: {str(exc)[:200]}"
        ) from exc


@app.get("/sessions/{session_id}", response_model=SessionHistoryResponse)
def get_session_history(session_id: str) -> SessionHistoryResponse:
    """Retrieve conversation history for a session."""
    if not service.sessions.session_exists(session_id):
        raise HTTPException(status_code=404, detail="Session not found")

    raw_messages = service.sessions.get_messages(session_id)
    messages = []
    for msg in raw_messages:
        if isinstance(msg, HumanMessage):
            messages.append(HistoryMessage(role="user", content=msg.content))
        elif isinstance(msg, AIMessage):
            messages.append(HistoryMessage(role="assistant", content=msg.content))

    return SessionHistoryResponse(session_id=session_id, messages=messages)


@app.delete("/sessions/{session_id}")
def clear_session(session_id: str) -> dict:
    """Clear conversation history for a session."""
    cleared = service.sessions.clear_session(session_id)
    return {
        "session_id": session_id, 
        "cleared": cleared,
        "message": f"Session {'cleared' if cleared else 'not found'}"
    }


@app.get("/observability/status")
def observability_status() -> dict:
    """Get observability system status."""
    return {
        "phoenix_enabled": is_phoenix_enabled(),
        "phoenix_project": PHOENIX_PROJECT_NAME,
        "phoenix_endpoint": PHOENIX_COLLECTOR_ENDPOINT,
        "phoenix_api_key_set": bool(PHOENIX_API_KEY),
        "log_level": LOG_LEVEL,
    }


# ── Startup logging ────────────────────────────────────────────────────────
logger.info(f"ShopNest API v4.0.0 initialized | Phoenix: {'✓ ENABLED' if phoenix_enabled else '✗ DISABLED'}")

@app.get("/admin/cache/stats")
def get_cache_stats() -> dict:
    """Get the latest cache stats for the service."""
    return service.cache.stats()

@app.delete("/admin/cache/invalidate")
def invalidate_cache(query: str = None) -> dict:
    """Invalidate a specific cache or the whole cache."""
    service.cache.invalidate(query)
    return {"message": "cache invalidated", "query": query}
