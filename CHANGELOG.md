# Changelog

## [v1.9.1] - 2026-02-08 (Draft)

### Added
- Smoke-Test Skript `scripts/smoke-test-v1.9.0.sh` fuer schnellen Post-Deploy Check.
- Draft-Release Paket-Assets (`tar.gz` und `.zip`) fuer direkten Download.

### Documentation
- README um Download-Hinweis fuer Draft-Release ergaenzt.

## [v1.9.0] - 2026-02-08

### Changed
- Dashboard submodule auf `hytale-dashboard v1.5.0` (`426d13e`) aktualisiert.
- Docker release metadata auf `1.9.0` angehoben.
- Docker Hub Tag-Dokumentation fuer `1.9` ergaenzt (EN/DE).

### Compatibility
- Docker-spezifische Dashboard-Patch-Pipeline (`apply_docker_patches.py`, Setup/Tailscale route patch) gegen Dashboard `v1.5.0` validiert.
- Integration bleibt ueber Submodule-Pinning reproduzierbar.

## [v1.8.0] - 2026-01-25

### Changed
- Universe-Pfad auf `Server/universe/` umgestellt (Hytale 2026.01+).

### Added
- Automatisiertes Installationsscript und erweiterte Setup-Integrationen.
