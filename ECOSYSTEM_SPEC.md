# STRP — Strap L1 Tokenomics & Ecosystem Specification

**Version:** 1.0  
**Chain:** Strap L1 (Proof-of-Useful-Work)  
**Token:** STRP  
**Total Supply:** 1,000,000,000 (1 billion)  
**Consensus:** Proof-of-Useful-Work (PoUW)  
**Languages:** Rust (chain core) + C++ (PoUW verifier)  
**AI Integration:** 7-agent system via OpenRouter  

---

## 1. Token Allocation (1,000,000,000 STRP)

| Allocation | Percentage | Tokens | Wallet/Purpose |
|------------|-----------|--------|----------------|
| **Genesis Founder** | 15% | 150,000,000 | Initial owner address (strap-founder) |
| **PoUW Mining Rewards** | 35% | 350,000,000 | Released over time via proof mining |
| **Ecosystem & Development** | 20% | 200,000,000 | Treasury-controlled, community governance |
| **Community Airdrop** | 10% | 100,000,000 | Distributed to early participants |
| **Staking Rewards Pool** | 10% | 100,000,000 | For STRP stakers securing the network |
| **Liquidity & Exchange** | 5% | 50,000,000 | DEX/CEX listing liquidity |
| **AI Agent Rewards** | 5% | 50,000,000 | Reserved for the 7-agent AI system |

**Total: 1,000,000,000 STRP (100%)**

---

## 2. Token Properties

- **Name:** Strap
- **Symbol:** STRP
- **Decimals:** 18 (standard, like ETH)
- **Type:** Utility + Reward token
- **Burn Mechanism:** 10% of every PoUW reward goes to treasury (deflationary pressure via ecosystem spending)
- **No pre-mine beyond genesis founder** — all other supply enters circulation through mining, staking, and ecosystem distribution

---

## 3. Proof-of-Useful-Work (PoUW) Reward Structure

### 3.1 Reward Types

| Proof Type | Enum Value | Base Reward | Description |
|------------|-----------|-------------|-------------|
| **ComputeWork** | 0 | 10 STRP/block | AI inference, data processing, rendering |
| **PhysicalActivity** | 1 | 50 STRP/proof | Real-world activity (Bang-jump bridge example: 10m bridge jump) |
| **DataValidation** | 2 | 30 STRP/proof | Data verification, oracle feeds, fact-checking |
| **CreativeWork** | 3 | 40 STRP/proof | Content creation, art, writing, media |

### 3.2 Block Mining (ComputeWork)

- **Block time target:** 30 seconds
- **Block reward:** 10 STRP per block (from the 350M mining pool)
- **Difficulty:** Adjusted dynamically based on network hashrate
- **Miner:** Any node running the strap binary with `mine` command
- **PoUW requirement:** Miner must include a valid proof (nonce that produces leading zero bytes in SHA-256)

### 3.3 Activity Proof Rewards (Higher value)

- **PhysicalActivity (Bang-jump):** 50 STRP per verified proof
  - Example: Jumping a 10m bridge → proof generated → 50 STRP reward
  - "100% secure" — the proof cryptographically verifies the activity occurred
- **DataValidation:** 30 STRP — verifying real-world data feeds
- **CreativeWork:** 40 STRP — on-chain content with AI-assisted metadata

### 3.4 Reward Distribution Flow

```
PoUW Reward (e.g., 50 STRP)
├── 45 STRP → Miner/Prover wallet (90%)
└── 5 STRP → Treasury (10% burn/deflation)
```

The treasury accumulation creates a self-funding ecosystem fund.

---

## 4. Treasury (Ecosystem Fund)

**Initial treasury:** 10% of genesis supply = 100,000,000 STRP  
**Ongoing treasury inflow:** 10% of every PoUW reward

### Treasury Usage

| Category | Allocation | Purpose |
|----------|-----------|---------|
| **Development Grants** | 40% | Funding builders on Strap L1 |
| **Community Rewards** | 25% | Airdrops, contests, bounties |
| **Liquidity Provision** | 20% | DEX pools, market making |
| **AI Ecosystem Fund** | 15% | Incentivizing the 7-agent AI system |

The treasury is controlled by the genesis owner initially, with plans for community governance (DAO) as the ecosystem matures.

---

## 5. Staking System

### 5.1 Stake Mechanics

- **Stake token:** STRP
- **Minimum stake:** 1,000 STRP
- **Validator role:** Stakers become block validators (alongside PoUW miners)
- **Staking reward:** From the 100M staking pool, distributed proportionally

### 5.2 Stake Commands (future CLI)

```
strap stake --amount 10000    # Stake 10,000 STRP
strap unstake --amount 5000   # Unstake (with cooldown)
strap staking-rewards         # Claim earned staking rewards
```

### 5.3 Validator Selection

Validators are selected based on:
1. Stake size (weight)
2. Proof-of-Useful-Work history (activity proof)
3. Uptime/reliability

---

## 6. AI Agent Economy (7 Agents)

The 7 labeled agents are not just tools — they're **first-class participants** in the Strap ecosystem.

### 6.1 Agent Roles & Token Interactions

| Agent | Model | Role | Token Function |
|-------|-------|------|----------------|
| **mark** | nex-agi/nex-n2.5-pro:free | Lead Orchestrator | Coordinates mining, allocates tasks, manages ecosystem decisions |
| **sheylla** | inclusionai/ling-3.0-flash-sante:free | Creative & Content | Writes PoUW metadata, community content, generates creative proofs (40 STRP each) |
| **billie** | liquid/lfm-2.5-embedding-350m:free | Analysis & Embeddings | Analyzes chain data, detects patterns, optimizes mining strategies |
| **legative** | nvidia/nemotron-3.5-lightning:free | Logic & Reasoning | Plans PoUW strategies, economic modeling, proof optimization |
| **newbi** | poolside/laguna-s-2.1:free | Learning & Research | Researches new PoUW activity types, finds mining opportunities |
| **nurio** | liquid/lfm-2.5-2.6b:free | Assistant & Chat | User-facing assistant, answers ecosystem questions |

### 6.2 Agent Reward Mechanism

- Each agent task that results in a successful PoUW proof earns STRP
- The `strap/submit-proof` endpoint via `sheylla` enriches proof metadata
- The `strap/mine` endpoint via `legative` + `newbi` plans mining
- **50,000,000 STRP reserved** specifically for AI agent operations

### 6.3 Agent-to-Agent Transactions

Agents can:
- Delegate tasks to each other (mark → sheylla for content, mark → legative for logic)
- Share chain data (billie analyzes, newbi researches)
- Collaborate on multi-agent proofs (team/chat endpoint)

---

## 7. "Bang-Jump" Proof Concept

The user's specific example: **jumping a 10m bridge** as a PoUW proof.

### How it works:

1. **Activity:** User physically jumps a 10m bridge
2. **Proof generation:** The activity is recorded (sensor data, timestamp, location, photo/video metadata)
3. **On-chain submission:** `strap submit-proof --activity "Bang-jump 10m bridge at [location]" --proof_type physical`
4. **Verification:** C++ PoUW verifier checks the proof hash has sufficient leading zeros
5. **Reward:** 50 STRP credited to the prover's address
6. **Metadata:** Sheylla (AI agent) writes a vivid on-chain description of the jump

This is "Proof-of-Useful-Work" — the useful work is the actual physical activity + the cryptographic proof that it happened. Not wasted hash computation, but **real activity = real reward**.

---

## 8. Token Emission Schedule

### Phase 1: Genesis (Day 0)
- 150,000,000 STRP → Founder wallet
- 100,000,000 STRP → Treasury
- Remainder locked in reward pools

### Phase 2: Early Mining (Months 1-6)
- Block rewards: 10 STRP/block, targeting 30s block time
- ~28,800 STRP/day from block mining
- Activity proofs: variable, starting small
- Community airdrop begins distribution

### Phase 3: Ecosystem Growth (Months 6-24)
- Staking rewards activate
- AI agent rewards flow
- Treasury funds ecosystem development
- Liquidity pool establishment

### Phase 4: Maturity (Year 2+)
- Block reward may decrease (deflationary model)
- Governance transitions from founder to community
- Full decentralized operation

---

## 9. Mini Web App — "Strap Dashboard"

A web interface to view and interact with the Strap L1 ecosystem.

### 9.1 Architecture

```
┌─────────────────────────────────────────────────────┐
│                  Strap Web Dashboard                 │
│  (Single-page app, served by the OpenRouter proxy)  │
└─────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────┐
│              strap_agents.py (FastAPI)               │
│  Port 8080 — already running as the agent gateway   │
│  New endpoint: GET /dashboard → HTML + JSON API     │
└─────────────────────────────────────────────────────┘
         │
         ▼
┌──────────────┐    ┌──────────────┐    ┌────────────┐
│ strap binary │    │ OpenRouter   │    │ chain.json │
│ (CLI, PoUW)  │    │ (7 agents)   │    │ (local DB) │
└──────────────┘    └──────────────┘    └────────────┘
```

### 9.2 Dashboard Screens

**1. Home / Overview**
- Total STRP supply (1B)
- Circulating supply
- Treasury balance
- Current block height
- Latest hash
- 7 agents status (online/active)

**2. Token Distribution Chart**
- Visual pie chart of the 1B allocation
- Founder / Mining / Ecosystem / Community / Staking / Liquidity / AI

**3. Balances**
- Genesis founder balance
- All known addresses and their STRP balance
- Treasury balance

**4. Recent Activity / Proofs**
- List of recent PoUW proofs submitted
- Proof type, activity description, reward amount, timestamp
- Link to "Bang-jump" examples

**5. Agent Chat**
- Chat interface to talk to any of the 7 agents
- Team collaboration mode (all agents respond + mark synthesizes)
- Send PoUW proofs via chat

**6. Mining Dashboard**
- Start/stop mining from the web
- View mining progress
- Estimated rewards

### 9.3 API Endpoints (extend strap_agents.py)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/dashboard` | GET | Serve the HTML dashboard |
| `/api/supply` | GET | Total + circulating supply |
| `/api/treasury` | GET | Treasury balance |
| `/api/balances` | GET | All wallet balances |
| `/api/chain` | GET | Chain info (block height, latest hash) |
| `/api/agents` | GET | 7 agent statuses |
| `/api/proofs` | GET | Recent PoUW proofs |
| `/api/chat` | POST | Chat with agents (existing) |
| `/api/mine` | POST | Start mining (existing) |

---

## 10. Telegram Bot Integration

The Strap ecosystem is accessible via Telegram (chat_id: 8826382180).

### Bot Commands

| Command | Action |
|---------|--------|
| `/init` | Initialize the Strap chain |
| `/info` | Show chain info (supply, blocks, hash) |
| `/balance` | Show token balances |
| `/send <addr> <amount>` | Send STRP to an address |
| `/mine` | Start PoUW mining |
| `/proof <activity>` | Submit a PoUW proof |
| `/agents` | List the 7 AI agents |
| `/chat <message>` | Chat with the agent team |
| `/dashboard` | Open the web dashboard link |

---

## 11. Ecosystem Sustainability Model

### How Strap sustains itself automatically:

1. **PoUW Mining** — every useful activity generates STRP rewards, incentivizing participation
2. **Treasury accumulation** — 10% of every reward feeds the ecosystem fund
3. **AI agent operations** — agents earn STRP for useful work, creating an AI economy
4. **Staking** — holders earn rewards by securing the network
5. **Bang-jump and real activity** — physical world activities generate proofs, bridging real and digital economies
6. **Deflationary pressure** — treasury spending on development, liquidity, and rewards reduces circulating supply over time

### The flywheel:

```
Real Activity → PoUW Proof → STRP Reward → Treasury Growth
     ↑                                        ↓
     └──── AI Agents create content ←──── Ecosystem Funds
```

---

## 12. Implementation Status

| Component | Status | Notes |
|-----------|--------|-------|
| Token spec (1B STRP) | ✅ Defined | This document |
| Allocation table | ✅ Defined | 7 categories |
| PoUW reward structure | ✅ Defined | 4 proof types, rewards |
| Treasury model | ✅ Defined | 10% per-reward + initial 100M |
| Staking system | 📝 Design | Not yet in CLI |
| 7-agent system | ✅ Code exists | strap_agents.py |
| OpenRouter proxy | ✅ Code exists | strap_openrouter_api.py + agents |
| C++ PoUW verifier | ✅ Code exists | strap-pouw.cpp |
| Rust chain core | ⚠️ Build errors | src/main.rs needs fix |
| Mini web dashboard | ❌ Not built | Needs creation |
| Telegram bot gateway | ✅ Configured | chat_id 8826382180 |
| Bang-jump proof concept | ✅ Defined | PhysicalActivity type |

---

## 13. Next Steps (Ecosystem-First Priority)

1. **Finalize the 1B token distribution** — confirm allocation with user
2. **Define the genesis block** — 150M to founder, 100M to treasury, rest locked
3. **Build the web dashboard** — single-page app, served from the API
4. **Extend strap_agents.py** with dashboard endpoints
5. **Create Telegram bot commands** mapping to the ecosystem
6. **Then** — fix Rust build errors and get the `strap` binary running
7. **Then** — test PoUW mining end-to-end

---

*This document is the ecosystem blueprint. Code implementation follows.*
