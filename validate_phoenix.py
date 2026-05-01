#!/usr/bin/env python
"""
validate_phoenix.py — ShopNest Phoenix Integration Validator
=============================================================
Runs a series of checks to verify that Phoenix observability is
correctly configured and can send traces.

Usage:
    python validate_phoenix.py
"""

import os
import sys
import logging
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

# Load .env before any other imports
from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")

# ── Colours ────────────────────────────────────────────────────────────────

class C:
    GREEN  = "\033[92m"
    RED    = "\033[91m"
    YELLOW = "\033[93m"
    BLUE   = "\033[94m"
    BOLD   = "\033[1m"
    RESET  = "\033[0m"

def ok(msg):  print(f"  {C.GREEN}✓{C.RESET}  {msg}")
def fail(msg): print(f"  {C.RED}✗{C.RESET}  {msg}")
def warn(msg): print(f"  {C.YELLOW}⚠{C.RESET}  {msg}")

# ── Individual Checks ──────────────────────────────────────────────────────

def check_packages():
    """Check that required Python packages are importable."""
    print(f"\n{C.BOLD}[1] Python packages{C.RESET}")
    all_ok = True
    deps = {
        "phoenix.otel":                           "arize-phoenix (>=15.0.0)",
        "openinference.instrumentation.langchain": "openinference-instrumentation-langchain",
        "langchain":                               "langchain",
        "langchain_groq":                          "langchain-groq",
        "fastapi":                                 "fastapi",
        "dotenv":                                  "python-dotenv",
    }
    for module, pkg in deps.items():
        try:
            __import__(module)
            ok(f"{pkg}")
        except ImportError:
            fail(f"{pkg}  ← NOT installed  (run: pip install {pkg})")
            all_ok = False
    return all_ok


def check_env():
    """Check critical environment variables."""
    print(f"\n{C.BOLD}[2] Environment variables (.env){C.RESET}")
    all_ok = True

    enable = os.getenv("ENABLE_PHOENIX", "false").lower() == "true"
    if enable:
        ok(f"ENABLE_PHOENIX=true")
    else:
        warn("ENABLE_PHOENIX=false  ← Phoenix is disabled; set to 'true' to enable")
        # Not a hard failure — user may intentionally have it off
        return True   # continue other checks

    endpoint = os.getenv("PHOENIX_COLLECTOR_ENDPOINT", "").strip().strip("'\"")
    if not endpoint:
        fail("PHOENIX_COLLECTOR_ENDPOINT is not set")
        all_ok = False
    else:
        ok(f"PHOENIX_COLLECTOR_ENDPOINT={endpoint}")

    project = os.getenv("PHOENIX_PROJECT_NAME", "").strip()
    if project:
        ok(f"PHOENIX_PROJECT_NAME={project}")
    else:
        warn("PHOENIX_PROJECT_NAME not set — will default to 'shopnest-production'")

    api_key = os.getenv("PHOENIX_API_KEY", "").strip()
    is_cloud = "app.phoenix.arize.com" in endpoint if endpoint else False
    if is_cloud:
        if api_key:
            ok(f"PHOENIX_API_KEY=***{api_key[-6:]}  (cloud auth ✓)")
        else:
            fail("PHOENIX_API_KEY is required for Phoenix Cloud but is not set")
            all_ok = False
    else:
        if api_key:
            warn("PHOENIX_API_KEY is set but endpoint appears to be local — key may be ignored")
        else:
            ok("PHOENIX_API_KEY not set — correct for local Phoenix")

    return all_ok


def check_files():
    """Verify that required source files exist."""
    print(f"\n{C.BOLD}[3] Project files{C.RESET}")
    base = Path(__file__).resolve().parent
    required = [
        "src/observability/phoenix.py",
        "src/observability/callbacks.py",
        "src/observability/__init__.py",
        "src/config.py",
        "src/api/main.py",
        "src/api/service.py",
        "src/agent/shop_agent.py",
        "src/llm.py",
    ]
    all_ok = True
    for rel in required:
        p = base / rel
        if p.exists():
            ok(rel)
        else:
            fail(f"{rel}  ← MISSING")
            all_ok = False
    return all_ok


def check_config():
    """Verify config.py has all Phoenix variables."""
    print(f"\n{C.BOLD}[4] config.py content{C.RESET}")
    base = Path(__file__).resolve().parent
    cfg = (base / "src" / "config.py").read_text(encoding="utf-8")
    expected = [
        "ENABLE_PHOENIX",
        "PHOENIX_PROJECT_NAME",
        "PHOENIX_COLLECTOR_ENDPOINT",
        "PHOENIX_API_KEY",
        "PHOENIX_CAPTURE_LLM_DETAILS",
    ]
    all_ok = True
    for var in expected:
        if var in cfg:
            ok(f"{var}  defined")
        else:
            fail(f"{var}  NOT found in config.py")
            all_ok = False
    return all_ok


def check_phoenix_init():
    """Import and call init_phoenix to verify it works end-to-end."""
    print(f"\n{C.BOLD}[5] Phoenix init (live test){C.RESET}")
    enable = os.getenv("ENABLE_PHOENIX", "false").lower() == "true"
    if not enable:
        warn("ENABLE_PHOENIX=false — skipping live Phoenix init test")
        return True

    try:
        from src.observability.phoenix import init_phoenix, is_phoenix_enabled
        from src.config import (
            PHOENIX_PROJECT_NAME,
            PHOENIX_COLLECTOR_ENDPOINT,
            PHOENIX_API_KEY,
        )

        result = init_phoenix(
            enable_phoenix=True,
            project_name=PHOENIX_PROJECT_NAME,
            endpoint=PHOENIX_COLLECTOR_ENDPOINT,
            api_key=PHOENIX_API_KEY or None,
        )

        if result and is_phoenix_enabled():
            ok("init_phoenix() returned True — tracer provider registered ✓")
            return True
        else:
            fail(
                "init_phoenix() returned False — check logs above for details.\n"
                "    Common causes:\n"
                "      • Invalid or missing PHOENIX_API_KEY for cloud\n"
                "      • arize-phoenix not installed"
            )
            return False
    except Exception as exc:
        fail(f"Exception during init_phoenix(): {exc}")
        import traceback
        traceback.print_exc()
        return False


def check_connectivity():
    """Try to reach the Phoenix OTLP endpoint."""
    print(f"\n{C.BOLD}[6] Network connectivity{C.RESET}")
    enable = os.getenv("ENABLE_PHOENIX", "false").lower() == "true"
    endpoint = os.getenv("PHOENIX_COLLECTOR_ENDPOINT", "").strip().strip("'\"")

    if not enable:
        warn("ENABLE_PHOENIX=false — skipping connectivity check")
        return True

    if not endpoint:
        warn("PHOENIX_COLLECTOR_ENDPOINT not set — skipping connectivity check")
        return True

    try:
        import urllib.request, urllib.error, ssl

        # OTLP endpoint needs /v1/traces if not present
        effective_endpoint = endpoint
        if not effective_endpoint.endswith("/v1/traces"):
            effective_endpoint = f"{effective_endpoint.rstrip('/')}/v1/traces"

        # For cloud, endpoint is HTTPS — create SSL context
        is_cloud = "https://" in effective_endpoint
        ctx = ssl.create_default_context() if is_cloud else None

        req = urllib.request.Request(effective_endpoint, method="POST")
        req.add_header("Content-Type", "application/x-protobuf")
        api_key = os.getenv("PHOENIX_API_KEY", "")
        if api_key:
            req.add_header("Authorization", f"Bearer {api_key}")

        try:
            urllib.request.urlopen(req, timeout=5, context=ctx)
        except urllib.error.HTTPError as e:
            # 400 Bad Request = server is up, rejected our empty protobuf body — GOOD
            # 401 = reachable but API key rejected
            if e.code == 400:
                ok(f"Server reachable at {endpoint} (HTTP 400 for empty body is expected)")
                return True
            elif e.code == 401:
                fail(
                    f"Server reachable but returned 401 Unauthorized\n"
                    "    → Your PHOENIX_API_KEY has been revoked or is invalid.\n"
                    "    → Go to https://app.phoenix.arize.com → Settings → API Keys\n"
                    "      and generate a new key, then update PHOENIX_API_KEY in .env"
                )
                return False
            elif e.code in (403, 405, 415):
                ok(f"Server reachable at {endpoint} (HTTP {e.code})")
                return True
            raise
        except urllib.error.URLError as e:
            fail(f"Cannot reach {endpoint}: {e.reason}")
            if "app.phoenix.arize.com" not in endpoint:
                print(f"       → For local Phoenix, start it with:")
                print(f"         python -m phoenix.server.main serve")
            return False

        ok(f"Server reachable at {endpoint}")
        return True

    except Exception as exc:
        warn(f"Connectivity check error: {exc}")
        return False


# ── Main ───────────────────────────────────────────────────────────────────

def main():
    print(f"\n{C.BOLD}{'═'*60}{C.RESET}")
    print(f"{C.BOLD}  ShopNest — Phoenix Observability Validator{C.RESET}")
    print(f"{C.BOLD}{'═'*60}{C.RESET}")

    checks = [
        ("Packages",        check_packages),
        ("Env Variables",   check_env),
        ("Project Files",   check_files),
        ("Config Content",  check_config),
        ("Phoenix Init",    check_phoenix_init),
        ("Connectivity",    check_connectivity),
    ]

    results = {}
    for name, fn in checks:
        try:
            results[name] = fn()
        except Exception as exc:
            fail(f"Unexpected error in '{name}': {exc}")
            results[name] = False

    # ── Summary ────────────────────────────────────────────────────────────
    print(f"\n{C.BOLD}{'═'*60}{C.RESET}")
    print(f"{C.BOLD}  Summary{C.RESET}")
    print(f"{C.BOLD}{'═'*60}{C.RESET}\n")

    all_pass = True
    for name, passed in results.items():
        tag = f"{C.GREEN}PASS{C.RESET}" if passed else f"{C.RED}FAIL{C.RESET}"
        print(f"  {tag}  {name}")
        if not passed:
            all_pass = False

    print()
    if all_pass:
        print(f"{C.GREEN}{C.BOLD}✓ All checks passed! Phoenix integration is working.{C.RESET}\n")
        print("Next steps:")
        print("  1. Start the API:  python run_api.py")
        print("  2. Send a message: curl -X POST http://localhost:8000/chat \\")
        print("                           -H 'Content-Type: application/json' \\")
        print("                           -d '{\"message\": \"What is the refund policy?\"}'")
        print("  3. View traces:    https://app.phoenix.arize.com\n")
        return 0
    else:
        print(f"{C.RED}{C.BOLD}✗ Some checks failed. Fix the issues above and re-run.{C.RESET}\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
