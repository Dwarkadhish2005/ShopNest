"""
src/observability/phoenix.py — Phoenix Tracing Integration
===========================================================
Supports both Phoenix Cloud (app.phoenix.arize.com) and local Phoenix.

Configuration via .env:
  ENABLE_PHOENIX=true
  PHOENIX_API_KEY=<your-key>           # for cloud; omit for local
  PHOENIX_COLLECTOR_ENDPOINT=https://app.phoenix.arize.com/v1/traces
  PHOENIX_PROJECT_NAME=shopnest-production

Usage:
  from src.observability.phoenix import init_phoenix, is_phoenix_enabled
  init_phoenix(enable_phoenix=True, project_name="my-project")
"""
from __future__ import annotations

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

# Global tracer provider reference
_tracer_provider: Optional[object] = None


def init_phoenix(
    enable_phoenix: bool,
    project_name: str = "shopnest-production",
    endpoint: Optional[str] = None,
    api_key: Optional[str] = None,
) -> bool:
    """
    Initialize Phoenix tracing.

    Works with both Phoenix Cloud and local Phoenix server.
    Safe no-op when dependencies are missing or Phoenix is disabled.

    Args:
        enable_phoenix: Whether to enable Phoenix tracing.
        project_name:   Project name shown in the Phoenix dashboard.
        endpoint:       OTLP traces endpoint (e.g. https://app.phoenix.arize.com/v1/traces
                        or http://127.0.0.1:6006/v1/traces).
                        Falls back to PHOENIX_COLLECTOR_ENDPOINT env var.
        api_key:        API key for Phoenix Cloud. Falls back to PHOENIX_API_KEY env var.
                        Leave None / empty for a local (no-auth) Phoenix server.

    Returns:
        True if Phoenix was successfully initialized, False otherwise.
    """
    global _tracer_provider

    if not enable_phoenix:
        logger.info("Phoenix tracing is disabled (ENABLE_PHOENIX=false)")
        return False

    try:
        from phoenix.otel import register
        from openinference.instrumentation.langchain import LangChainInstrumentor
    except ImportError as exc:
        logger.warning(
            f"Phoenix dependencies not available: {exc}. "
            "Install with: pip install arize-phoenix openinference-instrumentation-langchain"
        )
        return False

    # Resolve endpoint — prefer explicit arg, then env var, then local default
    resolved_endpoint = (
        endpoint
        or os.getenv("PHOENIX_COLLECTOR_ENDPOINT", "")
        or "http://127.0.0.1:6006/v1/traces"
    ).strip().strip("'\"")

    # Resolve API key — prefer explicit arg, then env var
    resolved_api_key = (
        api_key
        or os.getenv("PHOENIX_API_KEY", "")
        or None
    )
    if isinstance(resolved_api_key, str) and not resolved_api_key.strip():
        resolved_api_key = None

    try:
        # Register the tracer provider with Phoenix
        # phoenix.otel.register reads PHOENIX_PROJECT_NAME / PHOENIX_API_KEY / 
        # PHOENIX_COLLECTOR_ENDPOINT env vars automatically, but we pass them
        # explicitly for clarity and override ability.
        _tracer_provider = register(
            project_name=project_name,
            endpoint=resolved_endpoint,
            api_key=resolved_api_key,
            set_global_tracer_provider=True,
            batch=True,          # buffer spans — avoids blocking on each call
            verbose=False,       # suppress per-call stdout noise
        )

        # Instrument LangChain with the registered tracer provider
        LangChainInstrumentor().instrument(tracer_provider=_tracer_provider)

        cloud_or_local = (
            "☁ Phoenix Cloud" if "app.phoenix.arize.com" in resolved_endpoint
            else "🏠 Local Phoenix"
        )
        logger.info(
            f"✓ Phoenix tracing initialized ({cloud_or_local}) | "
            f"endpoint={resolved_endpoint} | project={project_name}"
        )
        return True

    except Exception as exc:
        logger.warning(
            f"Phoenix tracing failed to initialize: {exc}. "
            "Continuing without Phoenix — app still works normally."
        )
        _tracer_provider = None
        return False


def get_tracer_provider() -> Optional[object]:
    """Return the global tracer provider, or None if not initialized."""
    return _tracer_provider


def is_phoenix_enabled() -> bool:
    """Return True if Phoenix tracing is active."""
    return _tracer_provider is not None
