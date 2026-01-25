#!/usr/bin/env python3
"""
Apply Docker-specific patches to the Hytale Dashboard.
This script modifies the cloned dashboard's app.py to use supervisord instead of systemd.

Note: This patching approach uses string matching, which makes it somewhat fragile to
changes in the upstream dashboard code. However, it's a pragmatic solution that:
1. Avoids forking the entire dashboard repository
2. Allows using the official dashboard releases
3. Makes minimal modifications only where needed for Docker compatibility

If the upstream dashboard adds Docker support natively, this patching can be removed.
"""

import sys
from pathlib import Path

DOCKER_OVERRIDE_IMPORT = """
# Docker-specific overrides
try:
    from docker_overrides import (
        get_service_status,
        get_logs,
        get_server_control_commands,
        get_backup_frequency as docker_get_backup_frequency,
        set_backup_frequency,
    )
    DOCKER_MODE = True
    print("[Dashboard] Running in Docker mode with supervisord")
except ImportError:
    DOCKER_MODE = False
    print("[Dashboard] Running in bare-metal mode with systemd")
"""


def apply_patches(dashboard_dir: Path):
    """Apply patches to make the dashboard work with supervisord in Docker."""
    
    app_py = dashboard_dir / "app.py"
    if not app_py.exists():
        print(f"ERROR: app.py not found at {app_py}", file=sys.stderr)
        return False
    
    print(f"Patching {app_py} for Docker/supervisord compatibility...")
    
    # Read the original app.py
    content = app_py.read_text()
    
    # Find the imports section and add our override imports
    docker_override_marker = "from docker_overrides import ("
    import_marker = "from fastapi.security import HTTPBasic, HTTPBasicCredentials"
    if import_marker in content:
        content = content.replace(import_marker, import_marker + DOCKER_OVERRIDE_IMPORT)
    else:
        print("WARNING: Could not find import marker, trying alternative location", file=sys.stderr)
        # Try to add after the FastAPI imports
        import_marker = "from fastapi.templating import Jinja2Templates"
        if import_marker in content:
            content = content.replace(import_marker, import_marker + DOCKER_OVERRIDE_IMPORT)
    
    # Patch the get_service_status function (only if not overridden)
    # We wrap the original function to use our override when in Docker mode
    old_get_service = 'def get_service_status() -> dict:\n    """Query systemd for hytale.service status."""'
    if old_get_service in content and docker_override_marker in content:
        new_get_service = 'def get_service_status_systemd() -> dict:\n    """Query systemd for hytale.service status (bare-metal mode)."""'
        content = content.replace(old_get_service, new_get_service)
        
        # Add a wrapper function that chooses the right implementation
        wrapper = '\n\ndef get_service_status() -> dict:\n    """Get service status (Docker-aware)."""\n    if DOCKER_MODE:\n        from docker_overrides import get_service_status as docker_get_service_status\n        return docker_get_service_status()\n    return get_service_status_systemd()\n\n'
        
        # Insert after the get_service_status_systemd function
        marker = '    data["StartTime"] = data.get("ActiveEnterTimestamp", "n/a") or "n/a"\n    return data'
        if marker in content:
            content = content.replace(marker, marker + wrapper)
    
    # Patch the get_logs function
    old_get_logs = 'def get_logs() -> list[str]:\n    """Fetch journal logs for hytale unit."""'
    if old_get_logs in content and docker_override_marker in content:
        new_get_logs = 'def get_logs_systemd() -> list[str]:\n    """Fetch journal logs for hytale unit (bare-metal mode)."""'
        content = content.replace(old_get_logs, new_get_logs)
        
        # Add wrapper
        wrapper = '\n\ndef get_logs() -> list[str]:\n    """Get logs (Docker-aware)."""\n    if DOCKER_MODE:\n        from docker_overrides import get_logs as docker_get_logs\n        return docker_get_logs()\n    return get_logs_systemd()\n\n'
        
        marker = '    return output.splitlines()'
        # Find the right occurrence (in get_logs function)
        parts = content.split(marker, 1)  # Split only on first occurrence
        if len(parts) == 2:
            # Insert after the first occurrence in get_logs
            content = parts[0] + marker + wrapper + parts[1]
    
    # Patch the get_backup_frequency function to avoid systemd in Docker
    old_backup_func = 'def get_backup_frequency() -> int:\n    """Read current backup frequency from hytale.service (or override)."""'
    if old_backup_func in content and docker_override_marker in content:
        new_backup_func = 'def get_backup_frequency_systemd() -> int:\n    """Read current backup frequency from hytale.service (or override)."""'
        content = content.replace(old_backup_func, new_backup_func)
        
        wrapper = (
            "\n\ndef get_backup_frequency() -> int:\n"
            "    \"\"\"Get backup frequency (Docker-aware).\"\"\"\n"
            "    if DOCKER_MODE:\n"
            "        return docker_get_backup_frequency()\n"
            "    return get_backup_frequency_systemd()\n\n"
        )
        
        marker_candidates = [
            "def build_exec_start",
            "@app.get(\"/api/config\")",
            "def api_config",
            "# Configuration Endpoints",
        ]
        for marker in marker_candidates:
            if marker in content:
                content = content.replace(marker, wrapper + marker, 1)
                break
        else:
            markers_list = ", ".join(marker_candidates)
            print(
                "WARNING: Could not find marker for backup frequency wrapper. "
                f"Tried: {markers_list}. Docker-aware wrapper could not be installed.",
                file=sys.stderr,
            )
    
    # Patch the api_server_action function to use supervisorctl
    old_allowed = '    allowed = {\n        "start": ["sudo", "/bin/systemctl", "start", SERVICE_NAME],\n        "stop": ["sudo", "/bin/systemctl", "stop", SERVICE_NAME],\n        "restart": ["sudo", "/bin/systemctl", "restart", SERVICE_NAME],\n    }'
    if old_allowed in content and docker_override_marker in content:
        new_allowed = '    if DOCKER_MODE:\n        from docker_overrides import get_server_control_commands\n        allowed = get_server_control_commands()\n    else:\n        allowed = {\n            "start": ["sudo", "/bin/systemctl", "start", SERVICE_NAME],\n            "stop": ["sudo", "/bin/systemctl", "stop", SERVICE_NAME],\n            "restart": ["sudo", "/bin/systemctl", "restart", SERVICE_NAME],\n        }'
        content = content.replace(old_allowed, new_allowed)
    
    # Patch the backup frequency functions (disable for Docker)
    # We'll modify the get_backup_frequency endpoint to check DOCKER_MODE
    old_backup_get = '@app.get("/api/config/backup-frequency")\nasync def api_get_backup_frequency(user: str = Depends(verify_credentials)):\n    freq = get_backup_frequency()\n    return {"frequency": freq}'
    if old_backup_get in content and docker_override_marker in content:
        new_backup_get = '@app.get("/api/config/backup-frequency")\nasync def api_get_backup_frequency(user: str = Depends(verify_credentials)):\n    if DOCKER_MODE:\n        # Backup frequency management is not available in Docker mode\n        return {"frequency": 0, "docker_mode": True, "message": "Backup frequency is managed via environment variables in Docker"}\n    freq = get_backup_frequency()\n    return {"frequency": freq}'
        content = content.replace(old_backup_get, new_backup_get)
    
    # Similar for set backup frequency
    old_backup_set = '@app.post("/api/config/backup-frequency")\nasync def api_set_backup_frequency(freq: int, user: str = Depends(verify_credentials)):\n    if not ALLOW_CONTROL:\n        raise HTTPException(status_code=403, detail="Control deaktiviert.")'
    if old_backup_set in content and docker_override_marker in content:
        new_backup_set = '@app.post("/api/config/backup-frequency")\nasync def api_set_backup_frequency(freq: int, user: str = Depends(verify_credentials)):\n    if DOCKER_MODE:\n        raise HTTPException(status_code=400, detail="Backup frequency cannot be changed in Docker mode. Use environment variables.")\n    if not ALLOW_CONTROL:\n        raise HTTPException(status_code=403, detail="Control deaktiviert.")'
        content = content.replace(old_backup_set, new_backup_set)
    
    # Write the patched content
    app_py.write_text(content)
    print(f"✓ Successfully patched {app_py}")
    
    return True


def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <dashboard_directory>", file=sys.stderr)
        sys.exit(1)
    
    dashboard_dir = Path(sys.argv[1])
    if not dashboard_dir.is_dir():
        print(f"ERROR: {dashboard_dir} is not a directory", file=sys.stderr)
        sys.exit(1)
    
    if apply_patches(dashboard_dir):
        print("✓ All patches applied successfully")
        sys.exit(0)
    else:
        print("✗ Failed to apply patches", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
