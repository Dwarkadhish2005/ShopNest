
from __future__ import annotations

import re
import logging
from dataclasses import dataclass, field
from typing import List, Optional

logger = logging.getLogger(__name__)




_DOMAIN_KEYWORDS: List[str] = [
    
    "order", "orders", "order_id", "order id", "purchase", "bought", "buy",
    "delivery", "deliver", "delivered", "shipment", "shipped", "shipping",
    "track", "tracking", "dispatch",
    
    "refund", "refunds", "money back", "return", "returns", "exchange",
    "reimbursement", "credit", "chargeback", "payment",
    
    "cancel", "cancellation", "cancelled", "void",
    
    "support", "ticket", "complaint", "issue", "problem", "help", "assist",
    "broken", "damaged", "missing", "lost",
    
    "product", "item", "quantity", "size", "color", "variant", "price",
    "discount", "coupon", "promo", "offer", "sale",
    
    "policy", "policies", "faq", "question", "procedure", "rule", "how long",
    "how do i", "what is", "when will", "can i", "do you",
    
    "account", "login", "password", "email", "profile",
    
    "shopnest", "shop nest", "store", "seller", "vendor",
    
    "status", "eta", "expected", "arrive", "arrival", "days", "business days",
]



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
    re.compile(r"^[\s!?.,:;\"'()\-_]+$"),   
    re.compile(r"^.{0,3}$"),                  
]


_MIN_TOKENS = 2


@dataclass
class InputGuardResult:
    is_valid: bool
    rejection_message: Optional[str] = None
    matched_reason: Optional[str] = None
    query_preview: str = ""


class InputGuard:

    FALLBACK_MSG = (
        "I'm ShopNest's customer support assistant and can only help with "
        "questions about your orders, refunds, shipping, cancellations, or "
        "our store policies. Please ask me something related to your ShopNest "
        "experience! 😊"
    )

    def check(self, query: str) -> InputGuardResult:
        preview = query.strip()[:80]

        
        stripped = query.strip()
        if not stripped or len(stripped) <= 3:
            logger.info(f"[InputGuard] REJECTED (too short): '{preview}'")
            return InputGuardResult(
                is_valid=False,
                rejection_message=self.FALLBACK_MSG,
                matched_reason="too_short",
                query_preview=preview,
            )

        
        for pattern in _REJECT_PATTERNS:
            if pattern.search(stripped):
                logger.info(f"[InputGuard] REJECTED (pattern={pattern.pattern[:40]}): '{preview}'")
                return InputGuardResult(
                    is_valid=False,
                    rejection_message=self.FALLBACK_MSG,
                    matched_reason=f"reject_pattern:{pattern.pattern[:40]}",
                    query_preview=preview,
                )

        
        lower_query = stripped.lower()
        tokens = lower_query.split()

        if len(tokens) < _MIN_TOKENS:
            
            if not any(kw in lower_query for kw in _DOMAIN_KEYWORDS):
                logger.info(f"[InputGuard] REJECTED (single off-domain token): '{preview}'")
                return InputGuardResult(
                    is_valid=False,
                    rejection_message=self.FALLBACK_MSG,
                    matched_reason="single_off_domain_token",
                    query_preview=preview,
                )

        
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
