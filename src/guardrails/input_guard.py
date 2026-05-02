"""
src/guardrails/input_guard.py — Input Guard (Layer 1)
======================================================
Rejects out-of-domain or nonsense queries BEFORE they reach the LLM or RAG
pipeline. Zero cost — pure regex + keyword matching, no extra API calls.

Domain: ShopNest e-commerce customer support only.

Usage:
    guard = InputGuard()
    result = guard.check("write a rap song")
    if not result.is_valid:
        return result.rejection_message
"""

from __future__ import annotations

import re
import logging
from dataclasses import dataclass, field
from typing import List, Optional

logger = logging.getLogger(__name__)


# ── Domain keywords — ANY of these → query is in-domain ──────────────────────

_DOMAIN_KEYWORDS: List[str] = [
    # Order / transactional
    "order", "orders", "order_id", "order id", "purchase", "bought", "buy",
    "delivery", "deliver", "delivered", "shipment", "shipped", "shipping",
    "track", "tracking", "dispatch",
    # Refund / money
    "refund", "refunds", "money back", "return", "returns", "exchange",
    "reimbursement", "credit", "chargeback", "payment",
    # Cancellation
    "cancel", "cancellation", "cancelled", "void",
    # Support / complaint
    "support", "ticket", "complaint", "issue", "problem", "help", "assist",
    "broken", "damaged", "missing", "lost",
    # Product
    "product", "item", "quantity", "size", "color", "variant", "price",
    "discount", "coupon", "promo", "offer", "sale",
    # Policies / FAQs
    "policy", "policies", "faq", "question", "procedure", "rule", "how long",
    "how do i", "what is", "when will", "can i", "do you",
    # Account
    "account", "login", "password", "email", "profile",
    # Company
    "shopnest", "shop nest", "store", "seller", "vendor",
    # Time / status
    "status", "eta", "expected", "arrive", "arrival", "days", "business days",
]

# ── Hard-reject patterns — explicit off-domain requests ──────────────────────

_REJECT_PATTERNS: List[re.Pattern] = [
    re.compile(r"\b(write|compose|create|make|generate)\s+(a\s+)?(rap|poem|song|story|essay|code|script|joke|haiku|limerick)\b", re.I),
    re.compile(r"\b(solve|calculate|compute|integrate|differentiate|math|algebra|calculus|equation)\b", re.I),
    re.compile(r"\b(translate|translation)\s+.{0,30}\b(to|into)\s+(spanish|french|german|hindi|arabic|chinese|japanese)\b", re.I),
    re.compile(r"\b(who\s+(is|was|are)|what\s+(is|was|are)\s+the\s+(capital|president|prime\s+minister|population))\b", re.I),
    re.compile(r"\b(recipe|cook|bake|ingredient|calories|nutrition)\b", re.I),
    re.compile(r"\b(weather|forecast|temperature|rain|sunny|cloudy)\b", re.I),
    re.compile(r"\b(stock|bitcoin|crypto|forex|invest|investment|trading|nifty|sensex)\b", re.I),
    re.compile(r"\b(movie|film|actress|actor|celebrity|instagram|youtube|tiktok|netflix)\b", re.I),
    re.compile(r"\b(sports|football|cricket|soccer|basketball|score|match|tournament)\b", re.I),
    re.compile(r"\b(doctor|medical|symptom|diagnosis|disease|medicine|hospital|treatment)\b", re.I),
    re.compile(r"\b(lawyer|legal advice|lawsuit|court|sue|attorney)\b", re.I),
    re.compile(r"\b(hello|hi|hey|yo|sup|wassup|greetings|good morning|good evening)\s*[!?.]*$", re.I),
    re.compile(r"^[\s!?.,:;\"'()\-_]+$"),   # punctuation-only / empty
    re.compile(r"^.{0,3}$"),                  # too short (≤3 chars)
]

# ── Minimum meaningful token count ───────────────────────────────────────────
_MIN_TOKENS = 2


@dataclass
class InputGuardResult:
    is_valid: bool
    rejection_message: Optional[str] = None
    matched_reason: Optional[str] = None
    query_preview: str = ""


class InputGuard:
    """
    Layer-1 Safety Guard: filters non-ShopNest queries before they hit the
    retriever or LLM.
    """

    FALLBACK_MSG = (
        "I'm ShopNest's customer support assistant and can only help with "
        "questions about your orders, refunds, shipping, cancellations, or "
        "our store policies. Please ask me something related to your ShopNest "
        "experience! 😊"
    )

    def check(self, query: str) -> InputGuardResult:
        """
        Validate whether a query is in-domain for ShopNest customer support.

        Returns:
            InputGuardResult with is_valid=True if the query should proceed,
            or is_valid=False with a rejection_message if it should be blocked.
        """
        preview = query.strip()[:80]

        # ── 0. Basic empty / too-short check ─────────────────────────────────
        stripped = query.strip()
        if not stripped or len(stripped) <= 3:
            logger.info(f"[InputGuard] REJECTED (too short): '{preview}'")
            return InputGuardResult(
                is_valid=False,
                rejection_message=self.FALLBACK_MSG,
                matched_reason="too_short",
                query_preview=preview,
            )

        # ── 1. Hard-reject pattern check ─────────────────────────────────────
        for pattern in _REJECT_PATTERNS:
            if pattern.search(stripped):
                logger.info(f"[InputGuard] REJECTED (pattern={pattern.pattern[:40]}): '{preview}'")
                return InputGuardResult(
                    is_valid=False,
                    rejection_message=self.FALLBACK_MSG,
                    matched_reason=f"reject_pattern:{pattern.pattern[:40]}",
                    query_preview=preview,
                )

        # ── 2. Domain keyword check ───────────────────────────────────────────
        lower_query = stripped.lower()
        tokens = lower_query.split()

        if len(tokens) < _MIN_TOKENS:
            # Single word — only accept if it's a known domain keyword
            if not any(kw in lower_query for kw in _DOMAIN_KEYWORDS):
                logger.info(f"[InputGuard] REJECTED (single off-domain token): '{preview}'")
                return InputGuardResult(
                    is_valid=False,
                    rejection_message=self.FALLBACK_MSG,
                    matched_reason="single_off_domain_token",
                    query_preview=preview,
                )

        # ── 3. Multi-word but completely off-domain ───────────────────────────
        if len(tokens) >= 3:
            has_domain = any(kw in lower_query for kw in _DOMAIN_KEYWORDS)
            if not has_domain:
                logger.info(f"[InputGuard] REJECTED (no domain keywords): '{preview}'")
                return InputGuardResult(
                    is_valid=False,
                    rejection_message=self.FALLBACK_MSG,
                    matched_reason="no_domain_keywords",
                    query_preview=preview,
                )

        logger.debug(f"[InputGuard] PASSED: '{preview}'")
        return InputGuardResult(is_valid=True, query_preview=preview)
