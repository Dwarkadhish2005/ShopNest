from __future__ import annotations

import logging
import os
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


def _normalize_collector_endpoint(raw_endpoint: str) -> str:
    endpoint = (raw_endpoint or "").strip().strip("'\"")
    if not endpoint:
        return ""

    parsed = urlparse(endpoint)
    if not parsed.scheme or not parsed.netloc:
        return endpoint

    # If a dashboard URL is provided (for example /s/<space>), convert to OTLP traces endpoint.
    if not parsed.path.endswith("/v1/traces"):
        return f"{parsed.scheme}://{parsed.netloc}/v1/traces"

    return endpoint


def init_phoenix(enable_phoenix: bool, project_name: str = "shopnest-phase4") -> bool:
    """Best-effort Phoenix tracing setup. Safe no-op when dependencies are missing."""
    if not enable_phoenix:
        logger.info("Phoenix tracing disabled.")
        return False

    # Force clear any lingering cloud configurations that might have been picked up from system env
    os.environ.pop("PHOENIX_API_KEY", None)
    os.environ.pop("PHOENIX_CLIENT_HEADERS", None)

    try:
        from phoenix.otel import register
        from openinference.instrumentation.langchain import LangChainInstrumentor

        endpoint = _normalize_collector_endpoint(os.getenv("PHOENIX_COLLECTOR_ENDPOINT", "http://127.0.0.1:6006/v1/traces"))
        
        tracer_provider = register(
            project_name=project_name, 
            endpoint=endpoint,
            set_global_tracer_provider=True
        )
        LangChainInstrumentor().instrument(tracer_provider=tracer_provider)
        logger.info(f"Phoenix tracing enabled locally. Traces should route to {endpoint} on project '{project_name}'.")
        return True
    except Exception as exc:
        logger.warning("Phoenix tracing setup skipped: %s", exc)
        return False
