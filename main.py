import os
import logging
from collections import OrderedDict
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

import groq_api
from fetch_mcp import FetchMCP
from guardrails import REFUSAL

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("main")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
static_dir = os.path.join(BASE_DIR, "static")

# Initialize MCP client instance
fetch_mcp = FetchMCP()

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("App starting up. Initializing FetchMCP...")
    try:
        await fetch_mcp.initialize()
    except Exception as err:
        logger.warning("FetchMCP failed to initialize on startup: %s", err)
    yield
    logger.info("App shutting down. Closing FetchMCP...")
    await fetch_mcp.close()


# Setup app and rate limiter
app = FastAPI(title="PyRef - Python CP Reference Assistant", lifespan=lifespan)
limiter = Limiter(key_func=get_remote_address, headers_enabled=True)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Disable browser caching for development static assets
@app.middleware("http")
async def add_no_cache_header(request: Request, call_next):
    response = await call_next(request)
    if request.url.path.endswith((".css", ".js", ".html")) or request.url.path == "/":
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response


# SCHEMA

class ChatRequest(BaseModel):
    message: str = Field(..., max_length=400)
    session_id: Optional[str] = Field(
        default=None, max_length=64, pattern=r"^[A-Za-z0-9_-]+$"
    )


# SESSIONS

SESSIONS: "OrderedDict[str, list[dict]]" = OrderedDict()
MAX_SESSIONS = 1000   # oldest sessions are dropped beyond this
MAX_ITEMS = 10        # last 10 messages per session


def get_history(session_id: Optional[str]) -> list[dict]:
    if not session_id or session_id not in SESSIONS:
        return []
    SESSIONS.move_to_end(session_id)
    return list(SESSIONS[session_id])


def save_turn(session_id: Optional[str], user_msg: str, reply: str) -> None:
    if not session_id:
        return
    hist = SESSIONS.setdefault(session_id, [])
    hist.append({"role": "user", "content": user_msg})
    hist.append({"role": "assistant", "content": reply})
    del hist[:-MAX_ITEMS]
    SESSIONS.move_to_end(session_id)
    while len(SESSIONS) > MAX_SESSIONS:
        SESSIONS.popitem(last=False)


# ENDPOINTS

# Health endpoint
@app.get("/health")
def health():
    return {"status": "ok"}

# LLM endpoint
@app.post("/chat")
@limiter.limit("5/minute")
async def chat(request: Request, response: Response, chat_request: ChatRequest):
    try:
        # Handle missing message or length exceeding limit
        clean_msg = chat_request.message.strip()
        if not clean_msg:
            return JSONResponse(
                status_code=400,
                content={"error": "Message cannot be empty."}
            )
        if len(clean_msg) > 400:
            return JSONResponse(
                status_code=400,
                content={"error": "Message exceeds maximum allowed limit of 400 characters."}
            )

        history = get_history(chat_request.session_id)
        reply = await groq_api.get_response_async(clean_msg, history, mcp_client=fetch_mcp)

        # Only remember turns that were actually answered, never refusals.
        if reply != REFUSAL:
            save_turn(chat_request.session_id, clean_msg, reply)

        return {"response": reply}

    except RuntimeError as exc:
        logger.error("[/chat] runtime error: %s", exc)
        return JSONResponse(
            status_code=500,
            content={"error": str(exc)},
        )
    except Exception as exc:
        logger.error("[/chat] unexpected error: %s", exc)
        return JSONResponse(
            status_code=500,
            content={"error": "An unexpected error occurred. Please try again."},
        )


# Serve static frontend at "/"
app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
