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
TOP_K = 3   # chunks returned per query

# ── LLM Provider ('groq' = free ✅  ) ───────────────────
LLM_PROVIDER    = "groq"
LLM_TEMPERATURE = 0.0   # deterministic → no hallucination

# ── Groq (FREE — https://console.groq.com) ────────────────────────────────
GROQ_API_KEY    = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL      = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

# ── API runtime ─────────────────────────────────────────────────────────────
API_HOST = os.getenv("API_HOST", "127.0.0.1")
API_PORT = int(os.getenv("API_PORT", "8000"))

# ── Observability & Monitoring ──────────────────────────────────────────
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Phoenix Tracing Configuration
ENABLE_PHOENIX = os.getenv("ENABLE_PHOENIX", "false").lower() == "true"
PHOENIX_PROJECT_NAME = os.getenv("PHOENIX_PROJECT_NAME", "shopnest-production")
PHOENIX_COLLECTOR_ENDPOINT = os.getenv("PHOENIX_COLLECTOR_ENDPOINT", "http://127.0.0.1:6006/v1/traces")
PHOENIX_API_KEY = os.getenv("PHOENIX_API_KEY", "")          # Cloud only; empty = local
PHOENIX_CAPTURE_LLM_DETAILS = os.getenv("PHOENIX_CAPTURE_LLM_DETAILS", "true").lower() == "true"

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
