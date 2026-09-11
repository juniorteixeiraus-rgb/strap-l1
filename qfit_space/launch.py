#!/usr/bin/env python3
"""
QFit.space — SaaS Application Launcher
AI Chatbot SaaS on Strap 722 Crypto Network
$799 Lifetime License — Private Infrastructure
"""

import os
import sys
import logging
from pathlib import Path

# ── Setup Paths ────────────────────────────────────────────────────────────────
QFIT_HOME = Path("/opt/qfit_space")
QFIT_DATA = QFIT_HOME / "data"
QFIT_MODELS = QFIT_HOME / "models"
QFIT_LOGS = QFIT_HOME / "logs"

for d in [QFIT_HOME, QFIT_DATA, QFIT_MODELS, QFIT_LOGS]:
    d.mkdir(parents=True, exist_ok=True)

# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [QFit] %(levelname)s: %(message)s",
    handlers=[
        logging.FileHandler(QFIT_LOGS / "qfit.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("qfit")


def print_banner():
    """Print QFit.space startup banner."""
    banner = """
╔══════════════════════════════════════════════════════════════════════════╗
║                                                                    ║
║   ███████╗███╗   ██╗██████╗  ██████╗ ██╗   ██╗██╗███╗   ███╗        ║
║   ██╔════╝████╗  ██║██╔══██╗██╔═══██╗██║   ██║██║████╗ ████║        ║
║   ███████╗██╔██╗ ██║██║  ██║██║   ██║██║   ██║██║██╔████╔██║        ║
║   ╚════██║██║╚██╗██║██║  ██║██║   ██║╚██╗ ██╔╝██║██║╚██╔╝██║        ║
║   ███████║██║ ╚████║██████╔╝╚██████╔╝ ╚████╔╝ ██║██║ ╚██╗ ██║        ║
║   ╚══════╝╚═╝  ╚═══╝╚═════╝  ╚═════╝   ╚═══╝  ╚═╝╚═╝  ╚═╝ ╚═╝        ║
║                                                                    ║
║   AI Chatbot SaaS — $799 Lifetime License                          ║
║   Running on Strap 722 Crypto Network                               ║
║   Private Infrastructure — Data Never Exposed                       ║
║                                                                    ║
╚══════════════════════════════════════════════════════════════════════════╝
    """
    log.info(banner)


def check_prerequisites():
    """Check that all prerequisites are met."""
    checks = []
    
    # Check LLM engine
    has_ollama = os.system("which ollama > /dev/null 2>&1") == 0
    checks.append(("Ollama (LLM engine)", has_ollama))
    
    # Check Strap 722 chain
    has_strap = os.system("curl -s http://localhost:8080/health > /dev/null 2>&1") == 0
    checks.append(("Strap 722 Chain (port 8080)", has_strap))
    
    # Check LHS network
    has_lhs = os.system("curl -s http://localhost:7220/health > /dev/null 2>&1") == 0
    checks.append(("LHS Network (port 7220)", has_lhs))
    
    # Check cloudflared
    has_cf = os.system("which cloudflared > /dev/null 2>&1") == 0
    checks.append(("Cloudflare Tunnel", has_cf))
    
    log.info("Prerequisite checks:")
    for name, result in checks:
        status = "✓" if result else "✗"
        log.info(f"  {status} {name}")
    
    if not all(r for _, r in checks):
        log.warning("Some prerequisites not met — QFit.space may run in limited mode")
    
    return all(r for _, r in checks)


def main():
    """Launch QFit.space SaaS application."""
    print_banner()
    log.info(f"QFit.space v1.0.0 — Starting up...")
    log.info(f"Home: {QFIT_HOME}")
    log.info(f"Data: {QFIT_DATA}")
    log.info(f"Models: {QFIT_MODELS}")
    log.info(f"Logs: {QFIT_LOGS}")
    
    # Check prerequisites
    check_prerequisites()
    
    # Set environment
    os.environ.setdefault("QFIT_PORT", "8082")
    os.environ.setdefault("QFIT_NETWORK", "Strap 722")
    os.environ.setdefault("QFIT_LICENSE_PRICE", "799")
    os.environ.setdefault("STRAP_CHAIN_URL", "http://localhost:8080")
    os.environ.setdefault("LHS_ENDPOINT", "http://localhost:7220")
    
    # Import and start the app
    sys.path.insert(0, str(QFIT_HOME))
    from qfit_space.app.qfit_space import main as qfit_main
    
    log.info("Launching QFit.space...")
    qfit_main()


if __name__ == "__main__":
    main()
