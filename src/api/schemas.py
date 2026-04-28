from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    session_id: Optional[str] = Field(default=None, description="Client-provided session id")


class ChatResponse(BaseModel):
    session_id: str
    response: str
    latency_ms: float
    telemetry: Dict[str, Any]


class HistoryMessage(BaseModel):
    role: str
    content: str


class SessionHistoryResponse(BaseModel):
    session_id: str
    messages: List[HistoryMessage]
