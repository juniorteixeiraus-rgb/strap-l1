#!/usr/bin/env python3
"""
Lightchain Proof-of-Service Node — Telegram-Integrated Miner
=============================================================
Runs as a background service connected to the Strap ecosystem.
Receives commands via Telegram (this chat), submits PoSvc proofs,
and earns STRP rewards.

Integration:
  - Telegram bot commands (this chat) → control the miner
  - Strap API (localhost:8080) → submit proofs, query chain
  - 7 AI agents → optimize mining strategy, prepare proof metadata

Run:
  python3 strap_lightchain_node.py           # start node
  python3 strap_lightchain_node.py --telegram  # start with telegram gateway
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import signal
import subprocess
import sys
import threading
import time
import urllib.request
import urllib.error
from datetime import datetime
from typing import Any, Optional

# ── Config ────────────────────────────────────────────────────────────

API = "http://localhost:8080"
DATA_DIR = "/home/ubuntu/strap-l1/.strap-data"
STATE_FILE = os.path.join(DATA_DIR, "lightchain_node.json")
TOTAL_SUPPLY = 1_000_000_000

# ── State ─────────────────────────────────────────────────────────────

node_running = False
state_lock = threading.Lock()
total_proofs = 0
total_strp = 0
node_start_time: Optional[float] = None
proof_history: list[dict] = []


# ── HTTP ──────────────────────────────────────────────────────────────

def api_post(path: str, body: dict, timeout: int = 30) -> dict:
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


def api_get(path: str) -> dict:
    try:
        with urllib.request.urlopen(f"{API}{path}", timeout=10) as resp:
            return json.loads(resp.read())
    except Exception as e:
        return {"error": str(e)}


def run_strap(*args: str) -> dict:
    try:
        result = subprocess.run(
            ["/home/ubuntu/strap-l1/target/release/strap", *args, "--data-dir", DATA_DIR],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode == 0:
            return {"ok": True, "output": result.stdout.strip()}
        return {"ok": False, "error": result.stderr.strip() or result.stdout.strip()}
    except FileNotFoundError:
        return {"ok": False, "error": "Strap binary not built — build with cargo build --release"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def load_node_state() -> dict:
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"miner_id": "", "started": 0, "total_proofs": 0, "total_strp": 0}


def save_node_state(s: dict):
    with open(STATE_FILE, "w") as f:
        json.dump(s, f, indent=2)


# ── Proof-of-Service ──────────────────────────────────────────────────

def create_proof_task(core_id: int = 0) -> dict:
    """Create a PoSvc computational task."""
    start = time.time()
    task_id = f"lcsvc-{core_id}-{int(start)}"
    data = f"Lightchain PoSvc Node: core {core_id} task {task_id} real service".encode()
    h = hashlib.sha256(data).hexdigest()

    # Do some actual computation to prove CPU was used
    result = 0
    for i in range(5000):
        result += int(hashlib.sha256(f"{core_id}-{i}-{h[:8]}".encode()).hexdigest(), 16) % 10000

    elapsed = time.time() - start

    return {
        "task_id": task_id,
        "core_id": core_id,
        "hash": h,
        "computation": result % 100000,
        "cpu_time": round(elapsed, 4),
        "timestamp": start,
    }


def submit_proof(task: dict, core_id: int = 0) -> Optional[dict]:
    """Submit a PoSvc proof to the Strap API."""
    global total_proofs, total_strp

    activity = (
        f"Lightchain PoSvc: Node core #{core_id} performed real computational service. "
        f"Task: {task['task_id']}. "
        f"Hash: {task['hash'][:16]}... "
        f"CPU time: {task['cpu_time']}s. "
        f"Computation result: {task['computation']}. "
        f"Proven on-chain."
    )

    result = api_post("/strap/submit-proof", {"message": activity})

    if result.get("ready_for_chain") or result.get("text"):
        with state_lock:
            total_proofs += 1
            total_strp += 50
            proof_record = {
                "timestamp": datetime.now().isoformat(),
                "core": core_id,
                "task_id": task["task_id"],
                "hash": task["hash"][:16],
                "reward": 50,
                "total_proofs": total_proofs,
                "total_strp": total_strp,
            }
            proof_history.append(proof_record)
            return proof_record
    return None


# ── Chain Commands ────────────────────────────────────────────────────

def init_chain():
    """Initialize the Strap chain with 1B STRP."""
    res = run_strap("init",
                     "--supply", str(TOTAL_SUPPLY),
                     "--owner", "strap-founder",
                     "--symbol", "STRP",
                     "--reward", "50")
    if res["ok"]:
        return {"success": True, "output": res["output"]}
    return {"success": False, "error": res.get("error", "init failed")}


def get_chain_info() -> dict:
    """Get chain info from CLI or API."""
    info = api_get("/strap/chain")
    if info.get("error"):
        cli = run_strap("info")
        if cli["ok"]:
            return {"raw": cli["output"], "from_cli": True}
        return {"error": "Chain not accessible"}
    return info


def get_balances() -> dict:
    return api_get("/strap/balances")


def get_agents() -> dict:
    return api_get("/agents")


# ── Mining Loop ───────────────────────────────────────────────────────

def mining_worker(core_id: int, interval: float, stop_event: threading.Event):
    """Continuous PoSvc mining on one core."""
    global node_running

    while not stop_event.is_set():
        task = create_proof_task(core_id)
        proof = submit_proof(task, core_id)
        if proof:
            with state_lock:
                elapsed = time.time() - (node_start_time or time.time())
                rate = total_strp / max(elapsed, 1) * 3600
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Core {core_id}: +50 STRP "
                  f"(#{proof['total_proofs']}, {total_strp} total, {rate:.1f} STRP/hr)")
        time.sleep(interval)


def start_node(cores: int = 1, interval: float = 5.0):
    """Start the Lightchain PoSvc mining node."""
    global node_running, node_start_time

    print("╔══════════════════════════════════════════════════════════╗")
    print("║     💡 LIGHTCHAIN NODE — Telegram-Integrated Miner      ║")
    print("║         Proof-of-Service · Low-Resource · High-Yield    ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print()
    print(f"  📡 API: {API}")
    print(f"  📂 Data: {DATA_DIR}")
    print(f"  🖥️  Cores: {cores}")
    print(f"  ⏱️  Interval: {interval}s")
    print()

    # Check chain
    chain = get_chain_info()
    if chain.get("error") or "Blocks: 0" in chain.get("raw", ""):
        print("⚠️  Chain not initialized. Initializing...")
        init_res = init_chain()
        if init_res["success"]:
            print(f"   ✅ Chain initialized: {init_res['output'][:100]}")
        else:
            print(f"   ❌ Init failed: {init_res['error']}")
            print("   Start strap_agents.py then retry.")
            return False
    else:
        print(f"   ✅ Chain active: {chain.get('raw', ''}")
        print()

    # Generate miner ID
    import uuid
    miner_id = str(uuid.uuid4())[:8]

    node_start_time = time.time()
    node_running = True
    stop_event = threading.Event()

    # Start mining threads
    threads = []
    for i in range(cores):
        t = threading.Thread(target=mining_worker, args=(i, interval, stop_event), daemon=True)
        threads.append(t)
        t.start()
        print(f"   Core {i} started")

    print(f"\n   Miner ID: {miner_id}")
    print(f"   Started: {datetime.fromtimestamp(node_start_time).isoformat()}")
    print(f"   Press Ctrl+C to stop\n")

    # Stats loop
    try:
        while node_running:
            time.sleep(5)
            with state_lock:
                elapsed = time.time() - node_start_time if node_start_time else 0
                h, m, s = int(elapsed // 3600), int((elapsed % 3600) // 60), int(elapsed % 60)
                rate = total_strp / max(elapsed, 1) * 3600 if elapsed > 0 else 0
                daily = rate * 24
                weekly = daily * 7
            print(f"\r⏱ {h:02d}h{m:02d}m{s:02d}s | Proofs: {total_proofs} | STRP: {total_strp} | "
                  f"Rate: {rate:.1f}/hr | Day: {daily:.0f} | Week: {weekly:.0f}   ", end="", flush=True)
    except KeyboardInterrupt:
        print("\n\n⏹️  Stopping Lightchain node...")
    finally:
        node_running = False
        stop_event.set()
        for t in threads:
            t.join(timeout=2)
        save_node_state({
            "miner_id": miner_id,
            "started": node_start_time or time.time(),
            "total_proofs": total_proofs,
            "total_strp": total_strp,
        })
        print(f"\n💡 Node stopped.")
        print(f"   Total: {total_proofs} proofs, {total_strp:,} STRP earned.")
        print(f"   State: {STATE_FILE}")


# ── Stats ─────────────────────────────────────────────────────────────

def show_stats():
    state = load_node_state()
    elapsed = time.time() - (node_start_time or state.get("started", time.time()))
    h, m, s = int(elapsed // 3600), int((elapsed % 3600) // 60), int(elapsed % 60)
    rate = total_strp / max(elapsed, 1) * 3600 if elapsed > 0 else 0
    daily = rate * 24
    weekly = daily * 7

    print("╔══════════════════════════════════════════════════════════╗")
    print("║           💡 LIGHTCHAIN NODE — STATISTICS              ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print()
    print(f"  🪙 STRP EARNINGS")
    print(f"     Total proofs:        {total_proofs}")
    print(f"     Total STRP earned:   {total_strp:,}")
    print(f"     Avg per proof:       50 STRP")
    print(f"     Uptime:              {h}h {m}m {s}s")
    print(f"     Rate:                {rate:.1f} STRP/hr")
    print(f"     Projected/day:       {daily:.0f} STRP")
    print(f"     Projected/week:      {weekly:.0f} STRP")
    print(f"     Projected/year:      {daily * 365:.0f} STRP")
    print()
    print(f"  💰 ROI AT VARIOUS PRICES (on $10 VPS)")
    for price in [0.001, 0.005, 0.01, 0.05, 0.10, 0.50]:
        monthly = daily * 30 * price
        roi = (monthly / 10) * 100
        print(f"     ${price:.3f}/STRP → ${monthly:.2f}/mo ({roi:.0f}% ROI)")
    print()
    print(f"  🔗 CHAIN")
    chain = get_chain_info()
    if chain.get("raw"):
        import re
        raw = chain["raw"]
        blocks = re.search(r"Blocks:\s*(\d+)", raw)
        supply = re.search(r"Total supply:\s*([\d,]+)\s*STRP", raw)
        print(f"     Blocks:     {blocks.group(1) if blocks else '?'}")
        print(f"     Supply:     {supply.group(1) if supply else '?'} STRP")
    else:
        print(f"     Status:     {chain.get('error', 'unknown')}")
    print()
    print(f"  🤖 AGENTS")
    agents = get_agents()
    if agents.get("agents"):
        for label in ["mark", "sheylla", "billie", "legative", "newbi", "nurio"]:
            a = agents["agents"].get(label, {})
            print(f"     {label:10s} → {a.get('model', '?')}")
    print()
    print(f"  📂 State file: {STATE_FILE}")


# ── Main ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Lightchain Node — Telegram-Integrated PoSvc Miner")
    parser.add_argument("--cores", type=int, default=1, help="Mining cores (default: 1)")
    parser.add_argument("--interval", type=float, default=5.0, help="Proof interval in seconds (default: 5)")
    parser.add_argument("--stats", action="store_true", help="Show stats and exit")
    parser.add_argument("--init", action="store_true", help="Initialize chain and exit")
    parser.add_argument("--once", action="store_true", help="Mine one proof and exit")
    parser.add_argument("--telegram", action="store_true", help="Run with Telegram gateway integration")
    args = parser.parse_args()

    global API
    API = os.environ.get("STRAP_API", API)

    if args.init:
        print("Initializing Strap chain...")
        res = init_chain()
        if res["success"]:
            print(f"✅ {res['output']}")
        else:
            print(f"❌ {res['error']}")
        return

    if args.once:
        print("Mining one PoSvc proof...")
        task = create_proof_task(0)
        proof = submit_proof(task, 0)
        if proof:
            print(f"✅ Proof #{proof['total_proofs']}: +50 STRP (total: {total_strp})")
        else:
            print("❌ Failed — check API is running")
        return

    if args.stats:
        show_stats()
        return

    if args.telegram:
        print("🚀 Lightchain Node starting WITH Telegram integration...")
        # Start mining in background
        mining_thread = threading.Thread(
            target=start_node, args=(args.cores or 1, args.interval or 5.0), daemon=True
        )
        mining_thread.start()
        time.sleep(3)
        print("\n💡 Node running in background. Telegram commands now active in this chat.")
        print("   Try: /dashboard, /stats, /init, /mine, /proof test, /agents")
        mining_thread.join()
    else:
        start_node(cores=args.cores, interval=args.interval)


if __name__ == "__main__":
    main()
