"""
MODULE 6 — Context Assembler
=============================
Takes retrieved Document chunks and formats them into a clean context
block ready for the LLM prompt.

Rules:
  - Each chunk is labelled with its source + section
  - Chunks are numbered for easy reference
  - Total context is capped to avoid overwhelming the LLM
"""

import sys
from pathlib import Path
from typing import List

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from langchain_core.documents import Document

MAX_CHARS_PER_CHUNK = 800   # truncate very long chunks
MAX_TOTAL_CHARS     = 3000  # safety cap on total context


def assemble_context(docs: List[Document]) -> str:
    """
    Convert a list of retrieved chunks into a formatted context string.

    Example output:
        [1] Source: refund_policy | Section: processing_time
        After approval, the refund is credited …

        [2] Source: faq | Section: returns_refunds
        Q24: How long does it take to get a refund? …
    """
    if not docs:
        return "No relevant information found in the knowledge base."

    parts: List[str] = []
    total = 0

    for i, doc in enumerate(docs, start=1):
        meta    = doc.metadata
        source  = meta.get("source", "unknown")
        section = meta.get("section", "unknown")

        content = doc.page_content.strip()
        if len(content) > MAX_CHARS_PER_CHUNK:
            content = content[:MAX_CHARS_PER_CHUNK] + " …"

        block = (
            f"[{i}] Source: {source} | Section: {section}\n"
            f"{content}"
        )
        parts.append(block)
        total += len(block)

        if total >= MAX_TOTAL_CHARS:
            break

    return "\n\n".join(parts)


def get_sources_summary(docs: List[Document]) -> str:
    """Return a compact one-line summary of which sources were used."""
    seen = []
    for doc in docs:
        tag = "{source}:{section}".format(**doc.metadata)
        if tag not in seen:
            seen.append(tag)
    return " | ".join(seen)
