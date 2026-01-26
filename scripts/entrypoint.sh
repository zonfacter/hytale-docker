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

# Create directories if not exists (before setting permissions)
echo "[entrypoint] Ensuring directory structure..."
mkdir -p ${HYTALE_DIR}/logs
mkdir -p ${HYTALE_DIR}/mods
mkdir -p ${HYTALE_DIR}/backups
mkdir -p ${HYTALE_DIR}/.downloader
mkdir -p /var/log/supervisor

# Setup persistent machine-id for Hytale auth credential encryption
# The server derives the encryption key from /etc/machine-id
# Store in .downloader volume so it persists across container recreations
echo "[entrypoint] Setting up persistent machine-id..."
PERSISTENT_MACHINE_ID="${HYTALE_DIR}/.downloader/.machine-id"
if [ ! -f "$PERSISTENT_MACHINE_ID" ]; then
    echo "[entrypoint] Generating new persistent machine-id..."
    # Generate a valid machine-id format (32 hex characters)
    cat /proc/sys/kernel/random/uuid | tr -d '-' | head -c 32 > "$PERSISTENT_MACHINE_ID"
    echo "" >> "$PERSISTENT_MACHINE_ID"
    chmod 444 "$PERSISTENT_MACHINE_ID"
fi
# Apply to system (needed for Hytale EncryptedAuthCredentialStore)
cp "$PERSISTENT_MACHINE_ID" /etc/machine-id 2>/dev/null || true
mkdir -p /var/lib/dbus 2>/dev/null || true
cp "$PERSISTENT_MACHINE_ID" /var/lib/dbus/machine-id 2>/dev/null || true
echo "[entrypoint] Machine-id: $(cat $PERSISTENT_MACHINE_ID | head -c 8)..."

# Ensure scripts are executable (in case permissions were lost)
echo "[entrypoint] Ensuring script permissions..."
chmod +x ${HYTALE_DIR}/start.sh 2>/dev/null || true
chmod +x /usr/local/bin/hytale-*.sh 2>/dev/null || true

# Verify start.sh is executable (critical for supervisord)
if [ -f "${HYTALE_DIR}/start.sh" ]; then
    if [ ! -x "${HYTALE_DIR}/start.sh" ]; then
        echo "[entrypoint] WARNING: start.sh is not executable, fixing..."
        chmod +x ${HYTALE_DIR}/start.sh
    fi
    echo "[entrypoint] start.sh permissions: $(ls -la ${HYTALE_DIR}/start.sh)"
else
    echo "[entrypoint] WARNING: start.sh not found at ${HYTALE_DIR}/start.sh"
fi

# Fix permissions for volumes
echo "[entrypoint] Setting up permissions..."
chown -R hytale:hytale ${HYTALE_DIR}/universe || true
chown -R hytale:hytale ${HYTALE_DIR}/mods || true
chown -R hytale:hytale ${HYTALE_DIR}/backups || true
chown -R hytale:hytale ${HYTALE_DIR}/.downloader || true
chown -R hytale:hytale ${HYTALE_DIR}/logs || true

# Create default world config directory structure if not exists
# (needed because the 'universe' volume overrides what Dockerfile created)
WORLD_CONFIG_DIR="${HYTALE_DIR}/universe/worlds/default"
WORLD_CONFIG_FILE="${WORLD_CONFIG_DIR}/config.json"
if [ ! -d "$WORLD_CONFIG_DIR" ]; then
    echo "[entrypoint] Creating default world directory structure..."
    mkdir -p "$WORLD_CONFIG_DIR"
    chown -R hytale:hytale "${HYTALE_DIR}/universe"
fi
if [ ! -f "$WORLD_CONFIG_FILE" ]; then
    echo "[entrypoint] Creating default world config..."
    cat > "$WORLD_CONFIG_FILE" << 'EOFCONFIG'
{
  "Version": 1,
  "Name": "default",
  "GameMode": "Adventure",
  "Seed": "",
  "WorldGenerator": {
    "Type": "Hytale"
  }
}
EOFCONFIG
    chown hytale:hytale "$WORLD_CONFIG_FILE"
fi

# Copy download script to volume (needed for dashboard setup wizard)
if [ -f "/usr/local/bin/hytale-download.sh" ]; then
    cp /usr/local/bin/hytale-download.sh "${HYTALE_DIR}/.downloader/download.sh"
    chown hytale:hytale "${HYTALE_DIR}/.downloader/download.sh"
    chmod +x "${HYTALE_DIR}/.downloader/download.sh"
fi

# Try to fetch downloader if not present
echo "[entrypoint] Checking Hytale downloader..."
DOWNLOADER_BIN="${HYTALE_DIR}/.downloader/hytale-downloader-linux-amd64"
if [ ! -f "$DOWNLOADER_BIN" ]; then
    echo "[entrypoint] Downloader not found, attempting automatic fetch..."
    if [ -f "/usr/local/bin/hytale-fetch-downloader.sh" ]; then
        # Run fetch script with environment variables
        export DOWNLOADER_DIR="${HYTALE_DIR}/.downloader"
        export DOWNLOADER_BIN="$DOWNLOADER_BIN"
        if gosu hytale bash /usr/local/bin/hytale-fetch-downloader.sh; then
            echo "[entrypoint] Downloader fetch completed successfully"
        else
            EXIT_CODE=$?
            echo "[entrypoint] Downloader fetch exited with code ${EXIT_CODE}"
            echo "[entrypoint] Manual upload still possible via volume mount"
            echo "[entrypoint] See setup instructions at http://localhost:${DASHBOARD_PORT}/setup"
        fi
    else
        echo "[entrypoint] Fetch script not found"
    fi
else
    echo "[entrypoint] Downloader already present"
fi

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
