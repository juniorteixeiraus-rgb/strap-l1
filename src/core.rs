//! strap-l1: Strap L1 Proof-of-Useful-Work Layer 1 chain.
//! Core types: coin, block, transaction, PoUW proof, chain state.

use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::time::{SystemTime, UNIX_EPOCH};

// ── Hash ──────────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq, Hash)]
pub struct Hash(pub [u8; 32]);

impl Hash {
    pub fn from_bytes(bytes: &[u8]) -> Self {
        let mut h = [0u8; 32];
        h.copy_from_slice(&Sha256::digest(bytes)[..]);
        Hash(h)
    }
    pub fn raw(&self) -> [u8; 32] {
        self.0
    }
    pub fn clone_hash(&self) -> Hash {
        Hash(self.0)
    }
}

// ── Address ───────────────────────────────────────────────

pub type Address = [u8; 32];

pub fn addr(seed: &str) -> Address {
    let h = Sha256::digest(seed.as_bytes());
    let mut a = [0u8; 32];
    a.copy_from_slice(&h);
    a
}

// ── Transaction ───────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub enum TxType {
    Transfer,
    SubmitProof,
    ClaimReward,
    Stake,
    Unstake,
    Governance,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct Transaction {
    pub tx_type: TxType,
    pub sender: Address,
    pub recipient: Option<Address>,
    pub amount: u64,
    pub nonce: u64,
    pub fee: u64,
    pub payload: Vec<u8>,
    pub signature: Vec<u8>,
    pub timestamp: u64,
    pub tx_hash: Hash,
}

impl Transaction {
    pub fn new(
        tx_type: TxType,
        sender: Address,
        recipient: Option<Address>,
        amount: u64,
        nonce: u64,
        payload: Vec<u8>,
        fee: u64,
    ) -> Self {
        let mut t = Transaction {
            tx_type,
            sender,
            recipient,
            amount,
            nonce,
            fee,
            payload,
            signature: vec![],
            timestamp: now_secs(),
            tx_hash: Hash([0u8; 32]),
        };
        let ser = serde_json::to_vec(&t).unwrap();
        t.tx_hash = Hash::from_bytes(&ser);
        t
    }
}

fn now_secs() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_secs()
}

// ── Proof of Useful Work ──────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub enum ProofType {
    ComputeWork,
    PhysicalActivity,
    DataValidation,
    CommunityTask,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct PoUWProof {
    pub proof_type: ProofType,
    pub worker_id: Address,
    pub activity_hash: Hash,
    pub checksum: u64,
    pub nonce: u64,
    pub timestamp: u64,
    pub metadata: Vec<u8>,
    pub verified: bool,
    pub proof_hash: Hash,
}

impl PoUWProof {
    pub fn new(
        proof_type: ProofType,
        worker_id: Address,
        activity_hash: Hash,
        metadata: Vec<u8>,
    ) -> Self {
        let mut p = PoUWProof {
            proof_type,
            worker_id,
            activity_hash,
            checksum: 0,
            nonce: 0,
            timestamp: now_secs(),
            metadata,
            verified: false,
            proof_hash: Hash([0u8; 32]),
        };
        let ser = serde_json::to_vec(&p).unwrap();
        p.proof_hash = Hash::from_bytes(&ser);
        p
    }

    pub fn mine(&mut self, difficulty: usize) -> bool {
        let target = "0".repeat(difficulty);
        loop {
            self.nonce += 1;
            let ser = serde_json::to_vec(self).unwrap();
            let h = Hash::from_bytes(&ser);
            let hx = hex::encode(h.0);
            if hx.starts_with(&target) {
                self.proof_hash = h;
                return true;
            }
            if self.nonce > 2_000_000 {
                return false;
            }
        }
    }
}

// ── Block ─────────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct Block {
    pub height: u64,
    pub prev_hash: Hash,
    pub timestamp: u64,
    pub transactions: Vec<Transaction>,
    pub proofs: Vec<PoUWProof>,
    pub state_root: Hash,
    pub consensus_hash: Hash,
    pub validator: Address,
    pub reward_minted: u64,
}

impl Block {
    pub fn new(
        height: u64,
        prev_hash: Hash,
        transactions: Vec<Transaction>,
        proofs: Vec<PoUWProof>,
        validator: Address,
        reward_minted: u64,
    ) -> Self {
        let mut b = Block {
            height,
            prev_hash,
            timestamp: now_secs(),
            transactions,
            proofs,
            state_root: Hash([0u8; 32]),
            consensus_hash: Hash([0u8; 32]),
            validator,
            reward_minted,
        };
        let ser = serde_json::to_vec(&b).unwrap();
        let ch = Hash::from_bytes(&ser);
        b.consensus_hash = ch.clone_hash();
        b.state_root = ch;
        b
    }
}

// ── Genesis ───────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GenesisConfig {
    pub coin_name: String,
    pub symbol: String,
    pub initial_supply: u64,
    pub owner_address: Address,
    pub owner_balance: u64,
    pub reward_per_proof: u64,
    pub block_reward: u64,
    pub treasury_pct: u8,
    #[serde(skip)]
    pub max_block_size: usize,
}

// ── Chain ─────────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Chain {
    pub blocks: Vec<Block>,
    pub genesis_config: GenesisConfig,
    pub treasury: u64,
    pub total_supply: u64,
}

impl Chain {
    pub fn new(cfg: GenesisConfig) -> Self {
        let owner = cfg.owner_address;
        let mut genesis = Block {
            height: 0,
            prev_hash: Hash([0u8; 32]),
            timestamp: now_secs(),
            transactions: vec![],
            proofs: vec![],
            state_root: Hash([0u8; 32]),
            consensus_hash: Hash([0u8; 32]),
            validator: owner,
            reward_minted: cfg.initial_supply,
        };
        let ser = serde_json::to_vec(&genesis).unwrap();
        let gh = Hash::from_bytes(&ser);
        genesis.consensus_hash = gh.clone_hash();
        genesis.state_root = gh;

        let treasury = (cfg.initial_supply as u128 * cfg.treasury_pct as u128 / 100) as u64;

        Chain {
            blocks: vec![genesis],
            genesis_config: cfg,
            treasury,
            total_supply: cfg.initial_supply,
        }
    }

    pub fn latest_hash(&self) -> Hash {
        self.blocks
            .last()
            .map(|b| b.consensus_hash.clone())
            .unwrap_or(Hash([0u8; 32]))
    }

    pub fn latest_height(&self) -> u64 {
        self.blocks.len() as u64
    }

    pub fn add_block(&mut self, block: Block) -> Result<(), String> {
        if block.prev_hash != self.latest_hash() {
            return Err("prev_hash mismatch".into());
        }
        if block.height != self.latest_height() {
            return Err("height mismatch".into());
        }
        let reward = block.reward_minted;
        self.blocks.push(block);
        self.total_supply += reward;
        Ok(())
    }
}

// ── Default genesis ──────────────────────────────────────

pub fn default_genesis_config() -> GenesisConfig {
    let owner = addr("strap-founder");
    GenesisConfig {
        coin_name: "Strap".into(),
        symbol: "STRP".into(),
        initial_supply: 1_000_000 * 10u64.pow(8),
        owner_address: owner,
        owner_balance: 1_000_000 * 10u64.pow(8),
        reward_per_proof: 10 * 10u64.pow(8) / 1000,
        block_reward: 5 * 10u64.pow(8),
        treasury_pct: 10,
        max_block_size: 1024 * 1024,
    }
}
