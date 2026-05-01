from __future__ import annotations

import logging
from time import perf_counter
from typing import Any, Dict, Optional

from src.agent.shop_agent import build_shop_agent
from src.memory.session_store import InMemorySessionStore
from src.observability.callbacks import AgentTelemetryCallback

logger = logging.getLogger(__name__)


class ShopNestService:
    """
    Coordinates agent calls, session memory, and telemetry collection.
    
    Integrates with Phoenix observability for distributed tracing when enabled.
    """

    def __init__(self, max_turns: int = 12) -> None:
        """
        Initialize the ShopNest service.
        
        Args:
            max_turns: Maximum conversation turns to keep in memory
        """
        self.agent = build_shop_agent()
        self.sessions = InMemorySessionStore(max_turns=max_turns)
        logger.info(f"ShopNestService initialized with max_turns={max_turns}")

    def ask(
        self, 
        session_id: str, 
        message: str,
        capture_llm_details: bool = True
    ) -> Dict[str, Any]:
        """
        Process a user message and return an AI response with telemetry.
        
        Args:
            session_id: Unique session identifier
            message: User query
            capture_llm_details: Whether to capture detailed LLM metrics
            
        Returns:
            Dictionary with response, latency, and telemetry data
        """
        # Get conversation history from session store
        history = self.sessions.get_messages(session_id)
        
        # Create telemetry callback
        callback = AgentTelemetryCallback(
            session_id=session_id,
            capture_llm_details=capture_llm_details
        )

        # Invoke agent with timing
        started = perf_counter()
        try:
            result = self.agent.invoke(
                {
                    "input": message,
                    "chat_history": history,
                },
                config={"callbacks": [callback]},
            )
            latency_ms = (perf_counter() - started) * 1000
            
            answer = result.get("output", "")
            
            # Persist conversation to session memory
            self.sessions.append_turn(
                session_id=session_id, 
                user_text=message, 
                assistant_text=answer
            )

            # Collect telemetry snapshot
            telemetry = callback.snapshot()
            telemetry["request_latency_ms"] = round(latency_ms, 2)

            # Log metrics
            logger.info(
                f"chat_completed | session={session_id} | "
                f"latency_ms={latency_ms:.2f} | "
                f"tools={len(telemetry.get('tool_events', []))} | "
                f"llm_calls={telemetry.get('llm_calls', 0)} | "
                f"tool_errors={telemetry.get('tool_errors', 0)} | "
                f"llm_errors={telemetry.get('llm_errors', 0)}"
            )

            return {
                "response": answer,
                "latency_ms": round(latency_ms, 2),
                "telemetry": telemetry,
            }
            
        except Exception as e:
            latency_ms = (perf_counter() - started) * 1000
            logger.exception(
                f"agent_execution_failed | session={session_id} | "
                f"latency_ms={latency_ms:.2f} | error={str(e)[:200]}"
            )
            raise

