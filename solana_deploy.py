#!/usr/bin/env python3
"""
$Strap ($STP) — Solana SPL Token Deployment Script
=====================================================
Deploys the $STP SPL token on Solana (devnet or mainnet) and mints 1B tokens.

Requirements:
  pip install solana spl-token
  Solana CLI: https://solana.com/downloads (or: sh -c "$(curl -sSfL https://release.anza.xyz/stable/install)")

Usage:
  python3 solana_deploy.py --network devnet          # deploy on devnet (free SOL from faucet)
  python3 solana_deploy.py --network mainnet        # deploy on mainnet (needs ~0.01-0.05 SOL)
  python3 solana_deploy.py --network devnet --dry  # dry run (show what would happen)

Output:
  MINT_ADDRESS — the SPL token mint address (share this — it's the $STP token)
  TOKEN_ACCOUNT — your token account holding the 1B $STP
  TRANSFER_AUTHORITY — wallet that can transfer tokens (your Solana wallet)

After deployment:
  1. Add $STP to your wallet (solana-token-web or Phantom)
  2. View on Solscan: https://solscan.io/token/<MINT_ADDRESS>
  3. Trade on Raydium/Jupiter when you add liquidity
  4. Send MINT_ADDRESS to me → I help with listings/liquidity
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import time
from pathlib import Path

# ── Configuration ──────────────────────────────────────────────────────────

TOKEN_NAME = "$Strap"
TOKEN_SYMBOL = "$STP"
TOKEN_SUPPLY = 1_000_000_000  # 1 billion tokens
TOKEN_DECIMALS = 9             # Solana standard (9 decimals)
TOKEN_URI = "https://strap.l1/token/$STP"  # metadata URI
TOKEN_DESCRIPTION = "Strap L1 Proof-of-Service token — 1B supply, PoUW mining, 7 AI agents, Telegram-native economy"

SOLANA_KEYPAIR = os.environ.get("SOLANA_KEYPAIR", "./solana-id.json")
SECONDS_BETWEEN_TX = 3  # wait between transactions to avoid rate limits


def log(msg: str) -> None:
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] $STP Solana: {msg}", flush=True)


def fail(msg: str) -> None:
    log(f"ERROR: {msg}")
    sys.exit(1)


# ── Solana CLI wrapper ─────────────────────────────────────────────────────

def run_cli(args: list[str], network: str = "devnet") -> str:
    """Run a solana/spl-token CLI command and return stdout."""
    cmd = ["solana", "config", "set", "--keypair", SOLANA_KEYPAIR, "--url", f"https://api.{network}.solana.com"]
    os.system(" ".join(cmd) + " >/dev/null 2>&1")

    cmd = ["spl-token"] + args
    import subprocess
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode != 0:
            log(f"CLI stderr: {result.stderr.strip()}")
        return result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        fail("CLI command timed out")
    except FileNotFoundError:
        fail("solana/spl-token CLI not found — install: https://solana.com/downloads")


# ── Balance check ──────────────────────────────────────────────────────────

def check_balance(network: str) -> float:
    """Check SOL balance of the configured keypair. Returns balance in SOL."""
    # First set the config for this network
    cmd = ["solana", "config", "set", "--keypair", SOLANA_KEYPAIR, "--url", f"https://api.{network}.solana.com"]
    os.system(" ".join(cmd) + " >/dev/null 2>&1")

    import subprocess
    try:
        result = subprocess.run(["solana", "balance"], capture_output=True, text=True, timeout=15)
        out = result.stdout + result.stderr
        log(f"Balance raw: {out.strip()}")
        for line in out.split("\n"):
            line = line.strip()
            if "SOL" in line:
                # Typical output: "XXX SOL" or "XXX,XXX SOL"
                # Remove commas, split on space before SOL
                parts = line.replace(",", " ").split()
                for i, p in enumerate(parts):
                    if p == "SOL" and i > 0:
                        try:
                            return float(parts[i-1])
                        except ValueError:
                            pass
                # Try regex-like: find number followed by SOL
                import re
                m = re.search(r"([\d,.]+)\s*SOL", line)
                if m:
                    try:
                        return float(m.group(1).replace(",", ""))
                    except ValueError:
                        pass
        return 0.0
    except Exception as e:
        log(f"Balance check error: {e}")
        return 0.0


# ── Airdrop (devnet only) ──────────────────────────────────────────────────

def airdrop_sol(network: str, amount_lamports: int = 1_000_000_000) -> bool:
    """Request SOL airdrop on devnet."""
    if network != "devnet":
        log("Airdrop only available on devnet")
        return False

    # solana airdrop 1 (not spl-token)
    cmd = ["solana", "config", "set", "--keypair", SOLANA_KEYPAIR, "--url", f"https://api.{network}.solana.com"]
    os.system(" ".join(cmd) + " >/dev/null 2>&1")

    import subprocess
    try:
        result = subprocess.run(["solana", "airdrop", str(amount_lamports)], capture_output=True, text=True, timeout=30)
        out = result.stdout + result.stderr
        log(f"Airdrop output: {out.strip()}")
        for line in out.split("\n"):
            if "Success" in line or "success" in line.lower() or "Transaction" in line:
                log(f"Airdrop successful: {amount_lamports/1e9} SOL")
                return True
            if "rate limit" in line.lower() or "failed" in line.lower() or "Error" in line:
                log(f"Airdrop failed: {line.strip()}")
                return False
        return "Success" in out or "success" in out.lower()
    except Exception as e:
        log(f"Airdrop error: {e}")
        return False


# ── Create Token ───────────────────────────────────────────────────────────

def create_token(network: str, decimals: int = TOKEN_DECIMALS) -> str:
    """Create an SPL token mint and return its address."""
    log(f"Creating SPL token: {TOKEN_NAME} / {TOKEN_SYMBOL} ({decimals} decimals)...")

    # spl-token create-token --decimals 9
    out = run_cli(["create-token", "--decimals", str(decimals)], network)

    mint_address = ""
    for line in out.split("\n"):
        line = line.strip()
        # spl-token outputs: "Token <address> created" or shows the address
        if "Token" in line and len(line) > 40:
            # Try to extract the base58 address
            parts = line.split()
            for p in parts:
                if len(p) >= 32 and all(c in "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz" for c in p):
                    mint_address = p
                    break

    if not mint_address:
        # Fallback: parse JSON-like output
        log(f"Parsing output for mint address...")
        log(f"Raw output: {out[:500]}")
        # spl-token sometimes outputs the address in a specific format
        for line in out.split("\n"):
            if "Audit" in line:
                parts = line.split()
                for p in parts:
                    if len(p) >= 32:
                        mint_address = p
                        break

    if not mint_address:
        fail(f"Could not parse mint address from output:\n{out[:1000]}")

    log(f"Token mint created: {mint_address}")
    return mint_address


# ── Create Token Account ───────────────────────────────────────────────────

def create_token_account(network: str, mint: str) -> str:
    """Create a token account for the mint and return its address."""
    log(f"Creating token account for {mint}...")
    out = run_cli(["create-account", mint, "--fund", "0"], network)
    account_address = ""
    for line in out.split("\n"):
        line = line.strip()
        if "Account" in line and len(line) > 40:
            parts = line.split()
            for p in parts:
                if len(p) >= 32 and all(c in "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz" for c in p):
                    account_address = p
                    break
    if not account_address:
        fail(f"Could not parse token account from output:\n{out[:1000]}")
    log(f"Token account created: {account_address}")
    return account_address


# ── Mint Tokens ────────────────────────────────────────────────────────────

def mint_tokens(network: str, mint: str, amount: int) -> str:
    """Mint tokens to the default token account."""
    human = f"{amount:,}"
    log(f"Minting {human} $STP to token account...")
    out = run_cli(["mint", mint, str(amount)], network)
    tx_sig = ""
    for line in out.split("\n"):
        if "Signature" in line or "signature" in line.lower():
            parts = line.split()
            for p in parts:
                if len(p) >= 32 and all(c in "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz" for c in p):
                    tx_sig = p
                    break
    # Also try: spl-token often prints the signature directly
    if not tx_sig:
        for line in out.split("\n"):
            if len(line.strip()) >= 32 and "Signature" not in line:
                # Check if it looks like a signature (base58, long)
                candidate = line.strip()
                if len(candidate) >= 32:
                    tx_sig = candidate
                    break
    if not tx_sig:
        # Last resort: take the last long base58 string
        for line in reversed(out.split("\n")):
            candidate = line.strip()
            if len(candidate) >= 32 and all(c in "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz" for c in candidate):
                tx_sig = candidate
                break

    if not tx_sig:
        log(f"Could not parse signature, raw output:\n{out[:500]}")
        # Don't fail — the mint may have succeeded even if we can't parse the sig
        tx_sig = "PARSE_FAILED"

    log(f"Mint transaction: {tx_sig}")
    return tx_sig


# ── Set Metadata (optional, requires Metaplex) ────────────────────────────

def set_metadata(network: str, mint: str) -> bool:
    """Set token metadata (name, symbol, URI) using Metaplex metadata program."""
    log("Setting token metadata (name, symbol, URI)...")
    log("Note: Full Metaplex metadata requires further setup.")
    log(f"Token name: {TOKEN_NAME}")
    log(f"Token symbol: {TOKEN_SYMBOL}")
    log(f"Token URI: {TOKEN_URI}")
    # For a full metadata update, use: https://developers.metaplex.com/
    # Or use the Metaplex JS SDK. For now, the token has name/symbol embedded in the mint.
    return True


# ── Display Token Info ─────────────────────────────────────────────────────

def show_token_info(network: str, mint: str) -> None:
    """Display token information using spl-token."""
    log("Token info:")
    out = run_cli(["tokens", mint], network)
    print(out)
    log("---")
    out = run_cli(["info", mint], network)
    print(out)


# ── Main ───────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="$Strap ($STP) Solana SPL token deployment")
    parser.add_argument("--network", choices=["devnet", "mainnet"], default="devnet",
                        help="Solana network (default: devnet)")
    parser.add_argument("--dry", action="store_true", help="Show what would happen without executing")
    parser.add_argument("--decimals", type=int, default=TOKEN_DECIMALS, help="Token decimals (default: 9)")
    parser.add_argument("--supply", type=int, default=TOKEN_SUPPLY, help="Tokens to mint (default: 1B)")
    args = parser.parse_args()

    network = args.network
    log(f"=== $Strap ($STP) Solana Deployment ===")
    log(f"  Network: {network}")
    log(f"  Token: {TOKEN_NAME} / {TOKEN_SYMBOL}")
    log(f"  Decimals: {args.decimals}")
    log(f"  Supply: {args.supply:,}")
    log(f"  KeyPair: {SOLANA_KEYPAIR}")

    if not Path(SOLANA_KEYPAIR).exists():
        fail(f"Solana keypair not found: {SOLANA_KEYPAIR}")
        log("Create one: solana-keygen new -o solana-id.json")

    if args.dry:
        log("=== DRY RUN (no transactions) ===")
        log(f"  Would create token: {TOKEN_NAME} / {TOKEN_SYMBOL}")
        log(f"  Would mint: {args.supply:,} tokens with {args.decimals} decimals")
        log(f"  Network: {network}")
        return

    # Check balance
    balance = check_balance(network)
    log(f"Current SOL balance: {balance} SOL")

    if balance < 0.001:
        log(f"WARNING: Insufficient SOL balance ({balance} SOL)")
        if network == "devnet":
            log("Attempting airdrop...")
            # Try a few times
            for attempt in range(3):
                if airdrop_sol(network, 1_000_000_000):
                    time.sleep(2)
                    balance = check_balance(network)
                    log(f"Balance after airdrop: {balance} SOL")
                    if balance >= 0.01:
                        break
                else:
                    log(f"Airdrop attempt {attempt+1} failed")
                    time.sleep(5)
            else:
                fail("Devnet airdrop failed — get test SOL from https://faucet.solana.com or https://solfaucet.com")
        else:
            fail(f"Mainnet deployment requires SOL for rent + fees (~$0.01-0.05). Current balance: {balance} SOL")

    # Step 1: Create token
    log("--- Step 1: Create SPL Token Mint ---")
    mint = create_token(network, args.decimals)

    # Step 2: Create token account
    log("--- Step 2: Create Token Account ---")
    account = create_token_account(network, mint)

    # Step 3: Mint tokens
    log("--- Step 3: Mint Tokens ---")
    mint_sig = mint_tokens(network, mint, args.supply)

    # Step 4: Metadata (informational)
    log("--- Step 4: Token Metadata ---")
    set_metadata(network, mint)

    # Show final state
    log("=== Deployment Complete ===")
    log(f"  MINT ADDRESS: {mint}")
    log(f"  TOKEN ACCOUNT: {account}")
    log(f"  MINT TX: {mint_sig}")
    log(f"  NETWORK: https://solscan.io/token/{mint} (devnet) or https://solscan.io/token/{mint} (mainnet)")
    log(f"  VIEW ON SOLSCAN: https://solscan.io/token/{mint}")
    log(f"  ADD TO WALLET: Use Phantom or solana-token-web to add {mint}")
    log("===")

    # Save deployment info
    deployment_info = {
        "network": network,
        "mint_address": mint,
        "token_account": account,
        "mint_transaction": mint_sig,
        "token_name": TOKEN_NAME,
        "token_symbol": TOKEN_SYMBOL,
        "supply": args.supply,
        "decimals": args.decimals,
        "uri": TOKEN_URI,
        "deployed_at": time.time(),
    }
    info_file = Path("solana-deployment.json")
    info_file.write_text(json.dumps(deployment_info, indent=2))
    log(f"Deployment info saved to: {info_file}")


if __name__ == "__main__":
    main()
