from __future__ import annotations

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


_tracer_provider: Optional[object] = None


def init_phoenix(
    enable_phoenix: bool,
    project_name: str = "shopnest-production",
    endpoint: Optional[str] = None,
    api_key: Optional[str] = None,
) -> bool:
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

    
    resolved_endpoint = (
        endpoint
        or os.getenv("PHOENIX_COLLECTOR_ENDPOINT", "")
        or "http://127.0.0.1:6006/v1/traces"
    ).strip().strip("'\"")

    
    resolved_api_key = (
        api_key
        or os.getenv("PHOENIX_API_KEY", "")
        or None
    )
    if isinstance(resolved_api_key, str) and not resolved_api_key.strip():
        resolved_api_key = None

    try:
        _tracer_provider = register(
            project_name=project_name,
            endpoint=resolved_endpoint,
            api_key=resolved_api_key,
            set_global_tracer_provider=True,
            batch=True,          
            verbose=False,       
        )
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
    return _tracer_provider


def is_phoenix_enabled() -> bool:
    return _tracer_provider is not None
