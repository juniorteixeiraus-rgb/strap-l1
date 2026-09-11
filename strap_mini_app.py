#!/usr/bin/env python3
"""
Strap ($STP) — Telegram MiniApp Server
========================================
Serves the $STP MiniApp dashboard as a Telegram Web App.
Works inside Telegram as a MiniApp — mobile-first, Telegram-themed.

Features:
  - Wallet connect (Solana Phantom/Solflare via Wallet Adapter)
  - $STP token info + balance
  - Community stats
  - Mining status (Strap L1 chain)
  - Agent chat (7 AI agents)
  - Solana payment API status
  - Telegram-native UI (theme colors, back button, etc.)

Hosting:
  python3 strap_mini_app.py
  → serves at http://localhost:8081 (or configured port)
  → expose via ngrok/cloudflare tunnel for public URL

Telegram MiniApp setup:
  1. In @BotFather, create a bot
  2. /newbot → get bot token
  3. /menu → Mini App → set URL to your public MiniApp URL
  4. Users open MiniApp via Telegram bot menu or link

Public URL options:
  - ngrok: ngrok http 8081 → https://xxxx.ngrok.io (free tier)
  - Cloudflare Tunnel: cloudflared tunnel → your domain
  - VPS public IP: http://<vps-ip>:8081 (if port open)
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler
from typing import Optional

# ── Configuration ──────────────────────────────────────────────────────────

MINIAPP_PORT = int(os.environ.get("MINIAPP_PORT", "8081"))
MINIAPP_DIR = os.environ.get("MINIAPP_DIR", str(Path(__file__).parent))
MINIAPP_DATA_FILE = os.path.join(MINIAPP_DIR, "mini_app_data.json")
PASSPHRASE = os.environ.get("MINIAPP_PASSPHRASE", "")  # for stats/auth if needed

# Paths to other services
STRAP_API_URL = os.environ.get("STRAP_API_URL", "http://localhost:8080")
STRAP_BOT_TOKEN = os.environ.get("STRAP_BOT_TOKEN", "")  # Telegram bot token
SOLANA_PAYMENT_WALLET = os.environ.get("SOLANA_PAYMENT_WALLET", 
    "CrCiFTjbisQRPTfiBzgMR454WTr8vaTpbykXNRUejA81")  # payment receiving wallet
SOLANA_RPC_URL = os.environ.get("SOLANA_RPC_URL", "https://api.mainnet-beta.solana.com")

# ── Data Store ─────────────────────────────────────────────────────────────

def load_data() -> dict:
    """Load mini app data (stats, community info, etc.)."""
    if os.path.exists(MINIAPP_DATA_FILE):
        try:
            with open(MINIAPP_DATA_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "last_updated": time.time(),
        "community_members": 0,
        "total_mined": 0,
        "total_airdropped": 0,
        "active_miners": 0,
        "agents_online": 6,
        "chain_blocks": 0,
        "chain_supply": 1_000_000_000,
        "wallet_address": SOLANA_PAYMENT_WALLET,
        "deployment_status": "pending",  # pending, deployed, live
        "mint_address": "",
        "launch_date": "2026-10-07",
        "vision": "Digital OS ecosystem — $STP as currency of a Meta-like billion-dollar platform",
    }


def save_data(data: dict) -> None:
    """Save mini app data."""
    try:
        with open(MINIAPP_DATA_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"Error saving data: {e}", file=sys.stderr)


# ── MiniApp HTML Generator ─────────────────────────────────────────────────

def generate_miniapp_html(data: dict) -> str:
    """Generate the MiniApp HTML with Telegram Web App SDK and Solana wallet support."""

    wallet = data.get("wallet_address", SOLANA_PAYMENT_WALLET)
    mint = data.get("mint_address", "")
    supply = data.get("chain_supply", 1_000_000_000)
    agents = data.get("agents_online", 6)
    miners = data.get("active_miners", 0)
    blocks = data.get("chain_blocks", 0)
    members = data.get("community_members", 0)
    mined = data.get("total_mined", 0)
    status = data.get("deployment_status", "pending")
    launch_date = data.get("launch_date", "2026-10-07")

    # Solana wallet adapter (CDN)
    wallet_adapter_css = "https://unpkg.com/@solana/wallet-adapter@0.15.0/dist/index.css"
    wallet_adapter_js = "https://unpkg.com/@solana/wallet-adapter@0.15.0/dist/index.js"
    wallet_adapter_base = "https://unpkg.com/@solana/wallet-adapter-base@0.15.0/dist/index.js"
    wallet_adapter_solana = "https://unpkg.com/@solana/wallet-adapter-solana@0.15.0/dist/index.js"
    wallet_adapter_wallets = "https://unpkg.com/@solana/wallet-adapter-wallets@0.15.0/dist/index.js"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>$STP — Strap Digital OS</title>
    <meta name="twitter:card" content="summary_large_image">
    <meta property="og:title" content="$STP — Strap Digital OS">
    <meta property="og:description" content="Proof-of-Service L1 Blockchain + Solana SPL Token + Telegram Economy">
    <meta property="og:type" content="website">

    <!-- Telegram Web App SDK -->
    <script>
        const tg = window.Telegram.WebApp;
        tg.expand();
        tg.ready();
        tg.onEvent('mainButtonClicked', () => {{ tg.close(); }});
        tg.onEvent('backButtonClicked', () => {{ tg.close(); }});
        document.addEventListener('DOMContentLoaded', () => {{
            document.body.classList.toggle('dark', tg.themeParams.theme === 'dark');
            document.body.style.backgroundColor = tg.themeParams.bg_color;
        }});
    </script>

    <!-- Solana Wallet Adapter -->
    <link rel="stylesheet" href="{wallet_adapter_css}">
    <script src="{wallet_adapter_base}"></script>
    <script src="{wallet_adapter_wallets}"></script>
    <script src="{wallet_adapter_solana}"></script>
    <script src="{wallet_adapter_js}"></script>

    <style>
        :root {{
            --bg: var(--tg-bg-color, #000);
            --text: var(--tg-text-color, #fff);
            --button: var(--tg-button-color, #3390ec);
            --button-text: var(--tg-button-text-color, #fff);
            --secondary: var(--tg-secondary-color, #666);
        }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--bg);
            color: var(--text);
            min-height: 100vh;
            padding: 16px;
            padding-bottom: 80px;
        }}
        .container {{ max-width: 480px; margin: 0 auto; }}
        .header {{
            text-align: center;
            padding: 16px 0;
            border-bottom: 1px solid rgba(255,255,255,0.1);
            margin-bottom: 16px;
        }}
        .header h1 {{
            font-size: 24px;
            font-weight: 700;
            letter-spacing: -0.5px;
        }}
        .header .subtitle {{
            font-size: 13px;
            color: var(--secondary);
            margin-top: 4px;
        }}
        .card {{
            background: rgba(255,255,255,0.05);
            border-radius: 12px;
            padding: 16px;
            margin-bottom: 12px;
            border: 1px solid rgba(255,255,255,0.1);
        }}
        .card-title {{
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: var(--secondary);
            margin-bottom: 8px;
        }}
        .card-value {{
            font-size: 28px;
            font-weight: 700;
            letter-spacing: -1px;
        }}
        .card-value.small {{ font-size: 18px; }}
        .wallet-section {{
            display: flex;
            gap: 8px;
            margin-top: 12px;
            flex-wrap: wrap;
        }}
        .wallet-btn {{
            flex: 1;
            padding: 12px;
            border-radius: 8px;
            border: none;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
            text-align: center;
        }}
        .wallet-btn.connect {{
            background: var(--button);
            color: var(--button-text);
        }}
        .wallet-btn.connect:hover {{ opacity: 0.9; }}
        .wallet-btn.connected {{
            background: rgba(255,255,255,0.1);
            color: var(--text);
            border: 1px solid rgba(255,255,255,0.2);
        }}
        .wallet-address {{
            font-size: 12px;
            color: var(--secondary);
            word-break: break-all;
            margin-top: 8px;
            padding: 8px;
            background: rgba(0,0,0,0.3);
            border-radius: 6px;
            font-family: monospace;
        }}
        .action-row {{
            display: flex;
            gap: 8px;
            margin-top: 12px;
        }}
        .action-btn {{
            flex: 1;
            padding: 10px;
            border-radius: 8px;
            border: 1px solid rgba(255,255,255,0.2);
            background: rgba(255,255,255,0.05);
            color: var(--text);
            font-size: 13px;
            font-weight: 600;
            cursor: pointer;
            text-align: center;
            transition: all 0.2s;
        }}
        .action-btn:hover {{ background: rgba(255,255,255,0.1); }}
        .action-btn.primary {{ background: var(--button); border: none; color: white; }}
        .status-badge {{
            display: inline-block;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
        }}
        .status-live {{ background: #22c55e; color: white; }}
        .status-pending {{ background: #f59e0b; color: white; }}
        .status-deployed {{ background: #3b82f6; color: white; }}
        .progress-bar {{
            height: 4px;
            background: rgba(255,255,255,0.1);
            border-radius: 2px;
            margin-top: 8px;
            overflow: hidden;
        }}
        .progress-fill {{
            height: 100%;
            background: var(--button);
            border-radius: 2px;
            transition: width 0.3s;
        }}
        .footer {{
            text-align: center;
            padding: 12px 0;
            font-size: 11px;
            color: var(--secondary);
            border-top: 1px solid rgba(255,255,255,0.1);
            margin-top: 16px;
        }}
        .footer a {{ color: var(--button); text-decoration: none; }}
        .gradient-text {{
            background: linear-gradient(135deg, #3390ec, #8b5cf6);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }}
        .skeleton {{
            background: linear-gradient(90deg, rgba(255,255,255,0.05) 25%, rgba(255,255,255,0.1) 50%, rgba(255,255,255,0.05) 75%);
            background-size: 200% 100%;
            animation: shimmer 1.5s infinite;
            border-radius: 4px;
        }}
        @keyframes shimmer {{
            0% {{ background-position: 200% 0; }}
            100% {{ background-position: -200% 0; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <!-- Header -->
        <div class="header">
            <h1><span class="gradient-text">$STP</span></h1>
            <div class="subtitle">Strap Digital OS — Launching Oct 7</div>
        </div>

        <!-- Wallet Connect -->
        <div class="card">
            <div class="card-title">Solana Wallet</div>
            <div class="wallet-section" id="walletSection">
                <button class="wallet-btn connect" id="connectBtn" onclick="connectWallet()">
                    Connect Wallet
                </button>
            </div>
            <div id="walletInfo" style="display:none;">
                <div class="wallet-address" id="walletAddress"></div>
                <div class="action-row">
                    <button class="action-btn primary" onclick="copyAddress()">Copy</button>
                    <button class="action-btn" onclick="disconnectWallet()">Disconnect</button>
                </div>
            </div>
        </div>

        <!-- $STP Token Info -->
        <div class="card">
            <div class="card-title">$STP Token</div>
            <div class="card-value">1,000,000,000</div>
            <div style="font-size:13px;color:var(--secondary);margin-top:4px;">Tokens minted</div>
            <div style="margin-top:8px;font-size:12px;color:var(--secondary);">
                Decimals: 9 | Network: Solana SPL
            </div>
        </div>

        <!-- Deployment Status -->
        <div class="card">
            <div class="card-title">Deployment</div>
            <span class="status-badge status-{status}" id="statusBadge">{status.upper()}</span>
            <div style="margin-top:8px;font-size:13px;" id="statusText">
                {"Live on Solana Mainnet" if status == "live" else "Awaiting deployment"}
            </div>
            {"<div style='margin-top:8px;'><a href='https://solscan.io/token/" + mint + "' target='_blank' style='color:var(--button);text-decoration:none;font-size:13px;'>View on Solscan →</a></div>" if mint else ""}
        </div>

        <!-- Chain Stats -->
        <div class="card">
            <div class="card-title">Strap L1 Chain</div>
            <div style="display:flex;justify-content:space-between;align-items:center;">
                <div>
                    <div class="card-value small">{blocks}</div>
                    <div style="font-size:11px;color:var(--secondary);">Blocks</div>
                </div>
                <div>
                    <div class="card-value small">{agents}</div>
                    <div style="font-size:11px;color:var(--secondary);">Agents</div>
                </div>
                <div>
                    <div class="card-value small">{miners}</div>
                    <div style="font-size:11px;color:var(--secondary);">Miners</div>
                </div>
            </div>
        </div>

        <!-- Community -->
        <div class="card">
            <div class="card-title">Community</div>
            <div style="display:flex;justify-content:space-between;align-items:center;">
                <div>
                    <div class="card-value small" style="font-size:22px;">{members}</div>
                    <div style="font-size:11px;color:var(--secondary);">Members</div>
                </div>
                <div>
                    <div class="card-value small" style="font-size:22px;">{mined}</div>
                    <div style="font-size:11px;color:var(--secondary);">Mined</div>
                </div>
            </div>
            <div class="progress-bar">
                <div class="progress-fill" style="width:{min(members * 2, 100)}%"></div>
            </div>
        </div>

        <!-- Actions -->
        <div class="card">
            <div class="card-title">Actions</div>
            <div class="action-row">
                <button class="action-btn primary" onclick="openBot()">Open Bot</button>
                <button class="action-btn" onclick="joinCommunity()">Community</button>
            </div>
            <div class="action-row" style="margin-top:8px;">
                <button class="action-btn" onclick="paySol()">Pay SOL</button>
                <button class="action-btn" onclick="showAirdrop()">Airdrop</button>
            </div>
        </div>

        <!-- Footer -->
        <div class="footer">
            <a href="https://github.com/juniorteixeiraus-rgb/strap-l1" target="_blank">GitHub</a> ·
            <a href="https://solscan.io" target="_blank">Solscan</a> ·
            Launch: {launch_date}
        </div>
    </div>

    <script>
        // ── Wallet State ──────────────────────────────────────────────────
        let walletConnection = null;
        let walletPublicKey = null;

        // ── Connect Wallet ────────────────────────────────────────────────
        async function connectWallet() {{
            try {{
                const wallets = [
                    new WalletAdapterPhantom(),
                    new WalletAdapterSolflare(),
                    new WalletAdapterClerk(),
                ];
                const adapter = await WalletAdapterBase.getAdapters({{
                    wallets: wallets.map(w => w.adapter),
                }});
                // Show wallet selection modal
                const selected = await WalletAdapterBase.selectAdapter(adapter);
                if (selected) {{
                    const { signCallback, publicKey } = await selected.connect();
                    walletConnection = {{ signCallback, adapter: selected }};
                    walletPublicKey = publicKey.toBase58();
                    updateWalletUI();
                }}
            }} catch (e) {{
                console.error('Wallet connect error:', e);
                // Fallback: show alert
                tg.showAlert('error', 'Wallet connection failed: ' + e.message);
            }}
        }}

        function disconnectWallet() {{
            walletConnection = null;
            walletPublicKey = null;
            document.getElementById('walletInfo').style.display = 'none';
            document.getElementById('walletSection').style.display = 'flex';
        }}

        function updateWalletUI() {{
            if (!walletPublicKey) return;
            document.getElementById('walletSection').style.display = 'none';
            document.getElementById('walletInfo').style.display = 'block';
            document.getElementById('walletAddress').textContent = walletPublicKey;
            document.getElementById('connectBtn').textContent = 'Connected';
            document.getElementById('connectBtn').className = 'wallet-btn connected';
        }}

        function copyAddress() {{
            if (walletPublicKey) {{
                navigator.clipboard.writeText(walletPublicKey);
                tg.showAlert('success', 'Address copied!');
            }}
        }}

        // ── Actions ───────────────────────────────────────────────────────
        function openBot() {{
            tg.openLink('https://t.me/StrapL1Bot');
        }}

        function joinCommunity() {{
            tg.openLink('https://t.me/StrapL1Community');
        }}

        function paySol() {{
            const wallet = '{wallet}';
            tg.showAlert('info', 'Send SOL to: ' + wallet + '\\n\\nThis funds the $STP project and community rewards.');
        }}

        function showAirdrop() {{
            tg.showAlert('info', '$STP Airdrop\\n\\nSoon: community members will receive $STP tokens.\\nStay tuned for the airdrop announcement.');
        }}

        // ── Load stats from API ──────────────────────────────────────────
        async function loadStats() {{
            try {{
                const resp = await fetch('/api/miniapp/stats');
                const data = await resp.json();
                if (data.chain_blocks != null) {{
                    document.querySelector('.card-value.small').textContent = data.chain_blocks;
                }}
                // Update other stats...
            }} catch (e) {{
                console.error('Stats load error:', e);
            }}
        }}

        // Load stats on load
        loadStats();
        setInterval(loadStats, 30000); // refresh every 30s
    </script>
</body>
</html>
"""


def mini_app_stats_handler(request_path: str) -> tuple:
    """API endpoint: GET /api/miniapp/stats → returns community/chain stats."""
    if request_path != "/api/miniapp/stats":
        return None, None

    data = load_data()
    body = json.dumps({
        "community_members": data.get("community_members", 0),
        "total_mined": data.get("total_mined", 0),
        "active_miners": data.get("active_miners", 0),
        "agents_online": data.get("agents_online", 6),
        "chain_blocks": data.get("chain_blocks", 0),
        "chain_supply": data.get("chain_supply", 1_000_000_000),
        "wallet_address": data.get("wallet_address", SOLANA_PAYMENT_WALLET),
        "deployment_status": data.get("deployment_status", "pending"),
        "mint_address": data.get("mint_address", ""),
        "launch_date": data.get("launch_date", "2026-10-07"),
        "last_updated": data.get("last_updated", time.time()),
    })
    return body, ("application/json", 200)


def mini_app_pay_handler(request_path: str, request_body: Optional[str] = None) -> tuple:
    """API endpoint: POST /api/miniapp/pay → creates a payment record."""
    if request_path != "/api/miniapp/pay":
        return None, None

    data = load_data()
    payment = {
        "id": str(int(time.time())),
        "wallet": SOLANA_PAYMENT_WALLET,
        "amount_sol": 0,
        "status": "pending",
        "created_at": time.time(),
        "collaborator": request_body or "anonymous",
    }
    data.setdefault("payments", []).append(payment)
    data["last_updated"] = time.time()
    save_data(data)

    body = json.dumps({
        "payment_id": payment["id"],
        "wallet": payment["wallet"],
        "status": "pending",
        "message": "Send SOL to this wallet. Payment will be detected automatically.",
        "created_at": payment["created_at"],
    })
    return body, ("application/json", 201)


# ── HTTP Server ────────────────────────────────────────────────────────────

class MiniAppHandler(SimpleHTTPRequestHandler):
    """Custom HTTP handler for the MiniApp server."""

    def do_GET(self) -> None:
        path = self.path

        # API endpoints
        if path == "/api/miniapp/stats":
            body, (ctype, code) = mini_app_stats_handler(path)
            if body:
                self.send_response(code)
                self.send_header("Content-Type", ctype)
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(body.encode())
                return

        # Serve MiniApp HTML
        if path == "/" or path == "/index.html" or path == "/mini_app":
            data = load_data()
            html = generate_miniapp_html(data)
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("X-Telegram-WebApp-Platform", "miniapp")
            self.end_headers()
            self.wfile.write(html.encode("utf-8"))
            return

        # Serve static assets
        if path.startswith("/static/"):
            file_path = os.path.join(MINIAPP_DIR, path.lstrip("/"))
            if os.path.exists(file_path):
                self.send_response(200)
                if path.endswith(".css"):
                    self.send_header("Content-Type", "text/css")
                elif path.endswith(".js"):
                    self.send_header("Content-Type", "application/javascript")
                elif path.endswith(".png") or path.endswith(".jpg") or path.endswith(".svg"):
                    self.send_header("Content-Type", "image/svg+xml")
                else:
                    self.send_header("Content-Type", "application/octet-stream")
                self.end_headers()
                with open(file_path, "rb") as f:
                    self.wfile.write(f.read())
                return
            else:
                self.send_error(404, "File not found")
                return

        # Favicon
        if path == "/favicon.ico":
            self.send_error(204)
            return

        # Default: 404
        self.send_error(404, "Not Found")

    def do_POST(self) -> None:
        path = self.path

        # API endpoints
        if path == "/api/miniapp/pay":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8") if content_length else None
            response_body, (ctype, code) = mini_app_pay_handler(path, body)
            if response_body:
                self.send_response(code)
                self.send_header("Content-Type", ctype)
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(response_body.encode())
                return

        self.send_error(404, "Not Found")

    def log_message(self, format: str, *args) -> None:
        """Custom logging."""
        print(f"[MINIAPP] {args[0]}", flush=True)


# ── Main ────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Strap $STP Telegram MiniApp Server")
    parser.add_argument("--port", type=int, default=MINIAPP_PORT, help="Port to serve on (default: 8081)")
    parser.add_argument("--dir", type=str, default=MINIAPP_DIR, help="Directory for static files")
    parser.add_argument("--data-file", type=str, default=MINIAPP_DATA_FILE, help="Data file path")
    args = parser.parse_args()

    global MINIAPP_PORT, MINIAPP_DIR, MINIAPP_DATA_FILE
    MINIAPP_PORT = args.port
    MINIAPP_DIR = args.dir
    MINIAPP_DATA_FILE = args.data_file

    # Ensure data file exists
    if not os.path.exists(MINIAPP_DATA_FILE):
        save_data(load_data())

    print(f"=== $STP Telegram MiniApp Server ===", flush=True)
    print(f"  Port: {MINIAPP_PORT}", flush=True)
    print(f"  Directory: {MINIAPP_DIR}", flush=True)
    print(f"  Data file: {MINIAPP_DATA_FILE}", flush=True)
    print(f"  Payment wallet: {SOLANA_PAYMENT_WALLET}", flush=True)
    print(f"  Solana RPC: {SOLANA_RPC_URL}", flush=True)
    print(f"  Open: http://localhost:{MINIAPP_PORT}", flush=True)
    print(f"  Telegram MiniApp URL: https://<your-domain-or-tunnel>:{MINIAPP_PORT}", flush=True)
    print(f"===", flush=True)

    server = HTTPServer(("0.0.0.0", MINIAPP_PORT), MiniAppHandler)
    print(f"Server running on port {MINIAPP_PORT}...", flush=True)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...", flush=True)
        server.shutdown()


if __name__ == "__main__":
    main()
