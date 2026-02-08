#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

fail() {
  echo "[compat] ERROR: $*" >&2
  exit 1
}

APP="dashboard-source/app.py"
[[ -f "$APP" ]] || fail "Missing $APP"

required=(
  '@app.get("/api/status")'
  '@app.get("/api/logs")'
  '@app.get("/api/console/output")'
  '@app.get("/api/backups/list")'
  '@app.post("/api/backups/restore")'
  '@app.post("/api/backups/create")'
  'def get_logs() -> list[str]'
  'def _get_console_output('
  'DOCKER_MODE'
  'HYTALE_CONTAINER'
)

for token in "${required[@]}"; do
  grep -F "$token" "$APP" >/dev/null || fail "Missing contract token in dashboard-source/app.py: $token"
done

echo "[compat] Contract tokens present"

WORKDIR="$(mktemp -d)"
trap 'rm -rf "$WORKDIR"' EXIT

cp -a dashboard-source "$WORKDIR/dashboard-source"
cp -a dashboard "$WORKDIR/dashboard"
cp -a scripts "$WORKDIR/scripts"

python3 "$WORKDIR/dashboard/apply_docker_patches.py" "$WORKDIR/dashboard-source"
cp "$WORKDIR/dashboard/docker_overrides.py" "$WORKDIR/dashboard-source/docker_overrides.py"
cp "$WORKDIR/dashboard/setup_routes.py" "$WORKDIR/dashboard-source/setup_routes.py"
cp "$WORKDIR/dashboard/tailscale_routes.py" "$WORKDIR/dashboard-source/tailscale_routes.py"

DASHBOARD_DIR="$WORKDIR/dashboard-source" bash "$WORKDIR/scripts/patch-dashboard-setup.sh"
DASHBOARD_DIR="$WORKDIR/dashboard-source" bash "$WORKDIR/scripts/patch-dashboard-tailscale.sh"

python3 -m py_compile "$WORKDIR/dashboard-source/app.py"
grep -F "hard_log_console_overrides" "$WORKDIR/dashboard-source/app.py" >/dev/null || fail "Missing hard log/console override marker after patch"

echo "[compat] Docker patch pipeline OK"
