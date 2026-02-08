# Migration auf v1.9.5 (persistente Server-Dateien)

Diese Anleitung verhindert, dass nach Docker-Image-Updates der Hytale-Server erneut komplett heruntergeladen werden muss.

## Ziel

Ab `v1.9.5` soll auch folgendes persistent sein:

- `/opt/hytale-server/Server` (Server-Binaries + Runtime)

Damit bleiben die Server-Dateien bei Container-Neustarts und Image-Updates erhalten.

## Variante A: Named Volumes (empfohlen)

1. Repository aktualisieren:

```bash
git fetch --all --tags
git checkout v1.9.5
```

2. Compose neu starten:

```bash
docker compose down
docker compose up -d --build
```

3. Prüfen, ob Volume vorhanden ist:

```bash
docker volume ls | grep hytale-server-bin
```

## Variante B: Bind Mounts (eigener Host-Pfad)

Wenn du Host-Verzeichnisse bevorzugst, setze in `docker-compose.yml`:

```yaml
volumes:
  - ./data/server:/opt/hytale-server/Server
  - ./data/universe:/opt/hytale-server/Server/universe
  - ./data/mods:/opt/hytale-server/mods
  - ./data/backups:/opt/hytale-server/backups
  - ./data/downloader:/opt/hytale-server/.downloader
```

Dann:

```bash
mkdir -p ./data/server ./data/universe ./data/mods ./data/backups ./data/downloader
docker compose down
docker compose up -d --build
```

## Optional: vorhandene Server-Dateien in Bind-Mount übernehmen

Falls die Dateien bereits im alten Container liegen, einmalig kopieren:

```bash
CONTAINER=zonfacter_hytale-docker-1
mkdir -p ./data/server
sudo docker cp "$CONTAINER":/opt/hytale-server/Server/. ./data/server/
```

## Validierung

```bash
CONTAINER=zonfacter_hytale-docker-1
sudo docker exec -it "$CONTAINER" sh -lc "ls -lah /opt/hytale-server/Server | sed -n '1,60p'"
sudo docker exec -it "$CONTAINER" supervisorctl status
```

Erwartung:
- `hytale-server` bleibt nicht mehr dauerhaft auf `FATAL`, nur weil Server-Dateien beim ersten Start fehlen.
- Nach erfolgreichem Setup bleiben die Dateien persistent.

## Hinweis zu Backups

Backups und Restore werden stabiler, wenn sowohl
- `Server/universe` (Weltdaten)
- als auch `Server` (Runtime/Binaries)

persistent konfiguriert sind.
