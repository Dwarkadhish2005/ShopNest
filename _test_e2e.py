"""Quick end-to-end test of agent + Phoenix tracing."""
import sys
sys.path.insert(0, '.')
from dotenv import load_dotenv
load_dotenv()

# Init Phoenix first
from src.config import ENABLE_PHOENIX, PHOENIX_PROJECT_NAME, PHOENIX_COLLECTOR_ENDPOINT, PHOENIX_API_KEY, PHOENIX_CAPTURE_LLM_DETAILS
from src.observability.phoenix import init_phoenix, is_phoenix_enabled

init_phoenix(
    enable_phoenix=ENABLE_PHOENIX,
    project_name=PHOENIX_PROJECT_NAME,
    endpoint=PHOENIX_COLLECTOR_ENDPOINT,
    api_key=PHOENIX_API_KEY or None,
)
print(f"Phoenix enabled: {is_phoenix_enabled()}")

# Test via the full service stack (includes callbacks)
from src.api.service import ShopNestService
service = ShopNestService(max_turns=5)
result = service.ask(session_id="test-session-001", message="What is the refund policy?")

print(f"\nAnswer: {result['response'][:300]}")
print(f"Latency: {result['latency_ms']} ms")
print(f"Telemetry: {result['telemetry']}")
print("\n[OK] End-to-end test PASSED")
