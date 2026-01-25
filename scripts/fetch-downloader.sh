#!/bin/bash
#===============================================================================
# Hytale Downloader Fetch Script
# Attempts to automatically download the Hytale downloader if URL is provided
#===============================================================================

set -e

# Configuration
DOWNLOADER_DIR="${DOWNLOADER_DIR:-/opt/hytale-server/.downloader}"
DOWNLOADER_BIN="${DOWNLOADER_BIN:-${DOWNLOADER_DIR}/hytale-downloader-linux-amd64}"
DOWNLOADER_URL="${HYTALE_DOWNLOADER_URL:-}"
MIN_FILE_SIZE="${MIN_FILE_SIZE:-1000000}"  # Minimum expected file size (1MB)

log() {
    echo "[fetch-downloader] $1"
}

# Check if downloader already exists
if [ -f "$DOWNLOADER_BIN" ]; then
    log "✓ Downloader bereits vorhanden / Downloader already present"
    chmod +x "$DOWNLOADER_BIN"
    exit 0
fi

# Check if URL is provided
if [ -z "$DOWNLOADER_URL" ]; then
    log "⚠ HYTALE_DOWNLOADER_URL nicht gesetzt / not set"
    log ""
    log "═══════════════════════════════════════════════════════════════"
    log "HYTALE DOWNLOADER ERFORDERLICH / DOWNLOADER REQUIRED"
    log "═══════════════════════════════════════════════════════════════"
    log ""
    log "Der Downloader kann nicht automatisch heruntergeladen werden."
    log "The downloader cannot be downloaded automatically."
    log ""
    log "Option 1: Manuelle Installation / Manual Installation"
    log "  1. Besuche / Visit: https://hytale.com/"
    log "  2. Lade 'hytale-downloader-linux-amd64' herunter / Download"
    log "  3. Kopiere nach / Copy to:"
    log "     ./data/downloader/hytale-downloader-linux-amd64"
    log ""
    log "Option 2: Automatischer Download / Automatic Download"
    log "  Setze die Umgebungsvariable / Set environment variable:"
    log "  HYTALE_DOWNLOADER_URL=https://your-url/hytale-downloader-linux-amd64"
    log ""
    log "  Beispiel in docker-compose.yml:"
    log "  environment:"
    log "    - HYTALE_DOWNLOADER_URL=https://example.com/downloader"
    log ""
    log "═══════════════════════════════════════════════════════════════"
    log ""
    exit 1
fi

# URL is provided, attempt download
log "Lade Downloader herunter von / Downloading downloader from:"
log "$DOWNLOADER_URL"
log ""

# Create directory if not exists
mkdir -p "$DOWNLOADER_DIR"

# Download with wget or curl
if command -v wget &> /dev/null; then
    log "Verwende wget / Using wget..."
    wget -O "$DOWNLOADER_BIN" "$DOWNLOADER_URL" || {
        log "✗ Download mit wget fehlgeschlagen / wget download failed"
        exit 1
    }
elif command -v curl &> /dev/null; then
    log "Verwende curl / Using curl..."
    curl -L -o "$DOWNLOADER_BIN" "$DOWNLOADER_URL" || {
        log "✗ Download mit curl fehlgeschlagen / curl download failed"
        exit 1
    }
else
    log "✗ Weder wget noch curl verfügbar / Neither wget nor curl available"
    exit 1
fi

# Verify download
if [ ! -f "$DOWNLOADER_BIN" ]; then
    log "✗ Downloader-Datei nicht gefunden nach Download"
    log "✗ Downloader file not found after download"
    exit 1
fi

# Check file size (should be at least MIN_FILE_SIZE for a valid binary)
# Try GNU stat first, then BSD stat, with proper error handling
FILE_SIZE=0
if stat --version >/dev/null 2>&1; then
    # GNU stat
    FILE_SIZE=$(stat -c%s "$DOWNLOADER_BIN" 2>/dev/null || echo "0")
else
    # BSD stat (macOS)
    FILE_SIZE=$(stat -f%z "$DOWNLOADER_BIN" 2>/dev/null || echo "0")
fi

if [ "$FILE_SIZE" -lt "$MIN_FILE_SIZE" ]; then
    log "✗ Downloader-Datei ist zu klein (${FILE_SIZE} bytes, erwartet: >${MIN_FILE_SIZE})"
    log "✗ Downloader file is too small (${FILE_SIZE} bytes, expected: >${MIN_FILE_SIZE})"
    log "Möglicherweise ungültige URL oder Fehlerseite heruntergeladen"
    log "Possibly invalid URL or error page downloaded"
    rm -f "$DOWNLOADER_BIN"
    exit 1
fi

# Make executable
chmod +x "$DOWNLOADER_BIN"

log ""
log "✓ Downloader erfolgreich heruntergeladen / successfully downloaded"
log "✓ Größe / Size: ${FILE_SIZE} bytes"
log ""

exit 0
