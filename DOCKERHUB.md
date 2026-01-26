# Hytale Docker

🎮 Docker image for **Hytale Dedicated Server** with integrated **Web Dashboard**

🇩🇪 [Deutsche Version](#deutsche-version) | 🇬🇧 [English Version](#english-version)

---

# English Version

## What is this?

A ready-to-use Docker image that includes:
- **Hytale Dedicated Server** environment
- **Web Dashboard** for easy server management
- **Setup Wizard** with OAuth authentication support
- **Server Console** - send commands directly from the dashboard
- **Server Authentication** - easy Browser/Device login buttons
- **Port Mapping Display** - see external ports in bridge mode
- **Version Detection** - automatic update checking
- **Automatic Downloader** - fetches server files from hytale.com
- **CurseForge Integration** for one-click mod installation
- **Automatic Backups** system
- **Persistent Auth Credentials** - survives container restarts

## Quick Start

```bash
# Pull the image
docker pull zonfacter/hytale-docker:latest

# Create data directories
mkdir -p hytale-data/{universe,mods,backups,downloader}

# Run the container
docker run -d \
  --name hytale-server \
  -p 8088:8088 \
  -p 5520:5520/udp \
  -p 5523:5523 \
  -v ./hytale-data/universe:/opt/hytale-server/universe \
  -v ./hytale-data/mods:/opt/hytale-server/mods \
  -v ./hytale-data/backups:/opt/hytale-server/backups \
  -v ./hytale-data/downloader:/opt/hytale-server/.downloader \
  -e DASH_PASS=your-secure-password \
  zonfacter/hytale-docker:latest
```

Then open `http://localhost:8088/setup` in your browser.

## Initial Setup

1. **Automatic Downloader Fetch**
   - The container automatically downloads the Hytale Downloader from:
     `https://downloader.hytale.com/hytale-downloader.zip`
   - No manual action required!

2. **Complete Setup via Dashboard**
   - Open `http://localhost:8088/setup`
   - Click "Start Download"
   - Copy the OAuth link from the log and open it in your browser
   - Log in with your Hytale account
   - Wait for the download to complete

3. **Done!**
   - The server starts automatically
   - Access the dashboard at `http://localhost:8088`

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `HYTALE_MEMORY_MIN` | `2G` | Minimum Java heap size |
| `HYTALE_MEMORY_MAX` | `4G` | Maximum Java heap size |
| `HYTALE_DOWNLOADER_URL` | `https://downloader.hytale.com/hytale-downloader.zip` | URL for automatic downloader fetch (ZIP supported) |
| `DASH_USER` | `admin` | Dashboard username |
| `DASH_PASS` | `changeme` | Dashboard password (**change this!**) |
| `ALLOW_CONTROL` | `true` | Allow server control via dashboard |
| `CF_API_KEY` | *(empty)* | CurseForge API key for mod downloads |
| `TZ` | `Europe/Berlin` | Timezone |

## Ports

| Port | Protocol | Description |
|------|----------|-------------|
| 5520 | UDP | Hytale game server |
| 5523 | TCP | Nitrado WebServer API (plugins) |
| 8088 | TCP | Web Dashboard |

## Volumes

| Path | Description |
|------|-------------|
| `/opt/hytale-server/universe` | World data (players, builds) |
| `/opt/hytale-server/mods` | Installed mods |
| `/opt/hytale-server/backups` | Backup files |
| `/opt/hytale-server/.downloader` | Downloader & OAuth credentials |

## Docker Compose

```yaml
services:
  hytale:
    image: zonfacter/hytale-docker:latest
    container_name: hytale-server
    ports:
      - "8088:8088/tcp"
      - "5520:5520/udp"
      - "5523:5523/tcp"
    environment:
      - HYTALE_MEMORY_MIN=2G
      - HYTALE_MEMORY_MAX=4G
      - DASH_PASS=your-secure-password
      - CF_API_KEY=your-curseforge-key
      - TZ=Europe/Berlin
    volumes:
      - ./data/universe:/opt/hytale-server/universe
      - ./data/mods:/opt/hytale-server/mods
      - ./data/backups:/opt/hytale-server/backups
      - ./data/downloader:/opt/hytale-server/.downloader
      # Docker socket for port mapping display (optional)
      - /var/run/docker.sock:/var/run/docker.sock:ro
    restart: unless-stopped
    stop_signal: SIGINT
    stop_grace_period: 60s
```

## Tags

| Tag | Description |
|-----|-------------|
| `latest` | Latest stable release |
| `1.6.0`, `1.6` | Console commands, auth buttons, port display, version detection, persistent auth |
| `1.5.0`, `1.5` | Screen wrapper for server console |
| `1.4.0`, `1.4` | Runtime settings (CF_API_KEY, DOWNLOADER_URL) |
| `1.3.0`, `1.3` | Java 24 + Debian Trixie |
| `1.2.0`, `1.2` | Full Docker dashboard compatibility |
| `1.1.0`, `1.1`, `1` | Automatic downloader feature |
| `1.0.0`, `1.0` | Initial release |
| `master` | Development build (may be unstable) |

## Platform Support

This image supports multiple architectures:
- **linux/amd64** - Intel/AMD 64-bit processors
- **linux/arm64** - ARM 64-bit (Apple Silicon, Raspberry Pi 4/5)

Docker automatically selects the correct image for your platform.

### Custom Builds

Build with custom base image and Java version:

```bash
docker build \
  --build-arg DEBIAN_BASE_IMAGE=debian:trixie-slim \
  --build-arg DEBIAN_CODENAME=trixie \
  --build-arg JAVA_VERSION=24 \
  -t hytale-custom .
```

Available build arguments:
- `DEBIAN_BASE_IMAGE` - Base Debian image (default: `debian:trixie-slim`)
- `DEBIAN_CODENAME` - Debian codename for Java repo (default: `trixie`)
- `JAVA_VERSION` - Eclipse Temurin Java version (default: `24`)

## Links

- **GitHub:** [zonfacter/hytale-docker](https://github.com/zonfacter/hytale-docker)
- **Documentation:** [Setup Guide (EN)](https://github.com/zonfacter/hytale-docker/blob/master/docs/setup-guide-en.md)
- **Issues:** [Report bugs](https://github.com/zonfacter/hytale-docker/issues)

---

# Deutsche Version

## Was ist das?

Ein fertiges Docker-Image, das enthält:
- **Hytale Dedicated Server** Umgebung
- **Web Dashboard** zur einfachen Server-Verwaltung
- **Setup-Wizard** mit OAuth-Authentifizierung
- **Server-Konsole** - Befehle direkt aus dem Dashboard senden
- **Server-Authentifizierung** - einfache Browser/Device Login-Buttons
- **Port-Mapping Anzeige** - externe Ports im Bridge-Modus sehen
- **Versions-Erkennung** - automatische Update-Prüfung
- **Automatischer Downloader** - lädt Server-Dateien von hytale.com
- **CurseForge Integration** für Ein-Klick Mod-Installation
- **Automatische Backups**
- **Persistente Auth-Credentials** - überlebt Container-Neustarts

## Schnellstart

```bash
# Image herunterladen
docker pull zonfacter/hytale-docker:latest

# Daten-Verzeichnisse erstellen
mkdir -p hytale-data/{universe,mods,backups,downloader}

# Container starten
docker run -d \
  --name hytale-server \
  -p 8088:8088 \
  -p 5520:5520/udp \
  -p 5523:5523 \
  -v ./hytale-data/universe:/opt/hytale-server/universe \
  -v ./hytale-data/mods:/opt/hytale-server/mods \
  -v ./hytale-data/backups:/opt/hytale-server/backups \
  -v ./hytale-data/downloader:/opt/hytale-server/.downloader \
  -e DASH_PASS=dein-sicheres-passwort \
  zonfacter/hytale-docker:latest
```

Dann öffne `http://localhost:8088/setup` im Browser.

## Ersteinrichtung

1. **Automatischer Downloader**
   - Der Container lädt den Hytale Downloader automatisch von:
     `https://downloader.hytale.com/hytale-downloader.zip`
   - Keine manuelle Aktion erforderlich!

2. **Setup im Dashboard abschließen**
   - Öffne `http://localhost:8088/setup`
   - Klicke auf "Download starten"
   - Kopiere den OAuth-Link aus dem Log und öffne ihn im Browser
   - Melde dich mit deinem Hytale-Account an
   - Warte bis der Download abgeschlossen ist

3. **Fertig!**
   - Der Server startet automatisch
   - Dashboard erreichbar unter `http://localhost:8088`

## Umgebungsvariablen

| Variable | Standard | Beschreibung |
|----------|----------|--------------|
| `HYTALE_MEMORY_MIN` | `2G` | Minimaler Java-Heap |
| `HYTALE_MEMORY_MAX` | `4G` | Maximaler Java-Heap |
| `HYTALE_DOWNLOADER_URL` | `https://downloader.hytale.com/hytale-downloader.zip` | URL für automatischen Downloader (ZIP unterstützt) |
| `DASH_USER` | `admin` | Dashboard-Benutzer |
| `DASH_PASS` | `changeme` | Dashboard-Passwort (**ändern!**) |
| `ALLOW_CONTROL` | `true` | Server-Steuerung erlauben |
| `CF_API_KEY` | *(leer)* | CurseForge API-Key für Mods |
| `TZ` | `Europe/Berlin` | Zeitzone |

## Ports

| Port | Protokoll | Beschreibung |
|------|-----------|--------------|
| 5520 | UDP | Hytale Spielserver |
| 5523 | TCP | Nitrado WebServer API (Plugins) |
| 8088 | TCP | Web Dashboard |

## Volumes

| Pfad | Beschreibung |
|------|--------------|
| `/opt/hytale-server/universe` | Weltdaten (Spieler, Gebäude) |
| `/opt/hytale-server/mods` | Installierte Mods |
| `/opt/hytale-server/backups` | Backup-Dateien |
| `/opt/hytale-server/.downloader` | Downloader & OAuth-Credentials |

## Docker Compose

```yaml
services:
  hytale:
    image: zonfacter/hytale-docker:latest
    container_name: hytale-server
    ports:
      - "8088:8088/tcp"
      - "5520:5520/udp"
      - "5523:5523/tcp"
    environment:
      - HYTALE_MEMORY_MIN=2G
      - HYTALE_MEMORY_MAX=4G
      - DASH_PASS=dein-sicheres-passwort
      - CF_API_KEY=dein-curseforge-key
      - TZ=Europe/Berlin
    volumes:
      - ./data/universe:/opt/hytale-server/universe
      - ./data/mods:/opt/hytale-server/mods
      - ./data/backups:/opt/hytale-server/backups
      - ./data/downloader:/opt/hytale-server/.downloader
      # Docker Socket für Port-Mapping Anzeige (optional)
      - /var/run/docker.sock:/var/run/docker.sock:ro
    restart: unless-stopped
    stop_signal: SIGINT
    stop_grace_period: 60s
```

## Tags

| Tag | Beschreibung |
|-----|--------------|
| `latest` | Aktuellste stabile Version |
| `1.6.0`, `1.6` | Konsolen-Befehle, Auth-Buttons, Port-Anzeige, Versions-Erkennung, persistente Auth |
| `1.5.0`, `1.5` | Screen-Wrapper für Server-Konsole |
| `1.4.0`, `1.4` | Runtime Settings (CF_API_KEY, DOWNLOADER_URL) |
| `1.3.0`, `1.3` | Java 24 + Debian Trixie |
| `1.2.0`, `1.2` | Volle Docker Dashboard-Kompatibilität |
| `1.1.0`, `1.1`, `1` | Automatischer Downloader |
| `1.0.0`, `1.0` | Erstveröffentlichung |
| `master` | Entwicklungsversion (evtl. instabil) |

## Plattform-Unterstützung

Dieses Image unterstützt mehrere Architekturen:
- **linux/amd64** - Intel/AMD 64-bit Prozessoren
- **linux/arm64** - ARM 64-bit (Apple Silicon, Raspberry Pi 4/5)

Docker wählt automatisch das richtige Image für deine Plattform.

### Eigene Builds

Build mit benutzerdefiniertem Base-Image und Java-Version:

```bash
docker build \
  --build-arg DEBIAN_BASE_IMAGE=debian:trixie-slim \
  --build-arg DEBIAN_CODENAME=trixie \
  --build-arg JAVA_VERSION=24 \
  -t hytale-custom .
```

Verfügbare Build-Argumente:
- `DEBIAN_BASE_IMAGE` - Basis Debian-Image (Standard: `debian:trixie-slim`)
- `DEBIAN_CODENAME` - Debian Codename für Java-Repo (Standard: `trixie`)
- `JAVA_VERSION` - Eclipse Temurin Java-Version (Standard: `24`)

## Links

- **GitHub:** [zonfacter/hytale-docker](https://github.com/zonfacter/hytale-docker)
- **Dokumentation:** [Einrichtungsanleitung (DE)](https://github.com/zonfacter/hytale-docker/blob/master/docs/setup-guide-de.md)
- **Probleme melden:** [Issues](https://github.com/zonfacter/hytale-docker/issues)

---

## Credits

- **Development:** [Claude Opus 4.5](https://anthropic.com) (AI)
- **Project:** [zonfacter](https://github.com/zonfacter)
- **Hytale:** [Hypixel Studios](https://hytale.com/)

## License

MIT License - [View License](https://github.com/zonfacter/hytale-docker/blob/master/LICENSE)
