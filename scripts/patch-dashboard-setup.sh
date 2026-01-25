#!/bin/bash
#===============================================================================
# Patch Dashboard to include Setup Routes
# This script integrates the setup wizard routes into the dashboard app.py
#===============================================================================

set -e

DASHBOARD_DIR=${DASHBOARD_DIR:-/opt/hytale-dashboard}
APP_FILE="$DASHBOARD_DIR/app.py"
SETUP_ROUTES="$DASHBOARD_DIR/setup_routes.py"

echo "[patch] Integrating setup routes into dashboard..."

# Check if files exist
if [ ! -f "$APP_FILE" ]; then
    echo "[patch] ERROR: $APP_FILE not found!"
    exit 1
fi

if [ ! -f "$SETUP_ROUTES" ]; then
    echo "[patch] ERROR: $SETUP_ROUTES not found!"
    exit 1
fi

# Check if already patched
if grep -q "setup_routes" "$APP_FILE"; then
    echo "[patch] Setup routes already integrated - skipping"
    exit 0
fi

# Create a backup
cp "$APP_FILE" "$APP_FILE.backup"

# Append the integration code at the end of app.py
cat >> "$APP_FILE" << 'EOFPATCH'

# ============================================================================
# Setup Routes Integration (Docker deployment)
# ============================================================================
try:
    from setup_routes import router as setup_router
    app.include_router(setup_router)
    print("[Setup] Setup wizard routes integrated successfully")
except Exception as e:
    print(f"[Setup] Warning: Could not integrate setup routes: {e}")
EOFPATCH

echo "[patch] ✓ Setup routes integrated successfully"
exit 0
