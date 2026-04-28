const form = document.getElementById("chat-form");
const messageInput = document.getElementById("message");
const chatLog = document.getElementById("chat-log");
const sendBtn = document.getElementById("send-btn");
const sessionValue = document.getElementById("session-id");
const latencyValue = document.getElementById("latency");
const telemetryOutput = document.getElementById("telemetry-output");

let sessionId = localStorage.getItem("shopnest_session_id") || null;
if (sessionId) {
  sessionValue.textContent = sessionId;
}

function appendMessage(role, text) {
  const item = document.createElement("div");
  item.className = `message ${role}`;
  item.textContent = text;
  chatLog.appendChild(item);
  chatLog.scrollTop = chatLog.scrollHeight;
}

async function sendMessage(message) {
  const payload = { message, session_id: sessionId };

  const response = await fetch("/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const errText = await response.text();
    throw new Error(errText || "Request failed");
  }

  return response.json();
}

messageInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    form.requestSubmit();
  }
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const message = messageInput.value.trim();
  if (!message) return;

  appendMessage("user", message);
  messageInput.value = "";
  sendBtn.disabled = true;

  try {
    const data = await sendMessage(message);
    sessionId = data.session_id;
    localStorage.setItem("shopnest_session_id", sessionId);

    sessionValue.textContent = sessionId;
    latencyValue.textContent = `${data.latency_ms} ms`;
    telemetryOutput.textContent = JSON.stringify(data.telemetry, null, 2);

    appendMessage("assistant", data.response);
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    appendMessage("error", `Error: ${message}`);
  } finally {
    sendBtn.disabled = false;
    messageInput.focus();
  }
});

appendMessage(
  "assistant",
  "Hello! I can answer policy questions and perform actions like order status, cancellation, refunds, and ticket creation."
);
