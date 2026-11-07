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
    addMessage(message.content, message.role === "user" ? "user" : "bot", message.complexity || null);
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

// ---- Big-O Complexity Graph Visualizer ----

function classifyBigO(str) {
  if (!str) return "O(1)";
  const s = str.toLowerCase().replace(/\s+/g, "");
  if (s.includes("n!") || s.includes("factorial")) return "O(n!)";
  if (s.includes("2^n") || s.includes("2^") || s.includes("exponential")) return "O(2^n)";
  if (s.includes("n^3") || s.includes("cubic")) return "O(n^3)";
  if (s.includes("n^2") || s.includes("n2") || s.includes("quadratic")) return "O(n^2)";
  if (s.includes("nlogn") || s.includes("n*logn") || s.includes("n_log_n") || s.includes("linearithmic")) return "O(n log n)";
  if (s.includes("sqrt") || s.includes("√")) return "O(sqrt n)";
  if (s.includes("logn") || s.includes("log(n)") || s.includes("log_n") || s.includes("logarithmic")) return "O(log n)";
  if (s.includes("o(n)") || s.includes("linear") || s.match(/\bo\(?n\)?\b/)) return "O(n)";
  if (s.includes("o(1)") || s.includes("constant")) return "O(1)";
  return "O(log n)";
}

function generateBigOGraphSVG(targetTime, targetSpace) {
  const normTime = classifyBigO(targetTime);
  const normSpace = classifyBigO(targetSpace);

  const curves = [
    { id: "O(1)", label: "O(1)", d: "M 60,215 L 450,215", lx: 455, ly: 219 },
    { id: "O(log n)", label: "O(log n)", d: "M 60,225 Q 220,198 450,182", lx: 455, ly: 186 },
    { id: "O(n)", label: "O(n)", d: "M 60,225 L 410,55", lx: 415, ly: 52 },
    { id: "O(n log n)", label: "O(n log n)", d: "M 60,225 Q 255,180 330,40", lx: 335, ly: 36 },
    { id: "O(n^2)", label: "O(n²)", d: "M 60,225 Q 195,205 250,35", lx: 255, ly: 30 },
    { id: "O(n^3)", label: "O(n³)", d: "M 60,225 Q 155,212 195,32", lx: 200, ly: 26 },
    { id: "O(2^n)", label: "O(2ⁿ)", d: "M 60,225 Q 125,215 150,30", lx: 155, ly: 23 },
    { id: "O(n!)", label: "O(n!)", d: "M 60,225 Q 100,218 118,28", lx: 122, ly: 20 }
  ];

  let bgPaths = "";
  let bgLabels = "";
  let activePaths = "";
  let activeLabels = "";

  curves.forEach(c => {
    const isTarget = (c.id === normTime || (c.id === normSpace && normSpace !== normTime));

    if (!isTarget) {
      // Light grey curve for all other non-matching complexities
      bgPaths += `<path d="${c.d}" fill="none" stroke="#CBD5E1" stroke-width="1.8" stroke-linecap="round" />`;
      bgLabels += `<text x="${c.lx}" y="${c.ly}" fill="#94A3B8" font-family="'JetBrains Mono', Consolas, monospace" font-size="10.5" font-weight="500">${c.id}</text>`;
    } else {
      // Dark bold curve for this algorithm's complexity
      activePaths += `
        <path d="${c.d}" fill="none" stroke="#0F172A" stroke-width="4.2" stroke-linecap="round" />
      `;
      // End highlight point
      const lastCoord = c.d.split(" ").pop().split(",");
      const ex = parseFloat(lastCoord[0]);
      const ey = parseFloat(lastCoord[1]);
      activePaths += `<circle cx="${ex}" cy="${ey}" r="5" fill="#0F172A" stroke="#FFFFFF" stroke-width="2" />`;

      // Dark badge
      const badgeW = 95;
      activeLabels += `
        <g transform="translate(${Math.min(c.lx, 425)}, ${c.ly - 13})">
          <rect width="${badgeW}" height="19" rx="4" fill="#0F172A" filter="drop-shadow(0 2px 4px rgba(0,0,0,0.2))" />
          <text x="${badgeW / 2}" y="13" fill="#F8FAFC" font-family="'JetBrains Mono', Consolas, monospace" font-size="10" font-weight="700" text-anchor="middle">★ ${c.id}</text>
        </g>
      `;
    }
  });

  return `
    <div class="bigo-graph-container">
      <svg class="bigo-graph-svg" viewBox="0 0 540 260" width="100%" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <marker id="arrowX" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
            <path d="M 0 1 L 10 5 L 0 9 z" fill="#0F172A" />
          </marker>
          <marker id="arrowY" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
            <path d="M 0 1 L 10 5 L 0 9 z" fill="#0F172A" />
          </marker>
        </defs>

        <!-- Crisp white background card -->
        <rect x="0" y="0" width="540" height="260" rx="6" fill="#FFFFFF" />

        <!-- Graph title & subtitle -->
        <text x="60" y="18" fill="#475569" font-family="'Plus Jakarta Sans', sans-serif" font-size="10" font-weight="700" letter-spacing="0.04em">BIG-O COMPLEXITY GRAPH</text>
        <text x="480" y="18" fill="#64748B" font-family="'JetBrains Mono', monospace" font-size="9" text-anchor="end">DARK = THIS ALGORITHM · LIGHT GREY = OTHERS</text>

        <!-- Subtle horizontal grid lines -->
        <line x1="60" y1="180" x2="475" y2="180" stroke="#F1F5F9" stroke-width="1" stroke-dasharray="3,3" />
        <line x1="60" y1="130" x2="475" y2="130" stroke="#F1F5F9" stroke-width="1" stroke-dasharray="3,3" />
        <line x1="60" y1="80" x2="475" y2="80" stroke="#F1F5F9" stroke-width="1" stroke-dasharray="3,3" />

        <!-- All light grey background curves -->
        ${bgPaths}
        ${bgLabels}

        <!-- Active dark curves -->
        ${activePaths}
        ${activeLabels}

        <!-- Y Axis -->
        <line x1="60" y1="225" x2="60" y2="28" stroke="#0F172A" stroke-width="2" marker-end="url(#arrowY)" />
        <text x="68" y="32" fill="#0F172A" font-family="'JetBrains Mono', monospace" font-size="10.5" font-weight="700">Time ↑</text>

        <!-- X Axis -->
        <line x1="60" y1="225" x2="490" y2="225" stroke="#0F172A" stroke-width="2" marker-end="url(#arrowX)" />
        <text x="395" y="244" fill="#0F172A" font-family="'JetBrains Mono', monospace" font-size="10.5" font-weight="700">Input Size (N) →</text>
      </svg>
    </div>
  `;
}

// ---- Complexity Card Renderer ----

function renderComplexityCard(container, complexity) {
  if (!complexity || !complexity.time) return;

  const card = document.createElement("div");
  card.className = "complexity-card";

  const header = document.createElement("div");
  header.className = "complexity-card__header";

  const titleRow = document.createElement("div");
  titleRow.className = "complexity-card__title";
  titleRow.innerHTML = `
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
      <circle cx="12" cy="12" r="10"></circle>
      <polyline points="12 6 12 12 16 14"></polyline>
    </svg>
    <span>VISUAL TIME & SPACE COMPLEXITY</span>
  `;

  const safeBadge = document.createElement("span");
  safeBadge.className = "complexity-card__safe";
  safeBadge.textContent = complexity.safe_n ? `Safe: ${complexity.safe_n}` : "Contest Safe";

  header.appendChild(titleRow);
  header.appendChild(safeBadge);

  // Big-O visual graph form (Dark for this algo, light grey for others)
  const graphHtml = generateBigOGraphSVG(complexity.time, complexity.space);

  const grid = document.createElement("div");
  grid.className = "complexity-card__grid";

  const timeMetric = document.createElement("div");
  timeMetric.className = "complexity-metric";
  timeMetric.innerHTML = `
    <span class="complexity-metric__label">TIME COMPLEXITY</span>
    <span class="complexity-metric__value">${complexity.time}</span>
  `;

  const spaceMetric = document.createElement("div");
  spaceMetric.className = "complexity-metric";
  spaceMetric.innerHTML = `
    <span class="complexity-metric__label">AUXILIARY SPACE</span>
    <span class="complexity-metric__value">${complexity.space}</span>
  `;

  grid.appendChild(timeMetric);
  grid.appendChild(spaceMetric);

  card.appendChild(header);
  card.insertAdjacentHTML("beforeend", graphHtml);
  card.appendChild(grid);

  if (complexity.pitfall) {
    const pitfall = document.createElement("div");
    pitfall.className = "complexity-card__pitfall";
    pitfall.innerHTML = `<strong>CP TLE Caution:</strong> ${complexity.pitfall}`;
    card.appendChild(pitfall);
  }

  container.appendChild(card);
}

// ---- Add messages to DOM ----

function addMessage(text, role, complexity = null) {
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

    if (complexity) {
      renderComplexityCard(card, complexity);
    }

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
      addMessage(data.response, "bot", data.complexity || null);
      conversation.push({
        role: "assistant",
        content: data.response,
        complexity: data.complexity || null,
      });
      saveConversation();
    }
  } catch (err) {
    addMessage("Couldn't reach the backend server. Verify connection.", "error");
  } finally {
    setLoading(false);
    input.focus();
  }
});
