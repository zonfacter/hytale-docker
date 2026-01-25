# Hytale Docker - Setup Guide (English)

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Start](#quick-start)
3. [Initial Setup](#initial-setup)
4. [Server Download and OAuth](#server-download-and-oauth)
5. [After Installation](#after-installation)
6. [Configuration](#configuration)
7. [Troubleshooting](#troubleshooting)

---

## Prerequisites

- **Docker** (Version 20.10 or newer)
- **Docker Compose** (Version 2.0 or newer)
- **Hytale Account** (for server download)
- At least **4 GB RAM** for the server
- Open ports: **5520/UDP** (game), **8088/TCP** (dashboard)

### Installing Docker (if not installed)

```bash
# Debian/Ubuntu
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# After installation: Log out and back in
```

### Supported Platforms

This Docker image supports multiple architectures:
- **linux/amd64** - Intel/AMD 64-bit processors (standard PCs/servers)
- **linux/arm64** - ARM 64-bit (Apple Silicon Macs, Raspberry Pi 4/5)

Docker automatically selects the correct version for your system.

### Custom Builds (Optional)

If you need a different Debian version or Java version:

```bash
# Example: Debian Bullseye with Java 17
docker build \
  --build-arg DEBIAN_BASE_IMAGE=debian:bullseye-slim \
  --build-arg DEBIAN_CODENAME=bullseye \
  --build-arg JAVA_VERSION=17 \
  -t hytale-custom .
```

Available build arguments:
- `DEBIAN_BASE_IMAGE` - Base image (default: `debian:bookworm-slim`)
- `DEBIAN_CODENAME` - Debian codename (default: `bookworm`)
- `JAVA_VERSION` - Java version (default: `21`)

---

## Quick Start

```bash
# 1. Clone repository
git clone https://github.com/zonfacter/hytale-docker.git
cd hytale-docker

# 2. Start containers
docker-compose up -d

# 3. Open dashboard
# http://localhost:8088
```

---

## Initial Setup

### Step 1: Get the Hytale Downloader

The Hytale server cannot be distributed directly - you have two options:

#### Option A: Manual Download (Traditional)

1. Visit [hytale.com](https://hytale.com/)
2. Download the **Server Downloader for Linux**
3. The file is named: `hytale-downloader-linux-amd64`
4. Copy it to the Docker volume or a local directory:

**With named volumes (default):**
```bash
# Start temporary container to copy file
docker run --rm -v hytale-downloader:/downloader -v $(pwd):/host ubuntu cp /host/hytale-downloader-linux-amd64 /downloader/
```

**With bind mounts (if configured):**
```bash
# Create directory (if it doesn't exist)
mkdir -p ./data/downloader

# Copy downloader (example)
cp ~/Downloads/hytale-downloader-linux-amd64 ./data/downloader/
```

#### Option B: Automatic Download (Recommended for CI/CD)

If you have access to a URL hosting the Hytale downloader, you can automate the download:

1. Edit `docker-compose.yml` and set:
   ```yaml
   environment:
     - HYTALE_DOWNLOADER_URL=https://your-server.com/hytale-downloader-linux-amd64
   ```
2. The downloader will be fetched automatically on container start

⚠️ **Note:** The downloader URL must be provided by you. There is no official public download URL due to licensing restrictions.

### Step 2: Start the Container

```bash
docker-compose up -d
```

### Step 3: Open Setup Wizard

Open the dashboard in your browser:

```
http://localhost:8088/setup
```

or

```
http://YOUR-SERVER-IP:8088/setup
```

---

## Server Download and OAuth

### The OAuth Process

Hytale uses OAuth for authentication. On first download, you need to log in with your Hytale account.

**How it works:**

1. Click **"Start Download"** in the Setup Wizard
2. An **OAuth link** appears in the log output (highlighted in blue)
3. **Copy the link** and open it in your browser
4. Log in with your **Hytale account**
5. After logging in, the download continues automatically
6. Credentials are saved - no login required next time

### Example OAuth Link

The link looks something like this:
```
https://auth.hytale.com/oauth/authorize?client_id=...&redirect_uri=...
```

### After Download

Once the download is complete:

1. The Setup Wizard shows "Installation successful"
2. Click "Go to Dashboard"
3. The server starts automatically

---

## After Installation

### Dashboard Credentials

| Setting | Default |
|---------|---------|
| URL | `http://localhost:8088` |
| Username | `admin` |
| Password | `changeme` |

**⚠️ Change the password!** See [Configuration](#configuration).

### Server Ports

| Port | Protocol | Purpose |
|------|----------|---------|
| 5520 | UDP | Hytale game server |
| 5523 | TCP | Nitrado WebServer API |
| 8088 | TCP | Dashboard |

### Useful Commands

```bash
# Show container status
docker-compose ps

# View logs
docker-compose logs -f

# Stop containers
docker-compose down

# Restart containers
docker-compose restart

# Pull updates
docker-compose pull
docker-compose up -d
```

---

## Configuration

### Change Password

Edit `docker-compose.yml`:

```yaml
environment:
  - DASH_PASS=YOUR_SECURE_PASSWORD
```

Then restart the container:

```bash
docker-compose up -d
```

### CurseForge Integration

To install mods directly from CurseForge:

1. Create a free API key: [console.curseforge.com](https://console.curseforge.com/)
2. Add the key to `docker-compose.yml`:

```yaml
environment:
  - CF_API_KEY=your-api-key-here
```

### Adjust Server Memory

```yaml
environment:
  - HYTALE_MEMORY_MIN=2G
  - HYTALE_MEMORY_MAX=4G
```

### Volume Configuration

The default configuration uses **named volumes**, which is recommended because:
- ✅ Independent of working directory
- ✅ Better managed by Docker
- ✅ Consistent across different operating systems

**Used Volumes:**
- `hytale-universe` - World data (players, builds)
- `hytale-mods` - Installed mods
- `hytale-backups` - Backup files
- `hytale-downloader` - Downloader & OAuth credentials
- `hytale-logs` - Server logs

#### Alternative 1: Bind Mounts with Relative Paths

If you need direct file system access (e.g., for manual backups):

1. Edit `docker-compose.yml`
2. Comment out the named volumes (lines 86-100)
3. Uncomment the relative paths section (lines 106-112)

⚠️ **Important:** You must always run `docker-compose` from the repository root directory!

#### Alternative 2: Bind Mounts with Absolute Paths

For production environments with specific storage requirements:

1. Edit `docker-compose.yml`
2. Comment out the named volumes (lines 86-100)
3. Uncomment the absolute paths section (lines 116-122)
4. Replace `/path/to/hytale-data` with your actual data directory

This is the most reliable option for production.

#### Volume Management

```bash
# List volumes
docker volume ls

# Inspect a volume (shows storage location)
docker volume inspect hytale-universe

# Backup a volume (example for universe)
docker run --rm -v hytale-universe:/data -v $(pwd):/backup ubuntu tar czf /backup/universe-backup.tar.gz -C /data .

# Restore a volume
docker run --rm -v hytale-universe:/data -v $(pwd):/backup ubuntu tar xzf /backup/universe-backup.tar.gz -C /data

# Remove all volumes (WARNING: deletes all data!)
docker-compose down -v
```

### All Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `HYTALE_MEMORY_MIN` | `2G` | Minimum Java heap |
| `HYTALE_MEMORY_MAX` | `4G` | Maximum Java heap |
| `HYTALE_PORT` | `5520` | Game server port |
| `DASHBOARD_PORT` | `8088` | Dashboard port |
| `DASH_USER` | `admin` | Dashboard username |
| `DASH_PASS` | `changeme` | Dashboard password |
| `ALLOW_CONTROL` | `true` | Allow server control |
| `CF_API_KEY` | *(empty)* | CurseForge API key |
| `TZ` | `Europe/Berlin` | Timezone |

---

## Troubleshooting

### "Downloader not found"

**Problem:** Setup Wizard shows "Downloader not found"

**Solution with named volumes (default):**
1. Check if the file exists in the volume:
   ```bash
   docker run --rm -v hytale-downloader:/downloader ubuntu ls -la /downloader/
   ```
2. If not present, copy the file to the volume:
   ```bash
   docker run --rm -v hytale-downloader:/downloader -v $(pwd):/host ubuntu cp /host/hytale-downloader-linux-amd64 /downloader/
   ```

**Solution with bind mounts:**
1. Make sure the file exists:
   ```bash
   ls -la ./data/downloader/
   ```
2. The filename must be exactly `hytale-downloader-linux-amd64`
3. The file must be executable (set automatically)

### OAuth Link doesn't appear

**Problem:** No link appears after "Start Download"

**Solution:**
1. Click "Refresh Log"
2. Wait a few seconds
3. Scroll down in the log
4. Check if an error is displayed

### "Connection refused" on Dashboard

**Problem:** Browser shows "Connection refused"

**Solution:**
1. Check if container is running:
   ```bash
   docker-compose ps
   ```
2. Check the logs:
   ```bash
   docker-compose logs dashboard
   ```
3. Check firewall:
   ```bash
   sudo ufw allow 8088/tcp
   ```

### Server won't start

**Problem:** Server appears as "Stopped" in dashboard

**Solution:**
1. Check server logs in dashboard under "Logs"
2. Or via Docker:
   ```bash
   docker-compose logs hytale
   ```
3. Common causes:
   - Not enough RAM (increase `HYTALE_MEMORY_MAX`)
   - Port already in use
   - Missing server files

### Mods don't work

**Problem:** Installed mods are not loaded

**Solution:**
1. Mods must be `.jar` files directly in the `mods/` folder
2. After installing mods: Restart the server
3. Check server logs for errors

### Console commands not working

**Problem:** Commands sent via dashboard don't reach the server

**Cause:** Named Pipe (FIFO) compatibility issues with storage drivers or orchestration

**Diagnosis:**
```bash
# Check if pipe exists
docker exec hytale-server ls -l /opt/hytale-server/.console_pipe

# Should show: prw-rw---- (p = pipe)
```

**Solution:**
- See **[IPC Mechanisms Documentation](ipc-mechanisms.md)** for:
  - Storage driver compatibility
  - Kubernetes-specific issues
  - Alternative IPC methods (Unix Sockets, TCP)
  - Windows Docker Desktop considerations

---

## Support

- **GitHub Issues:** [github.com/zonfacter/hytale-docker/issues](https://github.com/zonfacter/hytale-docker/issues)
- **Dashboard Repository:** [github.com/zonfacter/hytale-dashboard](https://github.com/zonfacter/hytale-dashboard)

---

*Created with ❤️ by Claude Opus 4.5*
