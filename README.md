# Hytale Docker

[![Docker Hub](https://img.shields.io/docker/v/zonfacter/hytale-docker?label=Docker%20Hub&logo=docker)](https://hub.docker.com/r/zonfacter/hytale-docker)
[![Docker Pulls](https://img.shields.io/docker/pulls/zonfacter/hytale-docker?logo=docker)](https://hub.docker.com/r/zonfacter/hytale-docker)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Hytale](https://img.shields.io/badge/Hytale-Server-orange)](https://hytale.com/)

Docker image for **Hytale Dedicated Server** with integrated **Web Dashboard**.

🇩🇪 [Deutsche Anleitung](docs/setup-guide-de.md) | 🇬🇧 [English Guide](docs/setup-guide-en.md)

![Dashboard Screenshot](https://raw.githubusercontent.com/zonfacter/hytale-dashboard/master/docs/dashboard.png)

---

## Features

- 🎮 **Hytale Dedicated Server** - Ready to run
- 🖥️ **Web Dashboard** - Manage your server via browser
- 🔧 **Setup Wizard** - Guided installation with OAuth support
- 📦 **CurseForge Integration** - Install mods with one click
- 💾 **Automatic Backups** - Built-in backup system
- 🔄 **Easy Updates** - One command to update

---

## Quick Start

### Option 1: Using Docker Hub (Recommended)

```bash
# Pull image
docker pull zonfacter/hytale-docker:latest

# Run container with named volumes (recommended)
docker run -d \
  --name hytale-server \
  -p 8088:8088 \
  -p 5520:5520/udp \
  -v hytale-universe:/opt/hytale-server/universe \
  -v hytale-mods:/opt/hytale-server/mods \
  -v hytale-backups:/opt/hytale-server/backups \
  -v hytale-downloader:/opt/hytale-server/.downloader \
  -e DASH_PASS=changeme \
  zonfacter/hytale-docker:latest

# Open dashboard
# http://localhost:8088/setup
```

**Alternative:** If you prefer bind mounts for direct file access:

```bash
# Create data directory
mkdir -p hytale-data/{universe,mods,backups,downloader}

# Run container with bind mounts
docker run -d \
  --name hytale-server \
  -p 8088:8088 \
  -p 5520:5520/udp \
  -v $(pwd)/hytale-data/universe:/opt/hytale-server/universe \
  -v $(pwd)/hytale-data/mods:/opt/hytale-server/mods \
  -v $(pwd)/hytale-data/backups:/opt/hytale-server/backups \
  -v $(pwd)/hytale-data/downloader:/opt/hytale-server/.downloader \
  -e DASH_PASS=changeme \
  zonfacter/hytale-docker:latest
```

### Option 2: Using Docker Compose

```bash
# Clone repository
git clone https://github.com/zonfacter/hytale-docker.git
cd hytale-docker

# Start containers
docker-compose up -d

# Open dashboard
# http://localhost:8088/setup
```

**Default Credentials:**
- Username: `admin`
- Password: `changeme`

⚠️ **Change the password in `docker-compose.yml` before production use!**

---

## Initial Setup

### 1. Get the Hytale Downloader

The Hytale server binary cannot be distributed. You have two options:

#### Option A: Manual Download (Traditional)

1. Visit [hytale.com](https://hytale.com/)
2. Download the **Linux server downloader**
3. Copy to `./data/downloader/hytale-downloader-linux-amd64`

#### Option B: Automatic Download (Recommended for CI/CD)

If you have access to a URL hosting the Hytale downloader, you can automate the download:

1. Edit `docker-compose.yml` and set:
   ```yaml
   environment:
     - HYTALE_DOWNLOADER_URL=https://your-server.com/hytale-downloader-linux-amd64
   ```
2. The downloader will be fetched automatically on container start

⚠️ **Note:** The downloader URL must be provided by you. There is no official public download URL due to licensing restrictions.

### 2. Start and Configure

```bash
docker-compose up -d
```

### 3. Complete Setup via Dashboard

Open `http://localhost:8088/setup` and follow the wizard:

1. ✅ Downloader detected
2. 🔐 Click "Start Download" → OAuth link appears in log
3. 🌐 Open OAuth link in browser → Login with Hytale account
4. ⬇️ Server downloads automatically
5. 🎉 Done! Server starts automatically

---

## Configuration

Edit `docker-compose.yml`:

```yaml
environment:
  # Server Settings
  - HYTALE_MEMORY_MIN=2G
  - HYTALE_MEMORY_MAX=4G

  # Downloader Settings (Optional)
  - HYTALE_DOWNLOADER_URL=https://your-url/hytale-downloader-linux-amd64

  # Dashboard Settings
  - DASH_USER=admin
  - DASH_PASS=your-secure-password  # CHANGE THIS!

  # Optional: CurseForge API Key
  - CF_API_KEY=your-api-key
```

Then restart:

```bash
docker-compose up -d
```

---

## Build Arguments & Platform Support

### Supported Platforms

This image supports multiple architectures:
- **linux/amd64** (Intel/AMD 64-bit)
- **linux/arm64** (ARM 64-bit, e.g., Apple Silicon, Raspberry Pi 4/5)

Docker will automatically pull the correct image for your platform.

### Custom Build Arguments

You can customize the base image and Java version when building from source:

```bash
# Clone repository with submodules
git clone --recurse-submodules https://github.com/zonfacter/hytale-docker.git
cd hytale-docker

# Build with custom Debian version
docker build \
  --build-arg DEBIAN_BASE_IMAGE=debian:bullseye-slim \
  --build-arg DEBIAN_CODENAME=bullseye \
  --build-arg JAVA_VERSION=17 \
  -t hytale-custom .
```

Available build arguments:
- **DEBIAN_BASE_IMAGE**: Base Debian image (default: `debian:bookworm-slim`)
- **DEBIAN_CODENAME**: Debian codename for Java repository (default: `bookworm`)
- **JAVA_VERSION**: Eclipse Temurin Java version (default: `21`)

Or configure in `docker-compose.yml`:

```yaml
build:
  context: .
  dockerfile: Dockerfile
  args:
    DEBIAN_BASE_IMAGE: debian:bookworm-slim
    DEBIAN_CODENAME: bookworm
    JAVA_VERSION: 21
```

### Building from Source

When building from source, the dashboard is included as a Git submodule. To clone the repository with all dependencies:

```bash
# Clone with submodules
git clone --recurse-submodules https://github.com/zonfacter/hytale-docker.git

# Or if already cloned, initialize submodules
git submodule update --init --recursive
```

To update the dashboard to the latest version:

```bash
cd dashboard-source
git pull origin master
cd ..
git add dashboard-source
git commit -m "Update dashboard to latest version"
```

---

## Ports

| Port | Protocol | Description |
|------|----------|-------------|
| 5520 | UDP | Hytale Game Server |
| 5523 | TCP | Nitrado WebServer API |
| 8088 | TCP | Web Dashboard |

---

## Volumes

Data is stored in Docker-managed named volumes by default (recommended for production):

| Volume Name | Container Path | Description |
|-------------|----------------|-------------|
| `hytale-universe` | `/opt/hytale-server/universe` | World data (players, builds) |
| `hytale-mods` | `/opt/hytale-server/mods` | Installed mods |
| `hytale-backups` | `/opt/hytale-server/backups` | Backup files |
| `hytale-downloader` | `/opt/hytale-server/.downloader` | Downloader & OAuth credentials |
| `hytale-logs` | `/opt/hytale-server/logs` | Server logs |

### Volume Configuration Options

The default configuration uses **named volumes**, which are recommended because:
- ✅ Independent of working directory
- ✅ Better managed by Docker
- ✅ Consistent across different operating systems
- ✅ Easier to backup and migrate

#### Alternative 1: Bind Mounts with Relative Paths

If you need direct file system access (e.g., for manual backups), you can use bind mounts with relative paths. Edit `docker-compose.yml` and uncomment the relative path section (around line 106).

⚠️ **Important:** You must always run `docker-compose` from the repository root directory, or the data will be stored in unexpected locations.

#### Alternative 2: Bind Mounts with Absolute Paths

For production environments with specific storage requirements, use absolute paths. Edit `docker-compose.yml` and uncomment the absolute path section (around line 116), replacing `/path/to/hytale-data` with your actual data directory.

This is the most reliable option for production as it explicitly defines where data is stored.

### Managing Named Volumes

```bash
# List volumes
docker volume ls

# Inspect a volume to see where data is stored
docker volume inspect hytale-universe

# Backup a volume (example for universe)
docker run --rm -v hytale-universe:/data -v $(pwd):/backup ubuntu tar czf /backup/universe-backup.tar.gz -C /data .

# Restore a volume
docker run --rm -v hytale-universe:/data -v $(pwd):/backup ubuntu tar xzf /backup/universe-backup.tar.gz -C /data

# Remove all volumes (WARNING: deletes all data!)
docker-compose down -v
```

---

## Commands

```bash
# Start
docker-compose up -d

# Stop
docker-compose down

# View logs
docker-compose logs -f

# Restart
docker-compose restart

# Update
docker-compose pull && docker-compose up -d

# Enter container shell
docker-compose exec hytale bash
```

---

## CurseForge Integration

Install mods directly from CurseForge:

1. Get a free API key: [console.curseforge.com](https://console.curseforge.com/)
2. Add to `docker-compose.yml`:
   ```yaml
   - CF_API_KEY=your-api-key
   ```
3. Restart container
4. Browse & install mods via Dashboard → Manage → CurseForge

---

## Documentation

- 🇩🇪 [Einrichtungsanleitung (Deutsch)](docs/setup-guide-de.md)
- 🇬🇧 [Setup Guide (English)](docs/setup-guide-en.md)
- 🔧 [IPC Mechanisms & FIFO Documentation](docs/ipc-mechanisms.md)
- 📊 [Dashboard Repository](https://github.com/zonfacter/hytale-dashboard)

---

## Troubleshooting

### Downloader not found
**With named volumes (default):**
- Check if file exists in volume: `docker run --rm -v hytale-downloader:/downloader ubuntu ls -la /downloader/`
- Copy file to volume: `docker run --rm -v hytale-downloader:/downloader -v $(pwd):/host ubuntu cp /host/hytale-downloader-linux-amd64 /downloader/`
- **Automatic setup**: Set `HYTALE_DOWNLOADER_URL` in `docker-compose.yml` to your hosted downloader URL

**With bind mounts:**
- **Manual setup**: Copy `hytale-downloader-linux-amd64` to `./data/downloader/`
- Check container logs: `docker-compose logs hytale` to see fetch attempts

### OAuth link doesn't appear
- Click "Refresh Log" in the setup wizard
- Check if downloader file exists (see "Downloader not found" above)

### Server won't start
- Check logs: `docker-compose logs hytale`
- Ensure enough memory is available
- Verify server files were extracted correctly

### Mods not loading
- **With named volumes**: Mods can be added via the Dashboard's CurseForge integration or copied to volume using: `docker run --rm -v hytale-mods:/mods -v $(pwd):/host ubuntu cp /host/your-mod.jar /mods/`
- **With bind mounts**: JAR files must be directly in `./data/mods/` (not in subfolders)
- Restart server after installing mods

### Console commands not working / FIFO issues
- **Symptom**: Commands sent via dashboard don't reach the server
- **Cause**: Named Pipe (FIFO) compatibility issues with storage drivers or orchestration
- **Quick fix**: Check if pipe exists: `docker exec hytale-server ls -l /opt/hytale-server/.console_pipe`
- **Detailed documentation**: See [IPC Mechanisms Guide](docs/ipc-mechanisms.md) for:
  - Storage driver compatibility
  - Kubernetes-specific issues
  - Alternative IPC methods (Unix sockets, TCP)
  - Windows Docker Desktop considerations

---

## Credits

- **Dashboard & Docker Setup:** [Claude Opus 4.5](https://anthropic.com) (AI)
- **Project Concept:** [zonfacter](https://github.com/zonfacter)
- **Hytale:** [Hypixel Studios](https://hytale.com/)

---

## License

MIT License - See [LICENSE](LICENSE) for details.
