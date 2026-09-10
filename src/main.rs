// strap: Strap L1 — Proof-of-Useful-Work blockchain CLI and node
// Single-file lightweight build. Minimal deps. Fast compile.

use clap::{Parser, Subcommand};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::fs;
use std::path::PathBuf;
use std::time::{SystemTime, UNIX_EPOCH};

pub type Address = [u8; 32];

#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq, Hash)]
pub struct Hash(pub [u8; 32]);

impl Hash {
    pub fn from_bytes(data: &[u8]) -> Self {
        let mut h = [0u8; 32];
        h.copy_from_slice(&Sha256::digest(data));
        Hash(h)
    }
    pub fn to_hex(&self) -> String {
        hex::encode(self.0)
    }
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct CoinOwner {
    pub address: Address,
    pub balance: u64,
    pub stake: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub enum TxType {
    Transfer,
    ProofSubmission,
    Stake,
    Unstake,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Transaction {
    pub tx_type: TxType,
    pub sender: Address,
    pub recipient: Option<Address>,
    pub amount: u64,
    pub proof: Option<Proof>,
    pub nonce: u64,
    pub signature: Vec<u8>,
    pub fee: u64,
    pub timestamp: u64,
    pub tx_hash: Hash,
}

impl Transaction {
    pub fn new(tx_type: TxType, sender: Address, recipient: Option<Address>,
               amount: u64, proof: Option<Proof>, nonce: u64, fee: u64) -> Self {
        let mut tx = Transaction {
            tx_type, sender, recipient, amount, proof, nonce,
            signature: Vec::new(), fee,
            timestamp: now(),
            tx_hash: Hash([0u8; 32]),
        };
        tx.tx_hash = tx.compute_hash();
        tx
    }
    fn compute_hash(&self) -> Hash {
        let mut d = Vec::new();
        d.extend_from_slice(match self.tx_type {
            TxType::Transfer => &[0u8],
            TxType::ProofSubmission => &[1u8],
            TxType::Stake => &[2u8],
            TxType::Unstake => &[3u8],
        });
        d.extend_from_slice(self.sender.as_slice());
        if let Some(ref r) = self.recipient {
            d.extend_from_slice(r.as_slice());
        }
        d.extend_from_slice(&self.amount.to_le_bytes());
        if let Some(ref p) = self.proof {
            d.extend_from_slice(&p.serialize_byte());
        }
        d.extend_from_slice(&self.nonce.to_le_bytes());
        d.extend_from_slice(&self.fee.to_le_bytes());
        d.extend_from_slice(&self.timestamp.to_le_bytes());
        Hash::from_bytes(&d)
    }
}

#[repr(u8)]
#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq)]
pub enum ProofType {
    ComputeWork,
    PhysicalActivity,
    DataValidation,
    CreativeWork,
}

#[repr(C)]
#[derive(Debug, Clone, Copy)]
pub struct Proof {
    pub proof_type: u8,
    pub worker_id: [u8; 32],
    pub activity_hash: [u8; 32],
    pub timestamp: u64,
    pub nonce: u64,
    pub metadata: [u8; 64],
    pub metadata_len: u8, // max 64
}

impl Serialize for Proof {
    fn serialize<S>(&self, serializer: S) -> Result<S::Ok, S::Error>
    where
        S: serde::Serializer,
    {
        use serde::ser::SerializeSeq;
        let data = self.serialize_byte();
        let mut seq = serializer.serialize_seq(Some(data.len()))?;
        for b in data {
            seq.serialize_element(&b)?;
        }
        seq.end()
    }
}

impl<'de> Deserialize<'de> for Proof {
    fn deserialize<D>(deserializer: D) -> Result<Self, D::Error>
    where
        D: serde::Deserializer<'de>,
    {
        let data: Vec<u8> = Deserialize::deserialize(deserializer)?;
        if data.len() < 82 {
            return Err(serde::de::Error::custom("Proof data too short"));
        }
        let pt = data[0];
        let mut wid = [0u8; 32];
        wid.copy_from_slice(&data[1..33]);
        let mut ah = [0u8; 32];
        ah.copy_from_slice(&data[33..65]);
        let ts = u64::from_le_bytes(data[65..73].try_into().unwrap());
        let nn = u64::from_le_bytes(data[73..81].try_into().unwrap());
        let ml = data[81] as usize;
        let mut md = [0u8; 64];
        if ml > 0 && ml <= 64 {
            md[..ml].copy_from_slice(&data[82..82 + ml]);
        }
        Ok(Proof {
            proof_type: pt,
            worker_id: wid,
            activity_hash: ah,
            timestamp: ts,
            nonce: nn,
            metadata: md,
            metadata_len: ml as u8,
        })
    }
}

impl Proof {
    pub fn new(pt: ProofType) -> Self {
        Proof {
            proof_type: pt as u8,
            worker_id: [0u8; 32],
            activity_hash: [0u8; 32],
            timestamp: 0,
            nonce: 0,
            metadata: [0u8; 64],
            metadata_len: 0,
        }
    }
    pub fn serialize_byte(&self) -> Vec<u8> {
        let mut d = Vec::with_capacity(146);
        d.push(self.proof_type);
        d.extend_from_slice(&self.worker_id);
        d.extend_from_slice(&self.activity_hash);
        d.extend_from_slice(&self.timestamp.to_le_bytes());
        d.extend_from_slice(&self.nonce.to_le_bytes());
        d.push(self.metadata_len);
        d.extend_from_slice(&self.metadata[..self.metadata_len as usize]);
        d
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Block {
    pub height: u64,
    pub prev_hash: Hash,
    pub transactions: Vec<Transaction>,
    pub proof: Option<Proof>,
    pub validator: Address,
    pub timestamp: u64,
    pub state_root: Hash,
    pub block_hash: Hash,
}

impl Block {
    pub fn new(height: u64, prev: Hash, txs: Vec<Transaction>, proof: Option<Proof>, val: Address) -> Self {
        let ts = now();
        let sr = compute_state_root(&txs);
        let mut b = Block {
            height,
            prev_hash: prev,
            transactions: txs,
            proof,
            validator: val,
            timestamp: ts,
            state_root: sr,
            block_hash: Hash([0u8; 32]),
        };
        b.block_hash = b.compute_hash();
        b
    }
    fn compute_hash(&self) -> Hash {
        use sha2::Digest;
        let mut d = Vec::new();
        d.extend_from_slice(&self.height.to_le_bytes());
        d.extend_from_slice(&self.prev_hash.0);
        for t in &self.transactions {
            d.extend_from_slice(&t.tx_hash.0);
        }
        if let Some(ref p) = self.proof {
            d.extend_from_slice(&p.serialize_byte());
        }
        d.extend_from_slice(&self.validator);
        d.extend_from_slice(&self.timestamp.to_le_bytes());
        d.extend_from_slice(&self.state_root.0);
        Hash::from_bytes(&d)
    }
}

fn compute_state_root(txs: &[Transaction]) -> Hash {
    let mut h = Sha256::new();
    for t in txs {
        h.update(&t.tx_hash.0);
    }
    Hash(h.finalize().try_into().unwrap())
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GenesisConfig {
    #[serde(rename = "CoinName")]
    pub coin_name: String,
    pub symbol: String,
    pub initial_supply: u64,
    pub owner_address: Address,
    pub reward_per_proof: u64,
    pub block_reward: u64,
    pub max_block_size: usize,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Chain {
    pub genesis_config: GenesisConfig,
    pub blocks: Vec<Block>,
    pub treasury: u64,
    pub total_supply: u64,
    pub coin_owners: Vec<CoinOwner>,
}

impl Chain {
    pub fn new(cfg: GenesisConfig) -> Self {
        let addr = cfg.owner_address;
        let supply = cfg.initial_supply;
        let genesis = Block::new(0, Hash([0u8; 32]), Vec::new(), None, addr);
        let treasury = supply / 10;
        let balance = supply - treasury;
        Chain {
            genesis_config: cfg,
            blocks: vec![genesis],
            treasury,
            total_supply: supply,
            coin_owners: vec![CoinOwner {
                address: addr,
                balance,
                stake: 0,
            }],
        }
    }
}

#[link(name = "strap-pouw", kind = "static")]
#[link(name = "ssl", kind = "dylib")]
#[link(name = "crypto", kind = "dylib")]
extern "C" {
    fn strap_verify_proof(proof: *const Proof, difficulty: u8) -> bool;
    fn strap_mine_proof(proof: *mut Proof, difficulty: u8, max_attempts: u64) -> u64;
    fn strap_compute_proof_hash(proof: *const Proof, out: *mut u8);
}

fn verify_proof(p: &Proof, diff: u8) -> bool {
    unsafe { strap_verify_proof(p as *const Proof, diff) }
}

fn mine_proof(p: &mut Proof, diff: u8, max: u64) -> u64 {
    unsafe { strap_mine_proof(p as *mut Proof, diff, max) }
}

fn compute_proof_hash(p: &Proof) -> [u8; 32] {
    let mut out = [0u8; 32];
    unsafe {
        strap_compute_proof_hash(p as *const Proof, out.as_mut_ptr());
    }
    out
}

fn now() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_secs()
}

fn addr_from_seed(seed: &str) -> Address {
    let h = Sha256::digest(seed.as_bytes());
    let mut a = [0u8; 32];
    a.copy_from_slice(&h);
    a
}

#[derive(Parser)]
#[command(name = "strap", about = "Strap L1 PoUW Blockchain", version = env!("CARGO_PKG_VERSION"))]
struct Cli {
    #[arg(short, long, default_value = "./strap-data")]
    data_dir: PathBuf,
    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand)]
enum Commands {
    Init {
        #[arg(short, long, default_value = "1000000000000000000")]
        supply: u64,
        #[arg(short, long, default_value = "strap-founder")]
        owner: String,
        #[arg(short, long, default_value = "STRP")]
        symbol: String,
        #[arg(short, long, default_value = "50")]
        reward: u64,
    },
    Info,
    Send {
        #[arg(short, long)]
        to: String,
        #[arg(short, long)]
        amount: u64,
    },
    SubmitProof {
        #[arg(short, long)]
        activity: String,
        #[arg(short, long, default_value = "physical")]
        pt: String,
    },
    Mine {
        #[arg(short, long, default_value = "1")]
        count: u64,
        #[arg(short, long, default_value = "2")]
        diff: u8,
    },
    Balances,
    NewAddress {
        #[arg(short, long, default_value = "my-wallet")]
        label: String,
    },
}

fn load_chain(dir: &PathBuf) -> Result<Chain, String> {
    let d = fs::read_to_string(&dir.join("chain.json")).map_err(|e| e.to_string())?;
    serde_json::from_str(&d).map_err(|e| e.to_string())
}

fn save_chain(dir: &PathBuf, c: &Chain) -> Result<(), String> {
    let d = serde_json::to_string_pretty(c).map_err(|e| e.to_string())?;
    fs::write(dir.join("chain.json"), d).map_err(|e| e.to_string())?;
    if let Some(l) = c.blocks.last() {
        fs::write(dir.join("latest_hash.txt"), &l.block_hash.to_hex()).ok();
    }
    Ok(())
}

fn main() {
    let cli = Cli::parse();
    let dd = &cli.data_dir;
    if !dd.exists() {
        fs::create_dir_all(dd).ok();
    }

    match cli.command {
        Commands::Init { supply, owner, symbol, reward } => {
            let oa = addr_from_seed(&owner);
            let cfg = GenesisConfig {
                coin_name: "Strap".into(),
                symbol: symbol.clone(),
                initial_supply: supply,
                owner_address: oa,
                reward_per_proof: reward,
                block_reward: 10,
                max_block_size: 100,
            };
            let chain = Chain::new(cfg);
            save_chain(dd, &chain).unwrap();
            let sym = symbol.to_string();
            println!(
                "✅ Strap initialized! Symbol={} Owner={} Supply={}",
                sym, hex::encode(oa), supply
            );
        }
        Commands::Info => {
            let c = load_chain(dd).expect("No chain — run init");
            println!(
                "Blocks={} Supply={} Treasury={}",
                c.blocks.len(),
                c.total_supply,
                c.treasury
            );
            if let Some(l) = c.blocks.last() {
                println!("Latest={} Height={}", l.block_hash.to_hex(), l.height);
            }
        }
        Commands::Send { to, amount } => {
            let mut c = load_chain(dd).expect("No chain");
            let rec = addr_from_seed(&to);
            let sen = c.genesis_config.owner_address;
            let bal = c
                .coin_owners
                .iter()
                .find(|co| co.address == sen)
                .map(|co| co.balance)
                .unwrap_or(0);
            if bal < amount {
                eprintln!("Insufficient");
                std::process::exit(1);
            }
            let tx = Transaction::new(TxType::Transfer, sen, Some(rec), amount, None, 0, 1);
            let prev = c.blocks.last().unwrap().block_hash;
            let blk = Block::new(c.blocks.len() as u64, prev, vec![tx], None, sen);
            if let Some(co) = c.coin_owners.iter_mut().find(|co| co.address == sen) {
                co.balance -= amount + 1;
            }
            if let Some(co) = c.coin_owners.iter_mut().find(|co| co.address == rec) {
                co.balance += amount;
            } else {
                c.coin_owners.push(CoinOwner {
                    address: rec,
                    balance: amount,
                    stake: 0,
                });
            }
            c.blocks.push(blk);
            save_chain(dd, &c).unwrap();
            println!("✅ Sent {} STRP to {}", amount, hex::encode(rec).as_str());
        }
        Commands::SubmitProof { activity, pt } => {
            let mut c = load_chain(dd).expect("No chain");
            let sen = c.genesis_config.owner_address;
            let typ = match pt.as_str() {
                "compute" => ProofType::ComputeWork,
                "physical" => ProofType::PhysicalActivity,
                "data" => ProofType::DataValidation,
                "creative" => ProofType::CreativeWork,
                _ => ProofType::PhysicalActivity,
            };
            let mut proof = Proof::new(typ);
            proof.worker_id = sen;
            proof.timestamp = now();
            let len = activity.len().min(64) as u8;
            proof.metadata_len = len;
            proof.metadata[..len as usize]
                .copy_from_slice(&activity.as_bytes()[..len as usize]);
            let sd = format!("Activity: {}, Timestamp: {}", activity, proof.timestamp);
            proof
                .activity_hash
                .copy_from_slice(&Sha256::digest(sd.as_bytes()));
            let nonce = mine_proof(&mut proof, 2, 100000);
            if nonce == 0 {
                eprintln!("Failed");
                std::process::exit(1);
            }
            if !verify_proof(&proof, 2) {
                eprintln!("Verify failed");
                std::process::exit(1);
            }
            let reward = c.genesis_config.reward_per_proof;
            println!(
                "✅ Proof mined! Activity={} Reward={} Nonce={}",
                activity, reward, nonce
            );
            let tx = Transaction::new(
                TxType::ProofSubmission,
                sen,
                Some(sen),
                reward,
                Some(proof.clone()),
                0,
                0,
            );
            let prev = c.blocks.last().unwrap().block_hash;
            let blk = Block::new(c.blocks.len() as u64, prev, vec![tx], Some(proof), sen);
            if let Some(co) = c.coin_owners.iter_mut().find(|co| co.address == sen) {
                co.balance += reward;
            }
            c.treasury += reward / 10;
            c.total_supply += reward;
            c.blocks.push(blk);
            save_chain(dd, &c).unwrap();
            println!(
                "   Balance: {} STRP",
                c.coin_owners
                    .iter()
                    .find(|co| co.address == sen)
                    .unwrap()
                    .balance
            );
        }
        Commands::Mine { count, diff } => {
            let mut c = load_chain(dd).expect("No chain");
            let sen = c.genesis_config.owner_address;
            println!("⛏️ Mining {} blocks (diff={})...", count, diff);
            for i in 0..count {
                let mut proof = Proof::new(ProofType::ComputeWork);
                proof.worker_id = sen;
                proof.timestamp = now();
                proof.metadata_len = 8;
                proof.metadata[..8].copy_from_slice(b" mined #");
                proof.metadata[8..16].copy_from_slice(&(i + 1).to_le_bytes());
                let nonce = mine_proof(&mut proof, diff, 500000);
                if nonce == 0 {
                    eprintln!("Failed block {}", i + 1);
                    continue;
                }
                let reward = c.genesis_config.block_reward;
                let tx = Transaction::new(
                    TxType::ProofSubmission,
                    sen,
                    Some(sen),
                    reward,
                    Some(proof.clone()),
                    0,
                    0,
                );
                let prev = c.blocks.last().unwrap().block_hash;
                let blk = Block::new(c.blocks.len() as u64, prev, vec![tx], Some(proof), sen);
                if let Some(co) = c.coin_owners.iter_mut().find(|co| co.address == sen) {
                    co.balance += reward;
                }
                c.treasury += reward / 10;
                c.total_supply += reward;
                c.blocks.push(blk);
                if (i + 1) % 10 == 0 || i == 0 {
                    print!("\r  Mined {}/{}", i + 1, count);
                }
            }
            println!();
            save_chain(dd, &c).unwrap();
            println!("✅ Mining complete! Total supply: {} STRP", c.total_supply);
        }
        Commands::Balances => {
            let c = load_chain(dd).expect("No chain");
            for co in &c.coin_owners {
                println!("  {}: {} STRP", hex::encode(co.address).as_str(), co.balance);
            }
            println!("  Treasury: {} STRP", c.treasury);
            println!("  Total supply: {} STRP", c.total_supply);
        }
        Commands::NewAddress { label } => {
            let a = addr_from_seed(&label);
            println!("✅ Address: {} ({})", hex::encode(a), label);
        }
    }
}
