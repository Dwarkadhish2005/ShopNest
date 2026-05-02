from __future__ import annotations

import logging
from time import perf_counter
from typing import Any, Dict, Optional

from src.agent.shop_agent import ShopAgent
from src.memory.session_store import InMemorySessionStore
from src.observability.callbacks import AgentTelemetryCallback
from src.performance.cache import ResponseCache
from src.config import CACHE_TTL_SECONDS, CACHE_MAX_SIZE

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
        self.agent = ShopAgent()
        self.sessions = InMemorySessionStore(max_turns=max_turns)
        self.cache = ResponseCache(ttl_seconds=CACHE_TTL_SECONDS, max_size=CACHE_MAX_SIZE)
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
        started = perf_counter()
        
        # Check cache (only if we have no ongoing session history or history allows it, 
        # but typical response cache keys might just use the query for stateless FAQ.
        # Let's keep it simple: cache exact queries)
        cached_response = self.cache.get(message)
        if cached_response is not None:
            latency_ms = (perf_counter() - started) * 1000
            self.sessions.append_turn(session_id=session_id, user_text=message, assistant_text=cached_response)
            return {
                "response": cached_response,
                "latency_ms": round(latency_ms, 2),
                "telemetry": {"cached": True}
            }

        # Get conversation history from session store
        history = self.sessions.get_messages(session_id)
        
        # Create telemetry callback
        callback = AgentTelemetryCallback(
            session_id=session_id,
            capture_llm_details=capture_llm_details
        )

        try:
            # We need to adapt the invoke config parameter if ShopAgent wrapper doesn't support 'config'.
            # Looking at ShopAgent: `def invoke(self, inputs: dict) -> dict:`
            # ShopAgent needs to pass kwargs down if we want callbacks. Wait, wait. 
            # I'll update ShopAgent to accept kwargs for `self.executor.invoke(inputs, **kwargs)`
            # For now, let's fix ShopAgent in another step if needed. 
            # Well, it's safer to just do self.agent.executor.invoke if we want to pass config.
            
            # Let's use ShopAgent's custom invoke but we need to supply config
            # Wait, `ShopAgent.invoke` does not accept `config` param. Let's fix that too.
            result = self.agent.invoke(
                {
                    "input": message,
                    "chat_history": history,
                },
                config={"callbacks": [callback]},
            )
            latency_ms = (perf_counter() - started) * 1000
            
            answer = result.get("output", "")
            
            # Store in cache
            self.cache.set(message, answer)
            
            # Persist conversation to session memory
            self.sessions.append_turn(
                session_id=session_id, 
                user_text=message, 
                assistant_text=answer
            )

            # Collect telemetry snapshot
            telemetry = callback.snapshot()
            telemetry["request_latency_ms"] = round(latency_ms, 2)
            telemetry["cached"] = False

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
