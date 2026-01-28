"""
Tailscale VPN API Routes for Docker deployment.
These routes provide Tailscale integration for the dashboard.
"""

import os
import json
import subprocess
from pathlib import Path
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter()

# Check if Tailscale is enabled
TAILSCALE_ENABLED = os.environ.get("TAILSCALE_ENABLED", "false").lower() == "true"


def run_tailscale_cmd(args: list, timeout: int = 10) -> tuple[str, int]:
    """Run a Tailscale command and return (stdout, returncode)."""
    try:
        result = subprocess.run(
            ["tailscale"] + args,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return result.stdout.strip(), result.returncode
    except subprocess.TimeoutExpired:
        return "Command timed out", 1
    except FileNotFoundError:
        return "Tailscale not found", 127
    except Exception as e:
        return str(e), 1


@router.get("/api/tailscale/status")
async def tailscale_status():
    """Get Tailscale connection status."""
    if not TAILSCALE_ENABLED:
        return JSONResponse({
            "enabled": False,
            "connected": False,
            "message": "Tailscale is not enabled. Set TAILSCALE_ENABLED=true to enable."
        })
    
    # Get JSON status
    output, returncode = run_tailscale_cmd(["status", "--json"])
    
    if returncode == 0:
        try:
            status_data = json.loads(output)
            
            # Extract relevant information
            backend_state = status_data.get("BackendState", "")
            self_info = status_data.get("Self", {})
            
            response = {
                "enabled": True,
                "connected": backend_state == "Running",
                "backend_state": backend_state,
                "hostname": self_info.get("HostName", ""),
                "tailscale_ips": self_info.get("TailscaleIPs", []),
                "online": self_info.get("Online", False),
                "peers": len(status_data.get("Peer", {})),
            }
            
            return JSONResponse(response)
        except json.JSONDecodeError:
            return JSONResponse({
                "enabled": True,
                "connected": False,
                "error": "Failed to parse Tailscale status"
            })
    else:
        return JSONResponse({
            "enabled": True,
            "connected": False,
            "error": output
        })


@router.get("/api/tailscale/ip")
async def tailscale_ip():
    """Get Tailscale IP address."""
    if not TAILSCALE_ENABLED:
        return JSONResponse({
            "enabled": False,
            "ip": None,
            "message": "Tailscale is not enabled"
        })
    
    output, returncode = run_tailscale_cmd(["ip", "-4"])
    
    if returncode == 0 and output:
        return JSONResponse({
            "enabled": True,
            "ip": output,
            "ipv4": output
        })
    
    # Try IPv6 as fallback
    output_v6, returncode_v6 = run_tailscale_cmd(["ip", "-6"])
    
    if returncode_v6 == 0 and output_v6:
        return JSONResponse({
            "enabled": True,
            "ip": output_v6,
            "ipv6": output_v6,
            "message": "Only IPv6 available"
        })
    
    return JSONResponse({
        "enabled": True,
        "ip": None,
        "error": "Not connected or no IP assigned"
    })


@router.post("/api/tailscale/up")
async def tailscale_up(request: Request):
    """Start Tailscale connection."""
    if not TAILSCALE_ENABLED:
        return JSONResponse({
            "success": False,
            "message": "Tailscale is not enabled. Set TAILSCALE_ENABLED=true to enable."
        }, status_code=400)
    
    body = await request.json() if request.headers.get("content-type") == "application/json" else {}
    
    # Build command
    cmd_args = ["up"]
    
    # Add hostname
    hostname = body.get("hostname") or os.environ.get("TAILSCALE_HOSTNAME", "hytale-server")
    cmd_args.extend(["--hostname", hostname])
    
    # Add authkey if provided
    authkey = body.get("authkey") or os.environ.get("TAILSCALE_AUTHKEY", "")
    if authkey:
        cmd_args.extend(["--authkey", authkey])
    
    # Add advertise routes if provided
    routes = body.get("advertise_routes") or os.environ.get("TAILSCALE_ADVERTISE_ROUTES", "")
    if routes:
        cmd_args.extend(["--advertise-routes", routes])
    
    output, returncode = run_tailscale_cmd(cmd_args, timeout=30)
    
    if returncode == 0:
        return JSONResponse({
            "success": True,
            "message": "Tailscale connection started",
            "output": output
        })
    else:
        return JSONResponse({
            "success": False,
            "message": "Failed to start Tailscale",
            "error": output
        }, status_code=500)


@router.post("/api/tailscale/down")
async def tailscale_down():
    """Stop Tailscale connection."""
    if not TAILSCALE_ENABLED:
        return JSONResponse({
            "success": False,
            "message": "Tailscale is not enabled"
        }, status_code=400)
    
    output, returncode = run_tailscale_cmd(["down"])
    
    if returncode == 0:
        return JSONResponse({
            "success": True,
            "message": "Tailscale connection stopped"
        })
    else:
        return JSONResponse({
            "success": False,
            "message": "Failed to stop Tailscale",
            "error": output
        }, status_code=500)
