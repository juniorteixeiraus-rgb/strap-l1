# Installation

## Prerequisites

- Python 3.11+
- Rust 1.98+ (for chain core)
- cmake 3.15+ (for C++ PoUW build)
- OpenSSL 3.x headers
- Node.js (optional, for frontend dev)

## Setup

```bash
# Clone the repository
git clone https://github.com/juniorteixeiraus-rgb/strap-l1.git
cd strap-l1

# Install Python dependencies
pip install -r requirements.txt

# Build the Rust chain binary (requires Rust + cmake + OpenSSL)
cd /home/ubuntu/strap-l1
export PATH="$HOME/.cargo/bin:$PATH"
cargo build --release
# Binary: target/release/strap

# Initialize the chain (optional — for local chain testing)
./target/release/strap init

# Start the AI Agent API (port 8080)
python3 -m strap_agents

# Start the Lightchain miner (earns 50 $STP per proof)
python3 strap_lightchain_miner.py --api http://localhost:8080

# Access the dashboard
# Web:   http://localhost:8080/dashboard
# Telegram: use the bot mini-app
```

## Token Deployment ($STP on Base)

See `contracts/StrAP.sol` for the token contract.

1. Open [Remix](https://remix.ethereum.org)
2. Paste `contracts/StrAP.sol`
3. Compile with Solidity 0.8.20
4. Deploy via MetaMask connected to Base Mainnet (chainId 8453)
5. Verify on [Basescan](https://basescan.org)

## Configuration

Environment variables:

```bash
OPENROUTER_API_KEY=sk-or-...     # OpenRouter API key for AI agents
STRAP_DATA_DIR=./strap-data      # Chain data directory
LIGHTCHAIN_API_URL=http://localhost:8080  # Miner API endpoint
```

## Project Structure

```
strap-l1/
├── contracts/
│   └── StrAP.sol            # $STP ERC-20 token contract
├── src/
│   ├── main.rs              # Rust chain core (CLI + node)
│   ├── ffi.rs               # FFI bindings
│   └── pouw/
│       ├── strap-pouw.cpp   # C++ PoUW verifier
│       └── CMakeLists.txt   # cmake build config
├── strap_agents.py          # 7-agent AI system + FastAPI
├── strap_telegram_bot.py    # Telegram mini-app bot
├── strap_lightchain_miner.py # Low-resource PoS miner
├── strap_pos_miner.py       # Full-capacity PoS miner
├── dashboard.html           # Web dashboard
├── ECOSYSTEM_SPEC.md        # Tokenomics & ecosystem spec
├── LIGHTCHAIN_SPEC.md       # Mining spec
└── README.md
```

## License

MIT
