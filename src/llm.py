import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import (
    LLM_PROVIDER,
    GROQ_API_KEY, GROQ_MODEL,
    LLM_TEMPERATURE,
)


def get_llm():
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

    else:
        raise ValueError(
            f"Unknown LLM_PROVIDER: '{provider}'. "
            "Supported values: 'groq'"
        )
