"""
src/guardrails/__init__.py
===========================
Three-layer safety system for ShopNest AI Agent.

  InputGuard   — rejects out-of-domain / nonsense queries
  ContextGuard — detects weak retrieval and forces fallback
  ToolGuard    — validates tool inputs before execution
"""

from src.guardrails.input_guard import InputGuard, InputGuardResult
from src.guardrails.context_guard import ContextGuard, ContextGuardResult
from src.guardrails.tool_guard import ToolGuard, ToolGuardResult

__all__ = [
    "InputGuard", "InputGuardResult",
    "ContextGuard", "ContextGuardResult",
    "ToolGuard", "ToolGuardResult",
]
