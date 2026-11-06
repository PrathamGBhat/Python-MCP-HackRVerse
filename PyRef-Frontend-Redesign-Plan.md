# PyRef Frontend Redesign: Implementation Plan

Goal: make the PyRef chat page look like a tool that a designer chose every detail for, not like a template that an AI generated in one shot.

Files touched: `static/index.html`, `static/style.css`, `static/script.js`, plus new folders `static/fonts/` and `static/vendor/`. Optional small changes in `main.py` and `groq_api.py` (Phase 9).

> **Check first.** I wrote this plan from my earlier read of the repo (a `static/` folder with HTML, CSS and JS, a 400-character textarea with a counter, a send cooldown, a 429 countdown, `sessionStorage` history, `marked.js`, and a "Copy Snippet" button on code blocks). The zip is not open in this session, so before you start, open your files and confirm the real file names and element IDs. Every snippet below uses names like `#chat` and `#input`. Rename them to match your code. **Never rename an ID that your JS already uses unless you change the JS too.**

---

## 1. The design idea (read this before any code)

**What PyRef is:** a quick lookup tool for people in a coding contest. They are in a hurry. They want one answer, one small code example, and to get back to their editor.

**What PyRef is not:** a friendly companion. It does not chat, it does not solve problems. It is a reference book that politely refuses to give answers.

So the design should feel like **a reference book page on a desk**, not like a messaging app.

**The one memorable thing:** the empty screen is a **book index**. Real Python names on the left, a dotted line, and what they do on the right. Click one and it sends the question. Everything else on the page stays quiet.

**The one small signature detail:** a **highlighter-yellow underline** on inline code, like someone marked the important word in a book with a marker. It is used only for inline code and for the hover state of the index. Nowhere else.

### The mood in one sentence
Cool grey desk with faint graph-paper lines (competitive programmers draw on grid paper), a clean paper page in the middle, navy ink, dark code panels, and a yellow highlighter.

---

## 2. What we are deliberately NOT doing (the "AI slop" list)

These are the habits that make a page look generated. Each one has a replacement.

| Common tell | Why it looks generated | What PyRef does instead |
|---|---|---|
| Cream background, serif title, terracotta accent | Very common in AI output right now | Cool grey desk, navy ink, highlighter yellow |
| Black background with one neon green accent ("hacker look") | The default idea of "developer tool" | Light page. Only the code blocks are dark |
| Chat bubbles, round avatars, sparkle icons | Every chatbot template has them | No bubbles, no avatars, no icons. Question is a heading, answer is plain text |
| Every item in an identical rounded card with the same soft shadow | The "SaaS card kit" | No cards and no shadows. Corner radius depends on the role of the element |
| Tiny ALL-CAPS letter-spaced label above every heading | Template decoration | Sentence case, no labels unless the content needs one |
| Buttons like `Send →` | Generic button style | Plain verbs: `Ask`, `Copy`, `New chat` |
| Three bouncing dots while loading | The default loading style | Text "Looking it up" with a blinking caret |
| Every section fades and slides up on load | Motion with no purpose | No entrance animation. Motion only answers a click (Copy becomes Copied) |
| Copy like "Ask me anything!" | Says nothing | Specific copy: "Look up any Python function." |
| One highlighted word inside a headline | A classic generated headline trick | Plain headline, one style |

**Rule for yourself:** spend boldness in one place (the index). Everything else is calm. Before you finish, remove one thing you added. If you are not sure whether something helps, delete it.

---

## 3. Design tokens

A **token** is a named value (a color, a font, a size) that you define once and reuse everywhere. If you want to change a color later, you change it in one place.

### Colors

| Name | Hex | Used for |
|---|---|---|
| Paper | `#F4F6F8` | The page column background |
| Desk | `#E4EAF0` | The area outside the page, behind the grid |
| Desk grid | `#D3DBE5` | The faint grid lines on the desk |
| Rule | `#C9D2DD` | Thin borders and dividers |
| Ink | `#1F2A3C` | Main text |
| Pencil | `#5A6779` | Secondary text (counter, sources) |
| Pen blue | `#2F5D9E` | Links, focus ring, the bar next to a question |
| Highlighter | `#FFE066` | Inline code marker, index hover |
| Margin red | `#C0392B` | Rate limit, errors, refusals |
| Code slate | `#1E2733` | Code block background |

Contrast check (worked out by hand, please confirm with a real tool in Phase 8): Ink on Paper is about 13:1, Pencil on Paper about 5.5:1, Pen blue on Paper about 6:1, Margin red on Paper about 5:1. All pass the 4.5:1 rule for normal text.

### Fonts (two families, clearly different)

- **Literata** (serif): headings and all normal text. It was designed for reading on screens. Serif text gets a little more line height (1.6).
- **JetBrains Mono**: code only (code blocks, inline code, and the names in the index, because those are code names).

Self-host the fonts (put the files in your project) instead of loading them from Google. Reasons: the app works offline and inside Docker, loads faster, and does not depend on another company's server.

### Type scale

| Token | Size | Used for |
|---|---|---|
| `--text-sm` | 14px | Counter, sources, code block header |
| `--text-base` | 17px | Body text |
| `--text-lg` | 20px | The question |
| `--text-xl` | 24px | Wordmark |
| `--text-title` | 32px | Empty-state headline |

### Corner radius depends on the role

- Code block: `6px`
- Small buttons: `4px`
- Textarea: `0` (it is a ruled line, not a box)

Do not use one radius everywhere. That is a tell.

---

## 4. Layout

Left-aligned everywhere. Centered text feels like a landing page; this is a reading tool. The page is one column, about 44rem wide (around 700px), so lines stay short enough to read comfortably.

**Desktop, empty state:**

```
 desk (grid)  |  page (paper)                                  |  desk (grid)
              |                                                |
              |  PyRef                              New chat   |
              |  ------------------------------------------    |
              |                                                |
              |  Look up any Python function.                  |
              |  Syntax and the standard library, with short   |
              |  examples. PyRef won't solve contest problems. |
              |                                                |
              |  heapq ................... priority queues     |
              |  bisect .................. binary search       |
              |  collections ............. deque, Counter      |
              |  itertools ............... permutations        |
              |  ...                                           |
              |                                                |
              |  ------------------------------------------    |
              |  [ Ask about a function, e.g. bisect_left   ]  |
              |  0 / 400                                [Ask]  |
```

**Desktop, with a conversation:**

```
              |  PyRef                              New chat   |
              |                                                |
              |  | How does heapq work?          (blue bar)    |
              |                                                |
              |  heapq gives you a min-heap on a plain list.   |
              |  Use `heappush` to add and `heappop` to take   |
              |  the smallest item.                            |
              |                                                |
              |  +- python ---------------------- [Copy] -+    |
              |  | import heapq                           |    |
              |  | h = []                                 |    |
              |  | heapq.heappush(h, 5)                   |    |
              |  +----------------------------------------+    |
              |                                                |
              |  Source: docs.python.org/3/library/heapq.html  |
              |                                                |
              |  ------------------------------------------    |
              |  [ textarea ]                                  |
              |  12 / 400                               [Ask]  |
```

**Mobile (under 640px):** the page column fills the whole screen, so the desk and grid disappear. The composer stays pinned to the bottom, and respects the phone's safe area (the bar at the bottom of an iPhone).

---

## 5. Phases

Work on a new branch and commit after each phase, so you can always go back.

```bash
git checkout -b frontend-redesign
```

### Phase 0: Prepare (15 minutes)

1. Take screenshots of the current UI (empty state, a long answer, a code block, the 429 message). You will compare them at the end.
2. Open `static/index.html` and `static/script.js`. Write down every ID and class the JS uses (textarea, counter, send button, chat container, countdown element, new-chat button). Keep these names.
3. Check which `marked.js` version you use. Version 4 or newer uses `marked.parse(text)`. Older versions use `marked(text)`.

Commit: `git commit -am "Start frontend redesign branch"` (or nothing to commit yet, that is fine).

### Phase 1: Fonts and tokens

**Step 1.1: Get the font files.** Download them as `.woff2`. The easiest way is the npm packages `@fontsource-variable/literata` and `@fontsource-variable/jetbrains-mono`, which contain the files. Copy these into `static/fonts/`:

- `literata-variable.woff2` (normal)
- `literata-italic-variable.woff2` (italic, for emphasis in answers)
- `jetbrains-mono-variable.woff2`

**Step 1.2: Top of `static/style.css`.** Replace the old variables and font settings with this:

```css
@font-face {
  font-family: "Literata";
  src: url("/fonts/literata-variable.woff2") format("woff2");
  font-weight: 200 900;
  font-style: normal;
  font-display: swap;
}
@font-face {
  font-family: "Literata";
  src: url("/fonts/literata-italic-variable.woff2") format("woff2");
  font-weight: 200 900;
  font-style: italic;
  font-display: swap;
}
@font-face {
  font-family: "JetBrains Mono";
  src: url("/fonts/jetbrains-mono-variable.woff2") format("woff2");
  font-weight: 100 800;
  font-style: normal;
  font-display: swap;
}

:root {
  --paper: #F4F6F8;
  --desk: #E4EAF0;
  --desk-grid: #D3DBE5;
  --rule: #C9D2DD;
  --ink: #1F2A3C;
  --pencil: #5A6779;
  --pen: #2F5D9E;
  --marker: #FFE066;
  --margin-red: #C0392B;
  --code-bg: #1E2733;
  --code-text: #DCE6F2;

  --font-text: "Literata", Georgia, "Times New Roman", serif;
  --font-code: "JetBrains Mono", ui-monospace, "SF Mono", Menlo, Consolas, monospace;

  --text-sm: 0.875rem;
  --text-base: 1.0625rem;
  --text-lg: 1.25rem;
  --text-xl: 1.5rem;
  --text-title: 2rem;
}
```

**How it works, line by line:**

- `@font-face` tells the browser: "there is a font called Literata, and its file is at this URL." Because `main.py` serves the `static/` folder at `/`, the file `static/fonts/literata-variable.woff2` is available at `/fonts/literata-variable.woff2`.
- `font-weight: 200 900` means this is a **variable font**: one file that can be any weight between 200 and 900. So you do not need a separate file for bold.
- `font-display: swap` shows the fallback font immediately and swaps to Literata when it has loaded, so the page never shows invisible text.
- `:root` is the top of the page. Variables defined here (names starting with `--`) can be used anywhere with `var(--name)`.
- The font stacks have fallbacks (`Georgia`, `ui-monospace`). If a font file fails to load, the page still looks acceptable.
- `rem` units are relative to the browser's font size (1rem is usually 16px), so if a user increases their browser font size, the page scales.

**Step 1.3: Base styles.**

```css
*, *::before, *::after { box-sizing: border-box; }

html { -webkit-text-size-adjust: 100%; }

body {
  margin: 0;
  min-height: 100dvh;
  font: 400 var(--text-base) / 1.6 var(--font-text);
  color: var(--ink);
  background-color: var(--desk);
  background-image:
    linear-gradient(var(--desk-grid) 1px, transparent 1px),
    linear-gradient(90deg, var(--desk-grid) 1px, transparent 1px);
  background-size: 24px 24px;
}

:focus-visible {
  outline: 2px solid var(--pen);
  outline-offset: 2px;
}
```

**How it works:**

- `box-sizing: border-box` makes padding and borders count inside an element's width. Without it, width math gets confusing.
- `100dvh` is "100% of the visible screen height". It is better than `100vh` on phones, where the address bar changes the height.
- `font: 400 var(--text-base) / 1.6 var(--font-text)` is a shortcut for weight 400, size 17px, line height 1.6, and the font family.
- The grid: two `linear-gradient` layers draw one thin line each (one horizontal, one vertical). `background-size: 24px 24px` repeats them every 24px, which makes graph paper without an image file.
- `:focus-visible` shows a blue outline only when someone navigates with the keyboard. It is required for accessibility, so never remove it without a replacement.

Commit: `git commit -am "Add fonts and design tokens"`

### Phase 2: Page shell and header

**Step 2.1: HTML structure.** Replace the body of `static/index.html` (keep your existing script tags for now, and keep the IDs your JS needs):

```html
<body>
  <div class="page">
    <header class="masthead">
      <span class="wordmark">PyRef</span>
      <button type="button" id="new-chat" class="text-button">New chat</button>
    </header>

    <main id="chat" class="chat" aria-live="polite">
      <section id="start" class="start">
        <h1>Look up any Python function.</h1>
        <p>Syntax and the standard library, with short examples. PyRef won't solve contest problems.</p>
        <ul class="lookups" id="lookups"><!-- filled in Phase 6 --></ul>
      </section>
    </main>

    <div id="notice" class="notice" role="status" hidden></div>

    <form id="composer" class="composer">
      <label for="input" class="visually-hidden">Your question</label>
      <textarea id="input" rows="2" maxlength="400"
        placeholder="Ask about a function, e.g. bisect_left"></textarea>
      <div class="composer__row">
        <span id="counter" class="composer__count">0 / 400</span>
        <button type="submit" id="send" class="send">Ask</button>
      </div>
    </form>
  </div>
</body>
```

Also make sure `<head>` has these:

```html
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light dark">
<title>PyRef: Python reference for contests</title>
```

**Why each choice:**

- `aria-live="polite"` on the chat makes screen readers announce new answers without interrupting.
- `<label ... class="visually-hidden">` gives the textarea a real name for screen readers. A placeholder is not a label.
- The notice has `role="status"` so the rate-limit message is announced.
- Use a real `<form>` so pressing the button or `Ctrl+Enter` (see Phase 5) both submit the same way.
- `maxlength="400"` matches the server rule, but the server still checks, because the browser can be bypassed.

**Step 2.2: CSS for the shell.**

```css
.page {
  display: flex;
  flex-direction: column;
  max-width: 44rem;
  min-height: 100dvh;
  margin: 0 auto;
  background: var(--paper);
  border-inline: 1px solid var(--rule);
}

.masthead {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  padding: 1.25rem 1.5rem;
  border-bottom: 1px solid var(--rule);
}
.wordmark {
  font-size: var(--text-xl);
  font-weight: 700;
  letter-spacing: -0.01em;
}

.text-button {
  font: inherit;
  font-size: var(--text-sm);
  color: var(--pen);
  background: none;
  border: 0;
  padding: 0.25rem 0;
  cursor: pointer;
  text-decoration: underline;
  text-underline-offset: 3px;
}

.chat { flex: 1; padding-bottom: 2rem; }

.visually-hidden {
  position: absolute;
  width: 1px; height: 1px;
  overflow: hidden;
  clip-path: inset(50%);
  white-space: nowrap;
}

@media (max-width: 40rem) {
  .page { border-inline: 0; }
}
```

**How it works:**

- `.page` is a column that is at most 44rem wide and centered with `margin: 0 auto`. Because the body has the grid and `.page` has a solid paper color, the grid only shows on the left and right, like paper lying on a desk.
- `flex: 1` on `.chat` makes the chat area take all the free height, which pushes the composer to the bottom even when the chat is empty.
- `.visually-hidden` hides something from the eyes but keeps it for screen readers. (`display: none` would hide it from both.)
- The wordmark is plain text in one style. No colored half-word.

Commit: `git commit -am "Build page shell and header"`

### Phase 3: Conversation as entries, not bubbles

**Step 3.1: CSS.**

```css
.entry { padding: 2rem 1.5rem 0; }
.entry:last-child { min-height: calc(100dvh - 14rem); }

.question {
  margin: 0 0 0.75rem;
  padding-left: 0.75rem;
  border-left: 3px solid var(--pen);
  font-size: var(--text-lg);
  font-weight: 600;
  line-height: 1.35;
  scroll-margin-top: 1rem;
}

.answer > * { max-width: 68ch; }
.answer p { margin: 0 0 1em; }
.answer ul, .answer ol { padding-left: 1.25rem; margin: 0 0 1em; }
.answer li { margin-bottom: 0.35em; }

.answer :not(pre) > code {
  font: 500 0.88em var(--font-code);
  padding: 0 0.15em;
  background: linear-gradient(transparent 58%, var(--marker) 58%);
}

.answer a { color: var(--pen); text-underline-offset: 3px; }

.thinking { color: var(--pencil); }
.thinking::after {
  content: "";
  display: inline-block;
  width: 0.55ch;
  height: 1.1em;
  margin-left: 0.2em;
  vertical-align: text-bottom;
  background: var(--ink);
  animation: blink 1s steps(1) infinite;
}
@keyframes blink { 50% { opacity: 0; } }
@media (prefers-reduced-motion: reduce) {
  .thinking::after { animation: none; }
}

.answer[data-blocked="true"] {
  padding-left: 0.75rem;
  border-left: 3px solid var(--margin-red);
}
```

**How it works:**

- No bubble: the **question** is a heading with a blue bar on the left. The **answer** is plain text under it, using the full width of the column. This reads like a document, so long answers are easy to read.
- `.entry:last-child { min-height: ... }` gives the newest entry enough height so the page can scroll the question to the top of the screen. Without this, there is nothing below the answer to scroll into.
- `max-width: 68ch` limits each paragraph to about 68 characters per line (`ch` is the width of the letter "0"). Long lines are tiring to read.
- `:not(pre) > code` means: "a `code` tag whose parent is **not** a `pre`." Inline code has a `p` or `li` as parent. Code blocks have `pre` as parent, so they are not affected. This is how the yellow marker applies only to inline code.
- The marker effect: `linear-gradient(transparent 58%, var(--marker) 58%)` is transparent for the top 58% of the line and yellow for the bottom 42%. It looks like a highlighter stroke across the lower part of the word.
- The loading caret is a small block that blinks. `steps(1)` makes it jump on and off, like a real terminal caret, instead of fading. With `prefers-reduced-motion` (a system setting some people turn on), it stops blinking.
- `data-blocked="true"` is for refusals (Phase 9). A red bar on the left shows "this is a no" without a scary error box.

**Step 3.2: JS. Create an entry when the user asks.**

```js
const chatEl = document.getElementById("chat");
const startEl = document.getElementById("start");
const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

function addEntry(questionText) {
  startEl.hidden = true;

  const entry = document.createElement("article");
  entry.className = "entry";

  const q = document.createElement("h2");
  q.className = "question";
  q.textContent = questionText;

  const a = document.createElement("div");
  a.className = "answer thinking";
  a.textContent = "Looking it up";

  entry.append(q, a);
  chatEl.append(entry);

  q.scrollIntoView({ behavior: reduceMotion ? "auto" : "smooth", block: "start" });
  return a;
}
```

**How it works:**

- `document.createElement` makes a new HTML element in memory. `append` puts it on the page.
- `q.textContent = questionText` is important. `textContent` treats the text as plain text. If you used `innerHTML` for the user's question, someone could type `<img src=x onerror=...>` and run code in the page.
- The function returns the answer element, so the code that gets the server reply can fill it in later.
- `scrollIntoView({ block: "start" })` scrolls so the **question** is at the top of the screen. The reader starts at the top of the answer. Scrolling to the bottom would make people scroll back up to read.
- `reduceMotion` respects the user's system setting: no smooth scroll if they asked for less motion.

Commit: `git commit -am "Render conversation as entries"`

### Phase 4: Safe Markdown and code blocks

**Step 4.1: Add two libraries to `static/vendor/`.**

- **DOMPurify** (`purify.min.js`): cleans HTML so it cannot run scripts.
- **highlight.js**, a custom build with **only Python** selected (download from highlightjs.org/download). It is small (around 20 KB) and does the syntax colors.

If `marked.js` currently loads from a CDN, download it into `static/vendor/` too, so the app has no outside dependency. Load order in `index.html`: `marked`, `purify`, `highlight`, then `script.js`.

**Why DOMPurify is not optional:** the bot reads web pages, and the model's reply is turned into HTML. `marked` does **not** remove dangerous HTML. If a fetched page tricks the model into writing `<img src=x onerror="...">`, your page would run it. Sanitizing is the fix.

**Step 4.2: JS to render an answer.**

```js
function renderAnswer(answerEl, markdown) {
  answerEl.classList.remove("thinking");
  answerEl.textContent = "";

  const rawHtml = marked.parse(markdown);
  answerEl.innerHTML = DOMPurify.sanitize(rawHtml);

  enhanceCodeBlocks(answerEl);
}

function enhanceCodeBlocks(root) {
  root.querySelectorAll("pre > code").forEach((code) => {
    const pre = code.parentElement;
    const match = code.className.match(/language-(\w+)/);
    const lang = match ? match[1] : "text";

    if (window.hljs && hljs.getLanguage(lang)) {
      hljs.highlightElement(code);
    }

    const figure = document.createElement("figure");
    figure.className = "code";

    const bar = document.createElement("figcaption");
    const label = document.createElement("span");
    label.textContent = lang;

    const button = document.createElement("button");
    button.type = "button";
    button.className = "code__copy";
    button.textContent = "Copy";
    button.addEventListener("click", async () => {
      try {
        await navigator.clipboard.writeText(code.textContent);
        button.textContent = "Copied";
      } catch {
        button.textContent = "Copy failed";
      }
      setTimeout(() => { button.textContent = "Copy"; }, 1500);
    });

    bar.append(label, button);
    pre.replaceWith(figure);
    figure.append(bar, pre);
  });
}
```

**How it works, step by step:**

1. `marked.parse(markdown)` turns the model's Markdown text into an HTML string.
2. `DOMPurify.sanitize(...)` removes anything dangerous (scripts, `onerror=`, `javascript:` links) and keeps safe tags like `p`, `code`, `pre`, `ul`, and class names.
3. `enhanceCodeBlocks` finds every `<pre><code>` (a code block). `marked` puts the language into the class, like `language-python`, and the regex `/language-(\w+)/` pulls out the word `python`.
4. `hljs.highlightElement(code)` adds colored `<span>` tags around keywords, strings, and so on. The `hljs.getLanguage(lang)` check avoids errors if the language is not in your custom build.
5. We build a `<figure>` with a small header bar (language name and a Copy button), then move the original `<pre>` inside it. `pre.replaceWith(figure)` takes the `pre` out of the page and puts the `figure` in its place. Then `figure.append(bar, pre)` puts the bar and the `pre` into the figure.
6. Clicking Copy uses `navigator.clipboard.writeText`. The button text changes to "Copied" for 1.5 seconds. This is the only animation-like thing on the page, and it appears **because the user clicked**, which is the right kind of motion. It only works on `localhost` or `https`; on plain `http` it fails and the button says "Copy failed".
7. `code.textContent` gives the plain code without the color tags, so you copy clean code.

The old label "Copy Snippet" becomes "Copy". Keep the same name for the same action everywhere.

**Step 4.3: CSS for code blocks and colors.**

```css
.code {
  margin: 1.25rem 0;
  background: var(--code-bg);
  color: var(--code-text);
  border-radius: 6px;
  overflow: hidden;
}
.code figcaption {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.4rem 0.5rem 0.4rem 0.9rem;
  font-size: var(--text-sm);
  color: #9FB0C6;
  border-bottom: 1px solid #2E3B4B;
}
.code__copy {
  font: inherit;
  color: inherit;
  background: none;
  border: 1px solid #3A485A;
  border-radius: 4px;
  padding: 0.2rem 0.65rem;
  cursor: pointer;
}
.code__copy:hover { color: #FFFFFF; border-color: #6F829B; }
.code pre {
  margin: 0;
  padding: 1rem 0.9rem;
  overflow-x: auto;
  font: 400 0.9rem / 1.55 var(--font-code);
  tab-size: 4;
}
.code pre:focus-visible { outline-offset: -2px; }

/* highlight.js token colors: only four hues + comments */
.hljs-keyword, .hljs-literal { color: #8CB4F0; }
.hljs-built_in, .hljs-title  { color: #F2D479; }
.hljs-string                  { color: #A9D98A; }
.hljs-number                  { color: #F0907F; }
.hljs-comment                 { color: #8D9CB2; font-style: italic; }
```

**How it works:**

- `overflow: hidden` on `.code` makes the rounded corners clip the header and the code. `overflow-x: auto` on `pre` lets a long code line scroll sideways **inside** the block instead of breaking the page width.
- The code colors are written by hand from the palette instead of using a ready-made theme like "github-dark". Ready-made themes are one of the things that make pages look alike. Comments use `#8D9CB2` (not a darker grey) so they stay readable on the dark background.
- Code is the only dark area on a light page, so the eye goes to it first. That is what you want in a reference tool.

Commit: `git commit -am "Safe markdown rendering and styled code blocks"`

### Phase 5: Composer and states

**Step 5.1: CSS.**

```css
.composer {
  position: sticky;
  bottom: 0;
  padding: 0.75rem 1.5rem calc(0.75rem + env(safe-area-inset-bottom, 0px));
  background: var(--paper);
  border-top: 1px solid var(--rule);
}
.composer textarea {
  display: block;
  width: 100%;
  resize: none;
  font: inherit;
  font-size: 1rem;
  color: inherit;
  background: transparent;
  border: 0;
  border-bottom: 2px solid var(--rule);
  border-radius: 0;
  padding: 0.5rem 0;
}
.composer textarea::placeholder { color: var(--pencil); }
.composer textarea:focus { border-bottom-color: var(--pen); }

.composer__row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 0.5rem;
}
.composer__count {
  font-size: var(--text-sm);
  color: var(--pencil);
  font-variant-numeric: tabular-nums;
}
.composer__count[data-near="true"] { color: var(--margin-red); }

.send {
  font: inherit;
  font-weight: 600;
  color: var(--paper);
  background: var(--ink);
  border: 0;
  border-radius: 4px;
  padding: 0.5rem 1.25rem;
  cursor: pointer;
}
.send:hover:not(:disabled) { background: var(--pen); }
.send:disabled { background: var(--rule); color: var(--pencil); cursor: not-allowed; }

.notice {
  margin: 0 1.5rem 0.75rem;
  padding-left: 0.75rem;
  border-left: 3px solid var(--margin-red);
  font-size: var(--text-sm);
}
```

**How it works:**

- `position: sticky; bottom: 0` keeps the composer at the bottom of the screen while you scroll the chat.
- `env(safe-area-inset-bottom, 0px)` adds extra space on phones with a home bar, so the button is not hidden under it.
- The textarea has **no box**: only a line under it, like writing on a ruled line. The line turns blue on focus. That gives the textarea a clear focus state, and on keyboard focus the blue outline from Phase 1 also shows.
- `font-size: 1rem` (16px) is the smallest size that stops iPhones from zooming into the page when you tap the field. Do not go below it.
- `font-variant-numeric: tabular-nums` makes all digits the same width, so the counter does not jitter as you type.
- The send button is solid ink, with plain text "Ask". When disabled (during cooldown or waiting for an answer), it turns grey.

**Step 5.2: Update the counter.** Keep your existing counter logic and only change the text format and the warning state:

```js
function updateCounter() {
  const used = input.value.length;
  counterEl.textContent = `${used} / 400`;
  counterEl.dataset.near = used >= 360 ? "true" : "false";
}
input.addEventListener("input", updateCounter);
```

`dataset.near` sets the attribute `data-near`, which the CSS uses to turn the counter red in the last 40 characters.

**Step 5.3: Keyboard submit.** Add this so `Ctrl+Enter` (or `Cmd+Enter` on Mac) sends:

```js
input.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) {
    event.preventDefault();
    form.requestSubmit();
  }
});
```

Plain `Enter` still makes a new line, which is useful when someone pastes a code line.

**Step 5.4: Copy for every state.** Reuse your existing logic (the cooldown and the 429 countdown). Only change the words and where they show:

| State | Message |
|---|---|
| Waiting | Answer area shows: `Looking it up` with the blinking caret |
| Rate limit (429) | `Too many questions. You can ask again in 42 s.` shown in `#notice`, and the Ask button is disabled until it reaches 0 |
| Server down | `Can't reach PyRef. Check your connection and try again.` |
| Empty question | Do nothing. The Ask button is simply disabled when the box is empty |
| Message too long | The counter turns red. You do not need a popup |

Rules for the wording: sentence case, no apology, say what happened and what to do next. The same action keeps the same name everywhere (Ask, Copy, New chat).

Commit: `git commit -am "Style composer and states"`

### Phase 6: The index (empty state)

**Step 6.1: CSS.**

```css
.start { padding: 3rem 1.5rem 1rem; }
.start h1 {
  margin: 0 0 0.5rem;
  font-size: var(--text-title);
  line-height: 1.15;
  font-weight: 700;
  letter-spacing: -0.015em;
}
.start p { max-width: 52ch; margin: 0 0 2rem; color: var(--pencil); }

.lookups { list-style: none; margin: 0; padding: 0; }
.lookups button {
  display: flex;
  align-items: baseline;
  width: 100%;
  padding: 0.55rem 0;
  font: inherit;
  text-align: left;
  color: inherit;
  background: none;
  border: 0;
  cursor: pointer;
}
.lookups__name {
  font: 500 0.95rem var(--font-code);
}
.lookups__leader {
  flex: 1;
  margin: 0 0.6rem;
  border-bottom: 2px dotted var(--rule);
  transform: translateY(-0.3em);
}
.lookups__what { color: var(--pencil); }
.lookups button:hover .lookups__name {
  background: linear-gradient(transparent 58%, var(--marker) 58%);
}
```

**How it works:**

- Each row is a flex line: the name, a stretchy empty span with a **dotted bottom border** (the "leader"), and the description. Book indexes and tables of contents use leaders to connect a name to its page number. Here it connects a module to what it does, so the dots carry real information.
- `align-items: baseline` lines the name and the description up on the same text baseline even though they use different fonts.
- `transform: translateY(-0.3em)` lifts the dotted line a little so it sits at the bottom of the letters instead of below them. Adjust this number by eye after you see it.
- On hover the name gets the same highlighter stroke as inline code. One idea, used twice, so the page feels consistent.
- The headline is one style. The first line states what the tool does, and the second line states the limit (no problem solving). Saying the limit up front means fewer people are surprised by a refusal.

**Step 6.2: JS to build the list and send on click.**

```js
const LOOKUPS = [
  ["heapq", "priority queues", "How does heapq work?"],
  ["bisect", "binary search on sorted lists", "What do bisect_left and bisect_right do?"],
  ["collections", "deque, Counter, defaultdict", "What do deque, Counter and defaultdict do?"],
  ["itertools", "permutations and combinations", "How do itertools.permutations and combinations work?"],
  ["functools", "lru_cache and reduce", "What do functools.lru_cache and reduce do?"],
  ["sys.stdin", "fast input", "How do I read input fast with sys.stdin?"],
  ["math", "gcd, isqrt, comb", "What do math.gcd, isqrt and comb do?"],
];

const lookupsEl = document.getElementById("lookups");
LOOKUPS.forEach(([name, what, question]) => {
  const li = document.createElement("li");
  const btn = document.createElement("button");
  btn.type = "button";
  btn.innerHTML =
    `<span class="lookups__name">${name}</span>` +
    `<span class="lookups__leader" aria-hidden="true"></span>` +
    `<span class="lookups__what">${what}</span>`;
  btn.addEventListener("click", () => {
    input.value = question;
    updateCounter();
    form.requestSubmit();
  });
  li.append(btn);
  lookupsEl.append(li);
});
```

**How it works:**

- The list is an array of three-item arrays: short name, description, and the full question that gets sent. The array destructuring `([name, what, question])` unpacks each one.
- `innerHTML` is fine here because the strings are written by you in the code, not typed by a user or the model.
- `aria-hidden="true"` hides the dotted leader from screen readers, so they read "heapq, priority queues" without noise.
- Every question is a syntax or standard-library question, so none of them trigger your guardrails. Keep it that way if you edit the list.
- `form.requestSubmit()` runs your normal submit code, so the rate limit, the cooldown, and everything else apply as usual. Do not write a second send path.
- After the first question, `addEntry` (Phase 3) hides `#start`. **When you restore history from `sessionStorage` on page load, also hide `#start`**, or the index will show above an old conversation.

Commit: `git commit -am "Add lookup index empty state"`

### Phase 7: Responsive, dark mode and accessibility

**Step 7.1: Dark mode (system setting only, no toggle button).** A toggle is one more control for little value. Use the system preference:

```css
@media (prefers-color-scheme: dark) {
  :root {
    --paper: #171E28;
    --desk: #10151C;
    --desk-grid: #1A222D;
    --rule: #2B3644;
    --ink: #E4EAF2;
    --pencil: #9AA7B8;
    --pen: #7FA8E6;
    --margin-red: #F08A7E;
    --code-bg: #0E131A;
  }
  .answer :not(pre) > code,
  .lookups button:hover .lookups__name {
    background: linear-gradient(transparent 58%, rgba(255, 224, 102, 0.35) 58%);
  }
  .send { color: var(--paper); }
}
```

**How it works:** because every color is a variable, dark mode just gives the variables new values. The highlighter stays yellow but becomes see-through (35% opacity), so bright yellow does not glare against a dark page. The ink color (light) is used for text on top of it, which stays readable.

**Step 7.2: Small-screen check.**

- At 320px width, nothing scrolls sideways (except inside code blocks).
- Padding of `1.5rem` is fine on phones, but reduce `.start` top padding to `2rem` under 40rem if the index feels pushed down.
- The composer must never cover the last line of an answer. The `min-height` rule on `.entry:last-child` and the sticky composer handle this. Test with a long answer.

**Step 7.3: Accessibility checklist.**

- Every button is a real `<button>`, reachable with Tab, and activates with Enter or Space.
- Focus outline is visible on every control (the global `:focus-visible` rule).
- The textarea has a label, the notice has `role="status"`, and the chat area has `aria-live="polite"`.
- Do not use color alone for meaning. The refusal has a red bar **and** words. The near-limit counter turns red **and** the number shows the count.
- Code blocks with long lines are scrollable by keyboard: add `tabindex="0"` to each `pre` in `enhanceCodeBlocks` (`pre.tabIndex = 0;`), so keyboard users can focus it and scroll with the arrow keys.
- Respect `prefers-reduced-motion` (blink and smooth scroll are already handled).

Commit: `git commit -am "Dark mode, responsive fixes, accessibility"`

### Phase 8: Review pass (do not skip)

Work through this list with the page open next to your Phase 0 screenshots.

**Anti-slop check**

- [ ] No bubbles, avatars, gradients, emoji, or sparkle icons anywhere
- [ ] No ALL-CAPS tracked labels, no `→` on buttons, no spaced em-dash labels
- [ ] No shadow on anything, and not every element has the same radius
- [ ] No animation runs by itself, except the blinking caret while waiting
- [ ] The yellow marker appears only on inline code and the index hover
- [ ] Every piece of text says something specific. Delete any sentence you would be embarrassed to read aloud
- [ ] Remove one thing you added (the "Chanel rule"). Usually it is a border or a divider

**Quality check**

- [ ] Test widths 320, 375, 768 and 1440 px
- [ ] Light and dark mode
- [ ] Keyboard only: Tab through the whole page, send a question, copy a code block
- [ ] A 60-line answer and a code line that is 200 characters long
- [ ] Server stopped (error text), 6 quick questions (429 message and countdown), and a refused question
- [ ] Run Chrome DevTools **Lighthouse** (Accessibility score should be 95 or more) and, if you can, the **axe DevTools** extension
- [ ] Check contrast of Pencil, Pen blue and Margin red with a contrast checker, and fix any that fail
- [ ] Reload mid-conversation: history returns, and the index is hidden

When it passes, open a pull request from `frontend-redesign` into `main` on your own repo, and merge.

### Phase 9 (optional): Two small backend changes that make the UI better

These connect to the guardrails and "source links" ideas from earlier.

**9.1: Mark refusals.** In `groq_api.py`, when the guardrails return `REFUSAL`, return a flag with the text, for example `{"response": REFUSAL, "blocked": true}`. In `script.js`, after you create the answer element:

```js
if (data.blocked) answerEl.dataset.blocked = "true";
```

The CSS from Phase 3 then draws the red bar. A refusal is expected behavior of the product, so it should look like a calm note and not a crash.

**9.2: Show the source.** During the tool loop, collect the URLs the model fetched and return them as `"sources": [...]`. Then in `script.js`:

```js
function renderSources(answerEl, sources) {
  if (!sources || !sources.length) return;
  const p = document.createElement("p");
  p.className = "sources";
  p.append("Source: ");
  sources.forEach((url, i) => {
    const link = document.createElement("a");
    link.href = url;
    link.textContent = url.replace(/^https?:\/\//, "");
    link.target = "_blank";
    link.rel = "noopener";
    if (i > 0) p.append(", ");
    p.append(link);
  });
  answerEl.append(p);
}
```

```css
.sources { margin-top: 1.25rem; font-size: var(--text-sm); color: var(--pencil); }
.sources a { color: var(--pen); text-underline-offset: 3px; }
```

**How it works:** the `link.textContent` shows the URL without `https://`. It is set with `textContent` and `link.href`, never with `innerHTML`, so a strange URL cannot inject HTML. `rel="noopener"` stops the opened page from controlling your page. Only add links whose host is `docs.python.org` (see the fetch allow-list in the guardrails plan), and a source line is a quiet footnote, not a button.

---

## 6. Suggested commit history

```
Start frontend redesign branch
Add fonts and design tokens
Build page shell and header
Render conversation as entries
Safe markdown rendering and styled code blocks
Style composer and states
Add lookup index empty state
Dark mode, responsive fixes, accessibility
(optional) Mark refusals and show sources
```

Small commits with clear messages look professional in your GitHub history and make it easy to undo one step.

## 7. Done means

- The page has one memorable thing (the index) and one signature detail (the marker), and nothing else is shouting.
- It works with only a keyboard, on a 320px phone, and in dark mode.
- Model output is sanitized before it touches the page.
- No external servers are needed to display it (fonts and libraries are self-hosted).
- Someone who has never seen your project can tell what it does in five seconds from the first screen.
