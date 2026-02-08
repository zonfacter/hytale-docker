#!/bin/bash
#===============================================================================
# Hytale Server Wrapper Script
# Runs the server in a screen session for console command support
#===============================================================================

set -euo pipefail

HYTALE_DIR="${HYTALE_DIR:-/opt/hytale-server}"
SCREEN_NAME="hytale"
COMMAND_FILE="${HYTALE_DIR}/.server_command"
CHECK_INTERVAL="${HYTALE_SETUP_WAIT_SECONDS:-5}"

cd "$HYTALE_DIR"

server_files_present() {
    [[ -f "Server/HytaleServer.jar" && -f "Assets.zip" ]]
}

# Verify machine-id is set (required for Hytale auth credential encryption)
if [ -f /etc/machine-id ]; then
    echo "[wrapper] Machine-id available for auth encryption"
else
    echo "[wrapper] WARNING: /etc/machine-id not found - credentials may not persist!"
fi

# Create command file for receiving commands
touch "$COMMAND_FILE"
chmod 660 "$COMMAND_FILE"

# Function to send command to server
send_command() {
    if screen -list | grep -q "$SCREEN_NAME"; then
        screen -S "$SCREEN_NAME" -p 0 -X stuff "$1\n"
        echo "[wrapper] Sent command: $1"
    else
        echo "[wrapper] Server not running"
    fi
}

# Cleanup function
cleanup() {
    echo "[wrapper] Shutting down server..."
    if screen -list | grep -q "$SCREEN_NAME"; then
        screen -S "$SCREEN_NAME" -p 0 -X stuff "/stop\n"
        sleep 5
        screen -S "$SCREEN_NAME" -X quit 2>/dev/null || true
    fi
    rm -f "$COMMAND_FILE"
    exit 0
}

trap cleanup SIGTERM SIGINT

# Start server in screen session
start_server_screen() {
    echo "[wrapper] Starting Hytale Server in screen session..."
    mkdir -p logs
    screen -dmS "$SCREEN_NAME" bash -c "cd $HYTALE_DIR && ./start.sh 2>&1 | tee -a logs/server.log"

    # Wait for screen to start
    sleep 2

    if ! screen -list | grep -q "$SCREEN_NAME"; then
        echo "[wrapper] ERROR: Failed to start server in screen"
        return 1
    fi

    echo "[wrapper] Server started in screen session '$SCREEN_NAME'"
    echo "[wrapper] To send commands, write to: $COMMAND_FILE"
    return 0
}

# Main loop: avoid supervisor FATAL loops when setup is incomplete.
while true; do
    if ! server_files_present; then
        echo "[wrapper] Server files not found. Waiting for setup (Server/HytaleServer.jar + Assets.zip)..."
        sleep "$CHECK_INTERVAL"
        continue
    fi

    if ! screen -list | grep -q "$SCREEN_NAME"; then
        start_server_screen || {
            sleep "$CHECK_INTERVAL"
            continue
        }
    fi

    # If files disappear (e.g. during maintenance), stop current session and wait.
    if ! server_files_present; then
        echo "[wrapper] Server files disappeared, stopping running session..."
        screen -S "$SCREEN_NAME" -X quit 2>/dev/null || true
        sleep "$CHECK_INTERVAL"
        continue
    fi

    # Read and execute commands from command file
    if [ -s "$COMMAND_FILE" ]; then
        while IFS= read -r cmd; do
            if [ -n "$cmd" ]; then
                send_command "$cmd"
            fi
        done < "$COMMAND_FILE"
        > "$COMMAND_FILE"
    fi

    # Restart screen if server stopped unexpectedly
    if ! screen -list | grep -q "$SCREEN_NAME"; then
        echo "[wrapper] Server stopped unexpectedly, retrying..."
        sleep "$CHECK_INTERVAL"
        continue
    fi

    sleep 1
done
