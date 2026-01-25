#!/bin/bash
#===============================================================================
# Hytale Server Download Script
# Called from Dashboard Setup Wizard
#===============================================================================

cd /opt/hytale-server/.downloader

DOWNLOADER="./hytale-downloader-linux-amd64"
CREDENTIALS=".hytale-downloader-credentials.json"
DOWNLOAD_PATH="game.zip"
EXTRACT_PATH="/opt/hytale-server"

LOG_FILE="/opt/hytale-server/logs/download.log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Check if downloader exists
if [ ! -f "$DOWNLOADER" ]; then
    log "ERROR: Downloader nicht gefunden / Downloader not found"
    log ""
    log "Bitte den Hytale Downloader herunterladen:"
    log "Please download the Hytale Downloader:"
    log ""
    log "1. Besuche / Visit: https://hytale.com/"
    log "2. Lade 'hytale-downloader-linux-amd64' herunter"
    log "3. Kopiere die Datei nach / Copy file to:"
    log "   ./data/downloader/hytale-downloader-linux-amd64"
    log ""
    log "Dann starte den Download erneut."
    log "Then restart the download."
    exit 1
fi

chmod +x "$DOWNLOADER"

log "════════════════════════════════════════════════════════════════"
log "HYTALE SERVER DOWNLOAD"
log "════════════════════════════════════════════════════════════════"
log ""

# Check for existing credentials
if [ -f "$CREDENTIALS" ]; then
    log "Credentials gefunden / Credentials found"
else
    log "Keine Credentials gefunden - OAuth erforderlich"
    log "No credentials found - OAuth required"
    log ""
    log "══════════════════════════════════════════════════════════════"
    log "WICHTIG / IMPORTANT:"
    log "══════════════════════════════════════════════════════════════"
    log ""
    log "Der Downloader wird gleich einen OAuth-Link ausgeben."
    log "The downloader will output an OAuth link."
    log ""
    log "Bitte den Link kopieren und im Browser öffnen!"
    log "Please copy the link and open it in your browser!"
    log ""
    log "══════════════════════════════════════════════════════════════"
    log ""
fi

# Run downloader
log "Starte Download / Starting download..."
log ""

"$DOWNLOADER" \
    -download-path "$DOWNLOAD_PATH" \
    -credentials-path "$CREDENTIALS" \
    2>&1 | tee -a "$LOG_FILE"

RESULT=${PIPESTATUS[0]}

if [ $RESULT -ne 0 ]; then
    log ""
    log "ERROR: Download fehlgeschlagen (Exit Code: $RESULT)"
    log "ERROR: Download failed (Exit Code: $RESULT)"
    exit $RESULT
fi

# Check if download was successful
if [ ! -f "$DOWNLOAD_PATH" ]; then
    log "ERROR: game.zip nicht gefunden / game.zip not found"
    exit 1
fi

log ""
log "Download erfolgreich / Download successful"
log "Entpacke Server / Extracting server..."

# Extract
cd "$EXTRACT_PATH"
unzip -o ".downloader/$DOWNLOAD_PATH" 2>&1 | tee -a "$LOG_FILE"

if [ $? -ne 0 ]; then
    log "ERROR: Entpacken fehlgeschlagen / Extraction failed"
    exit 1
fi

# Verify installation
if [ -f "Server/HytaleServer.jar" ] && [ -f "Assets.zip" ]; then
    log ""
    log "════════════════════════════════════════════════════════════════"
    log "INSTALLATION ERFOLGREICH / INSTALLATION SUCCESSFUL"
    log "════════════════════════════════════════════════════════════════"
    log ""

    # Make start.sh executable (Hytale package includes its own start.sh)
    if [ -f "start.sh" ]; then
        chmod +x start.sh
        log "✓ start.sh ausführbar gemacht / start.sh made executable"
    fi

    # Signal to supervisord to enable server
    touch "$EXTRACT_PATH/.server_installed"

    # Try to start the server via supervisorctl
    log "Starte Server automatisch / Starting server automatically..."
    if supervisorctl start hytale-server 2>&1 | tee -a "$LOG_FILE"; then
        log ""
        log "✓ Server gestartet / Server started"
        log ""
    else
        log ""
        log "⚠ Konnte Server nicht automatisch starten"
        log "⚠ Could not start server automatically"
        log "Bitte manuell starten / Please start manually:"
        log "  supervisorctl start hytale-server"
        log ""
    fi

    log "Bitte das Dashboard neu laden."
    log "Please reload the Dashboard."
    log ""

    exit 0
else
    log "ERROR: Server-Dateien nicht gefunden / Server files not found"
    exit 1
fi
