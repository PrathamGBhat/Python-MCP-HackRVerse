from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, Response
from pydantic import BaseModel, Field
from typing import Literal
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

import llm

# Setup up app and rate limiter
app = FastAPI(title="PyRef - Python CP Reference Assistant")
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
def chat(request: Request, response: Response, chat_request: ChatRequest):
    try:

        # Handle missing message
        if not chat_request.message or not chat_request.message.strip():
            return JSONResponse(status_code=400, content={"error": "Message cannot be empty."})

        # Get and return response from LLM endpoint
        history = [item.model_dump() for item in chat_request.history if item.content.strip()]
        reply = llm.get_response(chat_request.message, history)
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

# Serve frontend (/static directory) at "/"
app.mount("/", StaticFiles(directory="static", html=True), name="static")