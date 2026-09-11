# Strap ($STP) — Community Project
## Proof-of-Service L1 Blockchain + Solana SPL Token + Telegram Economy

Welcome to Strap. This is a Proof-of-Service Layer 1 blockchain building toward a **digital OS ecosystem** like Meta — where $STP becomes the native currency of a billion-dollar digital platform.

|- **Proof-of-Useful-Work (PoUW)** mining — useful compute earns $STP
|- **7 AI agents** (mark, sheylla, billie, legative, newbi, nurio) working together
|- **Telegram-native economy** — bot + mini app as the main interface
|- **$STP token** — 1 billion supply, deployed on Solana SPL
|- **Strap L1 chain** — independent Rust chain running on VPS
|- **Bridge anchor to Base** — chain state hashed + anchored to Base for "unbreakable" security
|- **Multi-node ready** — decentralized architecture from day one
|- **Digital OS vision** — $STP as the currency of a Meta-like digital platform
|- **Community wallet**: `CrCiFTjbisQRPTfiBzgMR454WTr8vaTpbykXNRUejA81`

---

## What is $STP?

**$STP (Strap)** is the native token of the Strap L1 blockchain. It powers:
- **Mining rewards** — miners earn $STP for performing useful work (Proof-of-Service)
- **Agent economy** — 7 AI agents earn and spend $STP for their work
- **Governance** — token holders vote on chain parameters
- **Treasury** — 100M $STP reserved for ecosystem development

**Token details:**
- Name: $Strap
- Symbol: $STP
- Supply: 1,000,000,000 (1 billion)
- Decimals: 9 (Solana SPL standard)
- Network: Solana (SPL token) + Strap L1 (native chain)

---

## What is the Strap L1 Chain?

The **Strap L1** is an independent Proof-of-Service blockchain written in Rust:

- **Consensus**: Proof-of-Useful-Work — miners perform useful compute tasks and earn $STP
- **C++ PoUW verifier** — handles the heavy verification work
- **7 AI agents** — each agent acts as a validator + worker on the chain
- **Telegram bot** — the main interface for interacting with the chain
- **API** — FastAPI + OpenRouter proxy for agent access
- **Miner** — runs on VPS, earns 50 $STP per proof

**Architecture:**
```
Telegram Bot + Mini App  ←→  API (port 8080)  ←→  Strap L1 Chain (Rust binary)
                                                          ↓
                                                  C++ PoUW Verifier
                                                          ↓
                                                  Chain State (chain.json)
                                                          ↓
                                                  Bridge Anchor → Base
                                                          ↓
                                                  GCS Backup (snapshot)
```

**Security model ("unbreakable"):**
1. **Local chain** — chain.json on the VPS (the live ledger)
2. **Bridge anchor** — SHA256 hash of chain.json submitted to Base every N minutes (permanent proof)
3. **GCS backup** — periodic snapshots to Google Cloud Storage
4. **Multi-node** — multiple VPS running the chain (decentralized)
5. **Multi-agent validation** — 7 AI agents independently validate the chain
6. **GitHub** — all code public, redeployable if everything fails

**If all VPS die:**
1. Redeploy from GitHub
2. Restore chain.json from GCS backup (or replay from genesis)
3. Compute final hash → verify against last Base anchor
4. Chain recovered and proven authentic

---

## Solana $STP Token

The **$STP SPL token** on Solana is the public, tradeable version of the token:

**Current status:**
- Network: Solana Devnet (for testing) → Mainnet (for launch)
- Wallet: `6SGUKs4f1pFQDdEj63FrUk1MUZY43zenzPT7zet1kw9S` (community wallet)
- Status: Waiting for devnet SOL to deploy

**When deployed:**
- MINT ADDRESS: will be published here
- VIEW ON: https://solscan.io/token/<MINT_ADDRESS>
- ADD TO WALLET: Phantom or solflare
- TRADE ON: Raydium / Jupiter (when liquidity added)

**Deployment command (when SOL available):**
```bash
python3 solana_deploy.py --network devnet
# or for mainnet:
python3 solana_deploy.py --network mainnet
```

**Requirements:**
- Devnet: free test SOL from faucet (currently dry — wait for restoration)
- Mainnet: ~0.01-0.05 SOL for rent + fees

---

## How to Join the Community

### As a Miner
Run the Strap L1 miner on your VPS and earn $STP:
```bash
git clone https://github.com/juniorteixeiraus-rgb/strap-l1.git
cd strap-l1
pip install -r requirements.txt  # if needed
python3 strap_lightchain_miner.py --api http://<your-api-url> --service-interval 10 --block-interval 120
```
Earn **50 $STP per proof** submitted to the chain.

### As a Validator (Node Operator)
Run a full Strap L1 node:
```bash
git clone https://github.com/juniorteixeiraus-rgb/strap-l1.git
cd strap-l1
# Build the chain binary
cargo build --release
# Initialize and run
./target/release/strap init --data-dir .strap-data
# Run API + bot + miner together
./run_all.sh
```
Share your node with the community and earn rewards.

### As a Token Holder
1. Add the $STP Solana token to your wallet (Phantom, Solflare)
2. Hold $STP — participate in governance
3. Trade on DEXs when liquidity is available

### As a Developer
1. Read the code: https://github.com/juniorteixeiraus-rgb/strap-l1
2. Run the API locally: `python3 -m strap_agents`
3. Use the 7 agents via OpenRouter: `https://openrouter.ai/api/v1`
4. Build on top of the Strap L1 chain

### As a Telegram User
1. Open the Telegram bot (link to be shared)
2. Use `/dashboard` to view the chain
3. Use `/mine` to start mining
4. Use `/proof` to submit proofs
5. Use `/balances` to check token balances

---

## Tokenomics

**Total Supply: 1,000,000,000 $STP (1 billion)**

| Allocation | Amount | Purpose |
|-----------|--------|---------|
| Founder/Initial | 900,000,000 | Initial distribution, ecosystem growth |
| Treasury | 100,000,000 | Development, grants, partnerships |

**Rewards:**
- Mining: 50 $STP per proof (Proof-of-Service)
- Agent work: per-task rewards
- Staking: future (TBD)

**Distribution model:**
- Users buy/invest → receive $STP tokens
- More investment → more tokens (admin-controlled mint)
- Mining creates ongoing $STP supply (or burns via PoUW)

---

## Roadmap

### Phase 0 — Foundation (Now)
- [x] Rust Strap L1 chain binary built
- [x] 1B $STP initialized on chain
- [x] 7 AI agents running (API + OpenRouter)
- [x] Telegram bot + mini app
- [x] Lightchain miner (50 $STP/proof)
- [x] Bridge anchor daemon (strap_bridge.py)
- [ ] Solana $STP token deployed (waiting for SOL)
- [ ] GitHub repo public

### Phase 1 — Launch (Next)
- [ ] Deploy $STP on Solana mainnet
- [ ] Verify on Solscan
- [ ] Add liquidity on Raydium/Jupiter
- [ ] Telegram bot public launch
- [ ] Community announcement
- [ ] External API access (Cloudflare Tunnel or public IP)

### Phase 2 — Growth
- [ ] Multi-node deployment (2+ VPS)
- [ ] External miners join
- [ ] Staking contract
- [ ] On-chain DEX (Strap L1 native)
- [ ] Agent expansion (more AI agents)
- [ ] Bridge to Base/Solana (external liquidity)

### Phase 3 — Decentralization
- [ ] Community node operators
- [ ] P2P sync in Rust binary
- [ ] Decentralized governance (DAO)
- [ ] Token listings (CEXs, aggregators)
- [ ] Ecosystem apps built on Strap L1

---

## Architecture Deep Dive

### Proof-of-Service (PoS) Mining

Unlike traditional Proof-of-Work (hash grinding), Strap uses **Proof-of-Service**:
- Miners perform **useful compute tasks**
- The work is verified by the C++ PoUW verifier
- Successful proofs earn **50 $STP**
- The more useful work done, the more $STP earned

This makes $STP backed by real economic activity, not just speculation.

### 7 AI Agents

| Agent | Model | Role |
|-------|-------|------|
| mark | nex-agi/nex-n2.5-pro:free | Lead agent, coordination |
| sheylla | inclusionai/ling-3.0-flash-sante:free | Language, translation |
| billie | liquid/lfm-2.5-embedding-350m:free | Embeddings, search |
| legative | nvidia/nemotron-3.5-lightning:free | Reasoning, logic |
| newbi | poolside/laguna-s-2.1:free | Code, development |
| nurio | liquid/lfm-2.5-2.6b:free | Analysis, data |

Each agent acts as a **validator** on the Strap L1 chain — independently checking chain state and submitting proofs.

### Bridge Anchor Architecture

```
Strap L1 Chain (chain.json)
        ↓
    SHA256 hash (computed every N minutes)
        ↓
    Submitted to Base blockchain (permanent, immutable record)
        ↓
    GCS backup (periodic snapshot of chain.json)
        ↓
    Multi-node replication (secondary VPS)
        ↓
    GitHub (source code backup)
```

**Recovery scenario (all VPS destroyed):**
1. Redeploy strap binary from GitHub
2. Restore chain.json from GCS (or replay genesis → replay all blocks)
3. Compute final SHA256 hash
4. Verify hash matches last Base anchor transaction
5. Chain is recovered + proven authentic

This is the **"unbreakable"** property — the chain state is provably tied to Base blockchain, which nobody can rewrite.

### Multi-Node Expansion

| Node | Location | Status |
|------|----------|--------|
| Node 1 (primary) | VPS 1 | Running — chain, API, bot, miner, bridge |
| Node 2 | VPS 2 (future) | Planned — sync from Node 1 |
| Node 3 | VPS 3 (future) | Planned — sync from Node 1 |

**Sync mechanism:**
- Primary node exposes chain state via API
- Secondary nodes pull chain state periodically
- Both nodes validate independently
- If primary dies, secondary continues

**Future: P2P sync**
- Nodes discover each other via gossip protocol
- Blocks propagated peer-to-peer
- True decentralized consensus

---

## Project Structure

```
strap-l1/
├── Cargo.toml                 # Rust crate config
├── build.rs                   # CMake build of C++ PoUW library
├── src/
│   ├── main.rs               # CLI + chain logic + FFI bindings
│   ├── core.rs               # Core types (Address, Hash, Block, Chain)
│   ├── ffi.rs                # FFI struct definitions
│   └── pouw/
│       ├── CMakeLists.txt    # CMake config for strap-pouw
│       └── strap-pouw.cpp   # C++ PoUW verifier (OpenSSL EVP)
├── contracts/
│   ├── strap.sol             # $Strap ERC-20 (Base — legacy, kept for reference)
│   └── $Strap.sol            # $Strap contract (corrected)
├── STRAP.sol                  # $Strap ERC-20 (root — corrected)
├── STRP.sol                   # Legacy STRP ERC-20 draft (superseded)
├── strp_deploy.py            # Base deployment helper
├── solana_deploy.py          # Solana SPL deployment script
├── strap_openrouter_api.py   # FastAPI + OpenRouter proxy
├── strap_agents.py           # 7-agent router + /dashboard endpoint
├── strap_telegram_bot.py     # Telegram bot mini-app
├── strap_pos_miner.py        # Full-capacity PoS miner
├── strap_lightchain_miner.py # Low-resource high-yield miner
├── strap_lightchain_node.py  # Telegram-integrated node/miner
├── strap_anchor.py           # Bridge anchor daemon (Base/Solana)
├── strap_bridge.py           # Full bridge security architecture
├── dashboard.html            # Web dashboard
├── ECOSYSTEM_SPEC.md         # 1B tokenomics spec
├── LIGHTCHAIN_SPEC.md        # Lightchain spec
├── BASE_LAUNCH.md            # Base launch guide
├── README.md                 # Project overview
├── hattrib.rc                # Project config (cargo/ruff/clippy)
├── .gitignore                # Git ignore rules
└── solana-id.json            # Solana wallet (community)
```

---

## Developer Setup

### Prerequisites
- Rust: `rustup` (rustc 1.98+, cargo 1.98+)
- C++: cmake 3.22+, OpenSSL dev headers
- Python: 3.11+ (fastapi, uvicorn, httpx, pydantic)
- Solana CLI: https://solana.com/downloads

### Build the Rust chain
```bash
cd strap-l1
cargo build --release
# Binary: target/release/strap
```

### Run the API + agents
```bash
cd strap-l1
python3 -m strap_agents  # starts uvicorn on port 8080
# Health: http://localhost:8080/health
```

### Run the miner
```bash
cd strap-l1
python3 strap_lightchain_miner.py \
    --api http://localhost:8080 \
    --service-interval 10 \
    --block-interval 120
```

### Run the bridge anchor
```bash
cd strap-l1
STRAP_BRIDGE_KEY=<your_base_private_key> \
STRAP_BRIDGE_RPC=https://mainnet.base.org \
python3 strap_bridge.py
```

---

## Security & Transparency

### What makes Strap "unbreakable"

1. **Independent chain** — Strap L1 is not on anyone else's chain. You control it.
2. **Bridge anchor** — chain state hashed + anchored to Base blockchain every N minutes. Even if all VPS die, the chain is provably recoverable.
3. **Multi-node** — multiple VPS + future P2P = no single point of failure.
4. **Open source** — all code on GitHub. Anyone can verify, audit, or run a node.
5. **Multi-agent validation** — 7 AI agents independently validate the chain.
6. **GCS backup** — chain.json snapshots to Google Cloud.

### Credentials & Keys

**NEVER share these publicly:**
- Base private key (for bridge anchor): `STRAP_BRIDGE_KEY`
- Solana keypair: `solana-id.json`, `solana-id-community.json`
- GitHub PAT: keep private
- OpenRouter API key: keep private

**Safe to share:**
- Solana wallet address (public key): `6SGUKs4f1pFQDdEj63FrUk1MUZY43zenzPT7zet1kw9S`
- $STP mint address (when deployed)
- GitHub repo URL

---

## Contact & Community

- **GitHub**: https://github.com/juniorteixeiraus-rgb/strap-l1
- **Telegram**: @StrapL1 (bot + mini app)
- **OpenRouter**: https://openrouter.ai/api/v1
- **Base**: https://basescan.org
- **Solana**: https://solscan.io

---

## License

MIT — see individual file headers.
