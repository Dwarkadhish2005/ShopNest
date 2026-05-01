# How to Use ShopNest

This guide explains how to run the ShopNest API and the Phoenix Observability dashboard locally.

## 1. Start the Phoenix Dashboard (Required for Tracing)

The connection errors (`WinError 10061`) occur when the API tries to send traces to Phoenix, but the Phoenix server isn't running. You must start it first.

Open a **new terminal**, navigate to the project folder, and run:

```bash
# Install required packages if not already installed
pip install arize-phoenix openinference-instrumentation-langchain

# Start the Phoenix server
phoenix serve
```

*Keep this terminal open.* The dashboard will be available at `http://localhost:6006`.

## 2. Start the ShopNest API

Open a **second terminal**, set the environment variables, and start the API:

**For Windows PowerShell:**
```powershell
cd "c:\Dwarka\Machiene Learning\ShopNest"
$env:ENABLE_PHOENIX = "true"
$env:PHOENIX_COLLECTOR_ENDPOINT = "http://127.0.0.1:6018/v1/traces"
$env:PHOENIX_PROJECT_NAME = "shopnest-production"
python run_api.py
```

**For Windows CMD:**
```cmd
cd "c:\Dwarka\Machiene Learning\ShopNest"
set ENABLE_PHOENIX=true
set PHOENIX_COLLECTOR_ENDPOINT=http://127.0.0.1:6018/v1/traces
set PHOENIX_PROJECT_NAME=shopnest-production
python run_api.py
```

*Keep this terminal open.* The API will be available at `http://localhost:8000`.

## 3. Test the Application

Open a **third terminal** to test the API with a sample query:

**For Windows PowerShell:**
```powershell
$json = @{
    message = "What is your refund policy?"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8000/chat" `
  -Method Post `
  -ContentType "application/json" `
  -Body $json
```

**For Windows CMD/Bash:**
```bash
curl -X POST http://localhost:8000/chat ^
  -H "Content-Type: application/json" ^
  -d "{\"message\": \"What is your refund policy?\"}"
```

## 4. View Traces in Phoenix

1. Open your browser and go to `http://localhost:6006`
2. You will see the incoming traces from the ShopNest API under the `shopnest-production` project.
3. You can view the execution steps, latency, and LLM calls triggered by your chat requests.

---

## Technical Notes

*   **AttributeError Fixed:** The error `AttributeError("'NoneType' object has no attribute 'get'")` in the tracking callback has been fully patched in the code.
*   **Connection Errors Fixed:** The `ConnectionRefusedError` (port 6018) is resolved entirely by running Step 1 (`phoenix serve`) before Step 2 (`run_api.py`). The API won't crash if it can't connect, but it will keep reporting that tracing is failing if the Phoenix server isn't properly started.
