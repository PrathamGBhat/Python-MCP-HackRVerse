# PyRef — Python Competitive Programming Reference Assistant

A FastAPI + Groq powered web assistant designed for competitive programming contests. Contestants can use this interface to query **Python syntax, built-in functions, and standard library modules** (e.g. `heapq`, `collections`, `bisect`, `itertools`, `sys.stdin`).

It is equipped with strict system prompt guardrails to **refuse solving problem statements or generating full algorithmic solutions**, preventing contestants from deriving direct contest solutions.

## Project Structure

```
.
├── main.py           FastAPI app, POST /chat, rate limiting, lifespan MCP management
├── llm.py            Groq LLM client with MCP tool-calling loop & CP guardrails
├── mcp_client.py     Async Stdio MCP client wrapper for mcp-server-fetch
├── requirements.txt  Python dependencies (fastapi, groq, mcp-server-fetch, etc.)
├── static/           Frontend assets (HTML, CSS, JS)
└── tests/            Automated test suite (MCP fetch, LLM tool calling, FastAPI endpoints)
```

## Setup

1. **Activate your virtual environment**
   ```bash
   venv\Scripts\activate      # Linux/macOS: source venv/bin/activate
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure API Key**
   Copy `.env.example` to `.env` (or set `GROQ_API_KEY` in environment):
   ```env
   GROQ_API_KEY=your_groq_api_key_here
   GROQ_MODEL=llama-3.1-8b-instant
   ```

## Run Locally

```bash
uvicorn main:app --reload
```

Open **http://127.0.0.1:8000** in your browser.

## Features & Guardrails

- **Syntax & Standard Library Only**: Responds with concise syntax rules, built-in usage, and generic 3-5 line code snippets.
- **Problem Solving Refusal**: Strict system prompt directives block problem derivation, algorithm generation, or interpreting pasted contest question statements.
- **1-Click Copy Code**: Code blocks are formatted with language badges and a copy button.
- **Contest Rate Limiting**: Default rate limit set to `15 messages/minute` per IP address.

