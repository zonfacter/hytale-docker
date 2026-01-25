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

# Prepare supervisord configuration in writable location
# This allows the configuration to work in read-only containers
SUPERVISOR_CONFIG_DIR="/tmp/supervisor"
SUPERVISOR_CONFIG="${SUPERVISOR_CONFIG_DIR}/supervisord.conf"
mkdir -p "${SUPERVISOR_CONFIG_DIR}"

# Copy base configuration to writable location
cp /etc/supervisor/conf.d/supervisord.conf "${SUPERVISOR_CONFIG}"

# Check if server is installed
SERVER_JAR="${HYTALE_DIR}/Server/HytaleServer.jar"
ASSETS_ZIP="${HYTALE_DIR}/Assets.zip"

if [ -f "$SERVER_JAR" ] && [ -f "$ASSETS_ZIP" ]; then
    echo "[entrypoint] Hytale Server found - enabling auto-start"
    # Enable server in supervisord configuration (in writable location)
    sed -i 's/autostart=false/autostart=true/' "${SUPERVISOR_CONFIG}"
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

# Export config path for supervisord
export SUPERVISOR_CONFIG

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
# If supervisord is being started, use the config from writable location
if [ "$1" = "supervisord" ] || [ "$1" = "/usr/bin/supervisord" ]; then
    shift  # Remove 'supervisord' from arguments
    # Filter out any existing -c argument and its value
    ARGS=()
    while [ $# -gt 0 ]; do
        if [ "$1" = "-c" ]; then
            shift  # Skip -c
            if [ $# -gt 0 ]; then
                shift  # Skip its argument if it exists
            fi
        else
            ARGS+=("$1")
            shift
        fi
    done
    # Start supervisord with config from writable location
    if [ ${#ARGS[@]} -gt 0 ]; then
        exec supervisord -c "${SUPERVISOR_CONFIG}" "${ARGS[@]}"
    else
        exec supervisord -c "${SUPERVISOR_CONFIG}"
    fi
else
    exec "$@"
fi
