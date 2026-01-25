#!/bin/bash
#===============================================================================
# Hytale Server Start Script (with FIFO console pipe)
#===============================================================================

cd /opt/hytale-server

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

# Create FIFO pipe if not exists
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
    rm -f "$PIPE"
    kill 0
}
trap cleanup EXIT INT TERM

# Start server with FIFO pipe for stdin
tail -f "$PIPE" | exec java \
    -Xms${HYTALE_MEMORY_MIN:-2G} \
    -Xmx${HYTALE_MEMORY_MAX:-4G} \
    -jar "$SERVER_JAR" \
    --assets "$ASSETS" \
    --bind 0.0.0.0:${HYTALE_PORT:-5520}
