const form = document.getElementById("chatForm");
const input = document.getElementById("messageInput");
const sendBtn = document.getElementById("sendBtn");
const transcript = document.getElementById("transcript");
const status = document.getElementById("status");
const clearBtn = document.getElementById("clearBtn");

const HISTORY_KEY = "pyref-cp-conversation";
const DEFAULT_COOLDOWN_SECONDS = 4;
let cooldownUntil = 0;
let cooldownTimer = null;
let isLoading = false;

let conversation = loadConversation();

function loadConversation() {
  try {
    const saved = JSON.parse(sessionStorage.getItem(HISTORY_KEY) || "[]");
    return Array.isArray(saved)
      ? saved.filter((message) =>
          (message.role === "user" || message.role === "assistant") &&
          typeof message.content === "string" && message.content.trim()
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
  for (const message of conversation) {
    addMessage(message.content, message.role === "user" ? "user" : "bot");
  }
}

// Auto-grow textarea height
input.addEventListener("input", () => {
  input.style.height = "auto";
  input.style.height = Math.min(input.scrollHeight, 140) + "px";
});

// Enter to submit, Shift+Enter for new line
input.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    form.requestSubmit();
  }
});

// Clear conversation
if (clearBtn) {
  clearBtn.addEventListener("click", () => {
    if (confirm("Clear chat history?")) {
      conversation = [];
      sessionStorage.removeItem(HISTORY_KEY);
      // Clear transcript except first default message
      const botInitial = transcript.querySelector(".msg--bot");
      transcript.innerHTML = "";
      if (botInitial) transcript.appendChild(botInitial);
    }
  });
}

function renderFormattedContent(text) {
  if (window.marked) {
    try {
      return window.marked.parse(text, { breaks: true, gfm: true });
    } catch {
      // Fallback if parsing fails
    }
  }
  // Basic fallback escaping + line break
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML.replace(/\n/g, "<br>");
}

function enhanceCodeBlocks(container) {
  const preElements = container.querySelectorAll("pre");
  preElements.forEach((pre) => {
    if (pre.parentNode.classList.contains("code-wrapper")) return;

    const wrapper = document.createElement("div");
    wrapper.className = "code-wrapper";

    const header = document.createElement("div");
    header.className = "code-wrapper__header";

    const langSpan = document.createElement("span");
    const code = pre.querySelector("code");
    const langClass = code ? Array.from(code.classList).find(c => c.startsWith("language-")) : "";
    langSpan.textContent = langClass ? langClass.replace("language-", "").toUpperCase() : "PYTHON";

    const copyBtn = document.createElement("button");
    copyBtn.className = "code-wrapper__copy";
    copyBtn.textContent = "Copy Snippet";

    copyBtn.addEventListener("click", () => {
      const codeText = code ? code.innerText : pre.innerText;
      navigator.clipboard.writeText(codeText).then(() => {
        copyBtn.textContent = "Copied!";
        setTimeout(() => { copyBtn.textContent = "Copy Snippet"; }, 2000);
      }).catch(() => {
        copyBtn.textContent = "Failed";
      });
    });

    header.appendChild(langSpan);
    header.appendChild(copyBtn);

    pre.parentNode.insertBefore(wrapper, pre);
    wrapper.appendChild(header);
    wrapper.appendChild(pre);
  });
}

function addMessage(text, role) {
  const msg = document.createElement("div");
  msg.className = `msg msg--${role}`;

  const header = document.createElement("div");
  header.className = "msg__header";

  const label = document.createElement("span");
  label.className = "msg__label";
  label.textContent = role === "user" ? "You" : role === "error" ? "System Error" : "PyRef";

  const time = document.createElement("span");
  time.className = "msg__time";
  const now = new Date();
  time.textContent = `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}`;

  header.appendChild(label);
  header.appendChild(time);

  const contentDiv = document.createElement("div");
  contentDiv.className = "msg__content";

  if (role === "user") {
    const p = document.createElement("p");
    p.textContent = text;
    contentDiv.appendChild(p);
  } else {
    contentDiv.innerHTML = renderFormattedContent(text);
    enhanceCodeBlocks(contentDiv);
  }

  msg.appendChild(header);
  msg.appendChild(contentDiv);
  transcript.appendChild(msg);
  transcript.scrollTop = transcript.scrollHeight;
}

function setLoading(loading) {
  isLoading = loading;
  sendBtn.disabled = loading || getCooldownRemaining() > 0;
  input.disabled = loading;
  status.textContent = loading ? "PyRef is searching reference docs..." : "";
  status.classList.toggle("visible", Boolean(status.textContent));
}

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
    status.textContent = `Next query in ${remaining}s`;
    status.classList.add("visible");
  }
}

function startCooldown(seconds = DEFAULT_COOLDOWN_SECONDS) {
  cooldownUntil = Date.now() + Math.max(1, seconds) * 1000;
  clearInterval(cooldownTimer);
  cooldownTimer = setInterval(updateCooldown, 250);
  updateCooldown();
}

restoreConversation();

form.addEventListener("submit", async (e) => {
  e.preventDefault();

  if (isLoading || getCooldownRemaining() > 0) {
    updateCooldown();
    return;
  }

  const message = input.value.trim();
  if (!message) return;

  addMessage(message, "user");
  const history = conversation.slice();
  conversation.push({ role: "user", content: message });
  saveConversation();
  input.value = "";
  input.style.height = "auto";
  startCooldown(1);
  setLoading(true);

  try {
    const res = await fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, history }),
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

