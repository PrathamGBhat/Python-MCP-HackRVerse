import os
from typing import Literal
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

import llm
from mcp_client import MCPClient

# Initialize MCP client instance
mcp_client = MCPClient()


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[FastAPI] App starting up. Initializing MCPClient...")
    try:
        await mcp_client.initialize()
    except Exception as err:
        print(f"[FastAPI] WARNING: MCPClient failed to initialize on startup: {err}")
    yield
    print("[FastAPI] App shutting down. Closing MCPClient...")
    await mcp_client.close()


# Setup app and rate limiter
app = FastAPI(title="PyRef - Python CP Reference Assistant", lifespan=lifespan)
limiter = Limiter(key_func=get_remote_address, headers_enabled=True)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    message: str
    history: list[ChatMessage] = Field(default_factory=list)


# LLM endpoint
@app.post("/chat")
@limiter.limit("15/minute")
async def chat(request: Request, response: Response, chat_request: ChatRequest):
    try:
        # Handle missing message
        if not chat_request.message or not chat_request.message.strip():
            return JSONResponse(status_code=400, content={"error": "Message cannot be empty."})

        # Format chat history
        history = [item.model_dump() for item in chat_request.history if item.content.strip()]

        # Get response from LLM using MCP client
        reply = await llm.get_response_async(chat_request.message, history, mcp_client=mcp_client)
        return {"response": reply}

    except Exception as exc:
        print(f"[/chat] error: {exc}")
        return JSONResponse(
            status_code=500,
            content={"error": f"{exc}"},
        )


# Health endpoint
@app.get("/health")
def health():
    return {"status": "ok"}


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
static_dir = os.path.join(BASE_DIR, "static")

# Serve frontend (/static directory) at "/"
app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")