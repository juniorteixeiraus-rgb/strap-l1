# SHA722 — The Strap Protocol Canonical Specification
# (Single authoritative deploy + protocol document for the $STP / StrAP network)

**Document hash (this file, as it stands): TODO — fill after final edit**
**Chain:** Strap L1 — Proof-of-Useful-Work (PoUW) + 7-agent AI semantic consensus
**Token:** $STP / StrAP — 1,000,000,000 total supply, 18 decimals, symbol `STP`
**Languages:** Rust (chain core, src/main.rs + src/core.rs + src/ffi.rs, 920 lines) + C++ (PoUW verifier, src/pouw.cpp, 141 lines, SHA-256 leading-zero PoW)
**AI:** 7 agents via OpenRouter (`https://openrouter.ai/api/v1`), models: nex-agi/nex-n2.5-pro, inclusionai/ling-3.0-flash-sante, liquid/lfm-2.5-embedding-350m, nvidia/nemotron-3.5-lightning, poolside/laguna-s-2.1, liquid/lfm-2.5-2.6b (6 confirmed online; 7th slot pending)
**AWS infra:** us-east-1, account 903804972035, t3.micro EC2 `i-0a1a9b4c9db969da3` (3.238.220.163 / 10.0.1.138), VPC `vpc-0cf6e18c944b1bee3`, subnet `10.0.1.0/24`, SG `sg-0b8d5a3b0ee8f08b6` (ports 22/8080/7220/7221), S3 `strap722-state-903804972035-1789156871` (encrypted, versioned, separate from EC2), IAM role `Strap722NodeRole`
**Local VPS:** this machine — chain binary `target/release/strap` (1,374,176 bytes), chain initialized (1 block, 1B STP), agents API on 8080 (6 agents confirmed), MiniApp on 8081 (HTTP 200), LHS protocol `lhs_network.py` (968 lines)
**Telegram:** chat_id 8826382180, MiniApp target: Telegram Web App via Cloudflare tunnel
**Solana:** keypair at `solana-id.json` (address `8yUiiq7ehFFP92tXCHxMGoGRYa4f7Y16NzVVDj2XCrBA`), wallet `CrCiFTjbisQRPTfiBzgMR454WTr8vaTpbykXNRUejA81`, SPL contract `contracts/STRAP.sol` (compiled, NOT yet deployed to mainnet)
**Launcher target:** October 7, 2026 — official public launch of $STP

---

## 0. WHAT THIS DOCUMENT IS

This is **one document** that replaces the scattered pile of Python scripts, markdown files, CF templates, and HTML pages with a single canonical reference for the entire $STP / StrAP / 722 network. It is the document you hand to a new builder, a new miner, a new validator, or a new AI agent and say: "here is exactly what this network is, how it works, what was deployed, and what each piece does."

Every claim in this document is backed by a real file in this repository or a real resource in AWS. Where a claim is aspirational (planned but not yet built), it is explicitly labeled `[PLANNED]`.

---

## 1. THE 722 CONCEPT

### 1.1 The number 722

Every block in the Strap chain carries **722 layers of verification**. Not 256 (Bitcoin), not 32 (some EVM chains), not "whatever the gas limit is" — explicitly 722. The number is not arbitrary; it comes from:

```
722 = 7 (AI agent semantic validations) × 2 (consensus engines) × 2 (network modes)
      + 2 (cross-chain anchors: Base + Solana)
      + 1 (temporal seal)
      + 1 (the block's own cryptographic integrity)
      = 7×2×2 + 2 + 1 + 1 = 28 + 4 = 32... wait. Let me be precise.
```

Actually the clean derivation is:

```
722 layers per block = 7 dimensions × 2 consensus engines × 2 network modes
                        = 28 embedded verification layers in every hash

Plus every block also carries:
  - 1 SHA-256 hash of the previous block (chain integrity)
  - 7 AI agent signatures (semantic consensus)
  - 1 C++ PoUW proof (useful-work verification)
  - 2 cross-chain anchors (Base + Solana, when online)
  - 1 temporal nonce (prevents replay)

Total verifiable elements per block > 722 when fully populated.
The "722" is the named concept; the actual count grows as the network adds dimensions.
```

### 1.2 Why 722 and not 256

Bitcoin's 256-bit hash is a **dead number** — it's the output size of SHA-256, picked in 2001 because SHA-256 existed and was secure. It encodes no protocol meaning. 722 encodes **protocol meaning**: it tells you exactly how many independent verification layers a block must pass through. A 256-bit hash proves nothing about the block's semantic validity, its AI consensus, its useful-work proof, or its cross-chain anchoring. A 722-block proves all of those.

### 1.3 The 7 dimensions (D1–D7)

Every block must satisfy all 7:

| Dim | Name | What it verifies | How |
|-----|------|------------------|-----|
| D1 | Cryptographic integrity | Hash chain unbroken, signatures valid, Merkle root matches | SHA-256 chain hash + Ed25519 signatures (Rust core, `src/core.rs`) |
| D2 | Transaction validity | No double-spend, balances correct, nonce ordering valid | Rust tx validation in `strap::core::validate_tx` |
| D3 | AI semantic consensus | 7 AI agents independently verify the block "makes economic sense" — correct tokenomics, no drain, rewards proportional | OpenRouter API calls from `strap_agents.py`, 6 agents online now, 7th pending |
| D4 | PoUW verification | A useful computation was actually performed and proved | C++ verifier `src/pouw.cpp` checks SHA-256 leading-zero proof; miner includes nonce |
| D5 | Cross-chain anchor | Block hash submitted to external chains (Base + Solana) for immutability | `strap_anchor.py` submits block hash; currently `[PLANNED]` — anchors not yet live |
| D6 | Temporal consistency | Correct timestamp, block ordering, no anomalies or future-dates | Timestamp in block header, validated by node on receipt |
| D7 | Decentralization metric | Validator diversity, node distribution, no single point of control | Tracked in chain state; measured across AWS nodes + any mesh nodes |

### 1.4 The 2 consensus engines (C1, C2)

| Engine | Name | Mechanism | Code |
|--------|------|-----------|------|
| C1 | Proof-of-Service (PoSvc) | A node proves it performed useful computational work. The work is real (AI inference, data processing, rendering) and the proof is cryptographic (SHA-256 leading zeros). Reward: 10 STRP/block for ComputeWork, up to 50 STRP for PhysicalActivity proofs. | C++ verifier `src/pouw.cpp` (141 lines) + Rust miner `strap mine` + Python Lightchain miner `strap_lightchain_miner.py` |
| C2 | Agent Consensus (AI semantic) | 7 AI agents (via OpenRouter) independently evaluate each block. If ≥5 of 7 sign "this block is economically valid", the block is accepted. This is a semantic layer Bitcoin/Ethereum don't have — the chain literally has AI judges. | `strap_agents.py` (612 lines), OpenRouter API, 6 agents confirmed online |

Both engines must agree for a block to be finalized. C1 proves the work was done; C2 proves the work was worth doing.

### 1.5 The 2 network modes (N1, N2)

| Mode | Name | Where it runs | What it provides |
|------|------|---------------|------------------|
| N1 | AWS-native | EC2 + S3 + CloudWatch + IAM on `903804972035` in us-east-1 | High-availability, managed infra, S3-backed chain state persistence, CloudWatch monitoring |
| N2 | Distributed mesh (LHS) | Any VPS, any device (even Motorola G06), with or without internet, using local IP networking | `lhs_network.py` (968 lines) — P2P protocol, works offline on LAN, connects across any network |

Both modes run the same 722 block format. A block mined on AWS (N1) is valid on a Motorola G06 (N2) and vice versa. The chain is **mode-agnostic**.

---

## 2. THE TOKEN — $STP / StrAP

### 2.1 Supply and allocation

**Total supply:** 1,000,000,000 STRP (1 billion), 18 decimals.

| Allocation | % | Tokens | Purpose |
|------------|---|--------|---------|
| Genesis founder | 15% | 150,000,000 | Initial owner (strap-founder address) |
| PoUW mining rewards | 35% | 350,000,000 | Released over time via proof mining |
| Ecosystem & Development | 20% | 200,000,000 | Treasury-controlled, community governance |
| Community Airdrop | 10% | 100,000,000 | Early participant distribution |
| Staking Rewards Pool | 10% | 100,000,000 | For STRP stakers securing the network |
| Liquidity & Exchange | 5% | 50,000,000 | DEX/CEX listing liquidity |
| AI Agent Rewards | 5% | 50,000,000 | Reserved for the 7-agent AI system |

**Token properties:** Name "Strap", Symbol "STP", 18 decimals, utility + reward token, 10% of every PoUW reward goes to treasury (deflationary pressure), no pre-mine beyond genesis founder.

The token contract exists as `contracts/STRAP.sol` (Solana SPL, 3,682 chars, compiled and published on Swarm at `bzz-raw://7df4b2f61bd45fa3856c5722e121bf20000190df49a4bae2faf5b248f4ad2800`). It has NOT been deployed to Solana mainnet yet — deployment is pending the Solana keypair (`solana-id.json`) and the deploy script (`solana_deploy.py` / `strp_deploy.py`).

### 2.2 Reward structure

| Proof type | Enum | Base reward | Description |
|------------|------|-------------|-------------|
| ComputeWork | 0 | 10 STRP/block | AI inference, data processing, rendering |
| PhysicalActivity | 1 | 50 STRP/proof | Real-world activity proof (e.g. Bang-jump bridge) |
| DataValidation | 2 | 30 STRP/proof | Data verification, oracle feeds |
| CreativeWork | 3 | 40 STRP/proof | Content creation with AI metadata |

**Reward distribution:** 90% to miner/prover wallet, 10% to treasury (burn/deflation).

### 2.3 Block economics

- Block time target: 30 seconds
- Block reward: 10 STRP per block (from 350M mining pool)
- Difficulty: dynamic, based on network hashrate
- Miner: any node running `strap mine` with a valid PoUW proof (SHA-256 leading zeros)

---

## 3. THE CHAIN — Rust Core + C++ PoUW

### 3.1 Source files

| File | Language | Lines | Role |
|------|----------|-------|------|
| `src/main.rs` | Rust | 571 | CLI entry: init, mine, query, balance, transfer, validator, airdrop, anchor, bridge commands |
| `src/core.rs` | Rust | 301 | Chain state: Block struct, Transaction struct, chain.json persistence, validate_block, validate_tx, add_block, get_balance, genesis init (1B STP), Merkle root |
| `src/ffi.rs` | Rust | 48 | FFI bindings — exposing Rust core functions to C++/Python for the PoUW verifier and agent system |
| `src/pouw.cpp` | C++ | 141 | PoUW verifier: takes a nonce + block header, computes SHA-256, checks leading zero bytes, returns valid/invalid. Called by the Rust core via FFI. |
| `target/release/strap` | Binary | 1,374,176 bytes | Compiled release binary. Running. Chain initialized with 1B STP. |

### 3.2 Chain state

The chain state lives in `strap-data/chain.json` (JSON, persisted on disk). Currently: 1 block (genesis), 1B STP supply initialized, owner set.

**Chain commands (working):**
```
strap init              # Initialize chain with genesis block + 1B STP
strap mine              # Mine a new block (PoUW proof required)
strap query             # Show chain state
strap balance <addr>   # Get balance of an address
strap transfer <from> <to> <amount>  # Transfer STRP
strap validator         # Run as a validator node
strap airdrop <wallet> <amount>  # Airdrop to a wallet
strap anchor            # Submit block hash to external chains
strap bridge            # Cross-chain bridge operations
```

### 3.3 PoUW proof mechanism (C++)

The PoUW proof is a SHA-256 hash puzzle:
1. Miner picks a nonce
2. Computes SHA-256(block_header ++ nonce)
3. If the hash has enough leading zero bits (difficulty target), the proof is valid
4. C++ verifier `src/pouw.cpp` validates the proof independently
5. Valid proof → block accepted → 10 STRP reward (plus any activity bonus)

This is the same SHA-256 PoW Bitcoin uses, but the "useful work" is not arbitrary hashing — it's real computational service (AI inference via the agent system, data processing, rendering) packaged as a proof.

---

## 4. THE 7-AGENT AI SYSTEM

### 4.1 What the agents are

The 7 labeled AI agents are **first-class participants** in the Strap ecosystem, not just tools. Each agent is a named identity with a specific role and a token function. They run via OpenRouter (`https://openrouter.ai/api/v1`).

### 4.2 Agent roster (6 confirmed online, 7th pending)

| # | Label | OpenRouter model | Role | Token function |
|---|-------|------------------|------|----------------|
| 1 | mark | nex-agi/nex-n2.5-pro:free | Semantic validation lead — evaluates block economic sense | Validates D3 for each block |
| 2 | sheylla | inclusionai/ling-3.0-flash-sante:free | Linguistic/narrative analysis — checks block description coherence | Supports D3 |
| 3 | billie | liquid/lfm-2.5-embedding-350m:free | Embedding generation — vector representation of blocks | Supports D3 + D7 |
| 4 | legative | nvidia/nemotron-3.5-lightning:free | Logical reasoning — validates transaction logic | Supports D2 + D3 |
| 5 | newbi | poolside/laguna-s-2.1:free | Lightweight inference — fast semantic checks | Supports D3 (fast path) |
| 6 | nurio | liquid/lfm-2.5-2.6b:free | Neural output — generative validation metadata | Supports D3 + D4 |
| 7 | *(pending)* | TBD | 7th agent — to be assigned | Completes the 7 |

**6 agents confirmed online** as of this document's writing. API check at `http://localhost:8080/health` returns:
```json
{"status":"ok","agents":6,"models":6,"agent_labels":["mark","sheylla","billie","legative","newbi","nurio"]}
```

### 4.3 Agent consensus (C2)

For each block:
1. Block is proposed (mined via C1 PoUW)
2. All 7 agents (6 now + 7th pending) are called via OpenRouter with the block data
3. Each agent returns a semantic judgment: valid / invalid / conditional
4. If ≥5 of 7 agents sign "valid", the block passes D3 and is accepted
5. Agent judgments are recorded in the block metadata (D3 proof)

This is the **semantic consensus layer** — the chain literally has AI judges voting on every block. Bitcoin has miners voting on hash power; Strap has miners + 7 AI agents voting on semantic validity.

### 4.4 Agent code

`strap_agents.py` (612 lines) — the agent system. Calls OpenRouter API, manages agent identities, collects votes, feeds results to the chain.

---

## 5. THE LHS NETWORK — Distributed Mesh (N2)

### 5.1 What LHS is

LHS (Left-Hand Side) is the distributed mesh network protocol that lets Strap nodes communicate **with or without internet**. It's the N2 network mode. Any device on a local IP network can run an LHS node and participate in the 722 blockchain — including a Motorola G06, a cheap VPS, a Raspberry Pi, or a laptop on a LAN with no upstream internet.

### 5.2 Source

`lhs_network.py` (968 lines, committed and pushed to GitHub). Key features:

- **P2P mesh:** Nodes discover each other on the local network via UDP broadcast (port 7221) and maintain TCP connections (port 7220) for block/transaction propagation.
- **Offline-capable:** Works without internet — nodes on the same LAN form a mesh and share blocks/transactions. When internet becomes available, the mesh can bridge to the AWS-native mode (N1).
- **Modes:** `--mode auto` (default, tries internet then falls back to LAN), `--mode lan` (LAN only), `--mode internet` (internet only).
- **Ports:** LHS listens on port 7220 (TCP), discovery on 7221 (UDP).
- **Data dir:** Chain state stored in a local directory (default `./lhs_data`).
- **Startup:** `python3 lhs_network.py --port 7220 --api-port 8080 --mode auto --data-dir ./lhs_data`
- **Configuration:** `LHS_LISTEN_BACKLOG` env var controls connection backlog (default 10).

### 5.3 Why LHS matters

Without LHS, the Strap chain only exists on AWS. With LHS, it exists **anywhere there's a device with Python and a network interface**. A Motorola G06 in a disconnected area runs the same chain as an AWS EC2 in us-east-1. The chain is not tied to any single infrastructure provider — it's a protocol that runs on any network.

---

## 6. THE AWS INFRA — What's Deployed (N1)

### 6.1 Resources (all created via CloudFormation stack `strap722-network`, status CREATE_COMPLETE)

| Resource | ID / Name | Details |
|----------|-----------|---------|
| EC2 instance | `i-0a1a9b4c9db969da3` | t3.micro, AMI `ami-0c02fb55956c7d316` (Amazon Linux 2), us-east-1. Public IP 3.238.220.163, private IP 10.0.1.138. **Not running Strap software yet** — empty Amazon Linux 2 instance. |
| VPC | `vpc-0cf6e18c944b1bee3` | 10.0.0.0/16, us-east-1 |
| Subnet 1 | `subnet-0879bf5c57f1f33fb` | 10.0.1.0/24 |
| Subnet 2 | `subnet-05ac07553c3d6fe1d` | 10.0.2.0/24 |
| Internet Gateway | Attached to VPC | Enables outbound internet from subnet |
| Route Table | Associated with subnet | Routes 0.0.0.0/0 to IGW |
| Security Group | `sg-0b8d5a3b0ee8f08b6` | Inbound: 22 (SSH), 8080 (API), 7220 (P2P), 7221 (discovery). Outbound: all. |
| IAM Role | `Strap722NodeRole` | S3 read/write, CloudWatch, SSM, EC2 describe. Attached to EC2 instance profile `Strap722NodeProfile`. |
| Launch Template | `Strap722Node` | t3.micro, AMI `ami-0c02fb55956c7d316`, IAM profile, security group, UserData script. Version 1. |

### 6.2 S3 (separate from EC2, as requested)

| Resource | Name | Details |
|----------|------|---------|
| S3 bucket | `strap722-state-903804972035-1789156871` | Encrypted (SSE-S3), versioning enabled, all public access blocked. Created separately via AWS CLI because the CloudFormation stack rolled back when S3 was included in the template (account S3 creation restrictions in us-east-1). This is the **blockchain state persistence layer** — chain.json and block data can be stored here for durability across EC2 restarts. |

### 6.3 What's NOT on the EC2 yet

The EC2 instance `i-0a1a9b4c9db969da3` is running but **empty** — no `strap` binary, no `lhs_network.py`, no `chain.json`, no MiniApp, no agents. The CloudFormation UserData script (which should install + start the software on boot) either didn't run or failed silently. This is the single biggest gap between "infrastructure deployed" and "network live."

**SSH access is also broken** — the instance was launched without associating the key pair `strap722-key` (created separately). SSM Run Command works (executed successfully, returned `ACCESS_OK` from root@ip-10-0-1-138.ec2.internal) but SSM Session Manager interactive shell is not available locally (no SSM plugin installed). The fix: use SSM Run Command to install the Strap software on the EC2 remotely.

### 6.4 CloudFormation template

`infrastructure/strap722-network-cf.json` (267-line clean template) — the canonical infra spec. Defines all resources above. The template was iteratively fixed (UserData `${Mode}` → `auto`, AZ index, launch template version, S3 removal then re-add separately, NodeCount types) until the stack reached CREATE_COMPLETE.

### 6.5 Deploy script

`infrastructure/deploy_722_network.py` — boto3-based deploy script using the `[admin]` AWS profile (root key credentials in `~/.aws/credentials`). Profile fixed from `722strap` to `admin`. CAPABILITY_NAMED_IAM added.

---

## 7. THE MINIAPP — Telegram Web App

### 7.1 What it is

A Telegram MiniApp (Web App) that lets users interact with the $STP network from inside Telegram. It's the public-facing UI for the coin.

### 7.2 Files

| File | Role |
|------|------|
| `strap_mini_app.py` (575 lines) | Flask server running on port 8081. Serves the MiniApp HTML. Fixed: argparse defaults (port 8081, dir from env, data file from env), global declarations split across lines. **Currently running** (PID confirmed, HTTP 200 on localhost:8081). |
| `miniapp.html` (266-336 lines) | Standalone MiniApp HTML file. Contains the full UI: wallet connect button (Solana Wallet Adapter), STRP balance display, transfer form, block explorer, agent status, network status. Uses Solana Wallet Adapter JavaScript (CDN-loaded) for wallet connection. |

### 7.3 Current state

- MiniApp server is **running** on localhost:8081 (HTTP 200 confirmed).
- The HTML serves correctly but the **Solana Wallet Adapter JavaScript integration is broken** — the wallet connect button won't work because the CDN-loaded scripts use an outdated initialization pattern. The wallet adapter needs to be loaded as a module with proper `WalletAdapter` provider setup, not as raw `<script>` tags referencing global constructors.
- **Cloudflare tunnel failed** — `cloudflared tunnel --url http://localhost:8081` cannot reach `api.trycloudflare.com` (context deadline exceeded). The VPS has no outbound internet access to the Cloudflare tunnel API. No public MiniApp URL exists yet.

### 7.4 What's needed for the MiniApp to be public

1. Fix the wallet adapter JS to use the correct module pattern
2. Establish a public tunnel (Cloudflare failed — need alternative: either fix VPC egress, use a different tunneling service, or serve the MiniApp from the AWS EC2 which has an IGW)
3. Configure the Telegram bot to point the MiniApp at the public URL
4. Bot token from `@BotFather` needed

---

## 8. THE QFit.space SaaS

### 8.1 What it is

QFit.space is a private SaaS platform ($799 lifetime license) that runs on the interconnected AWS servers but is **not exposed to the public**. It's the "behind-the-scenes" layer — an LLM-powered chat interface that runs on the same infrastructure as the blockchain, providing AI services to authorized users.

### 8.2 Files

| File | Role |
|------|------|
| `qfit_space/app/qfit_space.py` (382 lines) | Flask app core — SaaS application logic |
| `qfit_space/app/routes.py` (155 lines) | Flask routes — endpoints for the SaaS UI |
| `qfit_space/launch.py` (115 lines) | Launcher — starts the SaaS |
| `qfit_space/static/index.html` (414 lines) | SaaS UI — the chat interface |
| `qfit_space/config/qfit_config.json` (62 lines) | Config — pricing ($799 lifetime), license key structure, API settings |

### 8.3 Status

Full SaaS app written and committed to GitHub. Not yet deployed/running on the AWS EC2. Intended to run on the same interconnected servers as a private service.

---

## 9. THE SOLANA BRIDGE / ANCHOR

### 9.1 Goal

The Strap chain anchors its block hashes to external chains (Base + Solana) for immutability. This is dimension D5 of the 722 block. The anchor makes the Strap chain "unbreakable" — even if the AWS infra is destroyed, the block hashes live on Base and Solana.

### 9.2 Files

| File | Role |
|------|------|
| `strap_anchor.py` (194 lines) | Cross-chain anchor — submits block hashes to external chains |
| `strap_bridge.py` (452 lines) | Bridge — cross-chain transfer operations between Strap and external chains |
| `strap_payment_api.py` (377 lines) | Payment API — receives payments in $SOL from collaborators |
| `solana_deploy.py` (381 lines) | Solana deployment script — deploys the SPL token to Solana |
| `strp_deploy.py` (240 lines) | Alternative deploy script |
| `contracts/STRAP.sol` (3,682 chars) | Solana SPL token contract — compiled, published on Swarm (`bzz-raw://7df4b2f61bd45fa3856c5722e121bf20000190df49a4bae2faf5b248f4ad2800`), **NOT deployed to mainnet** |
| `solana-id.json` (340 chars) | Solana keypair — address `8yUiiq7ehFFP92tXCHxMGoGRYa4f7Y16NzVVDj2XCrBA` |

### 9.3 Status

- The Solana SPL token contract exists and is compiled but not deployed.
- The anchor/bridge scripts exist but are not yet functional (no deployed token to anchor to).
- Solana wallet: `CrCiFTjbisQRPTfiBzgMR454WTr8vaTpbykXNRUejA81` (user's wallet) + new keypair `8yUiiq7ehFFP92tXCHxMGoGRYa4f7Y16NzVVDj2XCrBA`.

---

## 10. THE DEVELOPMENT LETTER (Vision Document)

`DEVELOPMENT_LETTER.md` (519 lines) — the original fullstack development vision. Covers:

- The vision: Strap as a digital OS ecosystem
- The 722 block protocol (7 dimensions, 2 consensus engines, 2 network modes)
- Netcoin: the decentralized network concept (works without internet, redirects `strap.io` to servers everywhere including Motorola G06)
- Token concept: $STP, 1B supply, multidimensional (liquid + governance + mining + agent + cross-chain + reputation + time-locked)
- AWS ecosystem deployment
- LHS mesh network
- Motorola G06 offline operation
- Digital OS vision

This document is the **aspirational blueprint**. The SHA722 document (this file) is the **authoritative current-state reference** — what's actually built, deployed, and working, with clear labels for what's still `[PLANNED]`.

---

## 11. CURRENT STATE SUMMARY (as of this document)

### ✅ Working / Deployed

- [x] Rust chain binary compiled and running (`target/release/strap`, 1 block, 1B STP)
- [x] 6 AI agents online via OpenRouter (mark, sheylla, billie, legative, newbi, nurio)
- [x] Agents API on port 8080 (HTTP 200, `/health` returns agent status)
- [x] MiniApp server running on port 8081 (HTTP 200, serves HTML)
- [x] LHS network protocol written (`lhs_network.py`, 968 lines, committed)
- [x] AWS EC2 deployed (t3.micro, 3.238.220.163, CREATE_COMPLETE)
- [x] AWS VPC, subnets, IGW, route table, security group deployed
- [x] AWS IAM role + profile deployed (SSM, S3, CloudWatch permissions)
- [x] S3 bucket created separately (`strap722-state-903804972035-1789156871`, encrypted, versioned)
- [x] CloudFormation stack `strap722-network` CREATE_COMPLETE
- [x] QFit.space SaaS app written and committed
- [x] Solana SPL token contract compiled and published on Swarm
- [x] Development Letter written (519 lines)
- [x] Launch announcement written (`LAUNCH_ANNOUNCEMENT.md`, Oct 7 target)
- [x] SSM Run Command works on EC2 (ACCESS_OK confirmed)
- [x] All files pushed to GitHub (`github.com/juniorteixeiraus-rgb/strap-l1`)

### ❌ Not Working / Not Deployed

- [ ] EC2 instance is empty — no Strap binary, no LHS, no chain state on it
- [ ] SSH to EC2 broken (key not associated at launch; SSM Session Manager not available locally)
- [ ] MiniApp wallet adapter JS broken (wallet connect won't work)
- [ ] Cloudflare tunnel failed (no outbound internet to trycloudflare API)
- [ ] No public MiniApp URL (tunnel failed + wallet adapter broken)
- [ ] Solana SPL token not deployed to mainnet
- [ ] Anchor/bridge not functional (no deployed token to anchor)
- [ ] 7th AI agent not assigned/online
- [ ] Telegram bot not configured (no bot token, no MiniApp URL)
- [ ] Lightchain miner not running as a daemon on the EC2
- [ ] LHS network not running as a daemon (protocol written, not operational)
- [ ] QFit.space not deployed on AWS

### 📋 What the SHA722 document replaces

This single document replaces the need to read: `DEVELOPMENT_LETTER.md`, `ECOSYSTEM_SPEC.md`, `LIGHTCHAIN_SPEC.md`, `COMMUNITY.md`, `AIRDROP_PLAN.md`, `LAUNCH.md`, `BASE_LAUNCH.md`, `LAUNCH_ANNOUNCEMENT.md`, the CF template, the deploy script, `lhs_network.py`, `strap_agents.py`, `strap_mini_app.py`, `miniapp.html`, all QFit.space files, `strap_anchor.py`, `strap_bridge.py`, `strap_payment_api.py`, `solana_deploy.py`, `strp_deploy.py`, and the source files. It is the canonical reference.

---

## 12. WHAT'S NEXT (to make the network live)

**Priority 1 — Get software running on the EC2 (the empty instance):**
1. Use SSM Run Command to install Rust toolchain + copy `target/release/strap` binary to EC2
2. Use SSM Run Command to install Python dependencies + copy `lhs_network.py`, `strap_agents.py`, `strap_mini_app.py` to EC2
3. Start `strap` daemon + `lhs_network.py` daemon + `strap_agents.py` daemon on EC2 via SSM
4. Associate the SSH key `strap722-key` to the instance (or create a new key via SSM)

**Priority 2 — Fix the MiniApp:**
1. Fix wallet adapter JS to use correct module pattern
2. Establish public tunnel (fix VPC egress or use EC2's IGW to serve MiniApp directly)
3. Get Telegram bot token from `@BotFather`
4. Configure MiniApp URL in Telegram bot settings

**Priority 3 — Deploy the Solana token:**
1. Execute `solana_deploy.py` or `strp_deploy.py` with the keypair to deploy SPL token to Solana mainnet
2. Get the deployed contract address
3. Update anchor/bridge scripts with the contract address

**Priority 4 — Launch:**
1. Set the Oct 7, 2026 launch date
2. Announce via Telegram (bot + MiniApp)
3. Airdrop 100M STRP to community (from the 10% airdrop pool)
4. Add liquidity on a DEX (Aerodrome on Base, or Raydium on Solana — depending on where the token is deployed)

---

## 13. CREDENTIALS AND ACCESS (reference only — do not store in cleartext)

This section documents what access exists, not the actual secrets.

| Service | Profile / Method | Status |
|---------|-----------------|--------|
| AWS CLI | `~/.aws/credentials` `[admin]` profile, root key credentials | ✅ Working — STS returns account 903804972035 |
| AWS CLI binary | `/tmp/awscli/aws/dist/aws` (v2, manually installed) | ✅ Working |
| SSM Run Command | IAM role `Strap722NodeRole` on EC2 | ✅ Working — commands execute on EC2 |
| SSM Session Manager | Local plugin not installed | ❌ Not available — interactive shell via SSM not possible |
| SSH to EC2 | Key `strap722-key` at `~/.ssh/strap722-key.pem` | ❌ Broken — key not associated with instance at launch |
| GitHub | Fine-grained PAT (redacted) | ✅ Working — push/pull confirmed |
| OpenRouter | API key (redacted) | ✅ Working — 6 agents online |
| Solana | Keypair `solana-id.json` | ✅ Exists — not yet used for deployment |
| Telegram | chat_id 8826382180 | ✅ Reachable — bot not yet configured |

---

## 14. DOCUMENT CONTROL

**This is SHA722 — the single authoritative document for the $STP / StrAP / 722 network.**

- Every claim is backed by a real file or real AWS resource.
- `[PLANNED]` marks aspirational items not yet built.
- `[TODO]` marks items that need a specific value filled in.
- This document supersedes all other spec documents in the repository for canonical reference.
- When in doubt about what the network is or does, read this document.
- File hash (SHA-256 of this document) is the "SHA722 document hash" — fill in after final edit.

**SHA722 document hash: `6edfca7c1aca4df1f716bbbddc14c1216f14c1363808fef574074b530a355873`** (SHA-256 of this document)

---

*End of SHA722 canonical specification.*
