// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * STRA — Strp (StrAP) Token
 * ERC-20 implementation for deployment on Base (Coinbase L2) or any EVM chain.
 *
 * Token name:  Strp
 * Symbol:      $STP
 * Total supply: 1,000,000,000 STp (1 billion)
 * Decimals:    18
 * Initial owner: deployer address (all tokens minted to deployer on deployment)
 *
 * Usage:
 *   1. Open remix.ethereum.org
 *   2. Paste this contract into a new file (e.g. STP.sol)
 *   3. Compile with compiler version 0.8.20+ (Remix auto-detects)
 *   4. Deploy using "Injected Provider" (MetaMask/Coinbase Wallet connected to Base)
 *      - Make sure your wallet is connected to Base Mainnet (chainId 8453)
 *      - You need a small amount of ETH on Base for gas (~0.001-0.01 ETH)
 *   5. After deployment, the token appears in your wallet and is tradeable on Base DEXs
 *
 * Network info:
 *   Base Mainnet:  chainId 8453, RPC https://mainnet.base.org
 *   Base Sepolia:   chainId 84531, RPC https://sepolia.base.org (testnet — free faucet ETH)
 *   Ethereum:      chainId 1,   RPC https://eth.llamarpc.com
 *
 * For testnet practice first: deploy on Base Sepolia, verify it works, then deploy on Base Mainnet.
 */

contract Strp {

    // ── ERC-20 state ──────────────────────────────────────────────────────
    string private _name = "Strp";
    string private _symbol = "$STP";
    uint8  private _decimals = 18;
    uint256 private _totalSupply = 0;

    mapping(address => uint256) private _balances;
    mapping(address => mapping(address => uint256)) private _allowances;

    // ── Events ────────────────────────────────────────────────────────────
    event Transfer(address indexed from, address indexed to, uint256 value);
    event Approval(address indexed owner, address indexed spender, uint256 value);

    // ── Constructor ───────────────────────────────────────────────────────
    // Mints the full 1B supply to the deployer on deployment.
    constructor() {
        _totalSupply = 1_000_000_000 * 10 ** uint256(_decimals);
        _balances[msg.sender] = _totalSupply;
        emit Transfer(address(0), msg.sender, _totalSupply);
    }

    // ── ERC-20 required view functions ───────────────────────────────────
    function name()  external pure returns (string memory) { return _name;  }
    function symbol() external pure returns (string memory) { return _symbol; }
    function decimals() external pure returns (uint8) { return _decimals; }
    function totalSupply() external view returns (uint256) { return _totalSupply; }

    function balanceOf(address account) external view returns (uint256) {
        return _balances[account];
    }

    function allowance(address owner, address spender) external view returns (uint256) {
        return _allowances[owner][spender];
    }

    // ── ERC-20 transfer ───────────────────────────────────────────────────
    function transfer(address to, uint256 amount) external returns (bool) {
        _transfer(msg.sender, to, amount);
        return true;
    }

    function approve(address spender, uint256 amount) external returns (bool) {
        _approve(msg.sender, spender, amount);
        return true;
    }

    function transferFrom(address from, address to, uint256 amount) external returns (bool) {
        uint256 currentAllowance = _allowances[from][msg.sender];
        require(currentAllowance >= amount, "StrAp: insufficient allowance");
        _approve(from, msg.sender, currentAllowance - amount);
        _transfer(from, to, amount);
        return true;
    }

    // ── Internal implementations ──────────────────────────────────────────
    function _transfer(address from, address to, uint256 amount) internal {
        require(from != address(0), "StrAp: transfer from zero address");
        require(to != address(0), "StrAp: transfer to zero address");
        require(_balances[from] >= amount, "StrAp: insufficient balance");

        _balances[from] = _balances[from] - amount;
        _balances[to]   = _balances[to]   + amount;
        emit Transfer(from, to, amount);
    }

    function _approve(address owner, address spender, uint256 amount) internal {
        require(owner != address(0), "StrAp: approve from zero address");
        require(spender != address(0), "StrAp: approve to zero address");
        _allowances[owner][spender] = amount;
        emit Approval(owner, spender, amount);
    }
}
