#!/usr/bin/env bash
set -euo pipefail

STACK_DIR="/opt/hytale-docker"   # Pfad zu deinem hytale-docker checkout
SERVICE="hytale"                  # Service-Name in docker-compose.yml
BASE_URL="http://127.0.0.1:8088"
DASH_USER="admin"
DASH_PASS="changeme"

need_cmd() {
  command -v "" >/dev/null 2>&1 || {
    echo "Fehlt: " >&2
    exit 1
  }
}

need_cmd docker
need_cmd curl
need_cmd jq

cd ""

echo "[1/8] Preflight"
docker --version
docker compose version
docker compose config >/tmp/hytale-compose-rendered.yml

echo "[2/8] Pull latest images + restart stack"
docker compose pull
docker compose up -d --remove-orphans

echo "[3/8] Wait for container health"
for i in {1..60}; do
  STATUS=""
  if [[ "" == "healthy" ]]; then
    echo "Container healthy"
    break
  fi
  sleep 3
done

echo "[4/8] Basic HTTP checks"
curl -fsS "/" >/dev/null
curl -fsS "/setup" >/dev/null
curl -fsS "/metrics" | head -n 5

echo "[5/8] Authenticated API checks"
AUTH="-u :"
curl -fsS  "/api/status" | jq '.service.ActiveState, .allow_control'
curl -fsS  "/api/backups/list" | jq '.backups | length'
curl -fsS  "/api/auth/status" | jq '.token_configured, .session_ready'
curl -fsS  "/api/performance" | jq '.cpu_percent, .ram_mb, .view_radius'

echo "[6/8] Backup create smoke test"
curl -fsS  -X POST "/api/backups/create" \
  -H "Content-Type: application/json" \
  -d '{"label":"smoke-test","comment":"post-release check"}' | jq '.ok, .output'

echo "[7/8] Logs quick scan"
docker compose logs --tail=120 "" | grep -Ei "error|traceback|exception|failed" || true

echo "[8/8] Done"
echo "Smoke test abgeschlossen."
