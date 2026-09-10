#!/usr/bin/env python3
"""
STRP Token Deployment Helper — guides you through deploying STRP.sol on Base.

This script does NOT hold or transmit your private key.
It generates the deployment steps and contract bytecode for you to paste
into Remix or run with your own wallet.

Usage:
  python3 strp_deploy.py              # step-by-step guide
  python3 strp_deploy.py --compile   # show compiled bytecode (for Remix)
  python3 strp_deploy.py --verify    # show Etherscan verification params
"""

from __future__ import annotations

import sys
import os
import json
import subprocess
import re
from pathlib import Path

STRP_SOL_PATH = Path(__file__).parent / "STRP.sol"
NETWORKS = {
    "base-mainnet": {
        "name": "Base Mainnet",
        "chain_id": 8453,
        "rpc": "https://mainnet.base.org",
        "explorer": "https://basescan.org",
        "token": "ETH",
        "gas_estimate": "tiny (~$0.50-2 per deploy)",
    },
    "base-sepolia": {
        "name": "Base Sepolia (Testnet)",
        "chain_id": 84531,
        "rpc": "https://sepolia.base.org",
        "explorer": "https://sepolia.basescan.org",
        "token": "ETH (faucet)",
        "gas_estimate": "free (testnet ETH from faucet)",
    },
    "ethereum": {
        "name": "Ethereum Mainnet",
        "chain_id": 1,
        "rpc": "https://eth.llamarpc.com",
        "explorer": "https://etherscan.io",
        "token": "ETH",
        "gas_estimate": "expensive (~$5-20 per deploy)",
    },
}

def print_banner():
    print("=" * 60)
    print("  STRP Token Deployment — Base Chain (Coinbase L2)")
    print("=" * 60)
    print()

def show_networks():
    print("Available networks:")
    print()
    for key, net in NETWORKS.items():
        print(f"  [{key}]  {net['name']}")
        print(f"         Chain ID:    {net['chain_id']}")
        print(f"         RPC:         {net['rpc']}")
        print(f"         Explorer:    {net['explorer']}")
        print(f"         Native:      {net['token']}")
        print(f"         Gas cost:    {net['gas_estimate']}")
        print()
    print("RECOMMENDATION: Start on [base-sepolia] (free testnet),")
    print("then deploy to [base-mainnet] once verified.")
    print()

def show_recipe():
    print("DEPLOYMENT RECIPE (no private key needed from this script):")
    print()
    print("  1. Install a wallet")
    print("     - MetaMask:    https://metamask.io")
    print("     - Coinbase Wallet: https://www.coinbase.com/wallet")
    print()
    print("  2. Add Base network to your wallet")
    print("     - MetaMask: Settings → Networks → Add Network")
    print("       Network Name: Base")
    print("       RPC URL:      https://mainnet.base.org")
    print("       Chain ID:     8453")
    print("       Currency:     ETH")
    print("       Block Explorer: https://basescan.org")
    print()
    print("     OR use Chainlist.org → search 'Base' → connect wallet")
    print()
    print("  3. Get ETH for gas")
    print("     - Mainnet: buy ETH on Coinbase → send to your wallet")
    print("     - Testnet: get free Sepolia ETH from faucet:")
    print("       https://www.alchemy.com/faucets/base-sepolia")
    print("       https://cloud.google.com/application/web3/faucet/base/ethereum")
    print()
    print("  4. Open Remix")
    print("     - Go to: https://remix.ethereum.org")
    print("     - Create new file → name it STRP.sol")
    print("     - Paste the contents of STRP.sol (in this folder)")
    print()
    print("  5. Compile")
    print("     - Go to 'Solidity Compiler' tab (left sidebar)")
    print("     - Select compiler: 0.8.20 (or latest 0.8.x)")
    print("     - Click 'Compile STRP.sol'")
    print("     - Verify: green checkmark, no errors")
    print()
    print("  6. Deploy")
    print("     - Go to 'Deploy & Run Transactions' tab")
    print("     - Environment: 'Injected Provider - MetaMask' (or Coinbase Wallet)")
    print("     - Make sure your wallet is on Base network")
    print("     - Contract: STRP → click 'Deploy'")
    print("     - Confirm in your wallet (gas fee shown)")
    print()
    print("  7. Verify on Basescan")
    print("     - Copy the deployed contract address from Remix")
    print("     - Go to https://basescan.org/address/<YOUR_ADDRESS>")
    print("     - Click 'Verify and Publish'")
    print("     - Select 'Solidity (Single file)' compilation")
    print("     - Paste the STRP.sol source code")
    print("     - Compiler version: match what you used in Remix")
    print("     - Click 'Verify and Publish'")
    print()
    print("  8. Add STRP to your wallet")
    print("     - In MetaMask: Settings → Assets → Import tokens")
    print("     - Token contract address: (your deployed address)")
    print("     - Symbol: STRP, Decimals: 18")
    print("     - Click 'Import'")
    print()
    print("  9. Trade / add liquidity")
    print("     - Base DEXs: https://aerodrome.finance, https://.uniswap.org")
    print("     - Connect wallet → trade STRP or add liquidity pool")
    print()

def compile_for_remix():
    """Check that solc is available and show bytecode if possible."""
    print("Checking for Solidity compiler (solc)...")
    try:
        result = subprocess.run(
            ["solc", "--version"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            print(f"  solc found: {result.stdout.strip()}")
        else:
            print("  solc not found or returned error.")
            print("  Install: https://github.com/ethereum/solidity/releases")
            print("  Or just use Remix (no local compiler needed).")
            return
    except FileNotFoundError:
        print("  solc not installed locally.")
        print("  Install: https://github.com/ethereum/solidity/releases")
        print("  Or just use Remix — no local compiler needed.")
        return

    if not STRP_SOL_PATH.exists():
        print(f"  ERROR: {STRP_SOL_PATH} not found!")
        return

    print(f"  Compiling {STRP_SOL_PATH}...")
    try:
        result = subprocess.run(
            ["solc", "--bin", "--optimize", str(STRP_SOL_PATH)],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode != 0:
            print(f"  Compilation error:\n{result.stderr}")
            return
        # Extract the bytecode from solc output
        lines = result.stdout.strip().split("\n")
        for line in lines:
            if line.startswith("Binary of the runtime part:"):
                continue
            if line.startswith("Binary of the init part:"):
                print()
                print("  === INIT CODE (for deployment) ===")
                # solc outputs hex in chunks; reassemble
                bytecode = ""
                for l in lines:
                    if l.startswith("Binary of"):
                        break
                    bytecode += l.strip()
                print(f"  {bytecode[:200]}...")
                print(f"  (length: {len(bytecode)} chars)")
                print()
                print("  Paste this into Remix 'Deploy' → 'At Address' or")
                print("  use it with a deployment script.")
                return
        print("  (solc output parsed — see above)")
    except Exception as e:
        print(f"  Compilation failed: {e}")
        print("  Fallback: use Remix at https://remix.ethereum.org")

def show_verify_params(network_key="base-mainnet"):
    net = NETWORKS.get(network_key, NETWORKS["base-mainnet"])
    print(f"Etherscan verification for {net['name']}:")
    print()
    print(f"  Explorer: {net['explorer']}")
    print(f"  Chain ID: {net['chain_id']}")
    print()
    print("  After deploying, go to:")
    print(f"    https://basescan.org/contracts")
    print()
    print("  Click 'Verify and Publish' on your contract page.")
    print("  Parameters:")
    print("    - Contract Name: STRP")
    print("    - Compiler:      v0.8.20 (or your chosen version)")
    print("    - Optimization:  Yes (200 runs)")
    print("    - Source Code:   paste STRP.sol contents")
    print("    - License:       MIT")
    print()

def main():
    print_banner()
    show_networks()

    if "--compile" in sys.argv:
        print("-" * 60)
        print("COMPILE MODE")
        print("-" * 60)
        compile_for_remix()
        return

    if "--verify" in sys.argv:
        net = "base-sepolia" if "--testnet" in sys.argv else "base-mainnet"
        print("-" * 60)
        print("VERIFY MODE")
        print("-" * 60)
        show_verify_params(net)
        return

    show_recipe()
    print()
    print("NEXT STEPS:")
    print("  1. python3 strp_deploy.py --compile   # see bytecode")
    print("  2. python3 strp_deploy.py --verify    # verification params")
    print("  3. Deploy via Remix: https://remix.ethereum.org")
    print()

if __name__ == "__main__":
    main()
