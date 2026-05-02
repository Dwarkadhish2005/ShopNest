"""
src/guardrails/tool_guard.py — Tool Guard (Layer 3)
====================================================
Validates tool inputs BEFORE execution to prevent:
  - Invalid order IDs being passed to action tools
  - Accidental or malformed destructive action calls

Usage:
    guard = ToolGuard()
    result = guard.validate_order_id(order_id)
    if not result.valid:
        return result.reason
"""

from __future__ import annotations

import re
import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

# ── Order ID format ───────────────────────────────────────────────────────────
# Accepts: ORD-12345, 12345, ABC123, order-abc-123  (3–30 alphanumeric/dash chars)
_ORDER_ID_PATTERN = re.compile(r"^[A-Za-z0-9]([A-Za-z0-9\-]{1,28}[A-Za-z0-9]|[A-Za-z0-9])$")

# ── Destructive actions that require extra validation ─────────────────────────
_DESTRUCTIVE_ACTIONS = {"cancel_order", "initiate_refund"}


@dataclass
class ToolGuardResult:
    valid: bool
    reason: Optional[str] = None          # human-readable explanation on failure
    sanitized_value: Optional[str] = None # cleaned value on success


class ToolGuard:
    """
    Layer-3 Safety Guard: validates tool inputs before execution.

    Methods
    -------
    validate_order_id(order_id)
        Ensures the order ID is syntactically valid before passing to tools.

    validate_destructive_action(action_name, order_id)
        Extra validation for cancel/refund — confirms ID is valid + logs intent.

    validate_issue_text(issue)
        Validates support ticket text is meaningful (not empty/trivial).
    """

    def validate_order_id(self, order_id: str) -> ToolGuardResult:
        """
        Validate an order_id input before passing it to any action tool.

        Rules:
          - Must be a non-empty string
          - Must match pattern: 2–30 alphanumeric/hyphen characters
          - Must NOT be a placeholder like 'your_order_id', 'ORDER_ID', etc.
          - Strips surrounding whitespace automatically
        """
        if not order_id or not isinstance(order_id, str):
            logger.warning("[ToolGuard] INVALID order_id — empty or wrong type")
            return ToolGuardResult(
                valid=False,
                reason="Order ID is required. Please provide your order ID (e.g., ORD-12345).",
            )

        cleaned = order_id.strip()

        # Reject obvious placeholders
        placeholders = {"order_id", "your_order_id", "order-id", "orderid", "id", "xxx", "null", "none", "na", "n/a"}
        if cleaned.lower() in placeholders:
            logger.warning(f"[ToolGuard] INVALID order_id — placeholder: '{cleaned}'")
            return ToolGuardResult(
                valid=False,
                reason=f"'{cleaned}' doesn't look like a real order ID. Please provide your actual order ID.",
            )

        # Length check
        if len(cleaned) < 2 or len(cleaned) > 30:
            logger.warning(f"[ToolGuard] INVALID order_id — length {len(cleaned)}: '{cleaned}'")
            return ToolGuardResult(
                valid=False,
                reason=f"Order ID must be between 2 and 30 characters. Got: '{cleaned}'",
            )

        # Pattern check
        if not _ORDER_ID_PATTERN.match(cleaned):
            logger.warning(f"[ToolGuard] INVALID order_id — pattern mismatch: '{cleaned}'")
            return ToolGuardResult(
                valid=False,
                reason=(
                    f"'{cleaned}' doesn't appear to be a valid order ID format. "
                    "Order IDs contain letters, numbers, and hyphens (e.g., ORD-12345)."
                ),
            )

        logger.debug(f"[ToolGuard] VALID order_id: '{cleaned}'")
        return ToolGuardResult(valid=True, sanitized_value=cleaned)

    def validate_destructive_action(
        self, action_name: str, order_id: str
    ) -> ToolGuardResult:
        """
        Extra validation for cancel_order and initiate_refund.
        Validates order_id AND logs the destructive intent for audit trail.
        """
        # First run standard order_id validation
        id_result = self.validate_order_id(order_id)
        if not id_result.valid:
            return id_result

        # Log for audit
        logger.info(
            f"[ToolGuard] DESTRUCTIVE ACTION | action={action_name} | "
            f"order_id={id_result.sanitized_value}"
        )

        return ToolGuardResult(valid=True, sanitized_value=id_result.sanitized_value)

    def validate_issue_text(self, issue: str) -> ToolGuardResult:
        """
        Validates that a support ticket issue description is meaningful.
        """
        if not issue or not isinstance(issue, str):
            return ToolGuardResult(
                valid=False,
                reason="Please describe your issue so we can create a support ticket.",
            )

        cleaned = issue.strip()

        if len(cleaned) < 10:
            return ToolGuardResult(
                valid=False,
                reason=(
                    "Issue description is too short. Please provide more detail "
                    "about your problem so we can help you effectively."
                ),
            )

        if len(cleaned) > 2000:
            cleaned = cleaned[:2000]
            logger.warning("[ToolGuard] Issue text truncated to 2000 chars")

        return ToolGuardResult(valid=True, sanitized_value=cleaned)
