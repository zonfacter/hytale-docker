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
- **CurseForge Integration** for one-click mod installation
- **Automatic Backups** system

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

1. **Get the Hytale Downloader**
   - Visit [hytale.com](https://hytale.com/)
   - Download the Linux server downloader
   - Copy `hytale-downloader-linux-amd64` to `./hytale-data/downloader/`

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
    restart: unless-stopped
    stop_signal: SIGINT
    stop_grace_period: 60s
```

## Tags

| Tag | Description |
|-----|-------------|
| `latest` | Latest stable release |
| `1.0.0`, `1.0`, `1` | Specific version |
| `master` | Development build (may be unstable) |

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
- **CurseForge Integration** für Ein-Klick Mod-Installation
- **Automatische Backups**

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

1. **Hytale Downloader besorgen**
   - Besuche [hytale.com](https://hytale.com/)
   - Lade den Linux Server-Downloader herunter
   - Kopiere `hytale-downloader-linux-amd64` nach `./hytale-data/downloader/`

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
    restart: unless-stopped
    stop_signal: SIGINT
    stop_grace_period: 60s
```

## Tags

| Tag | Beschreibung |
|-----|--------------|
| `latest` | Aktuellste stabile Version |
| `1.0.0`, `1.0`, `1` | Spezifische Version |
| `master` | Entwicklungsversion (evtl. instabil) |

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
