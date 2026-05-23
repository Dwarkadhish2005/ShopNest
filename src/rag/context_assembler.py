
import sys
from pathlib import Path
from typing import List

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from langchain_core.documents import Document

MAX_CHARS_PER_CHUNK = 800   
MAX_TOTAL_CHARS     = 3000  


def assemble_context(docs: List[Document]) -> str:
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
    seen = []
    for doc in docs:
        tag = "{source}:{section}".format(**doc.metadata)
        if tag not in seen:
            seen.append(tag)
    return " | ".join(seen)
