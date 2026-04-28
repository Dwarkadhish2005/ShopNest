from __future__ import annotations

from dataclasses import dataclass, asdict
from time import perf_counter
from typing import Any, Dict, List, Optional

from langchain_core.callbacks.base import BaseCallbackHandler


@dataclass
class ToolEvent:
    name: str
    status: str
    latency_ms: float
    input_preview: str = ""
    output_preview: str = ""
    error: str = ""


class AgentTelemetryCallback(BaseCallbackHandler):
    """Captures tool/LLM events from a single agent invoke call."""

    def __init__(self, session_id: str) -> None:
        super().__init__()
        self.session_id = session_id
        self._tool_started_at: Dict[str, float] = {}
        self.tool_events: List[ToolEvent] = []
        self.llm_calls = 0
        self.llm_errors = 0

    def _run_key(self, run_id: Any) -> str:
        return str(run_id) if run_id is not None else "unknown"

    def on_tool_start(
        self,
        serialized: Dict[str, Any],
        input_str: str,
        *,
        run_id: Any,
        **kwargs: Any,
    ) -> None:
        self._tool_started_at[self._run_key(run_id)] = perf_counter()
        name = serialized.get("name", "tool")
        self.tool_events.append(
            ToolEvent(
                name=name,
                status="started",
                latency_ms=0.0,
                input_preview=input_str[:160],
            )
        )

    def on_tool_end(self, output: Any, *, run_id: Any, **kwargs: Any) -> None:
        key = self._run_key(run_id)
        started = self._tool_started_at.pop(key, perf_counter())
        latency_ms = (perf_counter() - started) * 1000
        output_preview = str(output)[:200]
        for event in reversed(self.tool_events):
            if event.status == "started":
                event.status = "ok"
                event.latency_ms = latency_ms
                event.output_preview = output_preview
                return

    def on_tool_error(self, error: BaseException, *, run_id: Any, **kwargs: Any) -> None:
        key = self._run_key(run_id)
        started = self._tool_started_at.pop(key, perf_counter())
        latency_ms = (perf_counter() - started) * 1000
        for event in reversed(self.tool_events):
            if event.status == "started":
                event.status = "error"
                event.latency_ms = latency_ms
                event.error = str(error)
                return

    def on_llm_start(
        self,
        serialized: Dict[str, Any],
        prompts: List[str],
        *,
        run_id: Any,
        **kwargs: Any,
    ) -> None:
        self.llm_calls += 1

    def on_chat_model_start(self, *args: Any, **kwargs: Any) -> None:
        self.llm_calls += 1

    def on_llm_error(self, error: BaseException, *, run_id: Any, **kwargs: Any) -> None:
        self.llm_errors += 1

    def snapshot(self) -> Dict[str, Any]:
        return {
            "tool_events": [asdict(event) for event in self.tool_events if event.status != "started"],
            "llm_calls": self.llm_calls,
            "llm_errors": self.llm_errors,
        }
