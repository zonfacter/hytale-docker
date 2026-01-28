#!/bin/bash
#===============================================================================
# Patch Dashboard to include Tailscale Routes
# This script integrates the Tailscale VPN routes into the dashboard app.py
#===============================================================================

set -e

DASHBOARD_DIR=${DASHBOARD_DIR:-/opt/hytale-dashboard}
APP_FILE="$DASHBOARD_DIR/app.py"
TAILSCALE_ROUTES="$DASHBOARD_DIR/tailscale_routes.py"

echo "[patch] Integrating Tailscale routes into dashboard..."

# Check if files exist
if [ ! -f "$APP_FILE" ]; then
    echo "[patch] ERROR: $APP_FILE not found!"
    exit 1
fi

if [ ! -f "$TAILSCALE_ROUTES" ]; then
    echo "[patch] ERROR: $TAILSCALE_ROUTES not found!"
    exit 1
fi

# Check if already patched
if grep -q "tailscale_routes" "$APP_FILE"; then
    echo "[patch] Tailscale routes already integrated - skipping"
    exit 0
fi

# Validate that 'app' variable exists (FastAPI instance)
if ! grep -q "app\s*=\s*FastAPI\|app\s*=\s*fastapi\.FastAPI\|^app\s*:" "$APP_FILE"; then
    echo "[patch] WARNING: Could not find FastAPI app instance in $APP_FILE"
    echo "[patch] The integration might fail at runtime"
fi

# Create a backup if not exists
if [ ! -f "$APP_FILE.backup" ]; then
    cp "$APP_FILE" "$APP_FILE.backup"
fi

# Append the integration code at the end of app.py
cat >> "$APP_FILE" << 'EOFPATCH'

# ============================================================================
# Tailscale Routes Integration (Docker deployment)
# ============================================================================
try:
    from tailscale_routes import router as tailscale_router
    app.include_router(tailscale_router)
    print("[Tailscale] Tailscale VPN routes integrated successfully")
except (ImportError, AttributeError, NameError) as e:
    print(f"[Tailscale] Warning: Could not integrate Tailscale routes: {e}")
except Exception as e:
    print(f"[Tailscale] Error: Unexpected error during Tailscale routes integration: {e}")
EOFPATCH

echo "[patch] ✓ Tailscale routes integrated successfully"
exit 0
