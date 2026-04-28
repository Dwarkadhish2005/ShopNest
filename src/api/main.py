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
from src.observability.phoenix import init_phoenix
from src.config import ENABLE_PHOENIX, LOG_LEVEL

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(title="ShopNest AI API", version="4.0.0")
service = ShopNestService(max_turns=12)
init_phoenix(enable_phoenix=ENABLE_PHOENIX, project_name="shopnest-production")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", include_in_schema=False)
def root() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "shopnest-api"}


@app.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest) -> ChatResponse:
    session_id = payload.session_id or f"sess-{uuid.uuid4().hex[:12]}"

    try:
        result = service.ask(session_id=session_id, message=payload.message)
        return ChatResponse(
            session_id=session_id,
            response=result["response"],
            latency_ms=result["latency_ms"],
            telemetry=result["telemetry"],
        )
    except Exception as exc:
        logger.exception("chat_failed session=%s", session_id)
        raise HTTPException(status_code=500, detail=f"Agent failure: {exc}") from exc


@app.get("/sessions/{session_id}", response_model=SessionHistoryResponse)
def get_session_history(session_id: str) -> SessionHistoryResponse:
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
    cleared = service.sessions.clear_session(session_id)
    return {"session_id": session_id, "cleared": cleared}
