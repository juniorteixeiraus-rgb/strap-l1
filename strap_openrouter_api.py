"""
strap-openrouter-api — FastAPI chat proxy over OpenRouter.

Endpoints
---------
POST /chat/completions  — OpenAI-compatible chat endpoint
GET  /models            — list available models
POST /chat/complete     — simple single-request chat (json-in, text-out)
GET  /health            — liveness

Models (free tier)
-------------------
- inclusionai/ling-3.0-flash-fin:free
- nvidia/nemotron-3.5-lightning:free

Run
---
  uvicorn strap_openrouter_api:app --host 0.0.0.0 --port 8080 --reload
"""

from __future__ import annotations

import os
import time
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

# ── Config ──────────────────────────────────────────────────────────────

OPENROUTER_BASE = "https://openrouter.ai/api/v1"
API_KEY = os.environ.get("OPENROUTER_API_KEY", "")

MODELS = [
    "inclusionai/ling-3.0-flash-fin:free",
    "nvidia/nemotron-3.5-lightning:free",
]

DEFAULT_MODEL = MODELS[0]

# ── App ──────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Strap OpenRouter API",
    description="Chat proxy over OpenRouter (free models: Ling Flash, Nemotron Lightning)",
    version="0.1.0",
)

# ── HTTP client ──────────────────────────────────────────────────────────

http = httpx.Client(base_url=OPENROUTER_BASE, timeout=30.0)


# ── Pydantic models ──────────────────────────────────────────────────────

class ChatMessage(BaseModel):
    role: str = Field(..., pattern="^(system|user|assistant|tool)$")
    content: str | None = None
    name: str | None = None
    tool_calls: list[dict[str, Any]] | None = None


class ChatCompletionRequest(BaseModel):
    model: str = Field(default=DEFAULT_MODEL, pattern=r"^(inclusionai/ling-3.0-flash-fin:free|nvidia/nemotron-3.5-lightning:free)$")
    messages: list[ChatMessage] = Field(..., min_length=1)
    max_tokens: int | None = Field(default=4096, ge=1, le=16384)
    temperature: float | None = Field(default=0.7, ge=0.0, le=2.0)
    top_p: float | None = Field(default=1.0, ge=0.0, le=1.0)
    stream: bool = False
    stop: list[str] | None = None
    frequency_penalty: float | None = Field(default=None, ge=-2.0, le=2.0)
    presence_penalty: float | None = Field(default=None, ge=-2.0, le=2.0)


class ChatCompletionResponseChoice(BaseModel):
    index: int = 0
    message: dict[str, str]
    finish_reason: str = "stop"


class UsageInfo(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: list[ChatCompletionResponseChoice]
    usage: UsageInfo


# ── Helpers ──────────────────────────────────────────────────────────────

def _to_openrouter_messages(messages: list[ChatMessage]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for m in messages:
        obj: dict[str, Any] = {"role": m.role, "content": m.content or ""}
        if m.name:
            obj["name"] = m.name
        if m.tool_calls:
            obj["tool_calls"] = m.tool_calls
        out.append(obj)
    return out


def _openai_error(status: int, message: str, error_type: str = "APIError"):
    return JSONResponse(
        status_code=status,
        content={"error": {"message": message, "type": error_type, "param": None, "code": None}},
    )


# ── Endpoints ────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "models": MODELS, "default_model": DEFAULT_MODEL}


@app.get("/models")
async def list_models():
    return {
        "data": [
            {"id": m, "object": "model", "created": int(time.time()), "owned_by": "stickers"}
            for m in MODELS
        ],
        "object": "list",
    }


@app.post("/chat/completions", response_model=ChatCompletionResponse | None)
async def chat_completions(req: ChatCompletionRequest):
    if not API_KEY or API_KEY.startswith("sk-or-v1-") is False:
        # still allow empty key for testing — will 401 from OpenRouter
        pass

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://strap.local",  # optional, helps OpenRouter attribute
        "X-Title": "Strap L1 Chat API",
    }

    payload: dict[str, Any] = {
        "model": req.model,
        "messages": _to_openrouter_messages(req.messages),
        "max_tokens": req.max_tokens,
        "temperature": req.temperature,
        "top_p": req.top_p,
        "stream": req.stream,
    }
    if req.stop:
        payload["stop"] = req.stop
    if req.frequency_penalty is not None:
        payload["frequency_penalty"] = req.frequency_penalty
    if req.presence_penalty is not None:
        payload["presence_penalty"] = req.presence_penalty

    try:
        resp = http.post("/chat/completions", json=payload, headers=headers)
    except httpx.ConnectError:
        raise HTTPException(status_code=502, detail="OpenRouter unreachable")
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="OpenRouter timed out")

    if resp.status_code == 401:
        return _openai_error(401, "Invalid API key", "AuthenticationError")
    if resp.status_code == 404:
        return _openai_error(404, f"Model '{req.model}' not found", "NotFound")
    if resp.status_code == 429:
        return _openai_error(429, "Rate limit exceeded", "RateLimitError")
    if resp.status_code >= 500:
        return _openai_error(resp.status_code, "OpenRouter server error", "APIError")

    if resp.status_code != 200:
        try:
            body = resp.json()
            detail = body.get("error", {}).get("message", resp.text)
        except Exception:
            detail = resp.text
        raise HTTPException(status_code=resp.status_code, detail=detail)

    data = resp.json()

    # Convert to OpenAI-compatible response shape (non-streaming)
    choices = []
    for i, c in enumerate(data.get("choices", [])):
        msg = c.get("message", {})
        choices.append(
            ChatCompletionResponseChoice(
                index=c.get("index", i),
                message={"role": msg.get("role", "assistant"), "content": msg.get("content", "")},
                finish_reason=c.get("finish_reason", "stop"),
            )
        )

    usage = data.get("usage", {})
    return ChatCompletionResponse(
        id=data.get("id", f"chatcmpl-{int(time.time())}"),
        created=data.get("created", int(time.time())),
        model=data.get("model", req.model),
        choices=choices,
        usage=UsageInfo(
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            total_tokens=usage.get("total_tokens", 0),
        ),
    )


# ── Simple complete (single-turn convenience) ───────────────────────────

class SimpleChatRequest(BaseModel):
    model: str = Field(default=DEFAULT_MODEL, pattern=r"^(inclusionai/ling-3.0-flash-fin:free|nvidia/nemotron-3.5-lightning:free)$")
    prompt: str = Field(..., min_length=1)
    system: str | None = None
    max_tokens: int = Field(default=4096, ge=1, le=16384)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)


@app.post("/chat/complete")
async def simple_chat(req: SimpleChatRequest):
    messages: list[ChatMessage] = []
    if req.system:
        messages.append(ChatMessage(role="system", content=req.system))
    messages.append(ChatMessage(role="user", content=req.prompt))

    body = ChatCompletionRequest(
        model=req.model,
        messages=messages,
        max_tokens=req.max_tokens,
        temperature=req.temperature,
    )
    resp = await chat_completions(body)
    if isinstance(resp, JSONResponse):
        # forward error responses as-is
        return resp

    text = ""
    for choice in resp.choices:
        text += choice.message.get("content", "")
    return {"text": text, "model": resp.model, "id": resp.id}


# ── Warmup on startup ───────────────────────────────────────────────────

@app.on_event("startup")
async def _startup():
    # quick model list ping to validate key
    try:
        r = http.get("/models", headers={"Authorization": f"Bearer {API_KEY}"})
        if r.status_code != 200:
            print(f"⚠️  OpenRouter key validation returned {r.status_code} — chat will likely 401")
        else:
            print(f"✅ OpenRouter API key validated. Models: {MODELS}")
    except Exception as e:
        print(f"⚠️  Could not reach OpenRouter at startup: {e}")


@app.on_event("shutdown")
async def _shutdown():
    http.close()
