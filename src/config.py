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
TOP_K     = int(os.getenv("TOP_K", "3"))       # default chunks per query
TOP_K_MIN = int(os.getenv("TOP_K_MIN", "2"))   # dynamic range lower bound
TOP_K_MAX = int(os.getenv("TOP_K_MAX", "4"))   # dynamic range upper bound

# ── LLM Provider ('groq' = free ✅  ) ───────────────────
LLM_PROVIDER    = "groq"
LLM_TEMPERATURE = 0.0   # deterministic → no hallucination

# ── Groq (FREE — https://console.groq.com) ────────────────────────────────
GROQ_API_KEY    = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL      = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

# ── Voice Processing ──────────────────────────────────────────────────────
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")  # Rachel voice

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

# ── Performance & Caching ──────────────────────────────────────────────────
CACHE_TTL_SECONDS    = int(os.getenv("CACHE_TTL_SECONDS", "300"))   # 5 min response cache TTL
CACHE_MAX_SIZE       = int(os.getenv("CACHE_MAX_SIZE", "256"))       # max cached responses
EMBEDDING_CACHE_SIZE = int(os.getenv("EMBEDDING_CACHE_SIZE", "512")) # max cached embedding vectors

# ── Advanced Retrieval ─────────────────────────────────────────────────────
# Reranker: cross-encoder/ms-marco-MiniLM-L-6-v2 (free, ~70MB, local)
ENABLE_RERANKER  = os.getenv("ENABLE_RERANKER", "true").lower() == "true"
RERANKER_MODEL   = os.getenv("RERANKER_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2")
MULTI_QUERY_VARIATIONS = int(os.getenv("MULTI_QUERY_VARIATIONS", "3"))  # query variations

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
