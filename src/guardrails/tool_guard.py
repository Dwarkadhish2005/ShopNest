
from __future__ import annotations

import re
import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)



_ORDER_ID_PATTERN = re.compile(r"^[A-Za-z0-9]([A-Za-z0-9\-]{1,28}[A-Za-z0-9]|[A-Za-z0-9])$")


_DESTRUCTIVE_ACTIONS = {"cancel_order", "initiate_refund"}


@dataclass
class ToolGuardResult:
    valid: bool
    reason: Optional[str] = None          
    sanitized_value: Optional[str] = None 


class ToolGuard:

    def validate_order_id(self, order_id: str) -> ToolGuardResult:
        if not order_id or not isinstance(order_id, str):
            logger.warning("[ToolGuard] INVALID order_id — empty or wrong type")
            return ToolGuardResult(
                valid=False,
                reason="Order ID is required. Please provide your order ID (e.g., ORD-12345).",
            )

        cleaned = order_id.strip()

        
        placeholders = {"order_id", "your_order_id", "order-id", "orderid", "id", "xxx", "null", "none", "na", "n/a"}
        if cleaned.lower() in placeholders:
            logger.warning(f"[ToolGuard] INVALID order_id — placeholder: '{cleaned}'")
            return ToolGuardResult(
                valid=False,
                reason=f"'{cleaned}' doesn't look like a real order ID. Please provide your actual order ID.",
            )

        
        if len(cleaned) < 2 or len(cleaned) > 30:
            logger.warning(f"[ToolGuard] INVALID order_id — length {len(cleaned)}: '{cleaned}'")
            return ToolGuardResult(
                valid=False,
                reason=f"Order ID must be between 2 and 30 characters. Got: '{cleaned}'",
            )

        
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
        
        id_result = self.validate_order_id(order_id)
        if not id_result.valid:
            return id_result

        
        logger.info(
            f"[ToolGuard] DESTRUCTIVE ACTION | action={action_name} | "
            f"order_id={id_result.sanitized_value}"
        )

        return ToolGuardResult(valid=True, sanitized_value=id_result.sanitized_value)

    def validate_issue_text(self, issue: str) -> ToolGuardResult:
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
