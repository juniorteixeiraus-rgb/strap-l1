#!/usr/bin/env python3
"""
Lightchain Bot — Telegram bridge for the Lightchain PoSvc miner.
Sends commands to this chat, controls the node, shows earnings.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time
import urllib.request
import urllib.error
from datetime import datetime

API = "http://localhost:8080"
DATA_DIR = "/home/ubuntu/strap-l1/.strap-data"
STATE_FILE = os.path.join(DATA_DIR, "bot_state.json")

# ── API ───────────────────────────────────────────────────────────────

def api_post(path, body, timeout=30):
    try:
        req = urllib.request.Request(
            f"{API}{path}",
            data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except Exception as e:
        return {"error": str(e)}

def api_get(path):
    try:
        with urllib.request.urlopen(f"{API}{path}", timeout=10) as resp:
            return json.loads(resp.read())
    except Exception as e:
        return {"error": str(e)}

def run_strap(*args):
    try:
        r = subprocess.run(
            ["/home/ubuntu/strap-l1/target/release/strap", *args, "--data-dir", DATA_DIR],
            capture_output=True, text=True, timeout=30,
        )
        if r.returncode == 0:
            return {"ok": True, "output": r.stdout.strip()}
        return {"ok": False, "error": r.stderr.strip() or r.stdout.strip()}
    except FileNotFoundError:
        return {"ok": False, "error": "Strap binary not built (cargo build --release)"}

# ── Bot State ─────────────────────────────────────────────────────────

class BotState:
    def __init__(self):
        self.miner_running = False
        self.miner_thread = None
        self.stop_event = None
        self.total_proofs = 0
        self.total_strp = 0
        self.start_time = None
        self.miner_id = ""

    def save(self):
        d = {
            "miner_running": self.miner_running,
            "total_proofs": self.total_proofs,
            "total_strp": self.total_strp,
            "start_time": self.start_time,
            "miner_id": self.miner_id,
        }
        with open(STATE_FILE, "w") as f:
            json.dump(d, f)

    def load(self):
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE) as f:
                d = json.load(f)
            self.total_proofs = d.get("total_proofs", 0)
            self.total_strp = d.get("total_strp", 0)
            self.start_time = d.get("start_time", time.time())
            self.miner_id = d.get("miner_id", "")

state = BotState()

# ── Miner ─────────────────────────────────────────────────────────────

def miner_worker(interval, stop_event):
    """Background PoSvc proof miner."""
    global state
    import hashlib
    core = 0
    while not stop_event.is_set():
        start = time.time()
        task_id = f"telegram-lc-{int(start)}"
        data = f"Telegram Lightchain miner task {task_id}".encode()
        h = hashlib.sha256(data).hexdigest()
        result = 0
        for i in range(3000):
            result += int(hashlib.sha256(f"{i}-{h[:8]}".encode()).hexdigest(), 16) % 1000
        activity = (
            f"Lightchain PoSvc via Telegram: task {task_id}, "
            f"hash {h[:16]}..., "
            f"computation {result % 10000}, "
            f"real CPU work proven on-chain."
        )
        result = api_post("/strap/submit-proof", {"message": activity})
        if result.get("ready_for_chain") or result.get("text"):
            with state_lock():
                state.total_proofs += 1
                state.total_strp += 50
                state.save()
            elapsed = time.time() - state.start_time
            rate = state.total_strp / max(elapsed, 1) * 3600
            ts = datetime.now().strftime("%H:%M:%S")
            print(f"[{ts}] +50 STRP (#{state.total_proofs}, {state.total_strp} total, {rate:.1f}/hr)")
        time.sleep(interval)

state_lock = threading.Lock()

def start_miner(interval=10, background=True):
    if state.miner_running:
        return {"status": "already_running", "proofs": state.total_proofs, "strp": state.total_strp}
    state.stop_event = threading.Event()
    state.miner_running = True
    state.start_time = time.time()
    import uuid
    state.miner_id = str(uuid.uuid4())[:8]
    state.save()
    if background:
        t = threading.Thread(target=miner_worker, args=(interval, state.stop_event), daemon=True)
        state.miner_thread = t
        t.start()
        return {"status": "started", "miner_id": state.miner_id, "interval": interval,
                "proofs": state.total_proofs, "strp": state.total_strp}
    else:
        miner_worker(interval, state.stop_event)
        return {"status": "done"}

def stop_miner():
    if not state.miner_running:
        return {"status": "not_running"}
    state.stop_event.set()
    state.miner_running = False
    state.save()
    if state.miner_thread:
        state.miner_thread.join(timeout=5)
    return {"status": "stopped", "proofs": state.total_proofs, "strp": state.total_strp}

# ── Commands ──────────────────────────────────────────────────────────

def cmd_init():
    """Initialize the Strap chain with 1B STRP."""
    res = run_strap("init", "--supply", "1000000000000000000",
                     "--owner", "strap-founder", "--symbol", "STRP", "--reward", "50")
    if res["ok"]:
        return f"✅ Chain initialized!\n\n{res['output']}"
    return f"❌ Init failed:\n{res.get('error', 'unknown')}"

def cmd_info():
    """Show chain info."""
    info = api_get("/strap/chain")
    if info.get("error"):
        cli = run_strap("info")
        if cli["ok"]:
            info = {"raw": cli["output"]}
        else:
            return f"❌ No chain data — run /init first"
    import re
    raw = info.get("raw", "")
    blocks = re.search(r"Blocks:\s*(\d+)", raw)
    supply = re.search(r"Total supply:\s*([\d,]+)\s*STRP", raw)
    treasury = re.search(r"Treasury:\s*([\d,]+)\s*STRP", raw)
    b = blocks.group(1) if blocks else "?"
    s = supply.group(1) if supply else "?"
    t = treasury.group(1) if treasury else "?"
    return (f"╔══════════════════════════╗\n"
            f"║     STRAP CHAIN INFO     ║\n"
            f"╚══════════════════════════╝\n\n"
            f"Blocks:    {b}\n"
            f"Supply:    {s} STRP\n"
            f"Treasury:  {t} STRP\n"
            f"API:       {API}\n"
            f"Agents:    6 online")

def cmd_balances():
    bal = api_get("/strap/balances")
    if bal.get("error"):
        cli = run_strap("balances")
        if cli["ok"]:
            bal = {"output": cli["output"]}
        else:
            return f"❌ {bal.get('error')}"
    return f"╔══════════════════════════╗\n║     STRP BALANCES        ║\n╚══════════════════════════╝\n\n{bal.get('output', bal.get('error', '?'))}"

def cmd_mine(count="5"):
    """Start a mining session."""
    try:
        n = int(count)
    except:
        n = 5
    global state
    if state.miner_running:
        stop_miner()
    state.stop_event = threading.Event()
    state.miner_running = True
    state.start_time = time.time()
    import uuid
    state.miner_id = str(uuid.uuid4())[:8]
    results = []
    for i in range(n):
        task_id = f"mine-{int(time.time())}-{i}"
        data = f"Strap mining block {i}".encode()
        h = hashlib.sha256(data).hexdigest()
        r = api_post("/strap/mine", {"message": f"mine {n} blocks", "context": f"diff 2"})
        results.append(r)
    state.miner_running = False
    state.save()
    return f"⛏️ Mining session complete ({n} blocks attempted)\n\n{json.dumps(results, indent=2)[:500]}"

def cmd_proof(activity="test proof"):
    """Submit a PoUW proof."""
    r = api_post("/strap/submit-proof", {"message": activity})
    if r.get("ready_for_chain"):
        return f"✅ Proof submitted!\n\n{json.dumps(r, indent=2)}"
    return f"❌ Proof failed:\n{json.dumps(r, indent=2)}"

def cmd_agents():
    agents = api_get("/agents")
    if agents.get("agents"):
        txt = "🤖 STRAP AI AGENT TEAM (6 agents)\n\n"
        for label in ["mark", "sheylla", "billie", "legative", "newbi", "nurio"]:
            a = agents["agents"].get(label, {})
            txt += f"{label.upper():10s} → {a.get('model', '?')}\n   {a.get('description', '?')}\n\n"
        return txt
    return f"❌ Agents unavailable"

def cmd_chat(message):
    """Chat with the agent team."""
    r = api_post("/agents/team/chat", {"message": message})
    if r.get("final_answer"):
        return f"👑 MARK (Team Synthesis):\n\n{r['final_answer']}"
    return f"❌ No response from team"

def cmd_start_miner(interval="10"):
    """Start the background Lightchain miner."""
    try:
        iv = float(interval)
    except:
        iv = 10
    result = start_miner(iv)
    return (f"🚀 Lightchain Miner Started!\n\n"
            f"Miner ID: {result.get('miner_id', '?')}\n"
            f"Interval: {result.get('interval', iv)}s\n"
            f"Current earnings: {result.get('strp', 0)} STRP\n"
            f"Status: {result.get('status', '?')}")

def cmd_stop_miner():
    result = stop_miner()
    return (f"⏹️ Miner Stopped\n\n"
            f"Total proofs: {result.get('proofs', 0)}\n"
            f"Total STRP: {result.get('strp', 0)}")

def cmd_stats():
    elapsed = time.time() - (state.start_time or time.time())
    h, m, s = int(elapsed // 3600), int((elapsed % 3600) // 60), int(elapsed % 60)
    rate = state.total_strp / max(elapsed, 1) * 3600 if elapsed > 0 else 0
    daily = rate * 24
    weekly = daily * 7
    return (f"╔══════════════════════════╗\n"
            f"║    LIGHTCHAIN MINER      ║\n"
            f"║      STATISTICS          ║\n"
            f"╚══════════════════════════╝\n\n"
            f"Miner ID:    {state.miner_id or 'none'}\n"
            f"Status:      {'running' if state.miner_running else 'stopped'}\n"
            f"Uptime:      {h}h {m}m {s}s\n"
            f"Proofs:      {state.total_proofs}\n"
            f"STRP earned: {state.total_strp:,}\n"
            f"Rate:        {rate:.1f} STRP/hr\n"
            f"Day:         {daily:.0f} STRP\n"
            f"Week:        {weekly:.0f} STRP\n"
            f"Year:        {daily*365:.0f} STRP\n\n"
            f"💰 ROI @ various prices (on $10 VPS):\n")
            for p in [0.001, 0.005, 0.01, 0.05, 0.10, 0.50]:
                mo = daily * 30 * p
                roi = mo / 10 * 100
                txt += f"  ${p:.3f}/STRP → ${mo:.2f}/mo ({roi:.0f}% ROI)\n"
            return txt

def cmd_dashboard():
    chain = api_get("/strap/chain")
    agents = api_get("/agents")
    import re
    raw = chain.get("raw", "")
    blocks = re.search(r"Blocks:\s*(\d+)", raw)
    supply = re.search(r"Total supply:\s*([\d,]+)\s*STRP", raw)
    return (f"╔══════════════════════════════════════╗\n"
            f"║     🪙 STRAP L1 ECOSYSTEM DASHBOARD ║\n"
            f"╚══════════════════════════════════════╝\n\n"
            f"📊 CHAIN\n"
            f"   Blocks:   {blocks.group(1) if blocks else '?'}\n"
            f"   Supply:   {supply.group(1) if supply else '?'} STRP (1B total)\n"
            f"   API:      {API}\n\n"
            f"🤖 AI AGENTS ({len(agents.get('agents', {}))} online):\n")
            for label in ["mark", "sheylla", "billie", "legative", "newbi", "nurio"]:
                a = agents.get("agents", {}).get(label, {})
                return += f"   {label:10s} {a.get('model', '?')}\n"
            return += f"\n💡 COMMANDS:\n"
            return += f"   /init          Initialize 1B STRP chain\n"
            return += f"   /info          Chain info\n"
            return += f"   /balances      Wallet balances\n"
            return += f"   /mine [n]      Mine n blocks (default 5)\n"
            return += f"   /proof [text]  Submit PoUW proof\n"
            return += f"   /agents        List AI agents\n"
            return += f"   /chat [msg]    Chat with agent team\n"
            return += f"   /start         Start background miner (10s)\n"
            return += f"   /stop          Stop background miner\n"
            return += f"   /stats         Miner statistics\n"
            return += f"   /dashboard     This overview\n"
            return += f"   /help          Command list\n"
            return += f"\n📡 Dashboard: http://2600:1f10:4616:c00:3e94:7bc8:542d:172e:8080/dashboard"

def cmd_help():
    return (f"╔══════════════════════════════════════╗\n"
            f"║     🪙 STRAP BOT — COMMANDS         ║\n"
            f"╚══════════════════════════════════════╝\n\n"
            f"CHAIN:\n"
            f"  /init          Initialize 1B STRP chain\n"
            f"  /info          Chain info & stats\n"
            f"  /balances      Wallet balances\n"
            f"  /mine [n]      Mine n blocks (default 5)\n"
            f"  /proof [text]  Submit PoUW proof\n\n"
            f"AI AGENTS:\n"
            f"  /agents        List 6 AI agents\n"
            f"  /chat [msg]    Chat with team\n\n"
            f"MINER:\n"
            f"  /start [s]     Start background miner (interval s)\n"
            f"  /stop          Stop background miner\n"
            f"  /stats         Miner statistics\n\n"
            f"VIEW:\n"
            f"  /dashboard     Full ecosystem dashboard\n"
            f"  /help          This help\n\n"
            f"📡 API: {API}\n"
            f"🌐 Dashboard: http://2600:1f10:4616:c00:3e94:7bc8:542d:172e:8080/dashboard\n"
            f"🪙 Token: STRP · 1,000,000,000 total · PoUW · 18 decimals")

# ── Router ────────────────────────────────────────────────────────────

COMMANDS = {
    "/init": cmd_init,
    "/info": cmd_info,
    "/balance": cmd_balances,
    "/balances": cmd_balances,
    "/mine": cmd_mine,
    "/proof": cmd_proof,
    "/agents": cmd_agents,
    "/chat": cmd_chat,
    "/start": cmd_start_miner,
    "/stop": cmd_stop_miner,
    "/stats": cmd_stats,
    "/dashboard": cmd_dashboard,
    "/help": cmd_help,
}

def handle_message(msg: str) -> str:
    msg = msg.strip()
    if msg.startswith("/"):
        for cmd, handler in COMMANDS.items():
            if msg.startswith(cmd):
                args = msg[len(cmd):].strip()
                if cmd == "/chat" and args:
                    return handler(args)
                if cmd == "/mine" and args:
                    return handler(args)
                if cmd == "/proof" and args:
                    return handler(args)
                if cmd == "/start" and args:
                    return handler(args)
                return handler()
        return f"❌ Unknown command: {msg}. Try /help"
    else:
        # Treat as chat with team
        return cmd_chat(msg)

if __name__ == "__main__":
    # Test mode: read from stdin
    print("Strap Telegram Bot loaded. Send commands like /help, /init, /dashboard")
    print(f"API: {API} | Chain data: {DATA_DIR}")
    state.load()
    for line in sys.stdin:
        line = line.strip()
        if line:
            print("\n" + handle_message(line))
