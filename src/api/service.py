from __future__ import annotations

import logging
from time import perf_counter
from typing import Any, Dict

from src.agent.shop_agent import build_shop_agent
from src.memory.session_store import InMemorySessionStore
from src.observability.callbacks import AgentTelemetryCallback

logger = logging.getLogger(__name__)


class ShopNestService:
    """Coordinates agent calls, session memory, and telemetry."""

    def __init__(self, max_turns: int = 12) -> None:
        self.agent = build_shop_agent()
        self.sessions = InMemorySessionStore(max_turns=max_turns)

    def ask(self, session_id: str, message: str) -> Dict[str, Any]:
        history = self.sessions.get_messages(session_id)
        callback = AgentTelemetryCallback(session_id=session_id)

        started = perf_counter()
        result = self.agent.invoke(
            {
                "input": message,
                "chat_history": history,
            },
            config={"callbacks": [callback]},
        )
        latency_ms = (perf_counter() - started) * 1000

        answer = result.get("output", "")
        self.sessions.append_turn(session_id=session_id, user_text=message, assistant_text=answer)

        telemetry = callback.snapshot()
        telemetry["request_latency_ms"] = round(latency_ms, 2)

        logger.info(
            "chat_completed session=%s latency_ms=%.2f tools=%d llm_calls=%d llm_errors=%d",
            session_id,
            latency_ms,
            len(telemetry.get("tool_events", [])),
            telemetry.get("llm_calls", 0),
            telemetry.get("llm_errors", 0),
        )

        return {
            "response": answer,
            "latency_ms": round(latency_ms, 2),
            "telemetry": telemetry,
        }
