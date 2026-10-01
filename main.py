import os
import logging
from typing import Literal
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


# SCHEMA

class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str

class ChatRequest(BaseModel):
    history: list[ChatMessage] = Field(default_factory=list)
    message: str = Field(..., max_length=400)


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

        # Prompt the LLM
        history = [item.model_dump() for item in chat_request.history if item.content.strip()]
        history = history[-10:] # Max 10 previous turns
        reply = await groq_api.get_response_async(chat_request.message, history, mcp_client=fetch_mcp)

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