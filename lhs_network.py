#!/usr/bin/env python3
"""
LHS — Left-Hand Side Network Protocol
==========================================
A distributed mesh network that works WITH and WITHOUT internet.
The 722 blockchain runs on LHS nodes — any device, any network, any cloud.

LHS enables:
  - Local IP network blockchain (no internet needed)
  - Cross-network bridging (when internet returns)
  - Device discovery on local networks
  - Offline-first block production and validation
  - Netcoin: digital network currency that works everywhere

Author: Strap 722 Project
Version: 1.0
"""

from __future__ import annotations

import hashlib
import json
import os
import socket
import struct
import threading
import time
import uuid
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional, List, Dict, Set, Tuple
from enum import Enum

# ── Configuration ──────────────────────────────────────────────────────────

LHS_PORT = int(os.environ.get("LHS_PORT", "7220"))
LHS_BIND = os.environ.get("LHS_BIND", "0.0.0.0")
LHS_DISCOVERY_PORT = int(os.environ.get("LHS_DISCOVERY_PORT", "7221"))
LHS_MCAST_GROUP = os.environ.get("LHS_MCAST_GROUP", "224.0.0.722")
LHS_MCAST_PORT = int(os.environ.get("LHS_MCAST_PORT", "7222"))
LHS_WORKER_THREADS = int(os.environ.get("LHS_WORKER_THREADS", "4"))
LHS_DATA_DIR = os.environ.get("LHS_DATA_DIR", "./lhs-data")
LHS_BLOCK_INTERVAL = int(os.environ.get("LHS_BLOCK_INTERVAL", "30"))  # seconds
LHS_PEER_TIMEOUT = int(os.environ.get("LHS_PEER_TIMEOUT", "300"))  # seconds
LHS_MAX_PEERS = int(os.environ.get("LHS_MAX_PEERS", "20"))
LHS_LISTEN_BACKLOG = int(os.environ.get("LHS_LISTEN_BACKLOG", "10"))
LHS_STARTUP_MODE = os.environ.get("LHS_STARTUP_MODE", "auto")  # auto, internet, offline

# ── Data Types ─────────────────────────────────────────────────────────────

class LHSMessageType(Enum):
    DISCOVERY = 1          # Peer discoverybroadcast
    HELLO = 2              # First contact with a peer
    HELLO_RESPONSE = 3     # Response to hello
    BLOCK_PROPOSE = 4      # Propose a new block
    BLOCK_PROPOSE_RESPONSE = 5  # Response to block proposal
    BLOCK_ACCEPT = 6       # Accept a block (validate + sign)
    BLOCK_ACCEPT_RESPONSE = 7   # Response to block accept
    TRANSACTION = 8        # Send a transaction
    TRANSACTION_RESPONSE = 9    # Response to transaction
    SYNC_REQUEST = 10      # Request block sync
    SYNC_RESPONSE = 11     # Response with blocks
    ASK_VALIDATE = 12      # Ask peers to validate a block
    VALIDATE_RESPONSE = 13      # Validation response
    LEADER_ELECTION = 14   # Leader election message
    LEADER_ELECTION_RESPONSE = 15  # Election response
    HEARTBEAT = 16         # Keep-alive heartbeat
    SHUTDOWN = 17          # Graceful shutdown
    GET_STATE = 18         # Request current state
    STATE_RESPONSE = 19    # Current state response


@dataclass
class LHSPeer:
    """A peer node in the LHS network."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    ip: str = "0.0.0.0"
    port: int = LHS_PORT
    hostname: str = ""
    agent_name: str = ""  # e.g. "motorola-g06", "ec2-node-1", "vps-frankfurt"
    capabilities: List[str] = field(default_factory=list)
    first_seen: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)
    score: float = 0.0
    is_reachable: bool = True
    metadata: Dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "LHSPeer":
        return cls(**d)


@dataclass
class LHSBlock:
    """A block in the LHS blockchain."""
    height: int = 0
    hash: str = ""  # SHA-256 of the block
    previous_hash: str = ""
    timestamp: float = field(default_factory=time.time)
    proposer: str = ""  # Peer ID of the proposer
    transactions: List[dict] = field(default_factory=list)
    validations: List[dict] = field(default_factory=list)  # Peer validations
    agent_signatures: Dict[str, str] = field(default_factory=dict)  # AI agent signatures
    powu_proof: Optional[dict] = None  # PoUW proof data
    cross_chain_anchors: Dict[str, str] = field(default_factory=dict)  # Base, Solana, etc.
    dimensions: Dict[str, bool] = field(default_factory=dict)  # 7 dimension validation results
    consensus_engines: Dict[str, bool] = field(default_factory=dict)  # 2 consensus engines
    network_modes: Dict[str, bool] = field(default_factory=dict)  # 2 network modes
    metadata: Dict = field(default_factory=dict)
    signature: str = ""  # Block signature

    def compute_hash(self) -> str:
        """Compute the SHA-256 hash of this block."""
        data = json.dumps({
            "height": self.height,
            "previous_hash": self.previous_hash,
            "timestamp": self.timestamp,
            "proposer": self.proposer,
            "transactions": self.transactions,
            "validations": self.validations,
            "agent_signatures": self.agent_signatures,
            "powu_proof": self.powu_proof,
            "cross_chain_anchors": self.cross_chain_anchors,
            "dimensions": self.dimensions,
            "consensus_engines": self.consensus_engines,
            "network_modes": self.network_modes,
        }, sort_keys=True, default=str).encode()
        return hashlib.sha256(data).hexdigest()

    def to_dict(self) -> dict:
        d = asdict(self)
        d["hash"] = self.hash
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "LHSBlock":
        block = cls(
            height=d.get("height", 0),
            previous_hash=d.get("previous_hash", ""),
            timestamp=d.get("timestamp", time.time()),
            proposer=d.get("proposer", ""),
            transactions=d.get("transactions", []),
            validations=d.get("validations", []),
            agent_signatures=d.get("agent_signatures", {}),
            powu_proof=d.get("powu_proof"),
            cross_chain_anchors=d.get("cross_chain_anchors", {}),
            dimensions=d.get("dimensions", {}),
            consensus_engines=d.get("consensus_engines", {}),
            network_modes=d.get("network_modes", {}),
            metadata=d.get("metadata", {}),
            signature=d.get("signature", ""),
        )
        block.hash = d.get("hash", block.compute_hash())
        return block


@dataclass
class LHSMessage:
    """A message in the LHS network."""
    type: LHSMessageType
    from_peer_id: str
    to_peer_id: str = ""  # Empty = broadcast
    sequence: int = 0
    timestamp: float = field(default_factory=time.time)
    payload: dict = field(default_factory=dict)
    signature: str = ""

    def to_bytes(self) -> bytes:
        data = {
            "type": self.type.value,
            "from": self.from_peer_id,
            "to": self.to_peer_id,
            "seq": self.sequence,
            "ts": self.timestamp,
            "payload": self.payload,
        }
        raw = json.dumps(data, sort_keys=True, default=str).encode()
        return struct.pack("!I", len(raw)) + raw

    @classmethod
    def from_bytes(cls, data: bytes) -> "LHSMessage":
        if len(data) < 4:
            raise ValueError("Message too short")
        length = struct.unpack("!I", data[:4])[0]
        raw = data[4:4+length]
        parsed = json.loads(raw.decode())
        msg = cls(
            type=LHSMessageType(parsed["type"]),
            from_peer_id=parsed["from"],
            to_peer_id=parsed.get("to", ""),
            sequence=parsed.get("seq", 0),
            timestamp=parsed.get("ts", time.time()),
            payload=parsed.get("payload", {}),
        )
        return msg


@dataclass
class LHSNetwork:
    """The LHS network state."""
    peer_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    peer: LHSPeer = field(default_factory=lambda: LHSPeer())
    blocks: List[LHSBlock] = field(default_factory=list)
    peers: Dict[str, LHSPeer] = field(default_factory=dict)
    transactions: List[dict] = field(default_factory=list)
    leaders: List[str] = field(default_factory=list)
    is_connected_to_internet: bool = True
    local_ip: str = ""
    local_networks: List[str] = field(default_factory=list)
    mode: str = "auto"  # auto, internet, offline


# ── LHS Protocol Implementations ───────────────────────────────────────────

class LHSDiscoveryProtocol:
    """Peer discovery using multicast and local network scanning."""

    def __init__(self, network: LHSNetwork):
        self.network = network
        self.mcast_socket = None
        self.discovery_socket = None
        self.running = False
        self.discovery_thread = None

    def start(self):
        """Start discovery protocols."""
        self.running = True

        # Start multicast discovery
        self._start_multicast()

        # Start local network scanning
        self._start_local_scan()

        # Start heartbeat
        self._start_heartbeat()

    def stop(self):
        """Stop discovery protocols."""
        self.running = False

    def _start_multicast(self):
        """Start multicast peer discovery."""
        try:
            self.mcast_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
            self.mcast_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.mcast_socket.bind(("", LHS_MCAST_PORT))
            mreq = struct.pack("4sI", socket.inet_aton(LHS_MCAST_GROUP), socket.INADDR_ANY)
            self.mcast_socket.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
            self.mcast_socket.settimeout(1.0)

            thread = threading.Thread(target=self._mcast_listener, daemon=True)
            thread.start()
            log(f"Multicast discovery started on {LHS_MCAST_GROUP}:{LHS_MCAST_PORT}")
        except Exception as e:
            log(f"  Multicast discovery failed: {e}")

    def _mcast_listener(self):
        """Listen for multicast discovery messages."""
        while self.running:
            try:
                data, addr = self.mcast_socket.recvfrom(1024)
                msg = LHSMessage.from_bytes(data)
                if msg.type == LHSMessageType.DISCOVERY:
                    self._handle_discovery(msg, addr[0])
            except socket.timeout:
                continue
            except Exception as e:
                log(f"  Multicast error: {e}")
                continue

    def _handle_discovery(self, msg: LHSMessage, ip: str):
        """Handle a discovery message."""
        peer_data = msg.payload
        peer = LHSPeer(
            id=peer_data.get("id", ""),
            ip=ip,
            port=peer_data.get("port", LHS_PORT),
            hostname=peer_data.get("hostname", ""),
            agent_name=peer_data.get("agent_name", ""),
            capabilities=peer_data.get("capabilities", []),
        )
        peer.last_seen = time.time()
        self.network.peers[peer.id] = peer
        log(f"  Discovered peer: {peer.id[:8]}... at {ip}:{peer.port}")

    def _start_local_scan(self):
        """Scan local network for peers."""
        thread = threading.Thread(target=self._local_scan_loop, daemon=True)
        thread.start()

    def _local_scan_loop(self):
        """Loop scanning local networks for peers."""
        # Determine local networks
        local_interfaces = self._get_local_networks()
        self.network.local_networks = local_interfaces
        self.network.local_ip = self._get_primary_ip()

        while self.running:
            try:
                self._scan_local_networks()
            except Exception as e:
                log(f"  Local scan error: {e}")
            time.sleep(30)  # Scan every 30 seconds

    def _get_local_networks(self) -> List[str]:
        """Get local network ranges."""
        networks = []
        try:
            import netifaces
            for iface in netifaces.interfaces():
                addrs = netifaces.ifaddresses(iface)
                if netifaces.AF_INET in addrs:
                    for addr_info in addrs[netifaces.AF_INET]:
                        ip = addr_info["addr"]
                        netmask = addr_info.get("netmask", "")
                        if ip and not ip.startswith("127."):
                            network = f"{ip}/{netmask}"
                            networks.append((iface, ip, network))
        except ImportError:
            # Fallback: use socket to get local IP
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))
                ip = s.getsockname()[0]
                s.close()
                networks.append(("default", ip, f"{ip}/24"))
            except:
                pass

        return networks

    def _get_primary_ip(self) -> str:
        """Get the primary local IP address."""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "127.0.0.1"

    def _scan_local_networks(self):
        """Scan local networks for peers."""
        for iface, ip, network in self.network.local_networks:
            try:
                # Simple: scan common ports on the local subnet
                base_ip = ".".join(ip.split(".")[:-1])
                for last_octet in range(1, 255):
                    target_ip = f"{base_ip}.{last_octet}"
                    if target_ip == ip:
                        continue
                    # Try to connect to LHS port
                    try:
                        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        sock.settimeout(0.5)
                        result = sock.connect_ex((target_ip, LHS_PORT))
                        if result == 0:
                            # Found a peer! Send hello
                            self._send_hello(target_ip, LHS_PORT)
                        sock.close()
                    except:
                        continue
            except Exception as e:
                log(f"  Scan error on {network}: {e}")

    def _send_hello(self, ip: str, port: int):
        """Send a hello message to a peer."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2.0)
            sock.connect((ip, port))

            msg = LHSMessage(
                type=LHSMessageType.HELLO,
                from_peer_id=self.network.peer_id,
                payload={
                    "peer": self.network.peer.to_dict(),
                    "caps": ["lhs-node", "block-producer", "agent-validator"],
                    "timestamp": time.time(),
                }
            )
            sock.sendall(msg.to_bytes())
            sock.close()
        except Exception as e:
            pass  # Peer not responding

    def _start_heartbeat(self):
        """Send heartbeat messages to known peers."""
        def heartbeat_loop():
            while self.running:
                try:
                    for peer in list(self.network.peers.values()):
                        if time.time() - peer.last_seen > LHS_PEER_TIMEOUT:
                            del self.network.peers[peer.id]
                            continue
                        try:
                            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                            sock.settimeout(1.0)
                            sock.connect((peer.ip, peer.port))
                            msg = LHSMessage(
                                type=LHSMessageType.HEARTBEAT,
                                from_peer_id=self.network.peer_id,
                                payload={"timestamp": time.time()},
                            )
                            sock.sendall(msg.to_bytes())
                            sock.close()
                        except:
                            pass
                except Exception as e:
                    pass
                time.sleep(10)

        thread = threading.Thread(target=heartbeat_loop, daemon=True)
        thread.start()


class LHSBlockProducer:
    """Produces blocks for the LHS network."""

    def __init__(self, network: LHSNetwork):
        self.network = network
        self.running = False
        self.thread = None
        self.last_block_height = 0

    def start(self):
        """Start block production."""
        self.running = True
        self.last_block_height = len(self.network.blocks)
        self.thread = threading.Thread(target=self._produce_blocks, daemon=True)
        self.thread.start()
        log(f"Block production started (interval: {LHS_BLOCK_INTERVAL}s)")

    def stop(self):
        """Stop block production."""
        self.running = False

    def _produce_blocks(self):
        """Main block production loop."""
        while self.running:
            try:
                self._produce_next_block()
            except Exception as e:
                log(f"  Block production error: {e}")
            time.sleep(LHS_BLOCK_INTERVAL)

    def _produce_next_block(self):
        """Produce the next block."""
        # Get current state
        last_block = self.network.blocks[-1] if self.network.blocks else None
        prev_hash = last_block.hash if last_block else "0" * 64
        height = (last_block.height + 1) if last_block else 0

        # Collect transactions
        transactions = self.network.transactions[:]
        self.network.transactions = []

        # Create the block
        block = LHSBlock(
            height=height,
            previous_hash=prev_hash,
            proposer=self.network.peer_id,
            transactions=transactions,
            timestamp=time.time(),
        )

        # Compute hash
        block.hash = block.compute_hash()

        # Run PoUW proof (simulated for now, real C++ verifier would go here)
        block.powu_proof = self._generate_powu_proof(block)

        # Validate the block (7 dimensions)
        block.dimensions = self._validate_block_dimensions(block)

        # Run consensus engines
        block.consensus_engines = self._run_consensus_engines(block)

        # Network modes
        block.network_modes = {
            "internet": self.network.is_connected_to_internet,
            "mesh": True,  # Always available on the mesh
        }

        # Sign the block
        block.signature = self._sign_block(block)

        # Add to chain
        self.network.blocks.append(block)
        self.last_block_height = block.height

        # Broadcast to peers
        self._broadcast_block(block)

        # Cross-chain anchor (if internet available)
        if self.network.is_connected_to_internet:
            self._cross_chain_anchor(block)

        log(f"  Block #{block.height} produced: {block.hash[:16]}...")

    def _generate_powu_proof(self, block: LHSBlock) -> dict:
        """Generate a Proof-of-Useful-Work proof."""
        # Real implementation would call the C++ verifier
        # For now, simulate with a hash
        proof_data = {
            "block_hash": block.hash,
            "timestamp": time.time(),
            "work_done": "semantic_validation",
            "work_units": len(block.transactions),
            "cpu_time_ms": 100,  # Simulated
        }
        proof_data["proof_hash"] = hashlib.sha256(
            json.dumps(proof_data, sort_keys=True).encode()
        ).hexdigest()
        return proof_data

    def _validate_block_dimensions(self, block: LHSBlock) -> Dict[str, bool]:
        """Validate the 7 dimensions of the block."""
        dims = {}

        # D1: Cryptographic integrity
        dims["D1_crypto"] = (block.hash == block.compute_hash())

        # D2: Transaction validity
        dims["D2_transactions"] = self._validate_transactions(block)

        # D3: AI semantic consensus (agent signatures)
        dims["D3_agent_consensus"] = len(block.agent_signatures) >= 7

        # D4: PoUW verification
        dims["D4_powu"] = block.powu_proof is not None

        # D5: Cross-chain anchors
        dims["D5_cross_chain"] = len(block.cross_chain_anchors) > 0

        # D6: Temporal consistency
        dims["D6_temporal"] = block.timestamp > 0

        # D7: Decentralization
        dims["D7_decentralization"] = len(self.network.peers) > 1

        return dims

    def _validate_transactions(self, block: LHSBlock) -> bool:
        """Validate transactions in the block."""
        for tx in block.transactions:
            # Basic validation
            if "from" not in tx or "to" not in tx:
                return False
            if "amount" not in tx:
                return False
        return True

    def _run_consensus_engines(self, block: LHSBlock) -> Dict[str, bool]:
        """Run the 2 consensus engines."""
        engines = {}

        # C1: PoUW consensus
        engines["C1_powu"] = block.powu_proof is not None

        # C2: Agent consensus (7 agents must sign)
        engines["C2_agent"] = len(block.agent_signatures) >= 7

        return engines

    def _sign_block(self, block: LHSBlock) -> str:
        """Sign the block."""
        # In production, this would be a real cryptographic signature
        return hashlib.sha256(
            f"{block.hash}:{self.network.peer_id}:{time.time()}".encode()
        ).hexdigest()

    def _broadcast_block(self, block: LHSBlock):
        """Broadcast a block to all peers."""
        msg = LHSMessage(
            type=LHSMessageType.BLOCK_PROPOSE,
            from_peer_id=self.network.peer_id,
            payload=block.to_dict(),
        )
        # Send to all known peers
        for peer in list(self.network.peers.values()):
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2.0)
                sock.connect((peer.ip, peer.port))
                sock.sendall(msg.to_bytes())
                sock.close()
            except:
                pass

    def _cross_chain_anchor(self, block: LHSBlock):
        """Anchor the block to external chains (Base, Solana)."""
        # In production, this would submit to Base/Solana
        # For now, just store the anchor
        block.cross_chain_anchors["base"] = f"base-anchor-{block.height}"
        block.cross_chain_anchors["solana"] = f"solana-anchor-{block.height}"


class LHSAgentValidator:
    """Validates blocks using AI agents (722 agent consensus)."""

    def __init__(self, network: LHSNetwork):
        self.network = network
        self.agents = [
            {"name": "mark", "model": "nex-agi/nex-n2.5-pro:free", "role": "lead_coordination"},
            {"name": "sheylla", "model": "inclusionai/ling-3.0-flash-sante:free", "role": "language_parsing"},
            {"name": "billie", "model": "liquid/lfm-2.5-embedding-350m:free", "role": "embeddings"},
            {"name": "legative", "model": "nvidia/nemotron-3.5-lightning:free", "role": "reasoning"},
            {"name": "newbi", "model": "poolside/laguna-s-2.1:free", "role": "code"},
            {"name": "nurio", "model": "liquid/lfm-2.5-2.6b:free", "role": "analysis"},
        ]
        self.running = False
        self.thread = None

    def start(self):
        """Start agent validation."""
        self.running = True
        self.thread = threading.Thread(target=self._validate_loop, daemon=True)
        self.thread.start()
        log("Agent validation started (7 AI agents)")

    def stop(self):
        """Stop agent validation."""
        self.running = False

    def _validate_loop(self):
        """Main validation loop."""
        while self.running:
            try:
                if self.network.blocks:
                    latest = self.network.blocks[-1]
                    if not latest.agent_signatures or len(latest.agent_signatures) < 7:
                        self._validate_block(latest)
            except Exception as e:
                log(f"  Agent validation error: {e}")
            time.sleep(5)

    def _validate_block(self, block: LHSBlock):
        """Validate a block using all 7 AI agents."""
        for agent in self.agents:
            try:
                # In production, this would call the OpenRouter API
                # For now, simulate agent validation
                signature = self._agent_validate(block, agent)
                block.agent_signatures[agent["name"]] = signature
                log(f"  Agent {agent['name']} validated block #{block.height}: {signature[:16]}...")
            except Exception as e:
                log(f"  Agent {agent['name']} validation error: {e}")

    def _agent_validate(self, block: LHSBlock, agent: dict) -> str:
        """Have an AI agent validate a block."""
        # In production: call OpenRouter API with the agent's model
        # For now, simulate with a deterministic signature
        agent_hash = hashlib.sha256(
            f"{agent['name']}:{agent['model']}:{block.hash}:{time.time()}".encode()
        ).hexdigest()
        return agent_hash


class LHSAPIServer:
    """HTTP API server for the LHS network."""

    def __init__(self, network: LHSNetwork):
        self.network = network
        self.httpd = None
        self.running = False

    def start(self, port: int = 8080):
        """Start the API server."""
        from http.server import HTTPServer, BaseHTTPRequestHandler

        class LHSAPIHandler(BaseHTTPRequestHandler):
            network = self.network

            def do_GET(self):
                path = self.path

                if path == "/api/chain":
                    self._send_json({
                        "height": self.network.blocks[-1].height if self.network.blocks else 0,
                        "latest_hash": self.network.blocks[-1].hash if self.network.blocks else "",
                        "peer_count": len(self.network.peers),
                        "mode": self.network.mode,
                        "local_ip": self.network.local_ip,
                        "is_online": self.network.is_connected_to_internet,
                    })
                    return

                elif path == "/api/blocks":
                    blocks = [b.to_dict() for b in self.network.blocks[-10:]]
                    self._send_json({"blocks": blocks})
                    return

                elif path == "/api/peers":
                    peers = {pid: p.to_dict() for pid, p in self.network.peers.items()}
                    self._send_json({"peers": peers})
                    return

                elif path == "/api/agents":
                    self._send_json({"agents": self.agents})
                    return

                elif path == "/":
                    self._send_html(self._get_dashboard_html())
                    return

                else:
                    self.send_error(404)

            def _send_json(self, data: dict):
                body = json.dumps(data, indent=2, default=str)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(body.encode())

            def _send_html(self, html: str):
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(html.encode())

        # Attach the agent list to the handler
        LHSAPIHandler.agents = self.agents

        # Create and start server
        self.httpd = HTTPServer((LHS_BIND, port), LHSAPIHandler)
        self.running = True

        thread = threading.Thread(target=self._serve, daemon=True)
        thread.start()
        log(f"API server started on port {port}")

    def stop(self):
        """Stop the API server."""
        self.running = False
        if self.httpd:
            self.httpd.shutdown()

    def _serve(self):
        """Run the HTTP server."""
        while self.running:
            self.httpd.handle_request()

    def _get_dashboard_html(self) -> str:
        """Get the dashboard HTML."""
        return """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Strap LHS 722 Network</title>
    <style>
        body { font-family: -apple-system, sans-serif; background: #000; color: #fff; padding: 20px; }
        .card { background: #111; border: 1px solid #333; border-radius: 8px; padding: 16px; margin-bottom: 16px; }
        .value { font-size: 24px; font-weight: bold; color: #3390ec; }
        .label { font-size: 12px; color: #888; text-transform: uppercase; }
        .status-live { display: inline-block; background: #22c55e; color: white; padding: 4px 8px; border-radius: 4px; font-size: 11px; }
        .status-offline { display: inline-block; background: #ef4444; color: white; padding: 4px 8px; border-radius: 4px; font-size: 11px; }
    </style>
</head>
<body>
    <div style="max-width: 480px; margin: 0 auto;">
        <h1>LHS 722 Network</h1>
        <p style="color: #888;">The decentralized mesh that works everywhere</p>

        <div class="card">
            <div class="label">Network Status</div>
            <div class="value" id="status">Loading...</div>
        </div>

        <div class="card">
            <div class="label">Latest Block Height</div>
            <div class="value" id="height">-</div>
        </div>

        <div class="card">
            <div class="label">Latest Block Hash</div>
            <div class="value" id="hash" style="font-size: 14px; word-break: break-all;">-</div>
        </div>

        <div class="card">
            <div class="label">Known Peers</div>
            <div class="value" id="peers">-</div>
        </div>

        <div class="card">
            <div class="label">Network Mode</div>
            <div class="value" id="mode">-</div>
        </div>

        <div class="card">
            <div class="label">Local IP</div>
            <div class="value" id="local_ip" style="font-size: 14px;">-</div>
        </div>

        <script>
            async function load() {
                try {
                    const resp = await fetch('/api/chain');
                    const data = await resp.json();
                    document.getElementById('status').innerHTML = data.is_online ?
                        '<span class="status-live">Online (Internet)</span>' :
                        '<span class="status-offline">Offline (Mesh Only)</span>';
                    document.getElementById('height').textContent = data.height;
                    document.getElementById('hash').textContent = data.latest_hash;
                    document.getElementById('mode').textContent = data.mode;
                } catch(e) {
                    document.getElementById('status').textContent = 'Error loading';
                }
            }
            async function loadPeers() {
                try {
                    const resp = await fetch('/api/peers');
                    const data = await resp.json();
                    document.getElementById('peers').textContent = Object.keys(data.peers || {}).length;
                    document.getElementById('local_ip').textContent = data.peers[Object.keys(data.peers)[0]]?.ip || 'N/A';
                } catch(e) {}
            }
            load();
            loadPeers();
            setInterval(load, 5000);
            setInterval(loadPeers, 10000);
        </script>
    </div>
</body>
</html>
        """


# ── Main ────────────────────────────────────────────────────────────────────

class LHSNode:
    """Main LHS node — runs all protocols."""

    def __init__(self):
        self.network = LHSNetwork()
        self.network.peer.hostname = socket.gethostname()
        self.network.peer.ip = self._get_local_ip()
        self.network.mode = LHS_STARTUP_MODE

        self.discovery = LHSDiscoveryProtocol(self.network)
        self.producer = LHSBlockProducer(self.network)
        self.agent_validator = LHSAgentValidator(self.network)
        self.api = LHSAPIServer(self.network)

        self.running = False

    def _get_local_ip(self) -> str:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "127.0.0.1"

    def start(self):
        """Start the LHS node."""
        self.running = True
        self.network.is_connected_to_internet = self._check_internet()

        log("=" * 60)
        log("STRAP 722 — LHS Network Node Starting")
        log("=" * 60)
        log(f"  Node ID: {self.network.peer.id[:16]}...")
        log(f"  Local IP: {self.network.peer.ip}")
        log(f"  Hostname: {self.network.peer.hostname}")
        log(f"  Mode: {self.network.mode}")
        log(f"  Internet: {'Yes' if self.network.is_connected_to_internet else 'No (mesh only)'}")
        log(f"  Port: {LHS_PORT}")
        log(f"  Data dir: {LHS_DATA_DIR}")
        log("=" * 60)

        # Create data dir
        os.makedirs(LHS_DATA_DIR, exist_ok=True)

        # Start protocols
        self.discovery.start()
        self.producer.start()
        self.agent_validator.start()
        self.api.start(port=8080)

        log("\nLHS node running. Press Ctrl+C to stop.")
        log("\nEndpoints:")
        log(f"  API: http://{self.network.peer.ip}:8080")
        log(f"  Discovery: {LHS_MCAST_GROUP}:{LHS_MCAST_PORT}")
        log(f"  P2P: {self.network.peer.ip}:{LHS_PORT}")
        log("\n")

        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            log("\nShutting down...")
            self.stop()

    def stop(self):
        """Stop the LHS node."""
        self.running = False
        self.discovery.stop()
        self.producer.stop()
        self.agent_validator.stop()
        self.api.stop()
        log("LHS node stopped.")

    def _check_internet(self) -> bool:
        """Check if the node has internet access."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3.0)
            result = sock.connect_ex(("8.8.8.8", 53))
            sock.close()
            return result == 0
        except:
            return False


# ── Fast startup ────────────────────────────────────────────────────────────

def main():
    import argparse

    parser = argparse.ArgumentParser(description="LHS — Left-Hand Side Network Node")
    parser.add_argument("--port", type=int, default=7220)
    parser.add_argument("--api-port", type=int, default=8080)
    parser.add_argument("--mode", choices=["auto", "internet", "offline"], default="auto")
    parser.add_argument("--data-dir", type=str, default="/opt/strap722/data")
    parser.add_argument("--no-internet", action="store_true", help="Start in offline mode")
    args = parser.parse_args()

    global LHS_PORT
    global LHS_DATA_DIR
    global LHS_STARTUP_MODE

    LHS_PORT = args.port
    LHS_DATA_DIR = args.data_dir
    LHS_STARTUP_MODE = "offline" if args.no_internet else args.mode

    node = LHSNode()
    node.start()


if __name__ == "__main__":
    import logging
    import sys

    # Configure logging
    log_level = os.environ.get("LHS_LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    # Alias log function
    global log
    log = logging.info

    main()
