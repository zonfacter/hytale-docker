# Compatibility Contract

This document defines how `hytale-docker` tracks and validates compatibility with
`zonfacter/hytale-dashboard`.

## Integration Model

- `hytale-dashboard` is consumed through the `dashboard-source` submodule.
- Docker-specific behavior is applied via:
  - `dashboard/apply_docker_patches.py`
  - `scripts/patch-dashboard-setup.sh`
  - `scripts/patch-dashboard-tailscale.sh`

## Required Upstream Contract

`dashboard-source/app.py` must continue to provide at least:

- `GET /api/status`
- `GET /api/logs`
- `GET /api/console/output`
- `GET /api/backups/list`
- `POST /api/backups/restore`
- `POST /api/backups/create`

And symbols:

- `DOCKER_MODE`
- `HYTALE_CONTAINER`
- `def get_logs() -> list[str]`
- `def _get_console_output(`

## CI Gate

The script `.github/scripts/validate-dashboard-compat.sh` is the single source of truth for compatibility checks.
It validates:

1. Required endpoint/symbol tokens in `dashboard-source/app.py`.
2. Patch pipeline execution (`apply_docker_patches.py`, setup and tailscale patch scripts).
3. Post-patch compileability of `dashboard-source/app.py`.
4. Presence of the hard override marker for log/console fallback routing.

## Release Rule

- Docker image/tag releases must run compatibility validation first.
- Submodule updates are only merged when the compatibility gate is green.
