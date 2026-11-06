# PyRef — Python Competitive Programming Reference Assistant

A FastAPI + Groq powered web assistant designed for competitive programming contests. Contestants can use this interface to query **Python syntax, built-in functions, and standard library modules** (e.g. `heapq`, `collections`, `bisect`, `itertools`, `sys.stdin`).

It is equipped with a robust, multi-layer defense pipeline that **strictly refuses solving problem statements, providing algorithmic solutions, or answering LeetCode/Codeforces questions**, preventing contestants from deriving direct contest solutions.

---

## Project Structure

```
.
├── main.py              FastAPI app, server-side sessions, rate limiting, MCP lifespan
├── groq_api.py          Groq API client with async non-blocking execution & guard checks
├── guardrails.py        Multi-layer guardrail definitions, regex patterns & refusal logic
├── fetch_mcp.py         Async Stdio MCP client wrapper for mcp-server-fetch
├── requirements.txt     Python dependencies (fastapi, groq, mcp-server-fetch, slowapi, etc.)
├── Dockerfile           Container definition (python:3.12-slim, non-root user)
├── docker-compose.yml   One-command local container orchestrator
├── static/              Frontend assets (HTML, CSS, JS with session IDs)
└── tests/               Automated test suite (unit & integration tests)
    ├── test_guardrails.py   Offline unit tests for regex and rule filtering
    ├── test_fastapi_mcp.py  Integration tests for API endpoints & rate limits
    ├── test_llm_mcp.py      LLM tool-calling & guardrail verification tests
    └── test_mcp_fetch.py    MCP fetch tool subprocess connection tests
```

---

## Architecture & Defense Layers

```
User Query
   │
   ▼
[Layer 1: Deterministic Rules] ──(Blocked: known problems, LeetCode, pasted inputs)──► REFUSAL
   │
   ▼
[Layer 2: Fast AI Classifier]  ──(Blocked: rephrased / disguised algorithmic queries)──► REFUSAL
   │
   ▼
[Main LLM + Official Docs via MCP Fetch]
   │
   ▼
[Layer 3: Reply Verification]  ──(Blocked: generated code solves specific problem)──► REFUSAL
   │
   ▼
Safe Syntax & Documentation Answer
```

* **Layer 1 (Deterministic Rules):** Instant regex matching for known problem names (Two Sum, Kadane, 3Sum, Knapsack, etc.), platform keywords (`leetcode`, `codeforces`), and problem statement structures (`Example 1:`, `Constraints:`, `Input format`).
* **Layer 2 (Fast AI Classifier):** Uses a dedicated non-reasoning model (`qwen/qwen3.8-27b`) to classify disguised or paraphrased problem prompts before they hit the main model.
* **Layer 3 (Reply Guard):** Pre-delivery code verification to guarantee generated code snippets remain generic syntax examples and do not solve algorithmic challenges.
* **Server-Side Session Security:** Chat history is stored in-memory on the server and keyed by session ID; client-supplied conversation history is rejected to eliminate prompt injection and fake assistant turns.

---

## Setup

1. **Configure Environment Variables**
   Copy `.env.example` to `.env` and fill in your Groq API key:
   ```env
   GROQ_API_KEY=your_groq_api_key_here
   GROQ_MODEL=openai/gpt-oss-120b
   GUARD_MODEL=qwen/qwen3.8-27b
   SYSTEM_PROMPT="You are PyRef, a Python reference tool for competitive programmers. You ONLY explain Python syntax, built-in functions, and standard library modules..."
   ```

---

## Running Locally

1. **Create and activate a virtual environment:**
   ```bash
   # Windows PowerShell:
   python -m venv venv
   .\venv\Scripts\Activate.ps1

   # Linux/macOS:
   python3 -m venv venv
   source venv/bin/activate
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the server:**
   ```bash
   uvicorn main:app --reload
   ```

Open **[http://127.0.0.1:8000](http://127.0.0.1:8000)** in your browser.

---

## Running with Docker

### Option A: Using Docker Compose
```bash
docker compose up --build
```

### Option B: Using Plain Docker
```bash
# Build the image
docker build -t pyref .

# Run container with environment file
docker run -p 8000:8000 --env-file .env pyref
```

---

## Running Tests

To verify that all guardrails, MCP tools, and API endpoints are working properly:

```bash
# 1. Offline guardrails unit test (no internet or API key required)
python tests/test_guardrails.py

# 2. FastAPI integration tests
python tests/test_fastapi_mcp.py

# 3. LLM tool-calling & guardrail integration tests
python tests/test_llm_mcp.py

# 4. MCP fetch tool tests
python tests/test_mcp_fetch.py
```
