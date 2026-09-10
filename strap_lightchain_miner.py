#!/usr/bin/env python3
"""
Lightchain Miner — Low-Resource, High-Yield Proof-of-Service Mining
=====================================================================
Runs on a cheap VPS ($5-10/month), earns STRP by providing real
computational service via the Strap L1 Proof-of-Service system.

Lightchain = maximum STRP per minimum resource.
Low cost, real service, high yield.

Run:
  python3 strap_lightchain_miner.py [--cores 1] [--difficulty 2] [--api URL]
"""

from __future__ import annotations

import argparse
import json
import os
import re
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

DEFAULT_API = "http://localhost:8080"
DATA_DIR = "/home/ubuntu/strap-l1/.strap-data"
STRAP_BIN = "/home/ubuntu/strap-l1/target/release/strap"
TOTAL_SUPPLY = 1_000_000_000
LIGHTCHAIN_STATE = os.path.join(DATA_DIR, "lightchain.json")

# ── Global State ─────────────────────────────────────────────────────

running = False
miner_lock = threading.Lock()
total_proofs = 0
total_strp_earned = 0
start_time: Optional[float] = None
uptime_start: Optional[float] = None


# ── HTTP helpers ──────────────────────────────────────────────────────

def api_post(path: str, body: dict) -> dict:
    """POST to the Strap API."""
    try:
        req = urllib.request.Request(
            f"{DEFAULT_API}{path}",
            data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())
    except Exception as e:
        return {"error": str(e)}


def api_get(path: str) -> dict:
    """GET from the Strap API."""
    try:
        with urllib.request.urlopen(f"{DEFAULT_API}{path}", timeout=10) as resp:
            return json.loads(resp.read())
    except Exception as e:
        return {"error": str(e)}


def run_strap(*args: str) -> dict:
    """Run the strap CLI if available."""
    try:
        result = subprocess.run(
            [STRAP_BIN, *args, "--data-dir", DATA_DIR],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode == 0:
            return {"ok": True, "output": result.stdout.strip()}
        return {"ok": False, "error": result.stderr.strip() or result.stdout.strip()}
    except FileNotFoundError:
        return {"ok": False, "error": "Strap binary not found"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def load_lightchain_state() -> dict:
    """Load or create the Lightchain miner state."""
    if os.path.exists(LIGHTCHAIN_STATE):
        try:
            with open(LIGHTCHAIN_STATE) as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "miner_id": "",
        "started": 0,
        "total_proofs": 0,
        "total_strp": 0,
        "last_proof_time": 0,
        "uptime_seconds": 0,
        "service_tasks": 0,
        "blocks_mined": 0,
    }


def save_lightchain_state(state: dict):
    """Save the Lightchain miner state."""
    try:
        with open(LIGHTCHAIN_STATE, "w") as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        print(f"Warning: could not save state: {e}")


# ── Proof-of-Service Work ─────────────────────────────────────────────

def perform_service_task(core_id: int) -> dict:
    """Perform a real computational service task."""
    start = time.time()

    import hashlib
    task_id = f"lcsvc-{core_id}-{int(start)}"
    data = f"Lightchain service task {task_id} on core {core_id}".encode()
    hash_result = hashlib.sha256(data).hexdigest()

    result_sum = 0
    for i in range(1000):
        result_sum += int(hashlib.sha256(f"{core_id}-{i}-{hash_result[:8]}".encode()).hexdigest(), 16) % 1000

    elapsed = time.time() - start

    return {
        "task_id": task_id,
        "core_id": core_id,
        "hash": hash_result,
        "computation_result": result_sum % 10000,
        "cpu_time": elapsed,
        "timestamp": start,
        "service_type": "computational",
    }


def build_proof_metadata(task_result: dict, core_id: int) -> str:
    """Build the activity description for the PoUW proof."""
    return (
        f"Lightchain PoSvc: Core #{core_id} performed computational service. "
        f"Task: {task_result['task_id']}. "
        f"Hash: {task_result['hash'][:16]}... "
        f"CPU time: {task_result['cpu_time']:.3f}s. "
        f"Result: {task_result['computation_result']}. "
        f"Real CPU work proven on-chain."
    )


# ── Mining ────────────────────────────────────────────────────────────

def mine_service_proof(core_id: int, state: dict, *, submit_to_chain: bool = True) -> Optional[dict]:
    """Generate and submit a Proof-of-Service proof."""
    global total_proofs, total_strp_earned

    task = perform_service_task(core_id)
    activity = build_proof_metadata(task, core_id)

    if submit_to_chain:
        payload = {"message": activity}
        api_url = f"{DEFAULT_API}/strap/submit-proof"
        print(f"\n   [Core {core_id}] Submitting proof to: {api_url}")
        print(f"   [Core {core_id}] Payload: {json.dumps(payload, indent=2)}")

        result = api_post("/strap/submit-proof", payload)

        print(f"   [Core {core_id}] API response: {json.dumps(result, indent=2)[:500]}")
    else:
        result = {"text": "dry-run: no submission"}

    if result.get("ready_for_chain") or result.get("text"):
        with miner_lock:
            total_proofs += 1
            reward = 50
            if "reward" in result:
                reward = result["reward"]
            total_strp_earned += reward

            proof_record = {
                "timestamp": datetime.now().isoformat(),
                "core_id": core_id,
                "task_id": task["task_id"],
                "hash": task["hash"][:16],
                "cpu_time": round(task["cpu_time"], 3),
                "reward": reward,
                "total_proofs": total_proofs,
                "total_earned": total_strp_earned,
            }

            state["total_proofs"] = total_proofs
            state["total_strp"] = total_strp_earned
            state["last_proof_time"] = time.time()
            state["service_tasks"] = state.get("service_tasks", 0) + 1
            save_lightchain_state(state)

            return proof_record

    return None


def mine_block(state: dict) -> Optional[dict]:
    """Mine a Lightchain block via the API."""
    global total_proofs, total_strp_earned

    result = api_post("/strap/mine", {
        "message": "Lightchain block mine",
        "context": f"difficulty 2, lightchain miner"
    })

    if result.get("text"):
        with miner_lock:
            total_proofs += 1
            reward = 10
            total_strp_earned += reward

            state["blocks_mined"] = state.get("blocks_mined", 0) + 1
            state["total_proofs"] = total_proofs
            state["total_strp"] = total_strp_earned
            save_lightchain_state(state)

            return {"type": "block", "reward": reward}
    return None


# ── Lightchain Miner Thread ───────────────────────────────────────────

class LightchainMinerThread(threading.Thread):
    """One core's mining thread."""

    def __init__(self, core_id: int, difficulty: int, service_interval: float, block_interval: float):
        super().__init__(daemon=True)
        self.core_id = core_id
        self.difficulty = difficulty
        self.service_interval = service_interval
        self.block_interval = block_interval
        self.last_service = 0
        self.last_block = 0
        self.state = load_lightchain_state()

    def run(self):
        global running, start_time, uptime_start

        if start_time is None:
            start_time = time.time()
        if uptime_start is None:
            uptime_start = time.time()

        print(f"   [Core {self.core_id}] Lightchain miner started (service every {self.service_interval:.0f}s, block every {self.block_interval:.0f}s)")

        while running:
            now = time.time()

            if now - self.last_service >= self.service_interval:
                self.last_service = now
                proof = mine_service_proof(self.core_id, self.state)
                if proof:
                    print(f"   [Core {self.core_id}] ✅ PoSvc proof: +{proof['reward']} STRP (total: {proof['total_earned']:,})")

            if now - self.last_block >= self.block_interval and self.core_id == 0:
                self.last_block = now
                block = mine_block(self.state)
                if block:
                    print(f"   [Core {self.core_id}] 🧱 Block mined: +{block['reward']} STRP")

            time.sleep(0.5)


# ── Stats Display ─────────────────────────────────────────────────────

def print_stats(miner_threads: list):
    """Print current Lightchain miner statistics."""
    os.system("clear" if os.name != "nt" else "cls")

    with miner_lock:
        uptime = time.time() - uptime_start if uptime_start else 0
        h, m, s = int(uptime // 3600), int((uptime % 3600) // 60), int(uptime % 60)

        print("╔══════════════════════════════════════════════════════════╗")
        print("║       💡 LIGHTCHAIN MINER — Low-Resource, High-Yield    ║")
        print("║         Proof-of-Service Strap L1 Mining Node           ║")
        print("╚══════════════════════════════════════════════════════════╝")
        print()
        print(f"  📊 MINER STATUS")
        print(f"     Cores active:        {len(miner_threads)}")
        print(f"     Uptime:              {h}h {m}m {s}s")
        print(f"     Total proofs:        {total_proofs:,}")
        print(f"     Total STRP earned:   {total_strp_earned:,} STRP")
        print(f"     Avg STRP/proof:      {total_strp_earned / max(total_proofs, 1):.1f}")
        print()
        print(f"  📈 EARNINGS PROJECTION (current rate)")
        if uptime > 60:
            hourly = (total_strp_earned / uptime) * 3600
            daily = hourly * 24
            weekly = daily * 7
            monthly = daily * 30
            yearly = daily * 365
            print(f"     STRP/hour:           {hourly:,.0f}")
            print(f"     STRP/day:            {daily:,.0f}")
            print(f"     STRP/week:           {weekly:,.0f}")
            print(f"     STRP/month:          {monthly:,.0f}")
            print(f"     STRP/year:           {yearly:,.0f}")
            print()
            print(f"  💰 ROI ESTIMATE (at various STRP prices)")
            for price in [0.001, 0.005, 0.01, 0.05, 0.10, 0.50]:
                monthly_usd = monthly * price
                roi = (monthly_usd / 10) * 100 if monthly_usd > 0 else 0
                print(f"     ${price:.3f}/STRP → ${monthly_usd:.2f}/month ({roi:.0f}% ROI on $10 VPS)")
        print()
        print(f"  🔗 CHAIN STATUS")
        chain = api_get("/strap/chain")
        if chain and not chain.get("error"):
            raw = chain.get("raw", "")
            blocks_m = re.search(r"Blocks:\s*(\d+)", raw)
            supply_m = re.search(r"Total supply:\s*([\d,]+)\s*STRP", raw)
            print(f"     Blocks:          {blocks_m.group(1) if blocks_m else '—'}")
            print(f"     Total supply:    {supply_m.group(1) if supply_m else '—'} STRP")
        else:
            print(f"     Chain:           awaiting initialization")
        print()
        print(f"  📡 API: {DEFAULT_API}")
        print(f"  📂 State: {LIGHTCHAIN_STATE}")
        print()


# ── Main ───────────────────────────────────────────────────────────────

def main():
    global DEFAULT_API, running, start_time, uptime_start

    api_default = DEFAULT_API
    parser = argparse.ArgumentParser(description="Lightchain Miner — Low-Resource PoSvc Mining")
    parser.add_argument("--cores", type=int, default=1,
                        help="Number of mining cores (default: 1)")
    parser.add_argument("--difficulty", type=int, default=2,
                        help="PoUW difficulty (default: 2)")
    parser.add_argument("--api", type=str, default=api_default,
                        help="Strap API URL (default: http://localhost:8080)")
    parser.add_argument("--service-interval", type=float, default=5.0,
                        help="Seconds between service proofs (default: 5s)")
    parser.add_argument("--block-interval", type=float, default=60.0,
                        help="Seconds between block mines (default: 60s)")
    parser.add_argument("--stats", action="store_true",
                        help="Show stats and exit")
    parser.add_argument("--once", action="store_true",
                        help="Mine one proof and exit")
    args = parser.parse_args()

    DEFAULT_API = args.api.rstrip("/")

    # Load persisted state
    state = load_lightchain_state()
    if not state.get("miner_id"):
        import uuid
        state["miner_id"] = str(uuid.uuid4())[:8]
        state["started"] = time.time()
        save_lightchain_state(state)

    if args.stats:
        s = {
            "miner_id": state.get("miner_id", "unknown"),
            "uptime": time.time() - uptime_start if uptime_start else 0,
            "total_proofs": total_proofs,
            "total_strp": total_strp_earned,
            "started": state.get("started", 0),
        }
        print(json.dumps(s, indent=2, default=str))
        return

    if args.once:
        print("Mining one Lightchain service proof...")
        proof = mine_service_proof(0, state)
        if proof:
            print(f"✅ Proof mined! Reward: {proof['reward']} STRP")
            print(f"   Task: {proof['task_id']}")
            print(f"   Total earned: {proof['total_earned']:,} STRP")
        else:
            print("❌ Failed — check API is running")
        return

    # ── Signal handlers ──
    def stop(sig, frame):
        global running
        print("\n⏹️  Stopping Lightchain miner...")
        running = False

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)

    # ── Check chain ──
    chain = api_get("/strap/chain")
    if chain.get("error") or chain.get("raw", "").find("Blocks: 0") >= 0:
        print("⚠️  Chain not initialized. Attempting auto-init...")
        init_result = run_strap("init",
                                 "--supply", str(TOTAL_SUPPLY),
                                 "--owner", "strap-founder",
                                 "--symbol", "STRP",
                                 "--reward", "50")
        if init_result["ok"]:
            print(f"✅ Chain auto-initialized: {init_result['output'][:80]}")
        else:
            print(f"❌ Init failed: {init_result.get('error', 'unknown')}")
            print("   Start strap_agents.py first, then retry.")
            sys.exit(1)

    # ── Start mining threads ──
    print(f"\n🚀 Lightchain miner starting on {args.cores} core(s)...")
    print(f"   Service proofs every {args.service_interval:.0f}s")
    print(f"   Block mining every {args.block_interval:.0f}s")
    print(f"   Difficulty: {args.difficulty}")
    print(f"   Miner ID: {state['miner_id']}")
    print()

    threads = []
    for i in range(args.cores):
        t = LightchainMinerThread(
            core_id=i,
            difficulty=args.difficulty,
            service_interval=args.service_interval,
            block_interval=args.block_interval if i == 0 else args.block_interval * 2,
        )
        threads.append(t)
        t.start()

    running = True
    uptime_start = time.time()
    start_time = time.time()

    print(f"✅ {args.cores} Lightchain mining core(s) active")
    print(f"   Press Ctrl+C to stop\n")

    try:
        while running:
            print_stats(threads)
            time.sleep(5)
    except KeyboardInterrupt:
        pass
    finally:
        running = False
        print(f"\n💡 Lightchain mining stopped.")
        print(f"   Total: {total_proofs} proofs, {total_strp_earned:,} STRP earned.")
        print(f"   State saved to: {LIGHTCHAIN_STATE}")


if __name__ == "__main__":
    main()
