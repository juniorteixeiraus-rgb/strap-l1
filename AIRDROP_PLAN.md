# $STP Airdrop & Reward Plan
## All 1 Billion Tokens → Your Wallet → Sell or Reward

---

## Step 1: Deploy → All 1B $STP to Your Wallet

When we run `solana_deploy.py --network devnet` (or `mainnet`), this happens:

1. **Create SPL token mint** → $Strap / $STP, 9 decimals
2. **Create token account** for your wallet
3. **Mint 1,000,000,000 $STP** → all tokens go to YOUR wallet (`6SGUKs4f...`)
4. You now hold all 1B $STP

**Your wallet after deployment:**
```
Wallet: 6SGUKs4f1pFQDdEj63FrUk1MUZY43zenzPT7zet1kw9S
Balance: 1,000,000,000 $STP (1 billion)
Mint address: <the SPL token mint address>
```

---

## Step 2: Two Paths After Deployment

### Path A: Sell Tokens (liquidity + price discovery)

1. Add $STP to your wallet (Phantom, Solflare)
2. Go to Raydium or Jupiter
3. Add liquidity (pair $STP with SOL)
4. Start selling/buying — price discovery begins
5. You sell some, hold some, or all

**What you need:**
- SOL for transaction fees (~0.01-0.05 SOL)
- Liquidity pool on Raydium/Jupiter

**Risk:** Selling too much at once crashes the price. Sell gradually.

---

### Path B: Airdrop / Reward to Community

Instead of (or in addition to) selling, distribute $STP to people:

**Airdrop campaigns:**
- Early supporters get free $STP
- Telegram community members
- Miners who contribute compute
- Beta testers of the bot/dashboard

**Reward mechanisms:**
- Mining rewards (50 $STP per proof) — ongoing
- Agent work rewards — per task
- Staking rewards — future

**How to airdrop:**
```bash
# Send $STP to any wallet
spl-token transfer -u https://api.mainnet-beta.solana.com \
    <MINT_ADDRESS> \
    <AMOUNT> \
    <RECIPIENT_WALLET> \
    --authority <YOUR_KEYPAIR>
```

**Example:**
```bash
# Send 1,000 $STP to a community member
spl-token transfer -u https://api.mainnet-beta.solana.com \
    Etch... (mint address) \
    1000 \
    recipient-waller-address \
    --authority /path/to/your/keypair.json
```

---

## Step 3: Community Reward Structure (Proposed)

### Treasury Wallet (separate from your personal wallet)

Create a separate wallet for community rewards:
```bash
solana-keygen new --no-passphrase -o community-treasury.json
```

Send a portion of $STP to the treasury:
```bash
spl-token transfer -u https://api.mainnet-beta.solana.com \
    <MINT_ADDRESS> \
    100000000 \  # 100M $STP to treasury
    <TREASURY_WALLET> \
    --authority <YOUR_KEYPAIR>
```

### Reward Categories

| Category | Reward | Trigger |
|----------|--------|---------|
| Miners | 50 $STP per proof | Proof-of-Service submitted |
| Early adopters | 1,000-10,000 $STP | First 100 wallet holders |
| Telegram community | 100-500 $STP | Active members |
| Referral program | 500 $STP per referral | New users who join |
| Bug bounties | 1,000-10,000 $STP | Security issues found |
| Content creators | 500-5,000 $STP | Posts, videos, tutorials |
| Staking | TBD % APY | Lock $STP for rewards |

### Airdrop Phases

**Phase 1 — Genesis Airdrop (Day 1):**
- 10M $STP to early community members
- 5M $STP to Telegram beta testers
- 5M $STP to miners who pre-registered

**Phase 2 — Mining Rewards (Ongoing):**
- 50 $STP per proof, continuously
- Funded from... (TBD — either from supply or newly minted)

**Phase 3 — Growth Rewards (Month 1-6):**
- 50M $STP for community growth
- Referral bonuses
- Content creator rewards

**Phase 4 — Staking (Month 6+):**
- Lock $STP → earn yield
- Governance participation

---

## Wallet Structure Recommendation

```
Wallet 1: Your personal wallet (6SGUKs4f...)
  - Holds remaining $STP after airdrops
  - You sell from here (or hold)

Wallet 2: Community treasury
  - Holds airdrop funds
  - Used to reward community
  - Transparent on-chain (everyone can see)

Wallet 3: Mining rewards wallet (optional)
  - Receives mining rewards
  - Distributes to miners automatically

Wallet 4: Development fund (optional)
  - Funds for ongoing development
  - Multisig in the future
```

---

## Current Status

| Item | Status |
|------|--------|
| Solana wallet created | ✅ `6SGUKs4f1pFQDdEj63FrUk1MUZY43zenzPT7zet1kw9S` |
| Solana wallet balance | ❌ 0 SOL (devnet faucet dry) |
| Deploy script ready | ✅ `solana_deploy.py` |
| Script will mint | ✅ 1B $STP to your wallet on deploy |
| Airdrop mechanism | ✅ `spl-token transfer` ready |
| Community treasury wallet | ❌ Not yet created (do this on deployment) |

---

## What I Need From You

1. **Get test SOL on devnet** — go to https://solfaucet.com or https://faucet.rpcpool.com, paste your wallet address, get test SOL
2. **OR fund mainnet wallet** — send ~0.05 SOL to `6SGUKs4f...` for mainnet deployment
3. **Run the deploy** — once SOL is available:
   ```bash
   python3 solana_deploy.py --network devnet   # or mainnet
   ```
4. **Send me the mint address** — I'll help with listings, liquidity, and airdrop setup

---

## After Deployment — Your Options

| Option | Action | Result |
|--------|--------|--------|
| Sell on DEX | Add liquidity on Raydium → sell $STP/SOL | Price discovery, you get SOL back |
| Airdrop to community | Send $STP to hundreds of wallets | Community growth, buzz |
| Hold and stake | Lock $STP in staking contract (future) | Earn yield over time |
| Hybrid | Sell some, airdrop some, hold some | Best of all worlds |

**My recommendation:** Sell a small portion initially to establish price, airdrop to community for growth, hold the rest for long-term value.

---

## File: solana_deploy.py (what it does)

```python
# Creates the SPL token
mint = create_token(network, decimals)       # $Strap / $STP mint created

# Creates token account for your wallet
account = create_token_account(network, mint) # your token account

# Mints 1B $STP to your account
mint_sig = mint_tokens(network, mint, supply) # 1,000,000,000 $STP minted
```

All 1B tokens land in your wallet. You control them completely.

---

## Next: Push the airdrop plan to GitHub + wait for SOL

I'm pushing this plan + updating COMMUNITY.md. Once you have SOL (devnet or mainnet), we deploy and the 1B $STP are yours.
