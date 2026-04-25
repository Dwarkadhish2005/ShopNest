"""
src/llm.py — Centralized LLM Factory
======================================
Returns the correct LLM based on LLM_PROVIDER in .env.

Supported providers:
  - groq   (FREE ✅ — recommended)  console.groq.com
  - openai (paid)

Add new providers here without touching agent or chain code.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import (
    LLM_PROVIDER,
    GROQ_API_KEY, GROQ_MODEL,
    OPENAI_API_KEY, LLM_MODEL,
    LLM_TEMPERATURE,
)


def get_llm():
    """
    Return a LangChain chat model based on the configured provider.

    Raises:
        EnvironmentError: if the required API key is missing.
        ValueError: if the provider is unknown.
    """
    provider = LLM_PROVIDER.lower().strip()

    if provider == "groq":
        if not GROQ_API_KEY:
            raise EnvironmentError(
                "GROQ_API_KEY is not set.\n"
                "1. Sign up FREE at https://console.groq.com\n"
                "2. Create an API key (no credit card needed)\n"
                "3. Add  GROQ_API_KEY=gsk_...  to your .env file\n"
                "4. Re-run the script"
            )
        from langchain_groq import ChatGroq
        return ChatGroq(
            model=GROQ_MODEL,
            temperature=LLM_TEMPERATURE,
            groq_api_key=GROQ_API_KEY,
        )

    elif provider == "openai":
        if not OPENAI_API_KEY:
            raise EnvironmentError(
                "OPENAI_API_KEY is not set.\n"
                "Add it to your .env file."
            )
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=LLM_MODEL,
            temperature=LLM_TEMPERATURE,
            openai_api_key=OPENAI_API_KEY,
        )

    else:
        raise ValueError(
            f"Unknown LLM_PROVIDER: '{provider}'. "
            "Supported values: 'groq', 'openai'"
        )
