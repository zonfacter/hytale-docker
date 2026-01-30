#!/bin/bash
#===============================================================================
# Hytale Server Start Script (with FIFO console pipe)
#
# This script uses a Named Pipe (FIFO) for console input, allowing the
# dashboard to send commands to the server. Named Pipes may have compatibility
# issues in certain environments (storage drivers, Kubernetes, Windows).
# For detailed documentation and alternative IPC mechanisms, see:
# docs/ipc-mechanisms.md
#
# IMPORTANT: Since Hytale Server 2026.01, the server must run from the Server/
# subdirectory. Universe data is stored in Server/universe/ (not /universe/).
#===============================================================================

HYTALE_DIR="/opt/hytale-server"
cd "$HYTALE_DIR"

PIPE=".console_pipe"
SERVER_JAR="Server/HytaleServer.jar"
ASSETS="Assets.zip"

# Check if server files exist
if [ ! -f "$SERVER_JAR" ]; then
    echo "[start.sh] ERROR: Server JAR not found: $SERVER_JAR"
    echo "[start.sh] Please download the server first via Dashboard -> Setup"
    exit 1
fi

if [ ! -f "$ASSETS" ]; then
    echo "[start.sh] ERROR: Assets not found: $ASSETS"
    exit 1
fi

# Create FIFO pipe if not exists (in HYTALE_DIR, not Server/)
# Note: Named Pipes (FIFO) may have compatibility issues in some environments.
# See docs/ipc-mechanisms.md for troubleshooting and alternatives.
if [ ! -p "$PIPE" ]; then
    mkfifo "$PIPE"
    chmod 660 "$PIPE"
fi

echo "[start.sh] Starting Hytale Server..."
echo "[start.sh] Memory: ${HYTALE_MEMORY_MIN} - ${HYTALE_MEMORY_MAX}"
echo "[start.sh] Port: ${HYTALE_PORT:-5520}"

# Cleanup on exit
cleanup() {
    echo "[start.sh] Shutting down..."
    rm -f "$HYTALE_DIR/$PIPE"
    kill 0
}
trap cleanup EXIT INT TERM

# Change to Server directory (required since Hytale 2026.01)
# This ensures universe data is created in Server/universe/
cd "$HYTALE_DIR/Server"

# Start server with FIFO pipe for stdin
# Note: Assets path is relative to HYTALE_DIR (parent directory)
tail -f "$HYTALE_DIR/$PIPE" | exec java \
    -Xms${HYTALE_MEMORY_MIN:-2G} \
    -Xmx${HYTALE_MEMORY_MAX:-4G} \
    -jar "HytaleServer.jar" \
    --assets "../$ASSETS" \
    --bind 0.0.0.0:${HYTALE_PORT:-5520}
