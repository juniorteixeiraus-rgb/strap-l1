#!/usr/bin/env python3
"""
Helper script to set up Cloudflare Tunnel for the Strap 722 MiniApp.
This exposes the local MiniApp (port 8081) to the internet via Cloudflare Tunnel.
"""

import subprocess, time, sys, os, json, requests

CLOUDFLARED = "cloudflared"
TUNNEL_PORT = 8081

def log(msg):
    print(f"[SETUP] {msg}")

def run(cmd, timeout=60):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return r.stdout + r.stderr, r.returncode
    except subprocess.TimeoutExpired:
        return "TIMEOUT", 124
    except Exception as e:
        return str(e), 1

def main():
    log("="*60)
    log("Strap 722 — Cloudflare Tunnel Setup")
    log("="*60)
    
    # Check if cloudflared is installed
    out, rc = run(f"{CLOUDFLARED} --version", timeout=10)
    if rc != 0:
        log(f"cloudflared not found. Install with:")
        log("  Linux: curl -fsSL https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o /usr/local/bin/cloudflared && chmod +x /usr/local/bin/cloudflared")
        log("  Or: go install github.com/cloudflare/cloudflared/cmd/cloudflared@latest")
        return False
    
    log(f"cloudflared version: {out.strip()}")
    
    # Check if already logged in
    log("\nChecking if already logged in...")
    out, rc = run(f"{CLOUDFLARED} tunnel list", timeout=10)
    if rc == 0 and "ID" in out:
        log("Already logged in and has tunnels")
        # List tunnels
        log(f"Tunnels:\n{out}")
    else:
        log("Not logged in. Need to login.")
        log("\nTo login, run:")
        log(f"  {CLOUDFLARED} tunnel login")
        log("\nThis will open a browser. After login, run this script again.")
        return False
    
    # Check if tunnel already exists
    out, rc = run(f"{CLOUDFLARED} tunnel list", timeout=10)
    if rc == 0 and "strap722" in out.lower():
        log("Tunnel 'strap722' already exists. Starting it...")
        out, rc = run(f"{CLOUDFLARED} tunnel run strap722", timeout=30)
        log(f"Tunnel output: {out[:500]}")
        return True
    
    # Create tunnel
    log("\nCreating new tunnel 'strap722'...")
    out, rc = run(f"{CLOUDFLARED} tunnel create strap722", timeout=30)
    log(f"Create output: {out[:500]}")
    
    # Parse tunnel info from output
    tunnel_id = None
    for line in out.split('\n'):
        if 'ID:' in line or 'id:' in line.lower():
            parts = line.split(':')
            if len(parts) > 1:
                tunnel_id = parts[-1].strip()
                log(f"Tunnel ID: {tunnel_id}")
    
    if not tunnel_id:
        log("Could not parse tunnel ID from output")
        log(f"Full output:\n{out}")
        return False
    
    # Get tunnel credentials
    log(f"\nTunnel credentials should be at:")
    log(f"  ~/.cloudflared/{tunnel_id}.json")
    
    # Create tunnel config file
    config_path = f"/home/ubuntu/.cloudflared/{tunnel_id}.json"
    tunnel_config = {
        "tunnel": tunnel_id,
        "credentials-file": config_path,
        "metrics": f"localhost:9091",
        "ingress": [
            {
                "service": f"http://localhost:{TUNNEL_PORT}",
                "hostname": f"strap722.{os.environ.get('USER', 'ubuntu')}.cfargotunnel.com"
            }
        ]
    }
    
    # Write config as YAML (cloudflared expects YAML)
    yaml_content = f"""tunnel: {tunnel_id}
credentials-file: {config_path}
metrics: localhost:9091

ingress:
  - service: http://localhost:{TUNNEL_PORT}
"""
    
    config_file = f"/home/ubuntu/.cloudflared/{tunnel_id}.yml"
    with open(config_file, 'w') as f:
        f.write(yaml_content)
    
    log(f"Config written to: {config_file}")
    log(f"\nTo start tunnel, run:")
    log(f"  cloudflared tunnel --config {config_file} run strap722")
    log(f"\nOr run in background:")
    log(f"  nohup cloudflared tunnel --config {config_file} run strap722 &")
    
    return True

if __name__ == "__main__":
    main()
