#!/usr/bin/env python3
"""
Strap ($STP) — Solana Payment API
====================================
API for collaborators to pay in SOL. Tracks payments, detects incoming SOL,
manages payment records for community rewards, developer fund, etc.

Endpoints:
  GET  /api/payments           → list all payments
  POST /api/payments           → create a payment request/record
  GET  /api/payments/:id       → get payment by ID
  POST /api/payments/:id/mark-paid  → mark a payment as paid (after SOL received)
  GET  /api/wallet             → wallet address + balance
  POST /api/webhook/solana     → Solana transaction webhook (if using Helius/Dialect/etc.)

Payment flow:
  1. Collaborator requests to pay via MiniApp/Telegram
  2. API records the payment request
  3. Collaborator sends SOL to the project wallet
  4. Payment detected (manually by admin, or via Solana webhook in future)
  5. Payment marked as paid → collaborator gets access/reward

Environment:
  STRAP_PAYMENT_WALLET — project wallet receiving SOL (default: CrCiFTjbisQRPTfiBzgMR454WTr8vaTpbykXNRUejA81)
  SOLANA_RPC_URL        — Solana RPC endpoint (default: https://api.mainnet-beta.solana.com)
  STRAP_PAYMENT_PORT    — API port (default: 8082)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Optional, Dict, List
from http.server import HTTPServer, SimpleHTTPRequestHandler

# ── Configuration ──────────────────────────────────────────────────────────

PAYMENT_PORT = int(os.environ.get("STRAP_PAYMENT_PORT", "8082"))
PAYMENT_DIR = os.environ.get("STRAP_PAYMENT_DIR", str(Path(__file__).parent))
PAYMENT_DATA_FILE = os.path.join(PAYMENT_DIR, "payment_data.json")
PROJECT_WALLET = os.environ.get("STRAP_PAYMENT_WALLET",
    "CrCiFTjbisQRPTfiBzgMR454WTr8vaTpbykXNRUejA81")
SOLANA_RPC = os.environ.get("SOLANA_RPC_URL", "https://api.mainnet-beta.solana.com")
MINIAPP_URL = os.environ.get("STRAP_MINIAPP_URL", "http://localhost:8081")

# ── Data Store ─────────────────────────────────────────────────────────────

def load_payments() -> dict:
    """Load payment data."""
    if os.path.exists(PAYMENT_DATA_FILE):
        try:
            with open(PAYMENT_DATA_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "project_wallet": PROJECT_WALLET,
        "solana_rpc": SOLANA_RPC,
        "payments": [],
        "total_received_sol": 0.0,
        "total_received_usd": 0.0,  # approximate, updated manually
        "created_at": time.time(),
        "last_updated": time.time(),
    }


def save_payments(data: dict) -> None:
    """Save payment data."""
    try:
        with open(PAYMENT_DATA_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"Error saving payments: {e}", file=sys.stderr)


# ── Solana Balance Check ───────────────────────────────────────────────────

def get_sol_balance(wallet_address: str) -> float:
    """Check SOL balance of a wallet via Solana RPC."""
    try:
        import urllib.request
        import urllib.error
        import json as json_mod

        payload = json_mod.dumps({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getBalance",
            "params": [wallet_address],
        }).encode()

        req = urllib.request.Request(
            SOLANA_RPC,
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json_mod.loads(resp.read().decode())
            if "result" in result and "value" in result["result"]:
                lamports = result["result"]["value"]
                return lamports / 1e9  # convert to SOL
            return 0.0
    except Exception as e:
        print(f"Balance check error: {e}", file=sys.stderr)
        return 0.0


def get_sol_price_usd() -> float:
    """Get approximate SOL price in USD (from CoinGecko public API)."""
    try:
        import urllib.request
        import json as json_mod
        with urllib.request.urlopen("https://api.coingecko.com/api/v3/simple/price?ids=solana&vs_currencies=usd", timeout=10) as resp:
            data = json_mod.loads(resp.read().decode())
            return data.get("solana", {}).get("usd", 0.0)
    except Exception:
        return 0.0  # fallback: admin updates manually


# ── HTTP Handler ────────────────────────────────────────────────────────────

class PaymentHandler(SimpleHTTPRequestHandler):
    """HTTP handler for the payment API."""

    def _send_json(self, data: dict, code: int = 200) -> None:
        body = json.dumps(data, indent=2 if code == 200 else None)
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body.encode("utf-8"))

    def do_GET(self) -> None:
        path = self.path

        # GET /api/payments — list all payments
        if path == "/api/payments":
            data = load_payments()
            self._send_json({
                "payments": data.get("payments", []),
                "total_received_sol": data.get("total_received_sol", 0.0),
                "total_received_usd": data.get("total_received_usd", 0.0),
                "project_wallet": data.get("project_wallet", PROJECT_WALLET),
                "count": len(data.get("payments", [])),
            })
            return

        # GET /api/payments/:id — get payment by ID
        if path.startswith("/api/payments/"):
            payment_id = path.split("/")[-1]
            data = load_payments()
            for p in data.get("payments", []):
                if p.get("id") == payment_id:
                    self._send_json(p)
                    return
            self._send_json({"error": "Payment not found", "id": payment_id}, 404)
            return

        # GET /api/wallet — wallet info
        if path == "/api/wallet":
            balance = get_sol_balance(PROJECT_WALLET)
            price = get_sol_price_usd()
            data = load_payments()
            self._send_json({
                "wallet": PROJECT_WALLET,
                "balance_sol": round(balance, 9),
                "balance_usd": round(balance * price, 2),
                "price_sol_usd": round(price, 2),
                "total_received_sol": data.get("total_received_sol", 0.0),
                "total_received_usd": data.get("total_received_usd", 0.0),
                "network": "mainnet" if "mainnet" in SOLANA_RPC else "devnet",
            })
            return

        # GET /api/miniapp/stats — MiniApp stats (alias)
        if path == "/api/miniapp/stats":
            data = load_payments()
            self._send_json({
                "community_members": data.get("community_members", 0),
                "total_payments": len(data.get("payments", [])),
                "total_received_sol": data.get("total_received_sol", 0.0),
                "project_wallet": data.get("project_wallet", PROJECT_WALLET),
                "status": "active" if balance > 0 else "waiting",
            })
            return

        # Serve MiniApp (if requested from payment server)
        if path == "/" or path == "/mini_app" or path == "/index.html":
            # Redirect to MiniApp server
            self._send_json({
                "redirect": f"{MINIAPP_URL}",
                "message": "Use the MiniApp at " + MINIAPP_URL,
            }, 302)
            return

        self._send_json({"error": "Not found", "path": path}, 404)

    def do_POST(self) -> None:
        path = self.path

        # POST /api/payments — create a payment record
        if path == "/api/payments":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8") if content_length else "{}"
            try:
                req = json.loads(body)
            except json.JSONDecodeError:
                self._send_json({"error": "Invalid JSON"}, 400)
                return

            data = load_payments()
            payment = {
                "id": str(int(time.time() * 1000)),
                "collaborator": req.get("collaborator", "anonymous"),
                "email": req.get("email", ""),
                "amount_sol": req.get("amount_sol", 0.0),
                "amount_usd": req.get("amount_usd", 0.0),
                "purpose": req.get("purpose", "contribution"),
                "status": "pending",  # pending, paid, refunded
                "created_at": time.time(),
                "paid_at": None,
                "transaction_sig": None,
                "notes": req.get("notes", ""),
            }
            data["payments"].append(payment)
            data["last_updated"] = time.time()
            save_payments(data)

            self._send_json({
                "payment": payment,
                "wallet": PROJECT_WALLET,
                "message": "Send SOL to this wallet. Admin will mark as paid when received.",
                "created_at": payment["created_at"],
            }, 201)
            return

        # POST /api/payments/:id/mark-paid — mark payment as received
        if path.startswith("/api/payments/") and path.endswith("/mark-paid"):
            payment_id = path.split("/")[-2]
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8") if content_length else "{}"
            try:
                req = json.loads(body)
            except json.JSONDecodeError:
                req = {}

            data = load_payments()
            for p in data.get("payments", []):
                if p.get("id") == payment_id:
                    p["status"] = req.get("status", "paid")
                    p["paid_at"] = time.time()
                    p["transaction_sig"] = req.get("transaction_sig", p.get("transaction_sig"))
                    p["amount_sol_received"] = req.get("amount_sol", p.get("amount_sol", 0.0))
                    data["total_received_sol"] = round(
                        data.get("total_received_sol", 0.0) + p["amount_sol_received"], 9
                    )
                    data["last_updated"] = time.time()
                    save_payments(data)
                    self._send_json({
                        "payment": p,
                        "message": "Payment marked as received.",
                    })
                    return
            self._send_json({"error": "Payment not found", "id": payment_id}, 404)
            return

        # POST /api/webhook/solana — Solana transaction webhook (future: Helius/Dialect)
        if path == "/api/webhook/solana":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8") if content_length else "{}"
            try:
                webhook = json.loads(body)
            except json.JSONDecodeError:
                self._send_json({"error": "Invalid webhook payload"}, 400)
                return

            # Future: parse Solana webhook (Helius, Dialect, etc.)
            # For now: log and return 200
            print(f"[PAYMENT] Solana webhook received: {json.dumps(webhook)[:200]}", flush=True)
            data = load_payments()
            data["last_updated"] = time.time()
            save_payments(data)
            self._send_json({"status": "received", "message": "Webhook logged."})
            return

        self._send_json({"error": "Not found", "path": path}, 404)

    def do_OPTIONS(self) -> None:
        """Handle CORS preflight."""
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    def log_message(self, format: str, *args) -> None:
        """Custom logging."""
        print(f"[PAYMENT] {args[0]}", flush=True)


# ── Balance monitor (background thread) ────────────────────────────────────

def start_balance_monitor(data: dict, interval: int = 60) -> None:
    """Periodically check project wallet balance and update data."""
    import threading

    def monitor():
        while True:
            time.sleep(interval)
            try:
                balance = get_sol_balance(PROJECT_WALLET)
                price = get_sol_price_usd()
                data["wallet_balance_sol"] = round(balance, 9)
                data["wallet_balance_usd"] = round(balance * price, 2)
                data["sol_price_usd"] = round(price, 2)
                data["last_updated"] = time.time()
                save_payments(data)
                print(f"[PAYMENT MONITOR] Balance: {balance:.9f} SOL (~${balance*price:.2f})", flush=True)
            except Exception as e:
                print(f"[PAYMENT MONITOR] Error: {e}", flush=True)

    thread = threading.Thread(target=monitor, daemon=True)
    thread.start()


# ── Main ────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Strap $STP Solana Payment API")
    parser.add_argument("--port", type=int, default=PAYMENT_PORT, help="Port (default: 8082)")
    parser.add_argument("--wallet", type=str, default=PROJECT_WALLET, help="Project wallet address")
    parser.add_argument("--rpc", type=str, default=SOLANA_RPC, help="Solana RPC URL")
    parser.add_argument("--miniapp", type=str, default=MINIAPP_URL, help="MiniApp URL")
    parser.add_argument("--monitor-interval", type=int, default=60, help="Balance check interval in seconds")
    parser.add_argument("--no-monitor", action="store_true", help="Disable balance monitor")
    args = parser.parse_args()

    global PAYMENT_PORT, PROJECT_WALLET, SOLANA_RPC, MINIAPP_URL
    PAYMENT_PORT = args.port
    PROJECT_WALLET = args.wallet
    SOLANA_RPC = args.rpc
    MINIAPP_URL = args.miniapp

    print(f"=== Strap $STP Payment API ===", flush=True)
    print(f"  Port: {PAYMENT_PORT}", flush=True)
    print(f"  Wallet: {PROJECT_WALLET}", flush=True)
    print(f"  RPC: {SOLANA_RPC}", flush=True)
    print(f"  MiniApp: {MINIAPP_URL}", flush=True)
    print(f"  Data file: {PAYMENT_DATA_FILE}", flush=True)
    print(f"  Open: http://localhost:{PAYMENT_PORT}/api/wallet", flush=True)
    print(f"===", flush=True)

    data = load_payments()
    data["project_wallet"] = PROJECT_WALLET
    data["solana_rpc"] = SOLANA_RPC

    if not args.no_monitor:
        start_balance_monitor(data, args.monitor_interval)

    server = HTTPServer(("0.0.0.0", PAYMENT_PORT), PaymentHandler)
    print(f"Payment API running on port {PAYMENT_PORT}...", flush=True)
    print(f"Press Ctrl+C to stop.", flush=True)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...", flush=True)
        server.shutdown()


if __name__ == "__main__":
    main()
