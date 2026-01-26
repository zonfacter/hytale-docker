"""
Docker-specific overrides for the Hytale Dashboard.
This file replaces systemd-dependent functions with supervisord equivalents.
"""

import os
import subprocess
import json
from pathlib import Path
from datetime import datetime, timezone
from threading import Lock

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
                    lines.extend([line.rstrip() for line in error_lines[-50:]])  # Last 50 error lines
                    lines.append("")
        except (PermissionError, OSError) as e:
            lines.append(f"[Error reading error log: {e}]")
    
    # Then read the main server log
    if log_file.exists():
        try:
            with open(log_file, "r", encoding="utf-8", errors="replace") as f:
                log_lines = f.readlines()
                lines.append("=== Server Log ===")
                lines.extend([line.rstrip() for line in log_lines[-LOG_LINES:]])
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
    Returns version info without using the update script.
    """
    version_file = SERVER_DIR / "last_version.txt"
    latest_file = SERVER_DIR / ".latest_version"

    current = "unknown"
    latest = "unknown"

    try:
        if version_file.exists():
            current = version_file.read_text().strip()
    except (PermissionError, OSError):
        pass

    try:
        if latest_file.exists():
            latest = latest_file.read_text().strip()
    except (PermissionError, OSError):
        pass

    return {
        "current_version": current,
        "latest_version": latest,
        "update_available": current != latest and latest != "unknown",
        "docker_mode": True,
        "message": "Version check in Docker mode. Use 'docker pull' to update the image."
    }


def run_update() -> dict:
    """
    Run update in Docker.
    In Docker, updates are done by pulling a new image, not by running update scripts.
    """
    return {
        "error": None,
        "docker_mode": True,
        "message": "Updates in Docker should be done by pulling a new image: docker pull zonfacter/hytale-docker:latest"
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
    """
    import re

    log_file = LOG_DIR / "server.log"
    players = {}

    join_re = re.compile(
        r"(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}).*Adding player '([^']+)' to world '([^']+)' at location .+\(([a-f0-9-]+)\)"
    )
    leave_re = re.compile(
        r"(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}).*Removing player '([^']+?)(?:\s*\([^)]+\))?'.*\(([a-f0-9-]+)\)\s*$"
    )

    if not log_file.exists():
        return []

    try:
        with open(log_file, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                m = join_re.search(line)
                if m:
                    ts, name, world, uuid = m.group(1), m.group(2), m.group(3), m.group(4)
                    players[uuid] = {
                        "name": name, "uuid": uuid,
                        "online": True, "last_login": ts,
                        "last_logout": None, "world": world, "position": None,
                    }
                    continue
                m = leave_re.search(line)
                if m:
                    ts, name, uuid = m.group(1), m.group(2), m.group(3)
                    if uuid in players:
                        players[uuid]["online"] = False
                        players[uuid]["last_logout"] = ts
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
            # Return last 50 lines
            lines = [line.rstrip() for line in all_lines[-50:]]
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
