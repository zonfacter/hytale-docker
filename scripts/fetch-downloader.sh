#!/bin/bash
#===============================================================================
# Hytale Downloader Fetch Script
# Attempts to automatically download the Hytale downloader if URL is provided
# Supports both direct binary downloads and ZIP archives
#===============================================================================

set -e

# Configuration
DOWNLOADER_DIR="${DOWNLOADER_DIR:-/opt/hytale-server/.downloader}"
DOWNLOADER_BIN="${DOWNLOADER_BIN:-${DOWNLOADER_DIR}/hytale-downloader-linux-amd64}"
DOWNLOADER_URL="${HYTALE_DOWNLOADER_URL:-https://downloader.hytale.com/hytale-downloader.zip}"
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
    log "  HYTALE_DOWNLOADER_URL=https://downloader.hytale.com/hytale-downloader.zip"
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

# Determine if URL is a ZIP file
IS_ZIP=false
if [[ "$DOWNLOADER_URL" == *.zip ]] || [[ "$DOWNLOADER_URL" == *".zip?"* ]]; then
    IS_ZIP=true
    DOWNLOAD_TARGET="${DOWNLOADER_DIR}/hytale-downloader.zip"
else
    DOWNLOAD_TARGET="$DOWNLOADER_BIN"
fi

# Download with wget or curl
download_file() {
    local url="$1"
    local target="$2"

    if command -v wget &> /dev/null; then
        log "Verwende wget / Using wget..."
        wget -q --show-progress -O "$target" "$url" || {
            log "✗ Download mit wget fehlgeschlagen / wget download failed"
            return 1
        }
    elif command -v curl &> /dev/null; then
        log "Verwende curl / Using curl..."
        curl -L -o "$target" "$url" || {
            log "✗ Download mit curl fehlgeschlagen / curl download failed"
            return 1
        }
    else
        log "✗ Weder wget noch curl verfügbar / Neither wget nor curl available"
        return 1
    fi
    return 0
}

# Download the file
if ! download_file "$DOWNLOADER_URL" "$DOWNLOAD_TARGET"; then
    exit 1
fi

# Handle ZIP extraction
if [ "$IS_ZIP" = true ]; then
    log "ZIP-Archiv erkannt, entpacke... / ZIP archive detected, extracting..."

    if ! command -v unzip &> /dev/null; then
        log "✗ unzip nicht verfügbar / unzip not available"
        exit 1
    fi

    # Create temp directory for extraction
    EXTRACT_DIR="${DOWNLOADER_DIR}/.extract_tmp"
    rm -rf "$EXTRACT_DIR"
    mkdir -p "$EXTRACT_DIR"

    # Extract ZIP
    unzip -q "$DOWNLOAD_TARGET" -d "$EXTRACT_DIR" || {
        log "✗ Entpacken fehlgeschlagen / Extraction failed"
        rm -rf "$EXTRACT_DIR"
        exit 1
    }

    # Find the linux-amd64 binary
    FOUND_BIN=""
    for pattern in "hytale-downloader-linux-amd64" "hytale-downloader" "*linux*amd64*" "*downloader*"; do
        FOUND_BIN=$(find "$EXTRACT_DIR" -type f -name "$pattern" 2>/dev/null | head -1)
        if [ -n "$FOUND_BIN" ] && [ -f "$FOUND_BIN" ]; then
            break
        fi
    done

    if [ -z "$FOUND_BIN" ] || [ ! -f "$FOUND_BIN" ]; then
        log "✗ Konnte Downloader-Binary nicht im ZIP finden"
        log "✗ Could not find downloader binary in ZIP"
        log "ZIP-Inhalt / ZIP contents:"
        find "$EXTRACT_DIR" -type f | head -20
        rm -rf "$EXTRACT_DIR"
        exit 1
    fi

    log "Gefunden / Found: $(basename "$FOUND_BIN")"

    # Move binary to correct location
    mv "$FOUND_BIN" "$DOWNLOADER_BIN"

    # Cleanup
    rm -rf "$EXTRACT_DIR"
    rm -f "$DOWNLOAD_TARGET"

    log "✓ ZIP entpackt und aufgeräumt / ZIP extracted and cleaned up"
fi

# Verify download
if [ ! -f "$DOWNLOADER_BIN" ]; then
    log "✗ Downloader-Datei nicht gefunden nach Download"
    log "✗ Downloader file not found after download"
    exit 1
fi

# Check file size (should be at least MIN_FILE_SIZE for a valid binary)
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
