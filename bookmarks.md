# PyRef — Bookmarks / Pinned Answers Implementation Plan

## What We Are Building

A **Pin button** on every bot response that saves the Q&A pair to a persistent sidebar.
Pinned answers survive page refresh (stored in `localStorage`) and can be removed individually or all at once.

**No backend changes at all.** This is 100% frontend work across 3 files:
- `static/index.html`
- `static/script.js`
- `static/style.css`

---

## How It Will Look (UI Flow)

```
┌─────────────────────────────────────────────────┐
│  PyRef  STDLIB v3.12          [Pins (2)]  [Clear]│  ← header
├─────────────────────────────────────────────────┤
│                                                  │
│  YOU: how does heapq.heappush work?              │
│                                                  │
│  PyRef: heapq.heappush(heap, item) pushes...     │
│         [📌 Pin]  [Copy]                         │  ← pin button on bot card
│                                                  │
└─────────────────────────────────────────────────┘

When "Pins (2)" is clicked → sidebar slides open from the right:
┌──────────────────────┐
│  📌 PINNED REFERENCE │
│  ─────────────────── │
│  Q: heapq.heappush   │
│  A: heapq.heappush...│
│           [✕ Remove] │
│  ─────────────────── │
│  Q: bisect_left      │
│  A: bisect.bisect...  │
│           [✕ Remove] │
│  ─────────────────── │
│       [Clear All]    │
└──────────────────────┘
```

---

## Files That Change

| File | What Changes |
|---|---|
| `static/index.html` | Add sidebar HTML + "Pins (N)" button in header |
| `static/script.js` | Pin logic, localStorage read/write, sidebar render |
| `static/style.css` | Sidebar styles, pin button styles, overlay |

---

## Step-by-Step Implementation

---

### Step 1 — Add the Sidebar HTML to `index.html`

**Where:** Inside `<div class="app-shell">`, right after the closing `</main>` tag and before `<div class="status-bar">`.

Add this block:

```html
<!-- Pins Sidebar Overlay -->
<div class="pins-overlay" id="pinsOverlay" aria-hidden="true"></div>

<!-- Pins Sidebar Panel -->
<aside class="pins-sidebar" id="pinsSidebar" aria-label="Pinned answers">
  <div class="pins-sidebar__header">
    <div class="pins-sidebar__title">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
        <path d="M17 4a2 2 0 0 0-2-2H9a2 2 0 0 0-2 2v1H5v2h1v10a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2V7h1V5h-2V4zM9 4h6v1H9V4zm7 3v10H8V7h8z"/>
      </svg>
      <span>PINNED REFERENCE</span>
    </div>
    <button class="pins-sidebar__close" id="pinsClose" title="Close">✕</button>
  </div>
  <div class="pins-sidebar__list" id="pinsList">
    <!-- Pinned items rendered here by JS -->
  </div>
  <div class="pins-sidebar__footer">
    <button class="pins-clear-all" id="pinsClearAll">Clear All Pins</button>
  </div>
</aside>
```

**Also in the header** (`<div class="header-actions">`), add a Pins toggle button **before** the existing Clear button:

```html
<button class="action-btn" id="pinsToggleBtn" title="View pinned answers">
  <svg width="13" height="13" viewBox="0 0 24 24" fill="currentColor">
    <path d="M17 4a2 2 0 0 0-2-2H9a2 2 0 0 0-2 2v1H5v2h1v10a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2V7h1V5h-2V4z"/>
  </svg>
  <span id="pinsBtnLabel">Pins</span>
</button>
```

---

### Step 2 — Add Pin Storage Logic to `script.js`

**Where:** At the top of the file, alongside the existing `HISTORY_KEY` and `SESSION_KEY` constants.

#### 2a — Storage Key and Load/Save Helpers

```js
// ---- Pins Storage (localStorage — survives page refresh) ----

const PINS_KEY = "pyref-pins";

function loadPins() {
  try {
    const saved = JSON.parse(localStorage.getItem(PINS_KEY) || "[]");
    return Array.isArray(saved) ? saved : [];
  } catch {
    return [];
  }
}

function savePins(pins) {
  localStorage.setItem(PINS_KEY, JSON.stringify(pins));
}

// In-memory pins array — loaded once on page start
let pins = loadPins();
```

**Key design decision:** Use `localStorage` (not `sessionStorage`) so pins persist across sessions. The existing `conversation` history uses `sessionStorage` and dies when the tab closes — pins are meant to be permanent notes.

---

### Step 3 — Add the Pin Button to Bot Messages

**Where:** Inside the `addMessage()` function in `script.js`, in the `else` branch that builds bot cards.

After the `meta` div is built (around where `meta.innerHTML` is set), add a Pin button to the meta row:

```js
// Pin button — add after the existing meta content
const pinBtn = document.createElement("button");
pinBtn.className = "pin-btn";
pinBtn.title = "Pin this answer";
pinBtn.innerHTML = `
  <svg width="11" height="11" viewBox="0 0 24 24" fill="currentColor">
    <path d="M17 4a2 2 0 0 0-2-2H9a2 2 0 0 0-2 2v1H5v2h1v10a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2V7h1V5h-2V4z"/>
  </svg>
  <span>Pin</span>
`;

// Find the user's question for this bot reply
// (the last user message in the conversation array)
const questionText = conversation.length > 0
  ? conversation[conversation.length - 1]?.content || ""
  : "";

pinBtn.addEventListener("click", () => {
  addPin(questionText, text, complexity);
  pinBtn.querySelector("span").textContent = "Pinned ✓";
  pinBtn.disabled = true;
});

meta.appendChild(pinBtn);
```

**Why we grab `questionText` from the `conversation` array:** The bot card is created right after the user message is pushed to `conversation` (line ~729 in the current script.js), so `conversation[conversation.length - 1]` is always the user's question that triggered this response.

---

### Step 4 — Add `addPin()` Function

**Where:** After the `savePins()` helper, add:

```js
function addPin(question, answer, complexity) {
  // Avoid duplicate pins of the same question
  const alreadyPinned = pins.some(p => p.question === question);
  if (alreadyPinned) return;

  const pin = {
    id: Date.now().toString(),   // unique ID for removal
    question: question.slice(0, 200),  // cap length
    answer: answer,
    complexity: complexity || null,
    pinnedAt: new Date().toISOString(),
  };

  pins.unshift(pin);  // newest pin appears at the top
  savePins(pins);
  updatePinsButton();
  renderPinsSidebar();
}

function removePin(id) {
  pins = pins.filter(p => p.id !== id);
  savePins(pins);
  updatePinsButton();
  renderPinsSidebar();
}

function clearAllPins() {
  pins = [];
  savePins(pins);
  updatePinsButton();
  renderPinsSidebar();
}
```

---

### Step 5 — Render the Sidebar

**Where:** After `clearAllPins()`, add:

```js
function renderPinsSidebar() {
  const list = document.getElementById("pinsList");
  if (!list) return;

  if (pins.length === 0) {
    list.innerHTML = `
      <div class="pins-empty">
        <p>No pins yet.</p>
        <p>Click <strong>Pin</strong> on any PyRef answer to save it here.</p>
      </div>
    `;
    return;
  }

  list.innerHTML = "";  // clear before re-render

  pins.forEach(pin => {
    const item = document.createElement("div");
    item.className = "pin-item";

    const header = document.createElement("div");
    header.className = "pin-item__header";

    const q = document.createElement("div");
    q.className = "pin-item__question";
    q.textContent = pin.question || "Pinned answer";

    const removeBtn = document.createElement("button");
    removeBtn.className = "pin-item__remove";
    removeBtn.textContent = "✕";
    removeBtn.title = "Remove pin";
    removeBtn.addEventListener("click", () => removePin(pin.id));

    header.appendChild(q);
    header.appendChild(removeBtn);

    // Render answer as markdown using existing renderFormattedContent()
    const body = document.createElement("div");
    body.className = "pin-item__answer";
    body.innerHTML = renderFormattedContent(pin.answer);
    // Re-use existing code block enhancer so Copy buttons work in sidebar too
    enhanceCodeBlocks(body);

    item.appendChild(header);
    item.appendChild(body);
    list.appendChild(item);
  });
}
```

**Note:** `renderFormattedContent()` and `enhanceCodeBlocks()` already exist in `script.js` — we re-use them directly. No new markdown library needed.

---

### Step 6 — Sidebar Toggle + Close Logic

**Where:** After `renderPinsSidebar()`, add the sidebar open/close handlers:

```js
// ---- Sidebar Open/Close ----

const pinsToggleBtn = document.getElementById("pinsToggleBtn");
const pinsSidebar   = document.getElementById("pinsSidebar");
const pinsOverlay   = document.getElementById("pinsOverlay");
const pinsClose     = document.getElementById("pinsClose");
const pinsClearAll  = document.getElementById("pinsClearAll");

function openSidebar() {
  pinsSidebar.classList.add("is-open");
  pinsOverlay.classList.add("is-visible");
  renderPinsSidebar();  // always re-render on open in case new pins were added
}

function closeSidebar() {
  pinsSidebar.classList.remove("is-open");
  pinsOverlay.classList.remove("is-visible");
}

pinsToggleBtn?.addEventListener("click", () => {
  pinsSidebar.classList.contains("is-open") ? closeSidebar() : openSidebar();
});

pinsClose?.addEventListener("click", closeSidebar);
pinsOverlay?.addEventListener("click", closeSidebar);  // click outside to close

pinsClearAll?.addEventListener("click", () => {
  if (confirm("Remove all pinned answers?")) clearAllPins();
});

// Update the "Pins (N)" button label
function updatePinsButton() {
  const label = document.getElementById("pinsBtnLabel");
  if (label) {
    label.textContent = pins.length > 0 ? `Pins (${pins.length})` : "Pins";
  }
}

// Run once on page load to show correct count from localStorage
updatePinsButton();
```

---

### Step 7 — Add CSS to `style.css`

Add these styles at the end of `style.css`:

#### Sidebar Panel

```css
/* ---- Pins Sidebar ---- */
.pins-sidebar {
  position: fixed;
  top: 0;
  right: -400px;           /* hidden off-screen by default */
  width: 380px;
  max-width: 92vw;
  height: 100vh;
  background: var(--surface, #ffffff);
  border-left: 1px solid #E2E8F0;
  box-shadow: -4px 0 24px rgba(0, 0, 0, 0.08);
  display: flex;
  flex-direction: column;
  z-index: 200;
  transition: right 0.28s cubic-bezier(0.4, 0, 0.2, 1);
}

.pins-sidebar.is-open {
  right: 0;
}

.pins-overlay {
  display: none;
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.3);
  z-index: 199;
}

.pins-overlay.is-visible {
  display: block;
}
```

#### Sidebar Header & Footer

```css
.pins-sidebar__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
  border-bottom: 1px solid #E2E8F0;
  flex-shrink: 0;
}

.pins-sidebar__title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.08em;
  color: #0F172A;
  text-transform: uppercase;
}

.pins-sidebar__close {
  background: none;
  border: none;
  cursor: pointer;
  color: #64748B;
  font-size: 14px;
  padding: 4px 6px;
  border-radius: 4px;
  transition: background 0.15s;
}

.pins-sidebar__close:hover {
  background: #F1F5F9;
  color: #0F172A;
}

.pins-sidebar__list {
  flex: 1;
  overflow-y: auto;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.pins-sidebar__footer {
  padding: 12px 16px;
  border-top: 1px solid #E2E8F0;
  flex-shrink: 0;
}

.pins-clear-all {
  width: 100%;
  padding: 8px;
  background: none;
  border: 1px solid #E2E8F0;
  border-radius: 6px;
  font-size: 12px;
  color: #64748B;
  cursor: pointer;
  transition: all 0.15s;
}

.pins-clear-all:hover {
  background: #FEF2F2;
  border-color: #FECACA;
  color: #DC2626;
}
```

#### Pin Items

```css
.pin-item {
  background: #F8FAFC;
  border: 1px solid #E2E8F0;
  border-radius: 8px;
  padding: 10px 12px;
  font-size: 13px;
}

.pin-item__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 8px;
}

.pin-item__question {
  font-weight: 600;
  font-size: 12px;
  color: #0F172A;
  line-height: 1.4;
  flex: 1;
}

.pin-item__remove {
  background: none;
  border: none;
  cursor: pointer;
  color: #94A3B8;
  font-size: 12px;
  padding: 2px 4px;
  border-radius: 3px;
  flex-shrink: 0;
  transition: color 0.15s;
}

.pin-item__remove:hover {
  color: #DC2626;
}

.pin-item__answer {
  font-size: 12.5px;
  color: #334155;
  line-height: 1.6;
  /* Limit height so very long answers don't overwhelm the sidebar */
  max-height: 200px;
  overflow-y: auto;
}
```

#### Pin Button (on bot cards)

```css
/* ---- Pin Button on bot message cards ---- */
.pin-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  background: none;
  border: 1px solid transparent;
  border-radius: 4px;
  padding: 2px 7px;
  font-size: 11px;
  font-weight: 500;
  color: #64748B;
  cursor: pointer;
  transition: all 0.15s;
}

.pin-btn:hover {
  background: #F1F5F9;
  border-color: #CBD5E1;
  color: #0F172A;
}

.pin-btn:disabled {
  color: #2563EB;
  border-color: transparent;
  cursor: default;
  background: none;
}

/* Empty state */
.pins-empty {
  text-align: center;
  padding: 40px 20px;
  color: #94A3B8;
  font-size: 13px;
  line-height: 1.8;
}
```

---

## Final Checklist Before Testing

- [ ] `index.html` — sidebar HTML added after `</main>`
- [ ] `index.html` — "Pins" button added in `header-actions`
- [ ] `script.js` — `PINS_KEY`, `loadPins()`, `savePins()` added at top
- [ ] `script.js` — Pin button added inside `addMessage()` bot branch
- [ ] `script.js` — `addPin()`, `removePin()`, `clearAllPins()` added
- [ ] `script.js` — `renderPinsSidebar()` added
- [ ] `script.js` — sidebar toggle/close listeners added
- [ ] `script.js` — `updatePinsButton()` called on page load
- [ ] `style.css` — all sidebar and pin-button CSS added at the end

---

## Testing Checklist

1. Ask PyRef a question → bot reply appears → "Pin" button is visible in the meta row.
2. Click "Pin" → button changes to "Pinned ✓" and becomes disabled.
3. Click "Pins (1)" in the header → sidebar slides in from the right.
4. The pinned Q&A appears in the sidebar with the question as the title.
5. Code blocks inside the pinned answer have working Copy buttons.
6. Click "✕" on a pin → it disappears from the sidebar.
7. Refresh the page → the pin is still in the sidebar (localStorage persists).
8. Click "Clear All" → confirm dialog → all pins removed.
9. Clicking the dark overlay closes the sidebar.
10. Pressing "Pins" button again while sidebar is open → sidebar closes.

---

## What Does NOT Change

| Component | Status |
|---|---|
| Guardrail pipeline (all 3 layers) | ✅ Untouched |
| `/chat` endpoint and session logic | ✅ Untouched |
| Groq API / MCP fetch | ✅ Untouched |
| Complexity graph and typewriter | ✅ Untouched |
| Rate limiting | ✅ Untouched |
| All test files | ✅ Untouched |

> **Safety note:** Refusal messages are never saved to the `conversation` array (enforced in `main.py` line 128–130), so they can never be pinned. Only valid reference answers can reach the Pin button.

