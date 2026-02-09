#!/bin/bash
# Hytale auth token backup/restore helper (Docker compatible)
# Usage:
#   hytale-token.sh backup
#   hytale-token.sh restore <filename.enc>

set -euo pipefail
umask 027

SERVER_DIR="/opt/hytale-server"
BACKUP_DIR="${SERVER_DIR}/backups/auth_tokens"
AUTH_FILE_ROOT="${SERVER_DIR}/auth.enc"
AUTH_FILE_SERVER="${SERVER_DIR}/Server/auth.enc"
AUTH_BACKUP="${SERVER_DIR}/.downloader/auth.enc"
HYTALE_USER="hytale"
HYTALE_GROUP="hytale"

cmd="${1:-}"

json_error() {
  printf '{"ok":false,"error":"%s"}\n' "$1"
  exit 1
}

restart_server() {
  if command -v supervisorctl >/dev/null 2>&1; then
    supervisorctl restart hytale-server >/dev/null 2>&1 || true
    return 0
  fi
  if command -v systemctl >/dev/null 2>&1; then
    systemctl restart hytale.service >/dev/null 2>&1 || true
  fi
}

resolve_auth_file_for_backup() {
  if [[ -f "$AUTH_FILE_ROOT" ]]; then
    echo "$AUTH_FILE_ROOT"
    return 0
  fi
  if [[ -f "$AUTH_FILE_SERVER" ]]; then
    echo "$AUTH_FILE_SERVER"
    return 0
  fi
  if [[ -f "$AUTH_BACKUP" ]]; then
    echo "$AUTH_BACKUP"
    return 0
  fi
  return 1
}

sync_auth_targets() {
  local src="$1"
  cp -f "$src" "$AUTH_FILE_ROOT" 2>/dev/null || true
  cp -f "$src" "$AUTH_FILE_SERVER" 2>/dev/null || true
  cp -f "$src" "$AUTH_BACKUP" 2>/dev/null || true
  chown "${HYTALE_USER}:${HYTALE_GROUP}" "$AUTH_FILE_ROOT" "$AUTH_FILE_SERVER" "$AUTH_BACKUP" 2>/dev/null || true
  chmod 600 "$AUTH_FILE_ROOT" "$AUTH_FILE_SERVER" "$AUTH_BACKUP" 2>/dev/null || true
}

case "$cmd" in
  backup)
    auth_src="$(resolve_auth_file_for_backup)" || json_error "auth.enc nicht gefunden"
    mkdir -p "$BACKUP_DIR"
    ts="$(date +%Y%m%d_%H%M%S)"
    target="${BACKUP_DIR}/auth_${ts}.enc"
    cp -a "$auth_src" "$target"
    chown "${HYTALE_USER}:${HYTALE_GROUP}" "$target" 2>/dev/null || true
    chmod 600 "$target" 2>/dev/null || true
    printf '{"ok":true,"file":"%s"}\n' "$(basename "$target")"
    ;;
  restore)
    name="${2:-}"
    [[ -n "$name" ]] || json_error "Dateiname fehlt"
    [[ "$(basename "$name")" == "$name" ]] || json_error "Ungueltiger Dateiname"
    [[ "$name" == *.enc ]] || json_error "Nur .enc Dateien erlaubt"
    source_file="${BACKUP_DIR}/${name}"
    [[ -f "$source_file" ]] || json_error "Token-Backup nicht gefunden"

    cp -a "$AUTH_FILE_ROOT" "${AUTH_FILE_ROOT}.pre_restore_$(date +%Y%m%d_%H%M%S)" 2>/dev/null || true
    sync_auth_targets "$source_file"
    restart_server

    printf '{"ok":true,"restored":"%s"}\n' "$name"
    ;;
  *)
    json_error "Usage: $0 {backup|restore <file.enc>}"
    ;;
esac
