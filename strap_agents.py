"""
strap-agents — Multi-Agent system on OpenRouter.
             7 specialized AI agents working together over the Strap L1 blockchain.

Agents
-------
  mark    → nex-agi/nex-n2.5-pro:free       (orchestrator / lead)
  sheylla → inclusionai/ling-3.0-flash-sante:free (creative / content)
  billie  → liquid/lfm-2.5-embedding-350m:free    (analysis / embeddings)
  legative→ nvidia/nemotron-3.5-lightning:free    (logic / reasoning)
  newbi   → poolside/laguna-s-2.1:free            (learning / research)
  nurio   → liquid/lfm-2.5-2.6b:free              (assistant / chat)

Endpoints
---------
GET  /health              — liveness + agent roster
GET  /models             — all 7 models
GET  /agents             — agent metadata (name, label, model)
POST /chat/completions   — chat with any agent or orchestrate all
POST /agents/{label}/chat — chat with a specific agent
POST /agents/team/chat   — all agents collaborate on a task
POST /strap/mine         — AI-assisted Strap PoUW mining (calls legative + newbi)
POST /strap/submit-proof — submit a PoUW proof (calls sheylla for metadata)
GET  /strap/chain        — chain info (proxied to strap CLI)
GET  /strap/balances     — show balances

Run
---
  # Usage: OPENROUTER_API_KEY=sk-or-... uvicorn strap_agents:app --host 0.0.0.0 --port 8080
"""

from __future__ import annotations

import json
import os
import subprocess
import time
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field

# ── Config ────────────────────────────────────────────────────────

OPENROUTOR_BASE = "https://openrouter.ai/api/v1"
API_KEY = os.environ.get(
    "OPENROUTER_API_KEY",
    "",  # Set OPENROUTER_API_KEY env var to use agents
)

# ── 7 Agents ──────────────────────────────────────────────────────

AGENTS = {
    "mark": {
        "label": "Mark — Lead Orchestrator",
        "model": "nex-agi/nex-n2.5-pro:free",
        "description": "Lead AI orchestrator. Coordinates the other agents, makes final decisions.",
        "role": "system",
        "system_prompt": (
            "You are MARK, the lead orchestrator of the Strap AI Agent team. "
            "Your job is to coordinate the other 6 agents (sheylla, billie, legative, newbi, nurio) "
            "to accomplish tasks related to the Strap L1 Proof-of-Useful-Work blockchain. "
            "You can delegate to specific agents, synthesize their outputs, and produce final results. "
            "Be decisive, clear, and action-oriented."
        ),
    },
    "sheylla": {
        "label": "Sheylla — Creative & Content",
        "model": "inclusionai/ling-3.0-flash-sante:free",
        "description": "Creative AI: writes content, marketing, activity descriptions, community messages.",
        "role": "creative",
        "system_prompt": (
            "You are SHEYLA, the creative AI of the Strap team. "
            "You write engaging content: marketing copy, activity descriptions for PoUW proofs, "
            "community announcements, social media posts about Strap L1. "
            "Be vivid, energetic, and blockchain-native in your writing."
        ),
    },
    "billie": {
        "label": "Billie — Analysis & Embeddings",
        "model": "liquid/lfm-2.5-embedding-350m:free",
        "description": "Analytical AI: data analysis, pattern recognition, embedding-based insights.",
        "role": "analysis",
        "system_prompt": (
            "You are BILLIE, the analytical AI of the Strap team. "
            "You analyze data, find patterns, summarize chain activity, "
            "and provide data-driven insights about the Strap L1 ecosystem. "
            "Be precise, factual, and quantitative."
        ),
    },
    "legative": {
        "label": "Legative — Logic & Reasoning",
        "model": "nvidia/nemotron-3.5-lightning:free",
        "description": "Logical AI: reasoning, proof verification strategy, economic modeling.",
        "role": "logic",
        "system_prompt": (
            "You are LEGATIVE, the logical AI of the Strap team. "
            "You handle reasoning tasks: proof-of-work strategy, economic modeling, "
            "tokenomics analysis, consensus logic, and structured problem solving. "
            "Be rigorous, step-by-step, and precise."
        ),
    },
    "newbi": {
        "label": "Newbi — Learning & Research",
        "model": "poolside/laguna-s-2.1:free",
        "description": "Research AI: learns about new topics, researches blockchain tech, finds information.",
        "role": "research",
        "system_prompt": (
            "You are NEWBI, the research AI of the Strap team. "
            "You learn about new topics, research blockchain technology, "
            "find relevant information, and explain complex concepts simply. "
            "Be curious, thorough, and educational."
        ),
    },
    "nurio": {
        "label": "Nurio — Assistant & Chat",
        "model": "liquid/lfm-2.5-2.6b:free",
        "description": "Assistant AI: general chat, user support, quick answers.",
        "role": "assistant",
        "system_prompt": (
            "You are NURIO, the assistant AI of the Strap team. "
            "You handle general questions, user support, and quick conversational tasks. "
            "Be friendly, helpful, and concise. "
            "You are part of the Strap L1 Proof-of-Useful-Work blockchain project."
        ),
    },
}

ALL_MODELS = sorted({a["model"] for a in AGENTS.values()})
DEFAULT_MODEL = AGENTS["mark"]["model"]

# ── App ───────────────────────────────────────────────────────────

app = FastAPI(
    title="Strap AI Agents",
    description="7 specialized AI agents powered by OpenRouter, working together on the Strap L1 PoUW blockchain",
    version="1.0.0",
)

http = httpx.Client(base_url=OPENROUTOR_BASE, timeout=60.0)


# ── Pydantic models ───────────────────────────────────────────────

class ChatMessage(BaseModel):
    role: str = Field(..., pattern=r"^(system|user|assistant|developer)$")
    content: str | None = None
    name: str | None = None


class ChatRequest(BaseModel):
    model: str | None = None  # optional override
    messages: list[ChatMessage] = Field(..., min_length=1)
    max_tokens: int | None = Field(default=4096, ge=1, le=16384)
    temperature: float | None = Field(default=0.7, ge=0.0, le=2.0)
    stream: bool = False


class AgentChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    context: str | None = None
    max_tokens: int | None = Field(default=4096, ge=1, le=16384)
    temperature: float | None = Field(default=0.7, ge=0.0, le=2.0)


class TeamChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    agents: list[str] = Field(default=["mark", "sheylla", "legative", "newbi", "nurio", "billie"])
    context: str | None = None


class SimpleResponse(BaseModel):
    text: str
    model: str
    agent: str
    tokens_used: int = 0


class TeamResponse(BaseModel):
    final_answer: str
    agent_results: dict[str, str]
    orchestrator: str


# ── Internal helpers ──────────────────────────────────────────────

def _call_openrouter(model: str, messages: list[dict[str, Any]], max_tokens: int, temperature: float) -> dict[str, Any]:
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://strap.local",
        "X-Title": "Strap AI Agents",
    }
    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": False,
    }
    try:
        resp = http.post("/chat/completions", json=payload, headers=headers, timeout=90.0)
    except httpx.ConnectError:
        raise HTTPException(status_code=502, detail="OpenRouter unreachable")
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="OpenRouter timed out")

    if resp.status_code == 401:
        raise HTTPException(status_code=401, detail="Invalid OpenRouter API key")
    if resp.status_code >= 500:
        raise HTTPException(status_code=502, detail=f"OpenRouter error {resp.status_code}")

    try:
        return resp.json()
    except Exception:
        raise HTTPException(status_code=502, detail=f"Bad response: {resp.text[:200]}")


def _agent_chat(agent_label: str, message: str, context: str | None, max_tokens: int, temperature: float) -> dict[str, Any]:
    agent = AGENTS.get(agent_label)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Unknown agent: {agent_label}. Available: {list(AGENTS.keys())}")

    sys_prompt = agent["system_prompt"]
    user_msg = message
    if context:
        user_msg = f"[Context]\n{context}\n\n[User message]\n{message}"

    messages = [
        {"role": "system", "content": sys_prompt},
        {"role": "user", "content": user_msg},
    ]

    result = _call_openrouter(agent["model"], messages, max_tokens, temperature)
    choice = result.get("choices", [{}])[0]
    msg = choice.get("message", {})
    usage = result.get("usage", {})
    return {
        "text": msg.get("content", ""),
        "model": agent["model"],
        "agent": agent_label,
        "label": agent["label"],
        "tokens_used": usage.get("total_tokens", 0),
    }


def _team_collaboration(message: str, agent_labels: list[str], context: str | None) -> dict[str, Any]:
    """Have agents collaborate: each responds, then mark synthesizes."""
    results: dict[str, str] = {}

    # Phase 1: each agent responds
    for label in agent_labels:
        if label not in AGENTS:
            continue
        try:
            res = _agent_chat(label, message, context, max_tokens=2048, temperature=0.7)
            results[label] = res["text"]
        except Exception as e:
            results[label] = f"[Error: {e}]"

    # Phase 2: mark synthesizes
    synthesis_prompt = (
        f"TEAM INPUT:\n{message}\n\n"
        f"CONTEXT:\n{context or 'None'}\n\n"
        f"AGENT RESPONSES:\n"
    )
    for label, text in results.items():
        synthesis_prompt += f"\n--- {label.upper()} ---\n{text}"

    synthesis_prompt += (
        "\n\nSYNTHESIS TASK:\n"
        "Review all agent responses above. Identify agreements, disagreements, and gaps. "
        "Produce a final, comprehensive answer that draws on the best insights from each agent. "
        "Be concise but complete. Cite which agents contributed key points."
    )

    try:
        synth = _agent_chat("mark", synthesis_prompt, None, max_tokens=4096, temperature=0.5)
        return {
            "final_answer": synth["text"],
            "agent_results": results,
            "orchestrator": "mark",
        }
    except Exception as e:
        return {
            "final_answer": f"Synthesis failed: {e}\n\nRaw results:\n" + "\n\n".join(f"{k}: {v}" for k, v in results.items()),
            "agent_results": results,
            "orchestrator": "mark (failed)",
        }


# ── Endpoints ─────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "agents": len(AGENTS),
        "models": len(ALL_MODELS),
        "agent_labels": list(AGENTS.keys()),
    }


@app.get("/models")
async def list_models():
    return {
        "data": [
            {"id": m, "object": "model", "created": int(time.time()), "owned_by": "strap-agents"}
            for m in ALL_MODELS
        ],
        "object": "list",
    }


@app.get("/agents")
async def list_agents():
    return {
        "agents": {
            label: {
                "label": info["label"],
                "model": info["model"],
                "description": info["description"],
                "role": info["role"],
            }
            for label, info in AGENTS.items()
        }
    }


@app.post("/chat/completions")
async def chat_completions(req: ChatRequest):
    """OpenAI-compatible endpoint. If no model specified, uses mark (orchestrator)."""
    if req.model and req.model not in ALL_MODELS:
        raise HTTPException(status_code=400, detail=f"Unknown model. Available: {ALL_MODELS}")

    model = req.model or DEFAULT_MODEL
    messages = [{"role": m.role, "content": m.content or "", "name": m.name} for m in req.messages]
    result = _call_openrouter(model, messages, req.max_tokens or 4096, req.temperature or 0.7)

    choices = []
    for i, c in enumerate(result.get("choices", [])):
        msg = c.get("message", {})
        choices.append({
            "index": i,
            "message": {"role": msg.get("role", "assistant"), "content": msg.get("content", "")},
            "finish_reason": c.get("finish_reason", "stop"),
        })

    usage = result.get("usage", {})
    return {
        "id": result.get("id", f"chatcmpl-{int(time.time())}"),
        "object": "chat.completion",
        "created": result.get("created", int(time.time())),
        "model": result.get("model", model),
        "choices": choices,
        "usage": {
            "prompt_tokens": usage.get("prompt_tokens", 0),
            "completion_tokens": usage.get("completion_tokens", 0),
            "total_tokens": usage.get("total_tokens", 0),
        },
    }


@app.post("/agents/{label}/chat", response_model=SimpleResponse)
async def agent_chat(label: str, req: AgentChatRequest):
    """Chat with a specific named agent."""
    return _agent_chat(label, req.message, req.context, req.max_tokens or 4096, req.temperature or 0.7)


@app.post("/agents/team/chat")
async def team_chat(req: TeamChatRequest):
    """All agents collaborate on a message. Mark synthesizes the final answer."""
    labels = [l for l in req.agents if l in AGENTS] if req.agents else list(AGENTS.keys())
    if not labels:
        raise HTTPException(status_code=400, detail="No valid agents specified")

    result = _team_collaboration(req.message, labels, req.context)
    return result


@app.post("/strap/mine")
async def strap_mine(req: AgentChatRequest):
    """
    AI-assisted Strap PoUW mining.
    legative plans the proof strategy, newbi researches, mark orchestrates.
    Returns a mining plan and suggested proof parameters.
    """
    prompt = (
        f"STRAP L1 PROOF-OF-USEFUL-WORK MINING REQUEST\n"
        f"Activity description: {req.message}\n"
        f"Context: {req.context or 'None'}\n\n"
        f"Your task:\n"
        f"1. Analyze what kind of PoUW proof this activity would generate\n"
        f"2. Suggest proof parameters (difficulty, metadata, proof type)\n"
        f"3. Estimate mining time and reward\n"
        f"4. Provide a step-by-step mining plan\n\n"
        f"STRAP L1 ECONOMICS:\n"
        f"- Reward per proof: 50 STRP\n"
        f"- Block reward: 10 STRP\n"
        f"- Proof types: ComputeWork(0), PhysicalActivity(1), DataValidation(2), CreativeWork(3)\n"
        f"- Difficulty: leading zero bytes in SHA256 hash\n"
        f"- Current chain: ./strap-data/chain.json\n"
    )
    res = _agent_chat("legative", prompt, req.context, max_tokens=2048, temperature=0.5)
    # Also get newbi's research input
    try:
        research = _agent_chat("newbi", f"Research and explain: {req.message}", req.context, max_tokens=1024, temperature=0.7)
        res["research_notes"] = research["text"]
    except Exception:
        res["research_notes"] = "[research unavailable]"

    return res


@app.post("/strap/submit-proof")
async def strap_submit_proof(req: AgentChatRequest):
    """
    Prepare a PoUW proof submission using sheylla's creative writing for metadata.
    Returns enriched proof metadata ready for the strap CLI.
    """
    prompt = (
        f"Prepare PoUW proof metadata for this activity:\n{req.message}\n\n"
        f"Write a vivid, engaging 2-3 sentence description of this activity "
        f"that would appear on-chain as proof metadata. "
        f"Include: what happened, why it was useful, and the energy/effort involved. "
        f"Keep it under 200 characters for on-chain storage.\n\n"
        f"Respond with ONLY the metadata text, no other commentary."
    )
    sheylla_result = _agent_chat("sheylla", prompt, req.context, max_tokens=512, temperature=0.8)

    legative_prompt = (
        f"Based on this activity and metadata, suggest optimal proof parameters:\n"
        f"Activity: {req.message}\n"
        f"Metadata: {sheylla_result['text']}\n\n"
        f"Suggest: proof_type (0-3), difficulty level (1-4), and a sensor data hash prefix.\n"
        f"Respond as JSON: {{\"proof_type\": int, \"difficulty\": int, \"hash_prefix\": \"hex\"}}"
    )
    try:
        params = _agent_chat("legative", legative_prompt, None, max_tokens=256, temperature=0.3)
        import json as json_mod
        try:
            params_json = json_mod.loads(params["text"])
        except Exception:
            params_json = {"proof_type": 1, "difficulty": 2, "hash_prefix": "00"}
    except Exception:
        params_json = {"proof_type": 1, "difficulty": 2, "hash_prefix": "00"}

    return {
        "metadata": sheylla_result["text"],
        "proof_params": params_json,
        "activity": req.message,
        "ready_for_chain": True,
        "suggested_cli": f"strap submit-proof --activity \"{sheylla_result['text']}\" --proof_type {params_json.get('proof_type', 1)}",
    }


@app.get("/strap/chain")
async def strap_chain_info():
    """Proxy to strap CLI: chain info."""
    try:
        result = subprocess.run(
            ["/home/ubuntu/strap-l1/target/release/strap", "info", "--data-dir", "/home/ubuntu/strap-l1/.strap-data"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode != 0:
            return {"error": result.stderr, "note": "Run 'strap init' first to create the chain"}
        return {"output": result.stdout}
    except FileNotFoundError:
        return {"error": "strap binary not found. Build with: cd /home/ubuntu/strap-l1 && cargo build --release"}
    except Exception as e:
        return {"error": str(e)}


@app.get("/strap/balances")
async def strap_balances():
    """Proxy to strap CLI: show balances."""
    try:
        result = subprocess.run(
            ["/home/ubuntu/strap-l1/target/release/strap", "balances", "--data-dir", "/home/ubuntu/strap-l1/.strap-data"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode != 0:
            return {"error": result.stderr, "note": "Run 'strap init' first"}
        return {"output": result.stdout}
    except FileNotFoundError:
        return {"error": "strap binary not found"}
    except Exception as e:
        return {"error": str(e)}


@app.on_event("startup")
async def _startup():
    print(f"✅ Strap AI Agents started — {len(AGENTS)} agents, {len(ALL_MODELS)} models")
    for label, info in AGENTS.items():
        print(f"   {label:10s} → {info['model']:50s} ({info['label']})")
    try:
        r = http.get("/models", headers={"Authorization": f"Bearer {API_KEY}"})
        if r.status_code == 200:
            print("✅ OpenRouter API key validated")
        else:
            print(f"⚠️  OpenRouter key validation returned {r.status_code}")
    except Exception as e:
        print(f"⚠️  OpenRouter unreachable at startup: {e}")


@app.on_event("shutdown")
async def _shutdown():
    http.close()


@app.get("/dashboard")
async def dashboard():
    """Serve the Strap L1 web dashboard (HTML)."""
    try:
        with open("/home/ubuntu/strap-l1/dashboard.html", "r") as f:
            html = f.read()
        return Response(content=html, media_type="text/html")
    except FileNotFoundError:
        return JSONResponse(status_code=404, content={"error": "Dashboard not found — dashboard.html missing"})


# ── Token allocation endpoint ─────────────────────────────────────────

@app.get("/api/allocation")
async def token_allocation():
    """Return the 1B STRP token allocation breakdown."""
    return {
        "total_supply": 1_000_000_000,
        "symbol": "STRP",
        "decimals": 18,
        "allocations": [
            {"name": "Genesis Founder",      "pct": 15, "tokens": 150_000_000, "purpose": "Initial owner (strap-founder)"},
            {"name": "PoUW Mining Rewards",  "pct": 35, "tokens": 350_000_000, "purpose": "Released via proof mining over time"},
            {"name": "Ecosystem & Dev",      "pct": 20, "tokens": 200_000_000, "purpose": "Treasury-controlled, community governance"},
            {"name": "Community Airdrop",    "pct": 10, "tokens": 100_000_000, "purpose": "Distributed to early participants"},
            {"name": "Staking Rewards Pool", "pct": 10, "tokens": 100_000_000, "purpose": "For STRP stakers securing the network"},
            {"name": "Liquidity & Exchange", "pct":  5, "tokens":  50_000_000, "purpose": "DEX/CEX listing liquidity"},
            {"name": "AI Agent Rewards",     "pct":  5, "tokens":  50_000_000, "purpose": "Reserved for the 7-agent AI system"},
        ]
    }


@app.get("/api/supply")
async def live_supply():
    """Return circulating supply by reading chain data."""
    try:
        result = subprocess.run(
            ["/home/ubuntu/strap-l1/target/release/strap", "info", "--data-dir", "/home/ubuntu/strap-l1/.strap-data"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode != 0:
            return {"error": "Chain not initialized", "note": "Run /strap/init first"}
        # Parse "Total supply: X STRP"
        import re
        m = re.search(r"Total supply:\s*([\d,]+)\s*STRP", result.stdout)
        total = int(m.group(1).replace(",", "")) if m else 0
        m2 = re.search(r"Treasury:\s*([\d,]+)\s*STRP", result.stdout)
        treasury = int(m2.group(1).replace(",", "")) if m2 else 0
        return {"total_supply": total, "treasury": treasury, "circulating": total - treasury, "symbol": "STRP"}
    except FileNotFoundError:
        return {"error": "strap binary not found"}
    except Exception as e:
        return {"error": str(e)}


@app.post("/strap/init")
async def strap_init(req: AgentChatRequest):
    """Initialize the Strap chain with 1B tokens."""
    try:
        result = subprocess.run(
            ["/home/ubuntu/strap-l1/target/release/strap", "init",
             "--supply", "1000000000000000000",
             "--owner", "strap-founder",
             "--symbol", "STRP",
             "--reward", "50",
             "--data-dir", "/home/ubuntu/strap-l1/.strap-data"],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0:
            return {"error": result.stderr, "note": "Binary may not be built yet"}
        return {"output": result.stdout, "status": "ok"}
    except FileNotFoundError:
        return {"error": "strap binary not found — build with cargo build --release"}
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/rewards")
async def reward_info():
    """Return PoUW reward structure."""
    return {
        "proof_types": [
            {"type": "ComputeWork",       "enum": 0, "reward": 10, "description": "AI inference, data processing, rendering"},
            {"type": "PhysicalActivity",  "enum": 1, "reward": 50, "description": "Real-world activity (e.g., Bang-jump bridge)"},
            {"type": "DataValidation",    "enum": 2, "reward": 30, "description": "Data verification, oracle feeds"},
            {"type": "CreativeWork",      "enum": 3, "reward": 40, "description": "Content creation, art, writing"},
        ],
        "block_reward": 10,
        "reward_per_proof": 50,
        "treasury_rate": 0.10,
        "block_time_target": "30s",
        "total_supply": 1_000_000_000,
    }


# ── CLI helper for testing ───────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080, log_level="info")
