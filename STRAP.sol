// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * $Strap ($STP) Token — ERC-20 on Base (Coinbase L2)
 *
 * Token name: $Strap
 * Symbol:     $STP
 * Supply:     1,000,000,000 $STP (1 billion)
 * Decimals:   18
 *
 * Deployment:
 *   Remix → Compile 0.8.20 → Deploy via Injected Provider (MetaMask on Base)
 *   Verify on Basescan → Add liquidity on Aerodrome
 *
 * Networks:
 *   Base Mainnet:  chainId 8453, RPC https://mainnet.base.org
 *   Base Sepolia:  chainId 84531, RPC https://sepolia.base.org (testnet)
 */

contract $Strap {

    string private _name = "$Strap";
    string private _symbol = "$STP";
    uint8  private _decimals = 18;
    uint256 private _totalSupply = 0;

    mapping(address => uint256) private _balances;
    mapping(address => mapping(address => uint256)) private _allowances;

    event Transfer(address indexed from, address indexed to, uint256 value);
    event Approval(address indexed owner, address indexed spender, uint256 value);

    constructor() {
        _totalSupply = 1_000_000_000 * 10 ** uint256(_decimals);
        _balances[msg.sender] = _totalSupply;
        emit Transfer(address(0), msg.sender, _totalSupply);
    }

    function name()      external view returns (string memory) { return _name;  }
    function symbol()    external view returns (string memory) { return _symbol; }
    function decimals()  external view returns (uint8)         { return _decimals; }
    function totalSupply() external view returns (uint256)     { return _totalSupply; }

    function balanceOf(address account) external view returns (uint256) {
        return _balances[account];
    }

    function allowance(address owner, address spender) external view returns (uint256) {
        return _allowances[owner][spender];
    }

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
        require(currentAllowance >= amount, "$STP: insufficient allowance");
        _approve(from, msg.sender, currentAllowance - amount);
        _transfer(from, to, amount);
        return true;
    }

    function _transfer(address from, address to, uint256 amount) internal {
        require(from != address(0), "$STP: transfer from zero address");
        require(to != address(0), "$STP: transfer to zero address");
        require(_balances[from] >= amount, "$STP: insufficient balance");
        _balances[from] = _balances[from] - amount;
        _balances[to]   = _balances[to]   + amount;
        emit Transfer(from, to, amount);
    }

    function _approve(address owner, address spender, uint256 amount) internal {
        require(owner != address(0), "$STP: approve from zero address");
        require(spender != address(0), "$STP: approve to zero address");
        _allowances[owner][spender] = amount;
        emit Approval(owner, spender, amount);
    }
}
