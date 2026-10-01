# PyRef — Python Competitive Programming Reference Assistant

A FastAPI + Groq powered web assistant designed for competitive programming contests. Contestants can use this interface to query **Python syntax, built-in functions, and standard library modules** (e.g. `heapq`, `collections`, `bisect`, `itertools`, `sys.stdin`).

It is equipped with strict system prompt guardrails to **refuse solving problem statements or generating full algorithmic solutions**, preventing contestants from deriving direct contest solutions.

## Project Structure

```
.
├── main.py              FastAPI app, POST /chat, rate limiting, lifespan MCP management
├── groq_api.py          Groq API client with MCP tool-calling loop & guardrails
├── fetch_mcp.py         Async Stdio MCP client wrapper for mcp-server-fetch
├── requirements.txt     Python dependencies (fastapi, groq, mcp-server-fetch, etc.)
├── Dockerfile           Container definition (python:3.12-slim, non-root user)
├── docker-compose.yml   One-command local container orchestrator
├── static/              Frontend assets (HTML, CSS, JS)
└── tests/               Automated test suite
```

## Setup

1. **Configure Environment Variables**
   Copy `.env.example` to `.env` (or set `GROQ_API_KEY` in environment):
   ```env
   GROQ_API_KEY=your_groq_api_key_here
   GROQ_MODEL=llama-3.1-8b-instant
   # Optional: customize chatbot persona/behavior
   # SYSTEM_PROMPT="Your custom system prompt..."
   ```

## Running with Docker (Recommended)

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

## Running Locally (Without Docker)

1. **Activate virtual environment**
   ```bash
   venv\Scripts\activate      # Linux/macOS: source venv/bin/activate
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the server**
   ```bash
   uvicorn main:app --reload
   ```

Open **http://127.0.0.1:8000** in your browser.

## Features & Guardrails

- **Syntax & Standard Library Only**: Responds with concise syntax rules, built-in usage, and generic 3-5 line code snippets.
- **Problem Solving Refusal**: Strict system prompt directives block problem derivation, algorithm generation, or interpreting pasted contest question statements.
- **1-Click Copy Code**: Code blocks are formatted with language badges and a copy button.
- **Contest Rate Limiting**: Default rate limit set to `15 messages/minute` per IP address.

