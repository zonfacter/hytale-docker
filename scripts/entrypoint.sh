#!/bin/bash
#===============================================================================
# Docker Entrypoint Script
# Prepares the environment and starts services
#===============================================================================

set -e

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║           HYTALE SERVER + DASHBOARD (Docker)                   ║"
echo "║           https://github.com/zonfacter/hytale-docker           ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Fix permissions for volumes
echo "[entrypoint] Setting up permissions..."
chown -R hytale:hytale ${HYTALE_DIR}/universe || true
chown -R hytale:hytale ${HYTALE_DIR}/mods || true
chown -R hytale:hytale ${HYTALE_DIR}/backups || true
chown -R hytale:hytale ${HYTALE_DIR}/.downloader || true
chown -R hytale:hytale ${HYTALE_DIR}/logs || true

# Try to fetch downloader if not present
echo "[entrypoint] Checking Hytale downloader..."
if [ -f "${HYTALE_DIR}/.downloader/fetch.sh" ]; then
    if gosu hytale bash "${HYTALE_DIR}/.downloader/fetch.sh"; then
        echo "[entrypoint] Downloader check completed successfully"
    else
        EXIT_CODE=$?
        echo "[entrypoint] Downloader fetch script exited with code ${EXIT_CODE}"
        echo "[entrypoint] This is normal if downloader is not yet available"
        echo "[entrypoint] See setup instructions in dashboard at http://localhost:${DASHBOARD_PORT}/setup"
    fi
fi

# Create log directory if not exists
mkdir -p ${HYTALE_DIR}/logs
mkdir -p /var/log/supervisor

# Check if server is installed
SERVER_JAR="${HYTALE_DIR}/Server/HytaleServer.jar"
ASSETS_ZIP="${HYTALE_DIR}/Assets.zip"

if [ -f "$SERVER_JAR" ] && [ -f "$ASSETS_ZIP" ]; then
    echo "[entrypoint] Hytale Server found - enabling auto-start"
    # Enable server in supervisord
    sed -i 's/autostart=false/autostart=true/' /etc/supervisor/conf.d/supervisord.conf
else
    echo ""
    echo "╔════════════════════════════════════════════════════════════════╗"
    echo "║  HYTALE SERVER NICHT GEFUNDEN / SERVER NOT FOUND              ║"
    echo "╠════════════════════════════════════════════════════════════════╣"
    echo "║                                                                ║"
    echo "║  Bitte das Dashboard öffnen für die Ersteinrichtung:          ║"
    echo "║  Please open the Dashboard for initial setup:                 ║"
    echo "║                                                                ║"
    echo "║  → http://localhost:${DASHBOARD_PORT}/setup                   ║"
    echo "║                                                                ║"
    echo "╚════════════════════════════════════════════════════════════════╝"
    echo ""
fi

# Create console pipe if not exists
# Note: Named Pipes (FIFO) may have compatibility issues in some environments
# (e.g., certain storage drivers, Kubernetes, Windows). For details and alternatives,
# see: docs/ipc-mechanisms.md
CONSOLE_PIPE="${HYTALE_DIR}/.console_pipe"
if [ ! -p "$CONSOLE_PIPE" ]; then
    echo "[entrypoint] Creating console pipe..."
    mkfifo "$CONSOLE_PIPE"
    chown hytale:hytale "$CONSOLE_PIPE"
    chmod 660 "$CONSOLE_PIPE"
fi

echo "[entrypoint] Starting services..."
echo ""

# Execute the main command
exec "$@"
