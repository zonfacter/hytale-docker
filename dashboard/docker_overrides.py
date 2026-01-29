"""
Docker-specific overrides for the Hytale Dashboard.
This file replaces systemd-dependent functions with supervisord equivalents.
"""

import os
import re
import subprocess
import json
from pathlib import Path
from datetime import datetime, timezone
from threading import Lock


# ANSI escape code pattern for stripping terminal colors
ANSI_PATTERN = re.compile(r'\x1b\[[0-9;]*m|\[(?:[0-9;]*)?m')


def strip_ansi(text: str) -> str:
    """Remove ANSI escape codes from text."""
    return ANSI_PATTERN.sub('', text)

# Configuration
SERVICE_NAME = "hytale-server"  # supervisord program name
SERVER_DIR = Path(os.environ.get("HYTALE_DIR", "/opt/hytale-server"))
LOG_DIR = SERVER_DIR / "logs"
LOG_LINES = 150
DOWNLOAD_SCRIPT = "/usr/local/bin/hytale-download.sh"

# Runtime config file (persisted in volume)
CONFIG_FILE = SERVER_DIR / ".dashboard_config.json"
_config_lock = Lock()
_config_cache = None


def load_config() -> dict:
    """Load runtime configuration from file."""
    global _config_cache

    default_config = {
        "cf_api_key": os.environ.get("CF_API_KEY", ""),
        "downloader_url": os.environ.get("HYTALE_DOWNLOADER_URL", "https://downloader.hytale.com/hytale-downloader.zip"),
    }

    with _config_lock:
        if _config_cache is not None:
            # Merge with defaults (in case new keys added)
            merged = {**default_config, **_config_cache}
            return merged

        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r") as f:
                    _config_cache = json.load(f)
                # Merge with defaults
                merged = {**default_config, **_config_cache}
                return merged
            except (json.JSONDecodeError, PermissionError, OSError):
                pass

        _config_cache = default_config
        return default_config


def save_config(config: dict) -> bool:
    """Save runtime configuration to file."""
    global _config_cache

    with _config_lock:
        try:
            # Ensure directory exists
            CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(CONFIG_FILE, "w") as f:
                json.dump(config, f, indent=2)
            _config_cache = config
            return True
        except (PermissionError, OSError) as e:
            print(f"[docker_overrides] Failed to save config: {e}")
            return False


def get_config_value(key: str, default=None):
    """Get a single config value."""
    config = load_config()
    return config.get(key, default)


def set_config_value(key: str, value) -> bool:
    """Set a single config value."""
    config = load_config()
    config[key] = value
    return save_config(config)


def get_cf_api_key() -> str:
    """Get CurseForge API key (from config or env)."""
    return get_config_value("cf_api_key", "")


def get_downloader_url() -> str:
    """Get Hytale downloader URL (from config or env)."""
    return get_config_value("downloader_url", "https://downloader.hytale.com/hytale-downloader.zip")


def run_cmd(cmd: list[str], timeout: int = 10) -> tuple[str, int]:
    """
    Run a subprocess and return (stdout+stderr, returncode).
    
    Args:
        cmd: Command and arguments as a list
        timeout: Timeout in seconds
        
    Returns:
        tuple: (combined output string, return code int)
    """
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        output = result.stdout
        if result.stderr:
            output += "\n" + result.stderr
        return output.strip(), result.returncode
    except subprocess.TimeoutExpired:
        return "Command timed out", 1
    except FileNotFoundError:
        return f"Command not found: {cmd[0]}", 1
    except Exception as e:
        return str(e), 1


def get_service_status() -> dict:
    """Query supervisorctl for hytale-server status."""
    cmd = ["supervisorctl", "status", SERVICE_NAME]
    output, rc = run_cmd(cmd)
    
    # Parse supervisorctl output
    # Format: "hytale-server  RUNNING   pid 12345, uptime 1:23:45"
    # or:     "hytale-server  STOPPED   Jan 25 12:00 PM"
    
    data = {}
    if rc != 0:
        data["error"] = output
        data["ActiveState"] = "unknown"
        data["SubState"] = "unknown"
        data["MainPID"] = "0"
        data["StartTime"] = "n/a"
        return data
    
    # Parse the status line
    parts = output.split()
    if len(parts) < 2:
        data["ActiveState"] = "unknown"
        data["SubState"] = "unknown"
        data["MainPID"] = "0"
        data["StartTime"] = "n/a"
        return data
    
    status = parts[1].upper()
    
    if status == "RUNNING":
        data["ActiveState"] = "active"
        data["SubState"] = "running"
        # Extract PID if present
        pid = "0"
        for i, part in enumerate(parts):
            if part == "pid" and i + 1 < len(parts):
                pid = parts[i + 1].rstrip(",")
                break
        data["MainPID"] = pid
        # Note: supervisorctl doesn't provide exact start timestamp in standard output
        # The uptime is available but converting it to a timestamp would be imprecise
        data["StartTime"] = "running"
    elif status == "STOPPED":
        data["ActiveState"] = "inactive"
        data["SubState"] = "dead"
        data["MainPID"] = "0"
        data["StartTime"] = "n/a"
    elif status == "STARTING":
        data["ActiveState"] = "activating"
        data["SubState"] = "start"
        data["MainPID"] = "0"
        data["StartTime"] = "n/a"
    elif status == "FATAL":
        data["ActiveState"] = "failed"
        data["SubState"] = "failed"
        data["MainPID"] = "0"
        data["StartTime"] = "n/a"
    else:
        data["ActiveState"] = "unknown"
        data["SubState"] = status.lower()
        data["MainPID"] = "0"
        data["StartTime"] = "n/a"
    
    return data


def get_logs() -> list[str]:
    """Fetch logs from the server log file."""
    log_file = LOG_DIR / "server.log"
    error_log_file = LOG_DIR / "server-error.log"

    lines = []

    # Try to read the error log first (if it has content)
    if error_log_file.exists():
        try:
            with open(error_log_file, "r", encoding="utf-8", errors="replace") as f:
                error_lines = f.readlines()
                if error_lines:
                    lines.append("=== Error Log ===")
                    lines.extend([strip_ansi(line.rstrip()) for line in error_lines[-50:]])
                    lines.append("")
        except (PermissionError, OSError) as e:
            lines.append(f"[Error reading error log: {e}]")

    # Then read the main server log
    if log_file.exists():
        try:
            with open(log_file, "r", encoding="utf-8", errors="replace") as f:
                log_lines = f.readlines()
                lines.append("=== Server Log ===")
                lines.extend([strip_ansi(line.rstrip()) for line in log_lines[-LOG_LINES:]])
        except (PermissionError, OSError) as e:
            lines.append(f"[Error reading server log: {e}]")
    else:
        lines.append(f"[Log file not found: {log_file}]")
        lines.append("[Server may not have been started yet]")

    return lines


def get_server_control_commands() -> dict:
    """Return supervisorctl commands for server control."""
    return {
        "start": ["supervisorctl", "start", SERVICE_NAME],
        "stop": ["supervisorctl", "stop", SERVICE_NAME],
        "restart": ["supervisorctl", "restart", SERVICE_NAME],
    }


# Backup frequency configuration is not applicable in Docker
# The backup system should be configured through environment variables or config files
# rather than systemd service overrides
def get_backup_frequency() -> int:
    """
    Get backup frequency from environment or config file.
    In Docker, this is not managed via systemd overrides.
    """
    # For Docker deployment, backup frequency could be managed differently
    # For now, return 0 (disabled) as a safe default
    return 0


def set_backup_frequency(freq: int) -> bool:
    """
    Set backup frequency.
    In Docker, this is not managed via systemd overrides.
    """
    # For Docker deployment, this would need to be implemented differently
    # Perhaps through environment variables or a config file
    # For now, this is a no-op
    return False


def run_backup() -> tuple[str, int]:
    """
    Run backup in Docker.
    In Docker, we don't have the hytale-backup.sh script.
    This could be implemented with a simple tar command or similar.
    """
    import tarfile
    from datetime import datetime

    backup_dir = SERVER_DIR / "backups"
    universe_dir = SERVER_DIR / "universe"

    if not universe_dir.exists():
        return "Universe directory not found", 1

    backup_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = backup_dir / f"hytale_{timestamp}.tar.gz"

    try:
        with tarfile.open(backup_file, "w:gz") as tar:
            tar.add(universe_dir, arcname="universe")
        return f"Backup created: {backup_file.name}", 0
    except Exception as e:
        return f"Backup failed: {e}", 1


def check_version() -> dict:
    """
    Check for updates in Docker.
    Uses the hytale-downloader -print-version to get the latest available version.
    """
    import subprocess

    downloader_dir = SERVER_DIR / ".downloader"
    downloader_bin = downloader_dir / "hytale-downloader-linux-amd64"
    version_file = SERVER_DIR / "last_version.txt"

    current = "unknown"
    latest = "unknown"
    error = None

    # Get current installed version from last_version.txt
    try:
        if version_file.exists():
            current = version_file.read_text().strip()
    except (PermissionError, OSError) as e:
        error = f"Could not read current version: {e}"

    # Get latest available version using downloader's -print-version
    if downloader_bin.exists():
        try:
            result = subprocess.run(
                [str(downloader_bin), "-print-version"],
                cwd=str(downloader_dir),
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0 and result.stdout.strip():
                latest = result.stdout.strip()
                # Cache the latest version for quick access
                try:
                    latest_file = SERVER_DIR / ".latest_version"
                    latest_file.write_text(latest)
                except:
                    pass
            elif result.stderr:
                error = f"Downloader error: {result.stderr.strip()}"
        except subprocess.TimeoutExpired:
            error = "Version check timed out"
        except Exception as e:
            error = f"Failed to run downloader: {e}"
    else:
        # Fallback: try to read cached latest version
        try:
            latest_file = SERVER_DIR / ".latest_version"
            if latest_file.exists():
                latest = latest_file.read_text().strip()
        except:
            pass
        if latest == "unknown":
            error = "Downloader not found for version check"

    return {
        "current_version": current,
        "latest_version": latest,
        "update_available": current != latest and current != "unknown" and latest != "unknown",
        "docker_mode": True,
        "error": error,
        "message": "Im Docker wird das Update über das Dashboard 'Download starten' oder 'docker pull' durchgeführt."
    }


def run_update() -> dict:
    """
    Run update in Docker.
    Uses the hytale-downloader to download the latest server version.
    """
    import subprocess

    downloader_dir = SERVER_DIR / ".downloader"
    downloader_bin = downloader_dir / "hytale-downloader-linux-amd64"
    download_script = downloader_dir / "download.sh"

    if not downloader_bin.exists():
        return {
            "error": "Downloader not found",
            "docker_mode": True,
            "message": "Der Hytale Downloader wurde nicht gefunden. Bitte erst auf der Setup-Seite installieren."
        }

    # Get latest version first
    latest_version = "unknown"
    try:
        result = subprocess.run(
            [str(downloader_bin), "-print-version"],
            cwd=str(downloader_dir),
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0:
            latest_version = result.stdout.strip()
    except:
        pass

    # Run the download script (same as setup page)
    if download_script.exists():
        try:
            log_file = SERVER_DIR / "logs" / "update.log"
            log_file.parent.mkdir(parents=True, exist_ok=True)

            # Run download in background and capture output
            with open(log_file, "w") as f:
                result = subprocess.run(
                    ["/bin/bash", str(download_script)],
                    cwd=str(downloader_dir),
                    stdout=f,
                    stderr=subprocess.STDOUT,
                    timeout=600  # 10 minute timeout
                )

            if result.returncode == 0:
                # Update the version file
                try:
                    version_file = SERVER_DIR / "last_version.txt"
                    if latest_version != "unknown":
                        version_file.write_text(latest_version)
                except:
                    pass

                return {
                    "error": None,
                    "docker_mode": True,
                    "version": latest_version,
                    "message": f"Update auf Version {latest_version} erfolgreich! Server-Neustart empfohlen."
                }
            else:
                log_content = ""
                try:
                    log_content = log_file.read_text()[-500:]  # Last 500 chars
                except:
                    pass
                return {
                    "error": f"Download failed with code {result.returncode}",
                    "docker_mode": True,
                    "log": log_content,
                    "message": "Update fehlgeschlagen. Siehe Log für Details."
                }
        except subprocess.TimeoutExpired:
            return {
                "error": "Update timed out after 10 minutes",
                "docker_mode": True,
                "message": "Update-Timeout nach 10 Minuten."
            }
        except Exception as e:
            return {
                "error": str(e),
                "docker_mode": True,
                "message": f"Update-Fehler: {e}"
            }
    else:
        return {
            "error": "Download script not found",
            "docker_mode": True,
            "message": "Download-Script nicht gefunden. Setup-Seite prüfen."
        }


def check_auto_update() -> None:
    """
    Auto-update check in Docker.
    Not applicable - updates are done via image pulls.
    """
    pass


def get_players_from_logs() -> list[dict]:
    """
    Parse player events from log files instead of journalctl.
    
    Supports multiple log formats:
    - Simple: [INFO] Adding player 'Name' (uuid)
    - Detailed: [2026/01/26 19:00:36   INFO] Adding player 'Name' to world 'default' at location ... (uuid)
    - ISO format: 2026-01-26T19:00:36 INFO Adding player 'Name' (uuid)
    """
    log_file = LOG_DIR / "server.log"
    players = {}

    # Timestamp extraction pattern - matches various date/time formats
    # Examples: 2026/01/26 19:00:36, 2026-01-26T19:00:36, etc.
    timestamp_re = re.compile(r"(\d{4}[-/]\d{2}[-/]\d{2}[T ]\d{2}:\d{2}:\d{2})")
    
    # Player event patterns (without embedded timestamp - we extract it separately)
    # Format 1: Adding player 'Name' to world 'default' at location ... (uuid)
    join_detailed_re = re.compile(
        r"Adding player '([^']+)' to world '([^']+)' at location .+\(([a-f0-9-]+)\)",
        re.IGNORECASE
    )
    # Format 2: Adding player 'Name' (uuid)
    join_simple_re = re.compile(
        r"Adding player '([^']+)'\s*\(([a-f0-9-]+)\)",
        re.IGNORECASE
    )
    # Leave format: Removing player 'Name' (uuid)
    leave_re = re.compile(
        r"Removing player '([^']+?)(?:\s*\([^)]+\))?'\s*\(([a-f0-9-]+)\)",
        re.IGNORECASE
    )

    if not log_file.exists():
        return []

    try:
        with open(log_file, "r", encoding="utf-8", errors="replace") as f:
            for raw_line in f:
                # Strip ANSI codes before parsing
                line = strip_ansi(raw_line)
                
                # Extract timestamp if present (works for all formats)
                ts_match = timestamp_re.search(line)
                ts = ts_match.group(1) if ts_match else ""

                # Try detailed join pattern first (more specific)
                m = join_detailed_re.search(line)
                if m:
                    name, world, uuid = m.groups()
                    players[uuid] = {
                        "name": name,
                        "uuid": uuid,
                        "online": True,
                        "last_login": ts,
                        "last_logout": None,
                        "world": world,
                        "position": None,
                    }
                    continue

                # Try simple join pattern
                m = join_simple_re.search(line)
                if m:
                    name, uuid = m.groups()
                    players[uuid] = {
                        "name": name,
                        "uuid": uuid,
                        "online": True,
                        "last_login": ts,
                        "last_logout": None,
                        "world": "default",
                        "position": None,
                    }
                    continue

                # Try leave pattern
                m = leave_re.search(line)
                if m:
                    name, uuid = m.groups()
                    if uuid in players:
                        players[uuid]["online"] = False
                        players[uuid]["last_logout"] = ts
                    else:
                        # Player joined before log window, add as offline
                        players[uuid] = {
                            "name": name,
                            "uuid": uuid,
                            "online": False,
                            "last_login": None,
                            "last_logout": ts,
                            "world": None,
                            "position": None,
                        }
    except (PermissionError, OSError):
        pass

    return list(players.values())


def get_console_output(since: str = "") -> list[str]:
    """
    Get console output from log file instead of journalctl.
    """
    log_file = LOG_DIR / "server.log"
    lines = []

    if not log_file.exists():
        return ["[Log file not found - server may not have started yet]"]

    try:
        with open(log_file, "r", encoding="utf-8", errors="replace") as f:
            all_lines = f.readlines()
            # Return last 50 lines, strip ANSI codes
            lines = [strip_ansi(line.rstrip()) for line in all_lines[-50:]]
    except (PermissionError, OSError) as e:
        lines = [f"[Error reading log: {e}]"]

    return lines


def get_port_mappings() -> dict:
    """
    Get Docker port mappings for this container.
    Tries to read from Docker socket if available.
    """
    import socket
    import urllib.request

    result = {
        "available": False,
        "mappings": [],
        "internal_ports": {
            "game": "5520/udp",
            "api": "5523/tcp",
            "dashboard": "8088/tcp"
        },
        "hostname": "",
        "error": None
    }

    # Try to get hostname
    try:
        result["hostname"] = socket.gethostname()
    except:
        pass

    # Try Docker socket
    docker_socket = "/var/run/docker.sock"
    if os.path.exists(docker_socket):
        try:
            # Get container ID from hostname or cgroup
            container_id = None

            # Method 1: hostname is often the container ID
            hostname = socket.gethostname()
            if len(hostname) == 12 and all(c in '0123456789abcdef' for c in hostname.lower()):
                container_id = hostname

            # Method 2: Read from cgroup (cgroupv1 and cgroupv2)
            if not container_id:
                try:
                    with open("/proc/self/cgroup", "r") as f:
                        for line in f:
                            # cgroupv1: contains "docker" in path
                            if "docker" in line:
                                parts = line.strip().split("/")
                                if parts:
                                    container_id = parts[-1][:12]
                                    break
                            # cgroupv2: format is "0::/docker/<container_id>"
                            if line.startswith("0::"):
                                parts = line.strip().split("/")
                                for i, part in enumerate(parts):
                                    if part == "docker" and i + 1 < len(parts):
                                        cid = parts[i + 1]
                                        if len(cid) >= 12 and all(c in '0123456789abcdef' for c in cid[:12].lower()):
                                            container_id = cid[:12]
                                            break
                                if container_id:
                                    break
                except:
                    pass

            # Method 3: Read from cpuset (often works on cgroupv2)
            if not container_id:
                try:
                    with open("/proc/1/cpuset", "r") as f:
                        content = f.read().strip()
                        if "/docker/" in content:
                            parts = content.split("/docker/")
                            if len(parts) > 1:
                                cid = parts[-1].split("/")[0]
                                if len(cid) >= 12:
                                    container_id = cid[:12]
                except:
                    pass

            # Method 4: Read from mountinfo
            if not container_id:
                try:
                    with open("/proc/self/mountinfo", "r") as f:
                        for line in f:
                            if "/docker/containers/" in line:
                                start = line.find("/docker/containers/") + 19
                                end_part = line[start:start+64]  # Container IDs are 64 chars
                                container_id = end_part.split("/")[0][:12]
                                break
                except:
                    pass

            # Method 5: Use HOSTNAME environment variable (Docker sets this)
            if not container_id:
                hostname_env = os.environ.get("HOSTNAME", "")
                if len(hostname_env) == 12 and all(c in '0123456789abcdef' for c in hostname_env.lower()):
                    container_id = hostname_env

            if container_id:
                # Query Docker API via socket
                import http.client

                class DockerSocketConnection(http.client.HTTPConnection):
                    def __init__(self):
                        super().__init__("localhost")

                    def connect(self):
                        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                        self.sock.connect(docker_socket)

                conn = DockerSocketConnection()
                conn.request("GET", f"/containers/{container_id}/json")
                response = conn.getresponse()

                if response.status == 200:
                    data = json.loads(response.read().decode())
                    ports = data.get("NetworkSettings", {}).get("Ports", {})

                    mappings = []
                    for container_port, host_bindings in ports.items():
                        if host_bindings:
                            for binding in host_bindings:
                                host_port = binding.get("HostPort", "")
                                host_ip = binding.get("HostIp", "0.0.0.0")
                                if host_ip == "0.0.0.0":
                                    host_ip = ""
                                mappings.append({
                                    "container": container_port,
                                    "host": host_port,
                                    "ip": host_ip
                                })

                    result["available"] = True
                    result["mappings"] = mappings
                    result["container_id"] = container_id

                conn.close()

        except Exception as e:
            result["error"] = str(e)
    else:
        result["error"] = "Docker socket not available"

    return result


# ---------------------------------------------------------------------------
# Mod and Plugin Management
# ---------------------------------------------------------------------------

MODS_DIR = SERVER_DIR / "mods"


def get_mod_manifest(mod_path: Path) -> dict | None:
    """
    Read manifest information from a mod directory.
    Looks for manifest.json, plugin.json, or mod.json.
    """
    manifest_files = ["manifest.json", "plugin.json", "mod.json"]
    
    for manifest_name in manifest_files:
        manifest_path = mod_path / manifest_name
        if manifest_path.exists():
            try:
                with open(manifest_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, PermissionError, OSError):
                pass
    return None


def get_mods() -> list[dict]:
    """
    Get list of installed mods with metadata.
    Reads from /opt/hytale-server/mods/ directory.
    """
    mods = []
    
    if not MODS_DIR.exists():
        return mods
    
    try:
        for item in sorted(MODS_DIR.iterdir()):
            # Handle enabled JAR files (ending in .jar but not .jar.disabled)
            if item.is_file() and item.name.endswith(".jar") and not item.name.endswith(".jar.disabled"):
                display_name = item.name.removesuffix(".jar")
                size = item.stat().st_size
                mods.append({
                    "name": display_name,
                    "dir_name": item.name,
                    "enabled": True,
                    "is_jar": True,
                    "has_manifest": False,
                    "manifest": None,
                    "size": _human_size(size),
                    "size_bytes": size,
                })
            # Handle disabled JAR files
            elif item.is_file() and item.name.endswith(".jar.disabled"):
                display_name = item.name.removesuffix(".jar.disabled")
                size = item.stat().st_size
                mods.append({
                    "name": display_name,
                    "dir_name": item.name,
                    "enabled": False,
                    "is_jar": True,
                    "has_manifest": False,
                    "manifest": None,
                    "size": _human_size(size),
                    "size_bytes": size,
                })
            # Handle directories (mods with multiple files)
            elif item.is_dir():
                enabled = not item.name.endswith(".disabled")
                display_name = item.name.removesuffix(".disabled")
                manifest = get_mod_manifest(item)
                
                # Calculate total size
                total_size = sum(f.stat().st_size for f in item.rglob("*") if f.is_file())
                
                mod_info = {
                    "name": manifest.get("name", display_name) if manifest else display_name,
                    "dir_name": item.name,
                    "enabled": enabled,
                    "is_jar": False,
                    "has_manifest": manifest is not None,
                    "manifest": manifest,
                    "size": _human_size(total_size),
                    "size_bytes": total_size,
                }
                
                # Add manifest metadata if available
                if manifest:
                    mod_info["version"] = manifest.get("version", "")
                    mod_info["author"] = manifest.get("author", manifest.get("authors", ""))
                    mod_info["description"] = manifest.get("description", "")
                
                mods.append(mod_info)
    except (PermissionError, OSError):
        pass
    
    return mods


def check_plugin_installed(jar_pattern: str) -> dict:
    """
    Check if a plugin is installed by looking for JAR files matching pattern.
    
    Args:
        jar_pattern: Pattern like "nitrado-webserver" or "nitrado-query"
                    Must contain only alphanumeric characters, hyphens, and underscores.
    
    Returns:
        dict with installed, enabled status and file path if found
    """
    import re
    
    # Validate input: only allow alphanumeric, hyphens, underscores
    if not jar_pattern or not re.match(r'^[a-zA-Z0-9_-]+$', jar_pattern):
        return {"installed": False, "enabled": False, "path": None, "error": "Invalid pattern"}
    
    if not MODS_DIR.exists():
        return {"installed": False, "enabled": False, "path": None}
    
    # Normalize pattern for matching
    pattern_lower = jar_pattern.lower()
    # Create normalized version for directory matching (underscores -> hyphens)
    pattern_normalized = pattern_lower.replace("_", "-")
    
    try:
        for item in MODS_DIR.iterdir():
            name_lower = item.name.lower()
            
            # Check JAR files in root
            if item.is_file():
                if name_lower.endswith((".jar", ".jar.disabled")):
                    # Extract base name without .jar or .jar.disabled
                    base_name = name_lower.removesuffix(".disabled").removesuffix(".jar")
                    # Check if pattern matches the beginning of the jar name
                    # e.g., "nitrado-webserver" matches "nitrado-webserver-1.0.0.jar"
                    if base_name.startswith(pattern_lower) or base_name == pattern_lower:
                        enabled = not name_lower.endswith(".disabled")
                        return {
                            "installed": True,
                            "enabled": enabled,
                            "path": str(item),
                            "filename": item.name,
                        }
            
            # Check directories (old-style plugin installation)
            elif item.is_dir():
                # Normalize directory name (e.g., "Nitrado_WebServer" -> "nitrado-webserver")
                dir_normalized = name_lower.replace("_", "-").replace(" ", "-")
                dir_base = dir_normalized.removesuffix(".disabled")
                
                # Exact match or pattern matches the base name
                if dir_base == pattern_normalized:
                    enabled = not item.name.endswith(".disabled")
                    return {
                        "installed": True,
                        "enabled": enabled,
                        "path": str(item),
                        "is_directory": True,
                    }
    except (PermissionError, OSError):
        pass
    
    return {"installed": False, "enabled": False, "path": None}


def _human_size(size_bytes: int) -> str:
    """Convert bytes to human-readable size string."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}" if unit != "B" else f"{size_bytes} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


# ---------------------------------------------------------------------------
# Dashboard Update Check
# ---------------------------------------------------------------------------

# Version of the Docker image - should match Dockerfile LABEL
DASHBOARD_VERSION = os.environ.get("DASHBOARD_VERSION", "1.7.0")
GITHUB_REPO = "zonfacter/hytale-docker"
DOCKERHUB_REPO = "zonfacter/hytale-docker"

# Cache for update check results (to avoid rate limiting)
_update_cache = None
_update_cache_time = None
UPDATE_CACHE_TTL = 3600  # 1 hour cache TTL


def check_dashboard_update(force_refresh: bool = False) -> dict:
    """
    Check for available updates from GitHub releases and Docker Hub.
    
    Results are cached for 1 hour to avoid API rate limiting.
    
    Args:
        force_refresh: If True, bypass cache and fetch fresh data.
    
    Returns dict with:
    - current_version: Current installed version
    - github_release: Latest GitHub release info (if available)
    - dockerhub: Docker Hub image info (if available)
    - update_available: True if newer version exists
    - cached: True if result was from cache
    """
    global _update_cache, _update_cache_time
    
    # Check cache first (unless force refresh)
    if not force_refresh and _update_cache is not None and _update_cache_time is not None:
        cache_age = (datetime.now(timezone.utc) - _update_cache_time).total_seconds()
        if cache_age < UPDATE_CACHE_TTL:
            result = _update_cache.copy()
            result["cached"] = True
            result["cache_age_seconds"] = int(cache_age)
            return result
    import urllib.request
    import urllib.error
    
    result = {
        "current_version": DASHBOARD_VERSION,
        "github_release": None,
        "dockerhub": None,
        "update_available": False,
        "error": None,
        "cached": False,
    }
    
    # Check GitHub releases
    try:
        github_url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
        req = urllib.request.Request(
            github_url,
            headers={
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "HytaleDashboard/1.0",
            }
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode())
                tag = data.get("tag_name", "").lstrip("v")
                result["github_release"] = {
                    "tag": data.get("tag_name", ""),
                    "version": tag,
                    "name": data.get("name", ""),
                    "url": data.get("html_url", ""),
                    "published": data.get("published_at", ""),
                    "body": (data.get("body", "") or "")[:500],  # Truncate release notes
                }
                
                # Compare versions
                if tag and _version_compare(tag, DASHBOARD_VERSION) > 0:
                    result["update_available"] = True
    except urllib.error.HTTPError as e:
        if e.code != 404:  # Ignore 404 (no releases)
            result["error"] = f"GitHub API error: {e.code}"
    except urllib.error.URLError as e:
        result["error"] = f"GitHub connection error: {str(e.reason)}"
    except Exception as e:
        result["error"] = f"GitHub check failed: {str(e)}"
    
    # Check Docker Hub
    try:
        dockerhub_url = f"https://hub.docker.com/v2/repositories/{DOCKERHUB_REPO}/tags/latest"
        with urllib.request.urlopen(dockerhub_url, timeout=10) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode())
                result["dockerhub"] = {
                    "last_updated": data.get("last_updated", ""),
                    "digest": (data.get("digest", "") or "")[:19],  # Short digest
                    "full_digest": data.get("digest", ""),
                }
    except urllib.error.HTTPError:
        pass  # Docker Hub not reachable is not critical
    except urllib.error.URLError:
        pass
    except Exception:
        pass
    
    # Update cache
    _update_cache = result.copy()
    _update_cache_time = datetime.now(timezone.utc)
    
    return result


def _version_compare(v1: str, v2: str) -> int:
    """
    Compare two version strings.
    Returns: >0 if v1 > v2, <0 if v1 < v2, 0 if equal.
    """
    def normalize(v: str) -> list[int]:
        # Remove leading 'v' and split by dots
        v = v.lstrip("v")
        parts = []
        for p in v.split("."):
            # Extract numeric part
            num = ""
            for c in p:
                if c.isdigit():
                    num += c
                else:
                    break
            parts.append(int(num) if num else 0)
        return parts
    
    p1, p2 = normalize(v1), normalize(v2)
    
    # Pad shorter version with zeros
    while len(p1) < len(p2):
        p1.append(0)
    while len(p2) < len(p1):
        p2.append(0)
    
    for a, b in zip(p1, p2):
        if a > b:
            return 1
        if a < b:
            return -1
    return 0
