import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ── Paths ──────────────────────────────────────────────────────────────────
BASE_DIR        = Path(__file__).resolve().parent.parent
DATA_DIR        = BASE_DIR / "data"
FAISS_INDEX_DIR = BASE_DIR / "faiss_index"

# ── Embedding ──────────────────────────────────────────────────────────────
EMBEDDING_MODEL = "all-MiniLM-L6-v2"   # lightweight, free, runs locally

# ── Retrieval ──────────────────────────────────────────────────────────────
TOP_K = 4   # chunks returned per query

# ── LLM Provider ('groq' = free ✅  |  'openai' = paid) ───────────────────
LLM_PROVIDER    = os.getenv("LLM_PROVIDER", "groq")
LLM_TEMPERATURE = 0.0   # deterministic → no hallucination

# ── Groq (FREE — https://console.groq.com) ────────────────────────────────
GROQ_API_KEY    = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL      = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

# ── OpenAI (paid fallback) ─────────────────────────────────────────────────
OPENAI_API_KEY  = os.getenv("OPENAI_API_KEY", "")
LLM_MODEL       = os.getenv("LLM_MODEL", "gpt-3.5-turbo")

# ── Files ──────────────────────────────────────────────────────────────────
POLICY_FILES = [
    "refund_policy.txt",
    "shipping_policy.txt",
    "cancellation_policy.txt",
]
FAQ_FILE = "faq.txt"

# ── Category map (filename → domain tag) ──────────────────────────────────
CATEGORY_MAP = {
    "refund_policy":       "refund",
    "shipping_policy":     "shipping",
    "cancellation_policy": "cancellation",
    "faq":                 "faq",
}
