#!/bin/bash
#===============================================================================
# Tailscale Auto-Connect Script
# This script runs after tailscaled starts to automatically connect if configured
#===============================================================================

set -e

# Wait for tailscaled to be ready
echo "[tailscale-connect] Waiting for tailscaled to be ready..."
for i in {1..10}; do
    if tailscale status &>/dev/null; then
        echo "[tailscale-connect] tailscaled is ready"
        break
    fi
    echo "[tailscale-connect] Waiting... ($i/10)"
    sleep 2
done

# Check if we should auto-connect
if [ -z "$TAILSCALE_AUTHKEY" ]; then
    echo "[tailscale-connect] No TAILSCALE_AUTHKEY provided, skipping auto-connect"
    echo "[tailscale-connect] Use the dashboard to connect or run: docker exec <container> tailscale up"
    exit 0
fi

# Build connection command
echo "[tailscale-connect] Connecting to Tailscale network..."

CONNECT_ARGS=("--hostname=${TAILSCALE_HOSTNAME}")
CONNECT_ARGS+=("--authkey=${TAILSCALE_AUTHKEY}")

if [ -n "$TAILSCALE_ADVERTISE_ROUTES" ]; then
    CONNECT_ARGS+=("--advertise-routes=${TAILSCALE_ADVERTISE_ROUTES}")
fi

# Execute tailscale up
if tailscale up "${CONNECT_ARGS[@]}"; then
    echo "[tailscale-connect] ✓ Successfully connected to Tailscale"
    
    # Wait a moment for IP assignment
    sleep 2
    
    # Display connection info
    TAILSCALE_IP=$(tailscale ip -4 2>/dev/null || echo "")
    if [ -n "$TAILSCALE_IP" ]; then
        echo "╔════════════════════════════════════════════════════════════════╗"
        echo "║  Tailscale Connected                                           ║"
        echo "║  IP: ${TAILSCALE_IP}"
        echo "║  Hostname: ${TAILSCALE_HOSTNAME}"
        echo "║  Players can connect via: ${TAILSCALE_IP}:${HYTALE_PORT}"
        echo "╚════════════════════════════════════════════════════════════════╝"
    fi
else
    echo "[tailscale-connect] ✗ Failed to connect to Tailscale"
    echo "[tailscale-connect] You can try manually: docker exec <container> tailscale up"
    exit 1
fi
