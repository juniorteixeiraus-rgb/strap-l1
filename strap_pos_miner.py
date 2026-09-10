#!/usr/bin/env python3
"""
Strap Proof-of-Service (PoS) Miner — Full VPS Capacity Mining
==============================================================
Uses ALL CPU cores to continuously generate PoUW proofs, turning the VPS
into a Service Node that earns STRP by providing real computational capacity.

Concept:
  - Each CPU core runs a mining thread
  - Proofs record "service provided" metadata (CPU time, tasks, capacity)
  - Proofs are submitted to the Strap L1 chain via the API
  - Continuous 24/7 operation with auto-recovery
  - Proof-of-Service = real work = real value = STRP price appreciation

Run:
  python3 strap_pos_miner.py [--cores N] [--difficulty D] [--api URL]
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import threading
import time
import urllib.request
import urllib.error
from typing import Any, Optional

# ── Config ────────────────────────────────────────────────────────────

DEFAULT_API = "http://localhost:8080"
DATA_DIR = "/home/ubuntu/strap-l1/.strap-data"
STRAP_BIN = "/home/ubuntu/strap-l1/target/release/strap"
TOTAL_SUPPLY = 1_000_000_000

# ── State ─────────────────────────────────────────────────────────────

running = True
total_proofs_mined = 0
total_strp_earned = 0
start_time: Optional[float] = None
proof_log: list[dict] = []


# ── Helpers ───────────────────────────────────────────────────────────

def api_post(path: str, body: dict) -> dict:
    """Post to the Strap agents API."""
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
    """GET from the Strap agents API."""
    try:
        with urllib.request.urlopen(f"{DEFAULT_API}{path}", timeout=10) as resp:
            return json.loads(resp.read())
    except Exception as e:
        return {"error": str(e)}


def run_strap(*args: str) -> dict:
    """Run the strap CLI binary."""
    try:
        result = subprocess.run(
            [STRAP_BIN, *args, "--data-dir", DATA_DIR],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode == 0:
            return {"ok": True, "output": result.stdout.strip()}
        return {"ok": False, "error": result.stderr.strip() or result.stdout.strip()}
    except FileNotFoundError:
        return {"ok": False, "error": "Strap binary not found — build it first"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def get_chain_status() -> dict:
    """Get current chain info."""
    info = api_get("/strap/chain")
    if info.get("error"):
        # Fallback: try CLI
        cli = run_strap("info")
        if cli["ok"]:
            return {"raw": cli["output"], "from_cli": True}
        return {"error": "Chain not accessible"}
    return info


# ── Proof-of-Service Mining Core ──────────────────────────────────────

class ServiceMiner:
    """
    Mines PoUW proofs using VPS computational capacity.
    Each proof demonstrates real CPU work performed.
    """

    def __init__(self, cores: int, difficulty: int, api_url: str):
        self.cores = cores
        self.difficulty = difficulty
        self.api_url = api_url
        self.threads: list[threading.Thread] = []
        self.proofs_per_core = 0
        self.last_submit_time = 0
        self.submit_interval = 5  # seconds between API submissions
        self.cumulative_cpu_seconds = 0.0

    def get_service_description(self, core_id: int) -> str:
        """Generate a service description for this mining activity."""
        uptime = time.time() - start_time if start_time else 0
        h, m, s = int(uptime // 3600), int((uptime % 3600) // 60), int(uptime % 60)
        return (
            f"Proof-of-Service: VPS core #{core_id} providing {self.cores}-core "
            f"computational capacity for {self.difficulty}-difficulty PoUW mining. "
            f"Uptime: {h}h {m}m {s}s. Real CPU work performed continuously."
        )

    def mine_single_proof(self, core_id: int) -> Optional[dict]:
        """
        Attempt to mine a single PoUW proof using CPU capacity.
        Uses the strap binary's mine command on a single block.
        Returns proof result or None on failure.
        """
        global total_proofs_mined, total_strp_earned

        activity = self.get_service_description(core_id)

        # Use the strap CLI to mine one block (which includes a PoUW proof)
        result = run_strap("mine", "--count", "1", "--difficulty", str(self.difficulty))

        if result["ok"]:
            total_proofs_mined += 1
            # Parse reward from output
            import re
            reward_match = re.search(r"Reward:\s*(\d+)", result["output"])
            if reward_match:
                reward = int(reward_match.group(1))
                total_strp_earned += reward

            proof_hash_match = re.search(r"Hash=([a-f0-9]+)", result["output"])
            proof_hash = proof_hash_match.group(1) if proof_hash_match else "—"

            proof_record = {
                "core": core_id,
                "activity": activity[:80],
                "timestamp": time.time(),
                "proof_hash": proof_hash,
                "reward": reward if reward_match else 0,
                "total_proofs": total_proofs_mined,
                "total_earned": total_strp_earned,
            }
            proof_log.append(proof_record)

            return proof_record
        return None

    def mining_loop(self, core_id: int):
        """Continuous mining loop for one core."""
        global running

        while running:
            proof = self.mine_single_proof(core_id)
            if proof:
                # Throttle API submissions — batch locally, submit periodically
                now = time.time()
                if now - self.last_submit_time > self.submit_interval:
                    self.last_submit_time = now
                    # Submit via API (async, best-effort)
                    api_post("/strap/submit-proof", {"message": proof["activity"][:60]})

            # Small sleep to prevent CPU burn from the Python overhead
            time.sleep(0.1)

    def start_all_cores(self):
        """Start mining on all CPU cores."""
        global start_time
        start_time = time.time()

        print(f"🚀 Starting Proof-of-Service miner on {self.cores} cores")
        print(f"   Difficulty: {self.difficulty}")
        print(f"   API: {self.api_url}")
        print(f"   Data dir: {DATA_DIR}")
        print()

        for i in range(self.cores):
            t = threading.Thread(target=self.mining_loop, args=(i,), daemon=True)
            self.threads.append(t)
            t.start()
            print(f"   Core #{i} started")

        print(f"\n✅ All {self.cores} cores mining. Press Ctrl+C to stop.\n")

    def stats(self) -> dict:
        """Return current mining statistics."""
        uptime = time.time() - start_time if start_time else 0
        return {
            "cores": self.cores,
            "difficulty": self.difficulty,
            "total_proofs_mined": total_proofs_mined,
            "total_strp_earned": total_strp_earned,
            "uptime_seconds": int(uptime),
            "uptime_human": f"{int(uptime // 3600)}h {int((uptime % 3600) // 60)}m {int(uptime % 60)}s" if uptime > 0 else "0s",
            "proofs_per_second": total_proofs_mined / uptime if uptime > 0 else 0,
            "strp_per_hour": (total_strp_earned / uptime * 3600) if uptime > 0 else 0,
            "last_proofs": proof_log[-10:] if proof_log else [],
        }


# ── Dashboard / Status Output ─────────────────────────────────────────

def print_stats(miner: ServiceMiner, show_proofs: bool = False):
    """Print current mining statistics."""
    s = miner.stats()

    # Clear screen
    os.system("clear" if os.name != "nt" else "cls")

    # ── Header ──
    print("╔══════════════════════════════════════════════════════════╗")
    print("║          ⛏️  STRAP PROOF-OF-SERVICE MINER               ║")
    print("║         VPS Full-Capacity PoUW Mining Node              ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print()

    # ── Stats grid ──
    print(f"  📊 CORE CONFIGURATION")
    print(f"     Cores active:      {s['cores']}")
    print(f"     Difficulty:        {s['difficulty']}")
    print(f"     API endpoint:      {DEFAULT_API}")
    print()
    print(f"  ⛏️  MINING ACTIVITY")
    print(f"     Total proofs:      {s['total_proofs_mined']:,}")
    print(f"     STRP earned:       {s['total_strp_earned']:,} STRP")
    print(f"     Uptime:            {s['uptime_human']}")
    print(f"     Rate:              {s['proofs_per_second']:.2f} proofs/sec")
    print(f"     Projected/hr:      {s['strp_per_hour']:,.0f} STRP/hr")
    print()

    # ── Chain status ──
    chain = get_chain_status()
    if chain and not chain.get("error"):
        print(f"  🔗 CHAIN STATUS")
        raw = chain.get("raw", "")
        import re
        blocks_m = re.search(r"Blocks:\s*(\d+)", raw)
        supply_m = re.search(r"Total supply:\s*([\d,]+)\s*STRP", raw)
        treasury_m = re.search(r"Treasury:\s*([\d,]+)\s*STRP", raw)
        hash_m = re.search(r"Latest hash:\s*([a-f0-9]+)", raw)
        print(f"     Blocks:            {blocks_m.group(1) if blocks_m else '—'}")
        print(f"     Total supply:      {supply_m.group(1) if supply_m else '—'} STRP")
        print(f"     Treasury:          {treasury_m.group(1) if treasury_m else '—'} STRP")
        print(f"     Latest hash:       {hash_m.group(1)[:16] + '...' if hash_m else '—'}")
        print()

    # ── Price projection ──
    print(f"  📈 VALUE PROJECTION")
    rate = s['strp_per_hour']
    daily = rate * 24
    weekly = daily * 7
    monthly = daily * 30
    print(f"     STRP mined per hour:   {rate:,.0f}")
    print(f"     STRP mined per day:    {daily:,.0f}")
    print(f"     STRP mined per week:   {weekly:,.0f}")
    print(f"     STRP mined per month:  {monthly:,.0f}")
    print(f"     Annual projection:     {daily * 365:,.0f} STRP/year")
    print()

    # ── Proof log (last 5) ──
    if show_proofs and proof_log:
        print(f"  📝 RECENT PROOFs")
        for p in proof_log[-5:]:
            print(f"     Core #{p['core']}: {p['proof_hash'][:16]}... | +{p['reward']} STRP | {time.strftime('%H:%M:%S')}")
        print()

    # ── Footer ──
    print(f"  ═══════════════════════════════════════════════════════")
    print(f"  💡 Proof-of-Service: Real VPS work → Real STRP value")
    print(f"  📡 API: {DEFAULT_API} | 📂 Chain: {DATA_DIR}")
    print(f"  Press Ctrl+C to stop mining")


# ── Main ───────────────────────────────────────────────────────────────

def main():
    global DEFAULT_API, running, total_proofs_mined, total_strp_earned, start_time, proof_log
    parser = argparse.ArgumentParser(description="Strap Proof-of-Service Miner")
    parser.add_argument("--cores", type=int, default=0,
                        help="Number of CPU cores to use (default: auto-detect)")
    parser.add_argument("--difficulty", type=int, default=2,
                        help="PoUW mining difficulty (default: 2)")
    api_default = DEFAULT_API  # capture before any reassignment
    parser.add_argument("--api", type=str, default=api_default,
                        help="Strap agents API URL (default: http://localhost:8080)")
    parser.add_argument("--stats", action="store_true",
                        help="Show stats and exit")
    parser.add_argument("--once", action="store_true",
                        help="Mine a single proof and exit")
    args = parser.parse_args()

    DEFAULT_API = args.api.rstrip("/")

    # Auto-detect CPU cores
    if args.cores == 0:
        args.cores = os.cpu_count() or 2
        print(f"Auto-detected {args.cores} CPU cores")

    miner = ServiceMiner(args.cores, args.difficulty, args.api)

    if args.stats:
        s = miner.stats()
        print(json.dumps(s, indent=2, default=str))
        return

    if args.once:
        print("Mining one proof...")
        proof = miner.mine_single_proof(0)
        if proof:
            print(f"✅ Proof mined! Hash: {proof['proof_hash']}")
            print(f"   Reward: {proof['reward']} STRP")
            print(f"   Activity: {proof['activity']}")
        else:
            print("❌ Failed to mine proof — strap binary may not be built")
        return

    # ── Register signal handlers ──
    def signal_handler(sig, frame):
        global running
        print("\n\n⏹️  Stopping miner...")
        running = False

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # ── Initialize chain if needed ──
    chain = get_chain_status()
    if chain.get("error") or "Blocks: 0" in chain.get("raw", ""):
        print("⚠️  Chain not initialized. Running /init...")
        init_result = run_strap("init",
                                 "--supply", str(TOTAL_SUPPLY),
                                 "--owner", "strap-founder",
                                 "--symbol", "STRP",
                                 "--reward", "50")
        if init_result["ok"]:
            print(f"✅ Chain initialized: {init_result['output'][:100]}")
        else:
            print(f"❌ Init failed: {init_result.get('error', 'unknown')}")
            print("   Make sure the strap binary is built: cargo build --release")
            sys.exit(1)

    # ── Start mining ──
    miner.start_all_cores()

    # ── Stats loop ──
    try:
        while running:
            print_stats(miner, show_proofs=True)
            time.sleep(5)
    except KeyboardInterrupt:
        pass
    finally:
        print(f"\n⛏️  Mining stopped. Total: {total_proofs_mined} proofs, {total_strp_earned:,} STRP earned.")


if __name__ == "__main__":
    main()
