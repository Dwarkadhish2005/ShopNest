# Phoenix Observability Setup

## Quick Start (Local Python - No Docker)

### Terminal 1: Start Phoenix
```bash
pip install phoenix
phoenix serve
```
Phoenix will start on `http://localhost:6006`

### Terminal 2: Start ShopNest API
```bash
cd c:\Dwarka\Machiene Learning\ShopNest
set ENABLE_PHOENIX=true
set PHOENIX_COLLECTOR_ENDPOINT=http://127.0.0.1:6018/v1/traces
set PHOENIX_PROJECT_NAME=shopnest-production
python run_api.py
```

### Terminal 3: Test It
```bash
curl -X POST http://localhost:8000/chat ^
  -H "Content-Type: application/json" ^
  -d "{\"message\": \"What is your refund policy?\"}"
```

### Browser: View Traces
Open: `http://localhost:6006`

---

## Configuration

### Windows PowerShell
```powershell
$env:ENABLE_PHOENIX = "true"
$env:PHOENIX_COLLECTOR_ENDPOINT = "http://127.0.0.1:6018/v1/traces"
$env:PHOENIX_PROJECT_NAME = "shopnest-production"
$env:PHOENIX_CAPTURE_LLM_DETAILS = "true"
python run_api.py
```

### Windows CMD
```cmd
set ENABLE_PHOENIX=true
set PHOENIX_COLLECTOR_ENDPOINT=http://127.0.0.1:6018/v1/traces
set PHOENIX_PROJECT_NAME=shopnest-production
set PHOENIX_CAPTURE_LLM_DETAILS=true
python run_api.py
```

---

## Environment Variables

| Variable | Value | Description |
|----------|-------|-------------|
| ENABLE_PHOENIX | true/false | Enable tracing |
| PHOENIX_COLLECTOR_ENDPOINT | http://127.0.0.1:6018/v1/traces | Where traces go |
| PHOENIX_PROJECT_NAME | shopnest-production | Project name in dashboard |
| PHOENIX_CAPTURE_LLM_DETAILS | true/false | Performance tuning |

---

## Verify Setup

```bash
# Check Phoenix installed
python -c "import phoenix; print('✓ Phoenix installed')"

# Check packages
python -c "import openinference; print('✓ OpenInference installed')"

# Check API health
curl http://localhost:8000/health

# Check observability status
curl http://localhost:8000/observability/status
```

---

## API Endpoints

```
GET  /health                     - Health check
GET  /observability/status       - Phoenix config status
POST /chat                       - Chat with telemetry
GET  /sessions/{id}              - Session history
DELETE /sessions/{id}            - Clear session
```

---

## Code Changes Made

All these changes are in the code (nothing to do here):

| File | Change |
|------|--------|
| src/observability/phoenix.py | ✅ OTEL initialization + tracer tracking |
| src/observability/callbacks.py | ✅ Event tracking + LLM metrics |
| src/config.py | ✅ Phoenix configuration variables |
| src/api/main.py | ✅ Initialization + /observability/status |
| src/api/service.py | ✅ Callback integration |

---

## Troubleshooting

### "Phoenix tracing disabled" in logs
```powershell
$env:ENABLE_PHOENIX = "true"
python run_api.py
```

### Cannot find phoenix command
```bash
pip install arize-phoenix openinference-instrumentation-langchain
```

### Port 6006 already in use
Phoenix is already running on another terminal. Either:
- Close the existing Phoenix instance
- Use a different port: `phoenix serve --port 6007`

### No traces appearing
1. Verify Phoenix is running: `curl http://127.0.0.1:6006`
2. Check endpoint: `echo $env:PHOENIX_COLLECTOR_ENDPOINT`
3. Check API logs for errors
4. Restart API with LOG_LEVEL=DEBUG

### Chat requests slow
```powershell
$env:PHOENIX_CAPTURE_LLM_DETAILS = "false"
python run_api.py
```

---

## Example Response

```json
{
  "session_id": "sess-abc123",
  "response": "ShopNest offers a 30-day refund...",
  "latency_ms": 456.2,
  "telemetry": {
    "tool_events": [
      {
        "name": "knowledge_base",
        "status": "ok",
        "latency_ms": 234.5,
        "input_preview": "What is your refund policy?",
        "output_preview": "ShopNest offers...",
        "error": ""
      }
    ],
    "tool_calls": 1,
    "tool_errors": 0,
    "llm_calls": 3,
    "llm_errors": 0,
    "request_latency_ms": 456.2
  }
}
```

---

## Next Steps

1. ✅ Install packages: `pip install phoenix arize-phoenix openinference-instrumentation-langchain`
2. ✅ Start Phoenix: `phoenix serve`
3. ✅ Set environment variables (see above)
4. ✅ Start API: `python run_api.py`
5. ✅ View dashboard: `http://localhost:6006`
6. ✅ Make chat requests and monitor traces

**That's it! The code is ready to use.**
