const form = document.getElementById("chat-form");
const messageInput = document.getElementById("message");
const chatLog = document.getElementById("chat-log");
const sendBtn = document.getElementById("send-btn");
const micBtn = document.getElementById("mic-btn");
const sessionValue = document.getElementById("session-id");
const latencyValue = document.getElementById("latency");
const telemetryOutput = document.getElementById("telemetry-output");

let sessionId = localStorage.getItem("shopnest_session_id") || null;
if (sessionId) {
  sessionValue.textContent = sessionId;
}

let mediaRecorder;
let audioChunks = [];
let isRecording = false;
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

// Voice handling
micBtn.addEventListener("pointerdown", async (e) => {
  e.preventDefault(); // prevent text selection
  if (isRecording) return;
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    mediaRecorder = new MediaRecorder(stream);
    audioChunks = [];
    
    mediaRecorder.addEventListener("dataavailable", event => {
      audioChunks.push(event.data);
    });

    mediaRecorder.addEventListener("stop", async () => {
      const audioBlob = new Blob(audioChunks, { type: "audio/wav" });
      sendVoice(audioBlob);
    });
    
    mediaRecorder.start();
    isRecording = true;
    micBtn.classList.add("recording"); // User feedback indicator
  } catch (err) {
    appendMessage("error", "Microphone access denied or error: " + err.message);
  }
});

micBtn.addEventListener("pointerup", stopRecording);
micBtn.addEventListener("pointerleave", stopRecording);

function stopRecording(e) {
  if (e) e.preventDefault();
  if (!isRecording || !mediaRecorder) return;
  mediaRecorder.stop();
  mediaRecorder.stream.getTracks().forEach(t => t.stop());
  isRecording = false;
  micBtn.classList.remove("recording");
}

async function sendVoice(audioBlob) {
  appendMessage("user", "🎤 (Voice Message)");
  micBtn.disabled = true;
  messageInput.disabled = true;

  try {
    const formData = new FormData();
    formData.append("file", audioBlob, "recording.wav");
    
    const sessUrl = sessionId ? `?session_id=${encodeURIComponent(sessionId)}` : "";
    const response = await fetch(`/voice${sessUrl}`, {
      method: "POST",
      body: formData
    });

    if (!response.ok) {
      throw new Error(await response.text());
    }

    // Play the audio
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const audio = new Audio(url);
    
    // We append a generic text message since STT transcrip/agent result isn't passed back yet in JSON format,
    // the endpoint simply returns audio file.
    appendMessage("assistant", "🔊 (Audio response playing...)");
    audio.play();

  } catch (error) {
    appendMessage("error", `Voice Error: ${error.message || String(error)}`);
  } finally {
    micBtn.disabled = false;
    messageInput.disabled = false;
  }
}


appendMessage(
  "assistant",
  "Hello! I can answer policy questions and perform actions like order status, cancellation, refunds, and ticket creation."
);
