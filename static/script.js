// ============================================================
// PyRef — Clean Developer Chatbot UI (v3.0)
// ============================================================

const form = document.getElementById("chatForm");
const input = document.getElementById("messageInput");
const sendBtn = document.getElementById("sendBtn");
const transcript = document.getElementById("transcript");
const status = document.getElementById("status");
const clearBtn = document.getElementById("clearBtn");
const charCounter = document.getElementById("charCounter");
const welcomeMessage = document.getElementById("welcomeMessage");

// ---- Session Management ----

const HISTORY_KEY = "pyref-cp-conversation";
const SESSION_KEY = "pyref-session-id";

function newSessionId() {
  return (window.crypto && crypto.randomUUID)
    ? crypto.randomUUID()
    : Math.random().toString(36).slice(2) + Date.now().toString(36);
}

let sessionId = sessionStorage.getItem(SESSION_KEY);
if (!sessionId) {
  sessionId = newSessionId();
  sessionStorage.setItem(SESSION_KEY, sessionId);
}

// ---- State ----

const DEFAULT_COOLDOWN_SECONDS = 4;
let cooldownUntil = 0;
let cooldownTimer = null;
let isLoading = false;

let conversation = loadConversation();

// ---- Persistence ----

function loadConversation() {
  try {
    const saved = JSON.parse(sessionStorage.getItem(HISTORY_KEY) || "[]");
    return Array.isArray(saved)
      ? saved.filter((m) =>
          (m.role === "user" || m.role === "assistant") &&
          typeof m.content === "string" && m.content.trim()
        )
      : [];
  } catch {
    return [];
  }
}

function saveConversation() {
  sessionStorage.setItem(HISTORY_KEY, JSON.stringify(conversation));
}

function restoreConversation() {
  if (conversation.length > 0 && welcomeMessage) {
    welcomeMessage.style.display = "none";
  }
  for (const message of conversation) {
    addMessage(message.content, message.role === "user" ? "user" : "bot");
  }
}

// ---- Char counter ----

function updateCharCounter() {
  if (charCounter) {
    const len = input.value.length;
    charCounter.textContent = `${len}/400`;
    charCounter.classList.toggle("limit", len >= 380);
  }
}

// ---- Auto-grow textarea ----

input.addEventListener("input", () => {
  input.style.height = "auto";
  input.style.height = Math.min(input.scrollHeight, 130) + "px";
  updateCharCounter();
});

// Enter to submit, Shift+Enter for newline
input.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    form.requestSubmit();
  }
});

// ---- Clear chat ----

if (clearBtn) {
  clearBtn.addEventListener("click", () => {
    if (confirm("Clear conversation history?")) {
      conversation = [];
      sessionStorage.removeItem(HISTORY_KEY);
      sessionId = newSessionId();
      sessionStorage.setItem(SESSION_KEY, sessionId);

      transcript.innerHTML = "";
      if (welcomeMessage) {
        welcomeMessage.style.display = "";
        transcript.appendChild(welcomeMessage);
      }
    }
  });
}

// ---- Markdown rendering ----

function renderFormattedContent(text) {
  if (window.marked) {
    try {
      return window.marked.parse(text, { breaks: true, gfm: true });
    } catch {
      // fallback
    }
  }
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML.replace(/\n/g, "<br>");
}

// ---- Code block enhancement ----

function enhanceCodeBlocks(container) {
  const preElements = container.querySelectorAll("pre");
  preElements.forEach((pre) => {
    if (pre.parentNode.classList.contains("code-wrapper")) return;

    const wrapper = document.createElement("div");
    wrapper.className = "code-wrapper";

    const header = document.createElement("div");
    header.className = "code-wrapper__header";

    const langSpan = document.createElement("span");
    langSpan.className = "code-wrapper__lang";
    const code = pre.querySelector("code");
    const langClass = code ? Array.from(code.classList).find(c => c.startsWith("language-")) : "";
    langSpan.textContent = langClass ? langClass.replace("language-", "").toUpperCase() : "PYTHON";

    const copyBtn = document.createElement("button");
    copyBtn.className = "code-wrapper__copy";
    copyBtn.innerHTML = `
      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
        <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
      </svg>
      <span>Copy</span>
    `;

    copyBtn.addEventListener("click", () => {
      const codeText = code ? code.innerText : pre.innerText;
      navigator.clipboard.writeText(codeText).then(() => {
        copyBtn.querySelector("span").textContent = "Copied ✓";
        setTimeout(() => { copyBtn.querySelector("span").textContent = "Copy"; }, 2000);
      }).catch(() => {
        copyBtn.querySelector("span").textContent = "Failed";
      });
    });

    header.appendChild(langSpan);
    header.appendChild(copyBtn);

    pre.parentNode.insertBefore(wrapper, pre);
    wrapper.appendChild(header);
    wrapper.appendChild(pre);
  });
}

// ---- Add messages to DOM ----

function addMessage(text, role) {
  if (welcomeMessage && welcomeMessage.style.display !== "none") {
    welcomeMessage.style.display = "none";
  }

  const now = new Date();
  const timeStr = `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}`;

  const row = document.createElement("div");

  if (role === "user") {
    row.className = "message-row message-row--user";
    const bubble = document.createElement("div");
    bubble.className = "user-bubble";

    const meta = document.createElement("div");
    meta.className = "user-bubble__meta";
    meta.innerHTML = `<span>YOU</span><span>${timeStr}</span>`;

    const body = document.createElement("div");
    body.className = "user-bubble__text";
    body.textContent = text;

    bubble.appendChild(meta);
    bubble.appendChild(body);
    row.appendChild(bubble);

  } else if (role === "error") {
    row.className = "message-row message-row--error";
    const card = document.createElement("div");
    card.className = "error-card";
    card.textContent = text;
    row.appendChild(card);

  } else {
    // Bot message
    row.className = "message-row message-row--bot";
    const card = document.createElement("div");
    card.className = "bot-card";

    const meta = document.createElement("div");
    meta.className = "bot-card__meta";
    meta.innerHTML = `
      <span class="meta-tag">PyRef</span>
      <span>Official Reference</span>
      <span class="meta-time">${timeStr}</span>
    `;

    const content = document.createElement("div");
    content.className = "bot-card__content";
    content.innerHTML = renderFormattedContent(text);
    enhanceCodeBlocks(content);

    card.appendChild(meta);
    card.appendChild(content);
    row.appendChild(card);
  }

  transcript.appendChild(row);
  transcript.scrollTop = transcript.scrollHeight;
}

// ---- Loading state ----

function setLoading(loading) {
  isLoading = loading;
  sendBtn.disabled = loading || getCooldownRemaining() > 0;
  input.disabled = loading;

  if (loading) {
    status.textContent = "⚡ Fetching official reference docs & generating response...";
    status.classList.add("visible");
  } else if (getCooldownRemaining() <= 0) {
    status.textContent = "";
    status.classList.remove("visible");
  }
}

// ---- Cooldown ----

function getCooldownRemaining() {
  return Math.max(0, Math.ceil((cooldownUntil - Date.now()) / 1000));
}

function updateCooldown() {
  const remaining = getCooldownRemaining();
  if (remaining === 0) {
    clearInterval(cooldownTimer);
    cooldownTimer = null;
    if (!isLoading) {
      status.textContent = "";
      status.classList.remove("visible");
    }
    sendBtn.disabled = isLoading;
    return;
  }

  sendBtn.disabled = true;
  if (!isLoading) {
    status.textContent = `Contest cooldown: next query in ${remaining}s`;
    status.classList.add("visible");
  }
}

function startCooldown(seconds = DEFAULT_COOLDOWN_SECONDS) {
  cooldownUntil = Date.now() + Math.max(1, seconds) * 1000;
  clearInterval(cooldownTimer);
  cooldownTimer = setInterval(updateCooldown, 250);
  updateCooldown();
}

// ---- Initialize ----

restoreConversation();
updateCharCounter();

// ---- Form Submit Handler ----

form.addEventListener("submit", async (e) => {
  e.preventDefault();

  if (isLoading || getCooldownRemaining() > 0) {
    updateCooldown();
    return;
  }

  const message = input.value.trim();
  if (!message) return;

  addMessage(message, "user");
  conversation.push({ role: "user", content: message });
  saveConversation();
  input.value = "";
  input.style.height = "auto";
  updateCharCounter();
  startCooldown(1);
  setLoading(true);

  try {
    const res = await fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, session_id: sessionId }),
    });

    const data = await res.json();

    if (!res.ok) {
      if (res.status === 429) {
        const retryAfter = Number.parseInt(res.headers.get("Retry-After"), 10);
        startCooldown(Number.isFinite(retryAfter) ? retryAfter : DEFAULT_COOLDOWN_SECONDS);
      }
      addMessage(data.error || "Something went wrong. Please try again.", "error");
    } else {
      addMessage(data.response, "bot");
      conversation.push({ role: "assistant", content: data.response });
      saveConversation();
    }
  } catch (err) {
    addMessage("Couldn't reach the backend server. Verify connection.", "error");
  } finally {
    setLoading(false);
    input.focus();
  }
});
