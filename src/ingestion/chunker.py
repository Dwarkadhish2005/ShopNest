"""
MODULE 1 & 2 — Document Chunker + Metadata Tagger
===================================================
Policy files  → section-based chunks  (split on long-dash separator)
FAQ file      → one chunk per Q&A pair

Each chunk gets metadata:
    {source, section, category, chunk_type}
"""
import re
import sys
from pathlib import Path
from typing import List
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))   
from langchain_core.documents import Document
from src.config import DATA_DIR, POLICY_FILES, FAQ_FILE, CATEGORY_MAP   


# ── Helpers ────────────────────────────────────────────────────────────────

def _to_key(text: str) -> str:
    """Turn a section title into a clean snake_case key."""
    text = re.sub(r"^\d+\.\s*", "", text)          # remove leading number
    text = re.sub(r"[^a-z0-9 ]", "", text.lower())  # keep alphanumeric + space
    return text.strip().replace(" ", "_")[:60]

# ── Module 1a — Policy Chunker ─────────────────────────────────────────────

def chunk_policy_file(filepath: Path) -> List[Document]:
    """
    Split a policy .txt file into section-based chunks.

    The files use this pattern:
        ---------------------------------------------------------------
        N. SECTION TITLE
        ---------------------------------------------------------------
        section content ...
    Each (title + content) pair becomes one Document.
    """
    text     = filepath.read_text(encoding="utf-8")
    source   = filepath.stem
    category = CATEGORY_MAP.get(source, "general")
    docs     = []

    # ── 1. Capture numbered sections (title + body) ──
    pattern = re.compile(
        r"-{30,}\n"           # opening dash line
        r"(\d+\..+?)\n"       # numbered title  (group 1)
        r"-{30,}\n"           # closing dash line
        r"(.*?)"              # section body    (group 2)
        r"(?=-{30,}|\Z)",     # stops at next dash line or end
        re.DOTALL,
    )

    for m in pattern.finditer(text):
        title   = m.group(1).strip()
        body    = m.group(2).strip()
        if not body:
            continue

        docs.append(Document(
            page_content=f"{title}\n\n{body}",
            metadata={
                "source":     source,
                "section":    _to_key(title),
                "category":   category,
                "chunk_type": "policy_section",
            },
        ))

    # ── 2. Capture header / overview (everything before the first dash line) ──
    overview_match = re.match(r"(.*?)-{30,}", text, re.DOTALL)
    if overview_match:
        overview = overview_match.group(1).strip()
        if len(overview) > 40:
            docs.insert(0, Document(
                page_content=overview,
                metadata={
                    "source":     source,
                    "section":    "overview",
                    "category":   category,
                    "chunk_type": "policy_overview",
                },
            ))

    return docs


# ── Module 1b — FAQ Chunker ────────────────────────────────────────────────

# Maps FAQ section headers → category tags
_FAQ_SECTION_CATEGORIES = {
    "ORDERS":      "orders",
    "PAYMENTS":    "payments",
    "SHIPPING":    "shipping",
    "RETURNS":     "refund",
    "REFUNDS":     "refund",
    "CANCELLATIONS": "cancellation",
    "ACCOUNT":     "account",
    "PRODUCTS":    "products",
    "LOYALTY":     "loyalty",
    "TECHNICAL":   "technical",
    "CONTACT":     "support",
    "SUPPORT":     "support",
}


def _get_faq_category(section_header: str) ->str:
    for keyword , cat in _FAQ_SECTION_CATEGORIES.items():
        if keyword in section_header.upper():
            return cat
    return "faq"

def chunk_faq_file(filepath: Path) -> List[Document]:
    """
    Split the FAQ file so that each Q+A pair is one Document.
    Section headers (SECTION A, SECTION B …) are tracked for metadata.
    """
    text = filepath.read_text(encoding="utf-8")
    docs = []

    current_section     = "general"
    current_section_cat = "faq"
    current_q           = None
    current_a_lines: List[str] = []

    def flush(q, a_lines, section, cat):
        if not q or not a_lines:
            return None
        answer = "\n".join(a_lines).strip()
        if not answer:
            return None
        return Document(
            page_content=f"{q}\nA: {answer}",
            metadata={
                "source":     "faq",
                "section":    section,
                "category":   cat,
                "chunk_type": "faq_qa_pair",
                "question":   q,
            },
        )

    section_re  = re.compile(r"^SECTION\s+\w+:\s*(.+)", re.IGNORECASE)
    question_re = re.compile(r"^(Q\d+:.+)")
    answer_re   = re.compile(r"^A:\s*(.*)")

    in_answer = False

    for raw_line in text.splitlines():
        line = raw_line.rstrip()

        # ── Section header ──
        sec_m = section_re.match(line)
        if sec_m:
            doc = flush(current_q, current_a_lines, current_section, current_section_cat)
            if doc:
                docs.append(doc)
            current_q       = None
            current_a_lines = []
            in_answer       = False
            current_section     = sec_m.group(1).strip().lower().replace(" ", "_").replace("&", "and")[:50]
            current_section_cat = _get_faq_category(sec_m.group(1))
            continue

        # ── New question ──
        q_m = question_re.match(line)
        if q_m:
            doc = flush(current_q, current_a_lines, current_section, current_section_cat)
            if doc:
                docs.append(doc)
            current_q       = q_m.group(1).strip()
            current_a_lines = []
            in_answer       = False
            continue

        # ── Answer start ──
        a_m = answer_re.match(line)
        if a_m and current_q:
            in_answer = True
            current_a_lines.append(a_m.group(1))
            continue

        # ── Answer continuation ──
        if in_answer and current_q:
            current_a_lines.append(line.strip())

    # Flush last Q&A
    doc = flush(current_q, current_a_lines, current_section, current_section_cat)
    if doc:
        docs.append(doc)

    return docs


# ── Public API ─────────────────────────────────────────────────────────────

def chunk_all_documents() -> List[Document]:
    """Load + chunk every data file. Returns the full document list."""
    all_docs: List[Document] = []

    # Policy files
    for fname in POLICY_FILES:
        path = DATA_DIR / fname
        if not path.exists():
            print(f"[WARNING] {fname} not found — skipping")
            continue
        chunks = chunk_policy_file(path)
        all_docs.extend(chunks)
        print(f"  ✔ {fname:35s} → {len(chunks):3d} chunks")

    # FAQ
    faq_path = DATA_DIR / FAQ_FILE
    if faq_path.exists():
        chunks = chunk_faq_file(faq_path)
        all_docs.extend(chunks)
        print(f"  ✔ {FAQ_FILE:35s} → {len(chunks):3d} chunks")
    else:
        print(f"[WARNING] {FAQ_FILE} not found — skipping")

    print(f"\n  Total chunks: {len(all_docs)}")
    return all_docs    

