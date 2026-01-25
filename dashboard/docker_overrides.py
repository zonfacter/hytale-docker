"""
Docker-specific overrides for the Hytale Dashboard.
This file replaces systemd-dependent functions with supervisord equivalents.
"""

import os
import subprocess
from pathlib import Path
from datetime import datetime, timezone

# Configuration
SERVICE_NAME = "hytale-server"  # supervisord program name
SERVER_DIR = Path(os.environ.get("HYTALE_DIR", "/opt/hytale-server"))
LOG_DIR = SERVER_DIR / "logs"
LOG_LINES = 150


def run_cmd(cmd: list[str], timeout: int = 10) -> tuple[str, int]:
    """Run a subprocess and return (stdout+stderr, returncode)."""
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
        # For supervisor, we don't have exact start time easily, use current time
        data["StartTime"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
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
    # TODO: Implement Docker-specific backup frequency management
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
