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
    addMessage(message.content, message.role === "user" ? "user" : "bot", message.complexity || null, false);
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

// ---- In-Browser Python Sandbox (Pyodide Wasm) ----

let pyodideInstance = null;
let pyodideReadyPromise = null;

async function getPyodide() {
  if (pyodideInstance) return pyodideInstance;

  if (!pyodideReadyPromise) {
    pyodideReadyPromise = (async () => {
      if (!window.loadPyodide) {
        await new Promise((resolve, reject) => {
          const script = document.createElement("script");
          script.src = "https://cdn.jsdelivr.net/pyodide/v0.26.4/full/pyodide.js";
          script.onload = resolve;
          script.onerror = () => reject(new Error("Failed to load Pyodide WebAssembly engine. Check network connection."));
          document.head.appendChild(script);
        });
      }

      const pyodide = await window.loadPyodide({
        indexURL: "https://cdn.jsdelivr.net/pyodide/v0.26.4/full/"
      });

      return pyodide;
    })();
  }

  pyodideInstance = await pyodideReadyPromise;
  return pyodideInstance;
}

async function executePythonInWasm(pyodide, userCode) {
  const harness = `
import sys
import io
import time
import traceback

__out = io.StringIO()
__err = io.StringIO()
__old_stdout = sys.stdout
__old_stderr = sys.stderr
sys.stdout = __out
sys.stderr = __err

__start = time.perf_counter()
__error = None

try:
    exec(${JSON.stringify(userCode)}, globals())
except Exception:
    __error = traceback.format_exc()
finally:
    sys.stdout = __old_stdout
    sys.stderr = __old_stderr
    __duration = time.perf_counter() - __start

{
    "stdout": __out.getvalue(),
    "stderr": __err.getvalue(),
    "error": __error,
    "duration": round(__duration, 4)
}
`;

  const resultProxy = await pyodide.runPythonAsync(harness);
  const result = resultProxy.toJs({ dict_converter: Object.fromEntries });
  resultProxy.destroy();
  return result;
}

async function handleRunCode(preElement, runBtn, terminal) {
  const code = preElement.querySelector("code")?.innerText || preElement.innerText;
  const terminalBody = terminal.querySelector(".mini-terminal__body code");
  const terminalTime = terminal.querySelector(".mini-terminal__time");
  const runBtnText = runBtn.querySelector("span");

  terminal.style.display = "block";
  terminalBody.textContent = ">>> Initializing Python (Wasm) runtime...";
  terminalBody.className = "output-running";
  terminalTime.textContent = "";

  runBtn.disabled = true;
  runBtnText.textContent = "Running...";

  try {
    const pyodide = await getPyodide();
    terminalBody.textContent = ">>> Executing snippet...";

    const result = await executePythonInWasm(pyodide, code);

    terminalTime.textContent = `[${result.duration}s]`;

    if (result.error) {
      terminalBody.textContent = result.error;
      terminalBody.className = "output-error";
    } else {
      const output = (result.stdout || "").trim() || "(Code executed cleanly with no stdout output)";
      terminalBody.textContent = output;
      terminalBody.className = "output-success";
    }
  } catch (err) {
    terminalBody.textContent = `Execution Error: ${err.message}`;
    terminalBody.className = "output-error";
  } finally {
    runBtn.disabled = false;
    runBtnText.textContent = "Run";
  }
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

    const actions = document.createElement("div");
    actions.className = "code-wrapper__actions";

    // Run Button
    const runBtn = document.createElement("button");
    runBtn.className = "code-wrapper__btn code-wrapper__run";
    runBtn.innerHTML = `
      <svg width="11" height="11" viewBox="0 0 24 24" fill="currentColor">
        <polygon points="5 3 19 12 5 21 5 3"></polygon>
      </svg>
      <span>Run</span>
    `;

    // Copy Button
    const copyBtn = document.createElement("button");
    copyBtn.className = "code-wrapper__btn code-wrapper__copy";
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

    actions.appendChild(runBtn);
    actions.appendChild(copyBtn);
    header.appendChild(langSpan);
    header.appendChild(actions);

    // Terminal Output Drawer (Initially Hidden)
    const terminal = document.createElement("div");
    terminal.className = "mini-terminal";
    terminal.style.display = "none";
    terminal.innerHTML = `
      <div class="mini-terminal__header">
        <span class="mini-terminal__title">
          <span class="terminal-dot"></span>
          TERMINAL OUTPUT
        </span>
        <div class="mini-terminal__meta">
          <span class="mini-terminal__time"></span>
          <button type="button" class="mini-terminal__close">✕ Clear</button>
        </div>
      </div>
      <pre class="mini-terminal__body"><code></code></pre>
    `;

    runBtn.addEventListener("click", () => handleRunCode(pre, runBtn, terminal));

    terminal.querySelector(".mini-terminal__close").addEventListener("click", () => {
      terminal.style.display = "none";
      terminal.querySelector(".mini-terminal__body code").textContent = "";
    });

    pre.parentNode.insertBefore(wrapper, pre);
    wrapper.appendChild(header);
    wrapper.appendChild(pre);
    wrapper.appendChild(terminal);
  });
}

// ---- Big-O Complexity Graph Visualizer ----

function classifyBigO(str) {
  if (!str) return "O(1)";
  let s = str
    .toLowerCase()
    .replace(/[\u00B2\u00b2²]/g, "^2")
    .replace(/[\u00B3\u00b3³]/g, "^3")
    .replace(/[\u207Fⁿ]/g, "^n")
    .replace(/\*\*/g, "^")
    .replace(/\s+/g, "");

  if (s.includes("n!") || s.includes("factorial")) return "O(n!)";
  if (s.includes("2^n") || s.includes("2^") || s.includes("exponential")) return "O(2^n)";
  if (s.includes("n^3") || s.includes("n3") || s.includes("cubic")) return "O(n^3)";
  if (s.includes("n^2") || s.includes("n2") || s.includes("quadratic")) return "O(n^2)";
  if (s.includes("nlogn") || s.includes("n*logn") || s.includes("n_log_n") || s.includes("linearithmic")) return "O(n log n)";
  if (s.includes("sqrt") || s.includes("√")) return "O(sqrt n)";
  if (s.includes("logn") || s.includes("log(n)") || s.includes("log_n") || s.includes("logarithmic")) return "O(log n)";
  if (s.includes("o(n)") || s.includes("linear") || s.match(/o\(?n\)?/)) return "O(n)";
  if (s.includes("o(1)") || s.includes("constant")) return "O(1)";
  return "O(log n)";
}

function generateBigOGraphSVG(targetTime, targetSpace) {
  const normTime = classifyBigO(targetTime);

  const curves = [
    { id: "O(1)", label: "O(1)", d: "M 55,225 L 450,225", lx: 456, ly: 229 },
    { id: "O(log n)", label: "O(log n)", d: "M 55,235 Q 220,210 450,192", lx: 456, ly: 196 },
    { id: "O(n)", label: "O(n)", d: "M 55,235 L 415,75", lx: 420, ly: 72 },
    { id: "O(n log n)", label: "O(n log n)", d: "M 55,235 Q 255,192 335,55", lx: 340, ly: 50 },
    { id: "O(n^2)", label: "O(n²)", d: "M 55,235 Q 195,216 255,50", lx: 260, ly: 45 },
    { id: "O(n^3)", label: "O(n³)", d: "M 55,235 Q 155,222 195,48", lx: 200, ly: 43 },
    { id: "O(2^n)", label: "O(2ⁿ)", d: "M 55,235 Q 125,224 150,45", lx: 155, ly: 40 },
    { id: "O(n!)", label: "O(n!)", d: "M 55,235 Q 100,226 118,43", lx: 122, ly: 38 }
  ];

  let bgPaths = "";
  let bgLabels = "";
  let activePaths = "";
  let activeLabels = "";

  curves.forEach(c => {
    // Only shade dark the curve belonging to this algorithm's time complexity
    const isTarget = (c.id === normTime);

    if (!isTarget) {
      // Light grey curve for all other non-matching complexities
      bgPaths += `<path d="${c.d}" fill="none" stroke="#CBD5E1" stroke-width="1.8" stroke-linecap="round" />`;
      bgLabels += `<text x="${c.lx}" y="${c.ly}" fill="#94A3B8" font-family="'JetBrains Mono', Consolas, monospace" font-size="10.5" font-weight="500">${c.label || c.id}</text>`;
    } else {
      // Dark bold curve for this algorithm's complexity
      activePaths += `
        <path d="${c.d}" fill="none" stroke="#0F172A" stroke-width="4.2" stroke-linecap="round" />
      `;
      // End highlight point
      const lastCoord = c.d.split(" ").pop().split(",");
      const ex = parseFloat(lastCoord[0]);
      const ey = parseFloat(lastCoord[1]);
      activePaths += `<circle cx="${ex}" cy="${ey}" r="5.5" fill="#0F172A" stroke="#FFFFFF" stroke-width="2" />`;

      // Dark badge
      const badgeW = 95;
      const badgeX = Math.min(Math.max(c.lx - 12, 60), 430);
      const badgeY = Math.max(c.ly - 22, 18);
      activeLabels += `
        <g transform="translate(${badgeX}, ${badgeY})">
          <rect width="${badgeW}" height="20" rx="4" fill="#0F172A" filter="drop-shadow(0 2px 4px rgba(0,0,0,0.25))" />
          <text x="${badgeW / 2}" y="14" fill="#F8FAFC" font-family="'JetBrains Mono', Consolas, monospace" font-size="10.5" font-weight="700" text-anchor="middle">★ ${c.label || c.id}</text>
        </g>
      `;
    }
  });

  return `
    <div class="bigo-graph-container">
      <svg class="bigo-graph-svg" viewBox="0 0 540 270" width="100%" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <marker id="arrowX" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
            <path d="M 0 1 L 10 5 L 0 9 z" fill="#0F172A" />
          </marker>
          <marker id="arrowY" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
            <path d="M 0 1 L 10 5 L 0 9 z" fill="#0F172A" />
          </marker>
        </defs>

        <!-- Crisp white background card -->
        <rect x="0" y="0" width="540" height="270" rx="6" fill="#FFFFFF" />

        <!-- Graph title & subtitle with clear margin -->
        <text x="35" y="20" fill="#475569" font-family="'Plus Jakarta Sans', sans-serif" font-size="10" font-weight="700" letter-spacing="0.04em">BIG-O COMPLEXITY GRAPH</text>
        <text x="505" y="20" fill="#64748B" font-family="'JetBrains Mono', monospace" font-size="8.5" text-anchor="end">DARK = THIS ALGORITHM · LIGHT GREY = OTHERS</text>

        <!-- Subtle horizontal grid lines -->
        <line x1="55" y1="190" x2="480" y2="190" stroke="#F1F5F9" stroke-width="1" stroke-dasharray="3,3" />
        <line x1="55" y1="140" x2="480" y2="140" stroke="#F1F5F9" stroke-width="1" stroke-dasharray="3,3" />
        <line x1="55" y1="90" x2="480" y2="90" stroke="#F1F5F9" stroke-width="1" stroke-dasharray="3,3" />

        <!-- All light grey background curves -->
        ${bgPaths}
        ${bgLabels}

        <!-- Active dark curves -->
        ${activePaths}
        ${activeLabels}

        <!-- Y Axis -->
        <line x1="55" y1="235" x2="55" y2="35" stroke="#0F172A" stroke-width="2" marker-end="url(#arrowY)" />
        <text x="63" y="40" fill="#0F172A" font-family="'JetBrains Mono', monospace" font-size="10.5" font-weight="700">Time ↑</text>

        <!-- X Axis -->
        <line x1="55" y1="235" x2="495" y2="235" stroke="#0F172A" stroke-width="2" marker-end="url(#arrowX)" />
        <text x="400" y="254" fill="#0F172A" font-family="'JetBrains Mono', monospace" font-size="10.5" font-weight="700">Input Size (N) →</text>
      </svg>
    </div>
  `;
}

// ---- Complexity Card Renderer ----

function renderComplexityCard(container, complexity) {
  if (!complexity || !complexity.time) return;
  const t = complexity.time.trim().toLowerCase();
  if (t === "none" || t === "n/a" || t === "not applicable" || t === "null" || t === "-" || t === "trivial") return;

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

function addMessage(text, role, complexity = null, animate = false) {
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
      ${animate ? '<span class="typewriter-indicator">⚡ Streaming</span><span class="typewriter-skip-hint">click to skip</span>' : ''}
      <span class="meta-time">${timeStr}</span>
    `;

    const content = document.createElement("div");
    content.className = "bot-card__content";

    card.appendChild(meta);
    card.appendChild(content);
    row.appendChild(card);
    transcript.appendChild(row);

    if (!animate) {
      content.innerHTML = renderFormattedContent(text);
      enhanceCodeBlocks(content);
      if (complexity) {
        renderComplexityCard(card, complexity);
      }
      transcript.scrollTop = transcript.scrollHeight;
      return;
    }

    // Interactive Typewriter streaming animation
    card.classList.add("is-typing");
    const tokens = text.match(/\S+\s*|\n+/g) || [text];
    let tokenIndex = 0;
    let isFinished = false;

    // Responsive token pacing (~1.4s - 2.2s for pleasant, realistic typewriter feel)
    const targetDurationMs = Math.min(2200, Math.max(800, tokens.length * 9));
    const tickIntervalMs = 20;
    const totalTicks = Math.max(1, targetDurationMs / tickIntervalMs);
    const tokensPerTick = Math.max(1, Math.ceil(tokens.length / totalTicks));

    const cursor = document.createElement("span");
    cursor.className = "typewriter-cursor";
    cursor.setAttribute("aria-hidden", "true");

    function attachCursorToLastNode(elem) {
      let target = elem;
      while (target.lastElementChild && !target.lastElementChild.classList.contains("typewriter-cursor")) {
        const last = target.lastElementChild;
        const tag = last.tagName.toLowerCase();
        if (tag === "svg" || tag === "table") break;
        target = last;
      }
      target.appendChild(cursor);
    }

    function finish() {
      if (isFinished) return;
      isFinished = true;
      clearInterval(intervalId);
      card.classList.remove("is-typing");
      cursor.remove();
      const indicator = meta.querySelector(".typewriter-indicator");
      if (indicator) indicator.remove();
      const skipHint = meta.querySelector(".typewriter-skip-hint");
      if (skipHint) skipHint.remove();

      content.innerHTML = renderFormattedContent(text);
      enhanceCodeBlocks(content);

      if (complexity) {
        renderComplexityCard(card, complexity);
        card.querySelector(".complexity-card")?.classList.add("fade-in");
      }
      transcript.scrollTop = transcript.scrollHeight;
    }

    // Click anywhere on the bot message to complete typewriter instantly
    card.addEventListener("click", finish, { once: true });

    const intervalId = setInterval(() => {
      if (isFinished) return;

      tokenIndex = Math.min(tokens.length, tokenIndex + tokensPerTick);
      const currentSlice = tokens.slice(0, tokenIndex).join("");
      content.innerHTML = renderFormattedContent(currentSlice);
      attachCursorToLastNode(content);

      const isNearBottom = transcript.scrollHeight - transcript.scrollTop - transcript.clientHeight < 160;
      if (isNearBottom) {
        transcript.scrollTop = transcript.scrollHeight;
      }

      if (tokenIndex >= tokens.length) {
        finish();
      }
    }, tickIntervalMs);

    return;
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
      addMessage(data.response, "bot", data.complexity || null, true);
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
