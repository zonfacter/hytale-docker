#!/bin/bash
#===============================================================================
# Hytale Server Wrapper Script
# Runs the server in a screen session for console command support
#===============================================================================

HYTALE_DIR="${HYTALE_DIR:-/opt/hytale-server}"
SCREEN_NAME="hytale"
COMMAND_FILE="${HYTALE_DIR}/.server_command"

cd "$HYTALE_DIR"

# Check if server files exist
if [ ! -f "Server/HytaleServer.jar" ] || [ ! -f "Assets.zip" ]; then
    echo "[wrapper] Server files not found. Please run setup first."
    exit 1
fi

# Verify machine-id is set (required for Hytale auth credential encryption)
if [ -f /etc/machine-id ]; then
    echo "[wrapper] Machine-id available for auth encryption"
else
    echo "[wrapper] WARNING: /etc/machine-id not found - credentials may not persist!"
fi

# Create command file for receiving commands
touch "$COMMAND_FILE"
chmod 666 "$COMMAND_FILE"

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
        screen -S "$SCREEN_NAME" -X quit 2>/dev/null
    fi
    rm -f "$COMMAND_FILE"
    exit 0
}

trap cleanup SIGTERM SIGINT

# Start server in screen session
echo "[wrapper] Starting Hytale Server in screen session..."
screen -dmS "$SCREEN_NAME" bash -c "cd $HYTALE_DIR && ./start.sh 2>&1 | tee -a logs/server.log"

# Wait for screen to start
sleep 2

if ! screen -list | grep -q "$SCREEN_NAME"; then
    echo "[wrapper] ERROR: Failed to start server in screen"
    exit 1
fi

echo "[wrapper] Server started in screen session '$SCREEN_NAME'"
echo "[wrapper] To send commands, write to: $COMMAND_FILE"
echo "[wrapper] Or use: screen -S $SCREEN_NAME -p 0 -X stuff 'command\n'"

# Monitor command file and forward commands to server
while true; do
    # Check if screen session still exists
    if ! screen -list | grep -q "$SCREEN_NAME"; then
        echo "[wrapper] Server stopped unexpectedly"
        break
    fi

    # Read and execute commands from command file
    if [ -s "$COMMAND_FILE" ]; then
        while IFS= read -r cmd; do
            if [ -n "$cmd" ]; then
                send_command "$cmd"
            fi
        done < "$COMMAND_FILE"
        # Clear the file
        > "$COMMAND_FILE"
    fi

    sleep 1
done

cleanup
