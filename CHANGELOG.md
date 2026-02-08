# Changelog

## [v1.10.1] - 2026-02-08

### Added
- Farbiger globaler Hinweis-Banner auf der Dashboard-Hauptseite (Warnung bei fehlender Persistenz, Info zu aktuellen Releases).
- Automatische Token-Synchronisierung im Container:
  - Restore von `auth.enc` aus `.downloader/auth.enc` beim Start
  - Laufende Sicherung/Restore im Wrapper während Runtime

### Fixed
- Banner wird jetzt zuverlässig im Docker-Dashboard gerendert.

## [v1.10.0] - 2026-02-08

### Added
- Hinweise zu Persistenz und Releases auf der Dashboard-Hauptseite als Statuszeilen (GitHub + Docker Hub).

### Fixed
- Docker-Pfad-Kompatibilitaet fuer Weltkonfiguration verbessert: im Docker-Modus wird `Server/universe/...` bevorzugt.
- Legacy-Kompatibilitaet: `entrypoint.sh` legt bei Bedarf Symlink `/opt/hytale-server/universe -> /opt/hytale-server/Server/universe` an.

## [v1.9.9] - 2026-02-08

### Added
- Dashboard-Hinweis fuer Persistenz: zeigt auf der Hauptseite, ob zentrale Docker-Pfade (insb. `/opt/hytale-server/Server`) wirklich persistent gemountet sind.
- Dashboard-Update-Hinweis auf der Hauptseite mit Latest-Releases von:
  - `zonfacter/hytale-dashboard` (GitHub)
  - `zonfacter/hytale-docker` (GitHub)
  - `zonfacter/hytale-docker` (Docker Hub)

### Fixed
- Docker-Hinweise werden direkt im `/api/status` Modell bereitgestellt (`persistence`, `release_updates`) und im UI gerendert.

## [v1.9.8] - 2026-02-08

### Fixed
- Docker-Hard-Overrides jetzt fehlertolerant (kein kompletter Ausfall bei Teil-Importfehlern).
- `/manage` Console sendet im Docker immer in `.server_command` statt FIFO-Abhaengigkeit.
- Backup/Create und Version/Update Endpunkte werden im Docker-Modus robust auf Docker-Implementierungen geroutet (kein `/usr/local/sbin/...` mehr).
- EntryPoint erzeugt `worlds/default/config.json` nur noch bei wirklich leerer Weltstruktur, um `World default already exists on disk` Konflikte zu vermeiden.

## [v1.9.7] - 2026-02-08

### Fixed
- Auth-Reihenfolge korrigiert: zuerst `/auth login {device|browser}`, danach wird `persistence Encrypted` erst nach erfolgreichem Token gesetzt.
- Docker-Hard-Override fuer `/api/auth/login/start` startet nur noch den Login-Flow (keine vorzeitige Persistence).

## [v1.9.6] - 2026-02-08

### Fixed
- Docker Manage-Console nutzt jetzt robust den Wrapper-Command-Pfad statt alter FIFO-Abhaengigkeit (`/api/console/send`), auch bei Upstream-Signatur-Aenderungen.
- Setup-Auth fuehrt erst `/auth login {device|browser}` aus und setzt `persistence Encrypted` erst nach erfolgreichem Token.
- OAuth/HTTP-Links im Setup-Log bleiben klickbar (kein fehlerhaftes HTML-Rewriting mehr).
- Port-Mapping-Erkennung per Docker-Socket wurde fuer cgroupv1/v2/systemd-Scope robuster gemacht.
- Docker Socket Gruppen-Mapping im EntryPoint auf GID-basierten Zugriff gehaertet.

### Added
- Tailscale-Status wird im Dashboard-Statusmodell bereitgestellt und auf der Hauptseite als Status-Zeile angezeigt.

## [v1.9.5] - 2026-02-08

### Fixed
- Docker updates no longer require re-downloading server binaries when recommended volumes are used.
- `server-wrapper.sh` now waits gracefully for setup files instead of exiting quickly and causing supervisor `FATAL` loops.

### Changed
- Added persistent `hytale-server-bin` volume mapping (`/opt/hytale-server/Server`) in compose defaults.
- Updated README and Docker Hub docs with persistent binary volume guidance.

## [v1.9.4] - 2026-02-08

### Fixed
- Docker mode detection now auto-fallbacks via container markers in patched dashboard runtime.
- In container environments without reliable `/.dockerenv`, status/log/console overrides are still applied.
- Prevents fallback to native `systemctl` path in Docker-like runtimes.

## [v1.9.3] - 2026-02-08

### Fixed
- Docker Dashboard Service-Control in der Integration robust gegen Upstream-Aenderungen gemacht:
  - `api/server/{action}` wird im Docker-Kontext zuverlaessig auf `supervisorctl` geroutet.
  - Keine `docker start/stop/restart` Aufrufe mehr fuer den In-Container-Servicepfad.
- Docker Socket Rechte gehaertet (`scripts/entrypoint.sh`):
  - kein `chmod 666` mehr,
  - stattdessen gruppenbasierter Zugriff (`g+rw`) + Warnung bei fehlender Leseberechtigung.

### Added
- PR Template mit `docker_impact`-Pflichtcheck in beiden Repos.

## [v1.9.2] - 2026-02-08

### Fixed
- Docker Dashboard kann Logs wieder zuverlässig auslesen (`/api/logs` und `/api/console/output`).
- `dashboard/apply_docker_patches.py` um robuste Hard-Overrides erweitert, damit Log-/Console-Funktionen auch bei geaenderten Upstream-Signaturen weiter auf `docker_overrides` umgeleitet werden.

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
