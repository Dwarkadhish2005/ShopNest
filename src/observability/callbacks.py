from __future__ import annotations

import logging
from dataclasses import dataclass, asdict
from time import perf_counter
from typing import Any, Dict, List, Optional

from langchain_core.callbacks.base import BaseCallbackHandler

logger = logging.getLogger(__name__)


@dataclass
class ToolEvent:
    """Represents a tool execution event."""
    name: str
    status: str  # "started", "ok", "error"
    latency_ms: float
    input_preview: str = ""
    output_preview: str = ""
    error: str = ""


@dataclass
class LLMEvent:
    """Represents an LLM call event."""
    name: str
    status: str  # "started", "ok", "error"
    latency_ms: float
    error: str = ""


class AgentTelemetryCallback(BaseCallbackHandler):
    """
    Captures tool and LLM events from a single agent invoke call.
    Works seamlessly with Phoenix tracing when enabled.
    """

    def __init__(self, session_id: str, capture_llm_details: bool = True) -> None:
        """
        Initialize telemetry callback.
        
        Args:
            session_id: Unique session identifier
            capture_llm_details: Whether to capture detailed LLM metrics
        """
        super().__init__()
        self.session_id = session_id
        self._tool_started_at: Dict[str, float] = {}
        self._llm_started_at: Dict[str, float] = {}
        
        self.tool_events: List[ToolEvent] = []
        self.llm_events: List[LLMEvent] = []
        self.llm_calls = 0
        self.llm_errors = 0
        self.tool_calls = 0
        self.tool_errors = 0
        self.capture_llm_details = capture_llm_details

    def _run_key(self, run_id: Any) -> str:
        """Convert run_id to string key."""
        return str(run_id) if run_id is not None else "unknown"

    # ─── Tool Events ─────────────────────────────────────────────────────

    def on_tool_start(
        self,
        serialized: Dict[str, Any],
        input_str: str,
        *,
        run_id: Any,
        **kwargs: Any,
    ) -> None:
        """Called when tool execution starts."""
        self._tool_started_at[self._run_key(run_id)] = perf_counter()
        name = serialized.get("name", "unknown_tool")
        self.tool_calls += 1
        
        self.tool_events.append(
            ToolEvent(
                name=name,
                status="started",
                latency_ms=0.0,
                input_preview=input_str[:200],
            )
        )
        logger.debug(f"Tool started: {name} | run_id={run_id}")

    def on_tool_end(self, output: Any, *, run_id: Any, **kwargs: Any) -> None:
        """Called when tool execution completes successfully."""
        key = self._run_key(run_id)
        started = self._tool_started_at.pop(key, perf_counter())
        latency_ms = (perf_counter() - started) * 1000
        output_preview = str(output)[:300]
        
        # Find the matching started event and update it
        for event in reversed(self.tool_events):
            if event.status == "started":
                event.status = "ok"
                event.latency_ms = latency_ms
                event.output_preview = output_preview
                logger.debug(f"Tool completed: {event.name} | latency_ms={latency_ms:.2f}")
                return

    def on_tool_error(
        self, 
        error: BaseException, 
        *, 
        run_id: Any, 
        **kwargs: Any
    ) -> None:
        """Called when tool execution fails."""
        key = self._run_key(run_id)
        started = self._tool_started_at.pop(key, perf_counter())
        latency_ms = (perf_counter() - started) * 1000
        error_msg = str(error)[:300]
        self.tool_errors += 1
        
        # Find the matching started event and mark as error
        for event in reversed(self.tool_events):
            if event.status == "started":
                event.status = "error"
                event.latency_ms = latency_ms
                event.error = error_msg
                logger.warning(f"Tool failed: {event.name} | error={error_msg}")
                return

    # ─── LLM Events ──────────────────────────────────────────────────────

    def on_llm_start(
        self,
        serialized: Dict[str, Any],
        prompts: List[str],
        *,
        run_id: Any,
        **kwargs: Any,
    ) -> None:
        """Called when LLM call starts."""
        if self.capture_llm_details:
            self._llm_started_at[self._run_key(run_id)] = perf_counter()
        self.llm_calls += 1
        logger.debug(f"LLM call started | run_id={run_id}")

    def on_chat_model_start(
        self, 
        serialized: Dict[str, Any], 
        messages: List[List[Any]],
        *,
        run_id: Any,
        **kwargs: Any,
    ) -> None:
        """Called when chat model call starts."""
        if self.capture_llm_details:
            self._llm_started_at[self._run_key(run_id)] = perf_counter()
        self.llm_calls += 1
        logger.debug(f"Chat model called | run_id={run_id}")

    def on_llm_end(self, response: Any, *, run_id: Any, **kwargs: Any) -> None:
        """Called when LLM call completes."""
        if self.capture_llm_details:
            key = self._run_key(run_id)
            self._llm_started_at.pop(key, None)
        logger.debug(f"LLM call completed | run_id={run_id}")

    def on_llm_error(
        self, 
        error: BaseException, 
        *, 
        run_id: Any, 
        **kwargs: Any
    ) -> None:
        """Called when LLM call fails."""
        self.llm_errors += 1
        logger.warning(f"LLM call failed: {error}")

    def on_chain_start(
        self,
        serialized: Dict[str, Any],
        inputs: Dict[str, Any],
        *,
        run_id: Any,
        **kwargs: Any,
    ) -> None:
        """Called when chain execution starts."""
        if serialized is not None:
            logger.debug(f"Chain started: {serialized.get('name', 'unknown')}")
        else:
            logger.debug("Chain started (no serialized data)")

    def snapshot(self) -> Dict[str, Any]:
        """
        Return current telemetry snapshot.
        Filters out incomplete (started) tool events.
        """
        return {
            "session_id": self.session_id,
            "tool_events": [
                asdict(event) 
                for event in self.tool_events 
                if event.status != "started"
            ],
            "tool_calls": self.tool_calls,
            "tool_errors": self.tool_errors,
            "llm_calls": self.llm_calls,
            "llm_errors": self.llm_errors,
        }

