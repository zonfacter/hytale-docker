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
import re
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
        run_backup as docker_run_backup,
        check_version as docker_check_version,
        run_update as docker_run_update,
        check_auto_update as docker_check_auto_update,
        get_players_from_logs as docker_get_players,
        get_console_output as docker_get_console_output,
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

    # Skip if already patched
    if docker_override_marker in content:
        print("Already patched, skipping import injection")
    else:
        import_marker = "from fastapi.security import HTTPBasic, HTTPBasicCredentials"
        if import_marker in content:
            content = content.replace(import_marker, import_marker + DOCKER_OVERRIDE_IMPORT)
        else:
            print("WARNING: Could not find import marker, trying alternative location", file=sys.stderr)
            import_marker = "from fastapi.templating import Jinja2Templates"
            if import_marker in content:
                content = content.replace(import_marker, import_marker + DOCKER_OVERRIDE_IMPORT)

    # Patch the get_service_status function
    old_get_service = 'def get_service_status() -> dict:\n    """Query systemd for hytale.service status."""'
    if old_get_service in content:
        new_get_service = 'def get_service_status_systemd() -> dict:\n    """Query systemd for hytale.service status (bare-metal mode)."""'
        content = content.replace(old_get_service, new_get_service)

        wrapper = '\n\ndef get_service_status() -> dict:\n    """Get service status (Docker-aware)."""\n    if DOCKER_MODE:\n        from docker_overrides import get_service_status as docker_get_service_status\n        return docker_get_service_status()\n    return get_service_status_systemd()\n\n'

        marker = '    data["StartTime"] = data.get("ActiveEnterTimestamp", "n/a") or "n/a"\n    return data'
        if marker in content:
            content = content.replace(marker, marker + wrapper)

    # Patch the get_logs function
    old_get_logs = 'def get_logs() -> list[str]:\n    """Fetch journal logs for hytale unit."""'
    if old_get_logs in content:
        new_get_logs = 'def get_logs_systemd() -> list[str]:\n    """Fetch journal logs for hytale unit (bare-metal mode)."""'
        content = content.replace(old_get_logs, new_get_logs)

        wrapper = '\n\ndef get_logs() -> list[str]:\n    """Get logs (Docker-aware)."""\n    if DOCKER_MODE:\n        from docker_overrides import get_logs as docker_get_logs\n        return docker_get_logs()\n    return get_logs_systemd()\n\n'

        marker = '    return output.splitlines()'
        parts = content.split(marker, 1)
        if len(parts) == 2:
            content = parts[0] + marker + wrapper + parts[1]

    # Patch the get_backup_frequency function
    old_backup_func = 'def get_backup_frequency() -> int:\n    """Read current backup frequency from hytale.service (or override)."""'
    if old_backup_func in content:
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

    # Patch the api_server_action function to use supervisorctl in Docker
    old_server_action_block = """    if DOCKER_MODE and HYTALE_CONTAINER:
        # Docker mode
        docker_actions = {
            "start": ["docker", "start", HYTALE_CONTAINER],
            "stop": ["docker", "stop", HYTALE_CONTAINER],
            "restart": ["docker", "restart", HYTALE_CONTAINER],
        }
        if action not in docker_actions:
            raise HTTPException(status_code=400, detail=f"Unbekannte Aktion: {action}")
        output, rc = run_cmd(docker_actions[action], timeout=60)
    else:
        # Native mode with systemctl
        allowed = {
            "start": ["sudo", "/bin/systemctl", "start", SERVICE_NAME],
            "stop": ["sudo", "/bin/systemctl", "stop", SERVICE_NAME],
            "restart": ["sudo", "/bin/systemctl", "restart", SERVICE_NAME],
        }
        if action not in allowed:
            raise HTTPException(status_code=400, detail=f"Unbekannte Aktion: {action}")
        output, rc = run_cmd(allowed[action], timeout=30)
"""
    new_server_action_block = """    if DOCKER_MODE:
        from docker_overrides import get_server_control_commands
        allowed = get_server_control_commands()
        if action not in allowed:
            raise HTTPException(status_code=400, detail=f"Unbekannte Aktion: {action}")
        output, rc = run_cmd(allowed[action], timeout=60)
    else:
        # Native mode with systemctl
        allowed = {
            "start": ["sudo", "/bin/systemctl", "start", SERVICE_NAME],
            "stop": ["sudo", "/bin/systemctl", "stop", SERVICE_NAME],
            "restart": ["sudo", "/bin/systemctl", "restart", SERVICE_NAME],
        }
        if action not in allowed:
            raise HTTPException(status_code=400, detail=f"Unbekannte Aktion: {action}")
        output, rc = run_cmd(allowed[action], timeout=30)
"""
    if old_server_action_block in content:
        content = content.replace(old_server_action_block, new_server_action_block, 1)

    # Patch check_auto_update function
    old_check_auto = 'def check_auto_update() -> None:\n    """If update-after-backup flag is set and a new backup appeared, trigger update."""'
    if old_check_auto in content:
        new_check_auto = 'def check_auto_update_systemd() -> None:\n    """If update-after-backup flag is set and a new backup appeared, trigger update (bare-metal)."""'
        content = content.replace(old_check_auto, new_check_auto)

        # Add wrapper before the Routes section
        wrapper = (
            "\n\ndef check_auto_update() -> None:\n"
            "    \"\"\"Check for auto-update (Docker-aware).\"\"\"\n"
            "    if DOCKER_MODE:\n"
            "        docker_check_auto_update()\n"
            "        return\n"
            "    check_auto_update_systemd()\n\n"
        )
        routes_marker = "# ---------------------------------------------------------------------------\n# Routes"
        if routes_marker in content:
            content = content.replace(routes_marker, wrapper + routes_marker)

    # Patch api_backup_run to use Docker backup
    old_backup_run = '    output, rc = run_cmd(["sudo", "/usr/local/sbin/hytale-backup.sh"], timeout=120)'
    if old_backup_run in content:
        new_backup_run = '''    if DOCKER_MODE:
        output, rc = docker_run_backup()
    else:
        output, rc = run_cmd(["sudo", "/usr/local/sbin/hytale-backup.sh"], timeout=120)'''
        content = content.replace(old_backup_run, new_backup_run)

    # Patch api_set_backup_frequency to reject in Docker mode
    old_freq_check = '@app.post("/api/config/backup-frequency")\nasync def api_set_backup_frequency(request: Request, user: str = Depends(verify_credentials)):\n    if not ALLOW_CONTROL:'
    if old_freq_check in content:
        new_freq_check = '''@app.post("/api/config/backup-frequency")
async def api_set_backup_frequency(request: Request, user: str = Depends(verify_credentials)):
    if DOCKER_MODE:
        raise HTTPException(status_code=400, detail="Backup-Frequenz kann in Docker nicht geaendert werden.")
    if not ALLOW_CONTROL:'''
        content = content.replace(old_freq_check, new_freq_check)

    # Patch api_version_check
    old_version_check = '    output, rc = await asyncio.to_thread(run_cmd, ["sudo", UPDATE_SCRIPT, "check"], 300)'
    if old_version_check in content:
        new_version_check = '''    if DOCKER_MODE:
        result = docker_check_version()
        return JSONResponse(result)
    output, rc = await asyncio.to_thread(run_cmd, ["sudo", UPDATE_SCRIPT, "check"], 300)'''
        content = content.replace(old_version_check, new_version_check)

    # Patch api_update_run
    old_update_run = '    output, rc = await asyncio.to_thread(run_cmd, ["sudo", UPDATE_SCRIPT, "update"], 600)'
    if old_update_run in content:
        new_update_run = '''    if DOCKER_MODE:
        result = docker_run_update()
        return JSONResponse(result)
    output, rc = await asyncio.to_thread(run_cmd, ["sudo", UPDATE_SCRIPT, "update"], 600)'''
        content = content.replace(old_update_run, new_update_run)

    # Patch api_players to use log files instead of journalctl
    old_players = '''@app.get("/api/players")
async def api_players(user: str = Depends(verify_credentials)):
    """Parse journalctl for player join/leave events."""
    output, rc = run_cmd(
        ["journalctl", "-u", "hytale", "--no-pager", "-o", "short-iso"],
        timeout=15
    )
    if rc != 0:
        return JSONResponse({"players": [], "error": output})'''
    if old_players in content:
        new_players = '''@app.get("/api/players")
async def api_players(user: str = Depends(verify_credentials)):
    """Parse logs for player join/leave events."""
    if DOCKER_MODE:
        players = docker_get_players()
        return JSONResponse({"players": players})
    output, rc = run_cmd(
        ["journalctl", "-u", "hytale", "--no-pager", "-o", "short-iso"],
        timeout=15
    )
    if rc != 0:
        return JSONResponse({"players": [], "error": output})'''
        content = content.replace(old_players, new_players)

    # Patch api_console_output to use log files
    old_console = '''@app.get("/api/console/output")
async def api_console_output(user: str = Depends(verify_credentials), since: str = ""):
    """Return recent log lines from journalctl."""
    cmd = ["journalctl", "-u", "hytale", "-n50", "--no-pager"]
    if since:
        cmd.extend(["--since", since])
    output, rc = run_cmd(cmd, timeout=10)
    lines = output.splitlines() if rc == 0 else [f"[Fehler: {output}]"]
    return JSONResponse({"lines": lines})'''
    if old_console in content:
        new_console = '''@app.get("/api/console/output")
async def api_console_output(user: str = Depends(verify_credentials), since: str = ""):
    """Return recent log lines."""
    if DOCKER_MODE:
        lines = docker_get_console_output(since)
        return JSONResponse({"lines": lines})
    cmd = ["journalctl", "-u", "hytale", "-n50", "--no-pager"]
    if since:
        cmd.extend(["--since", since])
    output, rc = run_cmd(cmd, timeout=10)
    lines = output.splitlines() if rc == 0 else [f"[Fehler: {output}]"]
    return JSONResponse({"lines": lines})'''
        content = content.replace(old_console, new_console)

    # Patch console/send to use command file instead of FIFO pipe in Docker mode
    old_console_send = '''@app.post("/api/console/send")
async def api_console_send(request: Request, user: str = Depends(verify_credentials)):
    if not ALLOW_CONTROL:
        raise HTTPException(status_code=403, detail="Control-Aktionen deaktiviert.")

    body = await request.json()
    command = body.get("command", "").strip()
    if not command:
        raise HTTPException(status_code=400, detail="Kein Befehl angegeben.")

    if not CONSOLE_PIPE.exists():'''
    if old_console_send in content:
        new_console_send = '''@app.post("/api/console/send")
async def api_console_send(request: Request, user: str = Depends(verify_credentials)):
    if not ALLOW_CONTROL:
        raise HTTPException(status_code=403, detail="Control-Aktionen deaktiviert.")

    body = await request.json()
    command = body.get("command", "").strip()
    if not command:
        raise HTTPException(status_code=400, detail="Kein Befehl angegeben.")

    # Docker mode: use command file instead of FIFO pipe
    if DOCKER_MODE:
        command_file = SERVER_DIR / ".server_command"
        try:
            with open(command_file, "a") as f:
                f.write(command + "\\n")
            return JSONResponse({"ok": True, "message": f"Befehl gesendet: {command}"})
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Fehler beim Senden: {e}")

    if not CONSOLE_PIPE.exists():'''
        content = content.replace(old_console_send, new_console_send)

    # Patch CF_API_KEY to use config file in Docker mode
    old_cf_key = 'CF_API_KEY = os.environ.get("CF_API_KEY", "")'
    if old_cf_key in content:
        new_cf_key = '''CF_API_KEY = os.environ.get("CF_API_KEY", "")

def get_cf_api_key_dynamic():
    """Get CurseForge API key (Docker-aware: checks config file first)."""
    if DOCKER_MODE:
        try:
            from docker_overrides import get_cf_api_key
            key = get_cf_api_key()
            if key:
                return key
        except ImportError:
            pass
    return CF_API_KEY'''
        content = content.replace(old_cf_key, new_cf_key)

    # Replace CF_API_KEY usage in cf_request with dynamic getter
    old_cf_check = '''    if not CF_API_KEY:
        raise HTTPException(status_code=500, detail="CurseForge API Key nicht konfiguriert (CF_API_KEY)")'''
    if old_cf_check in content:
        new_cf_check = '''    api_key = get_cf_api_key_dynamic() if DOCKER_MODE else CF_API_KEY
    if not api_key:
        raise HTTPException(status_code=500, detail="CurseForge API Key nicht konfiguriert (CF_API_KEY)")'''
        content = content.replace(old_cf_check, new_cf_check)

    # Replace CF_API_KEY in request headers
    old_cf_header = '"x-api-key": CF_API_KEY,'
    if old_cf_header in content:
        new_cf_header = '"x-api-key": api_key,'
        content = content.replace(old_cf_header, new_cf_header)

    # Robust patch: api_server_action (upstream signature drift safe)
    server_action_re = re.compile(
        r'@app\.post\("/api/server/\{action\}"\)\n'
        r'async def api_server_action\(action: str, user: str = Depends\(verify_credentials\)\):\n'
        r'(?:    .*\n)+?'
        r'    return \{"ok": True, "action": action\}\n',
        re.MULTILINE,
    )
    server_action_repl = """@app.post("/api/server/{action}")
async def api_server_action(action: str, user: str = Depends(verify_credentials)):
    if not ALLOW_CONTROL:
        raise HTTPException(status_code=403, detail="Control-Aktionen deaktiviert. ALLOW_CONTROL=true setzen.")

    if DOCKER_MODE:
        from docker_overrides import get_server_control_commands
        allowed = get_server_control_commands()
        timeout = 60
    else:
        allowed = {
            "start": ["sudo", "/bin/systemctl", "start", SERVICE_NAME],
            "stop": ["sudo", "/bin/systemctl", "stop", SERVICE_NAME],
            "restart": ["sudo", "/bin/systemctl", "restart", SERVICE_NAME],
        }
        timeout = 30

    if action not in allowed:
        raise HTTPException(status_code=400, detail=f"Unbekannte Aktion: {action}")

    output, rc = run_cmd(allowed[action], timeout=timeout)
    if rc != 0:
        raise HTTPException(status_code=500, detail=output)
    return {"ok": True, "action": action}
"""
    content, n_server = server_action_re.subn(server_action_repl, content, count=1)
    if n_server == 0 and 'docker_actions = {' in content:
        print('[patch] warning: api_server_action robust replacement not applied')

    # Robust patch: reject backup-frequency writes in Docker mode even if old string
    # signatures changed in upstream.
    backup_freq_anchor = '@app.post("/api/config/backup-frequency")\nasync def api_set_backup_frequency(request: Request, user: str = Depends(verify_credentials)):\n    if not ALLOW_CONTROL:'
    if backup_freq_anchor in content:
        content = content.replace(
            backup_freq_anchor,
            '@app.post("/api/config/backup-frequency")\nasync def api_set_backup_frequency(request: Request, user: str = Depends(verify_credentials)):\n    if DOCKER_MODE:\n        raise HTTPException(status_code=400, detail="Backup-Frequenz kann in Docker nicht geaendert werden.")\n    if not ALLOW_CONTROL:',
            1,
        )

    # ---------------------------------------------------------------------------
    # Hard overrides for current upstream dashboard signatures
    # ---------------------------------------------------------------------------
    # Newer upstream app.py versions changed function bodies/signatures, so some
    # string replacements above may not trigger. This fallback ensures Docker log
    # and console output always use file-based overrides instead of journalctl.
    hard_override_marker = "# [DockerPatch] hard_log_console_overrides"
    if hard_override_marker not in content:
        content += """

# [DockerPatch] hard_log_console_overrides
try:
    # Auto-detect container runtime without forcing developer/native systems.
    if not DOCKER_MODE:
        _container_markers = [
            "/.dockerenv",
            "/run/.containerenv",
            "/var/run/supervisor.sock",
            "/etc/supervisor/conf.d/supervisord.conf",
        ]
        if any(Path(m).exists() for m in _container_markers):
            DOCKER_MODE = True

    if DOCKER_MODE:
        from docker_overrides import get_service_status as _docker_get_service_status
        from docker_overrides import get_logs as _docker_get_logs
        from docker_overrides import get_console_output as _docker_get_console_output

        def get_service_status() -> dict:
            return _docker_get_service_status()

        def get_logs() -> list[str]:
            return _docker_get_logs()

        def _get_console_output(since: str = "") -> list[str]:
            return _docker_get_console_output(since)

        print("[Dashboard] Applied Docker hard overrides for status/logs/console")
except Exception as e:
    print(f"[Dashboard] Warning: Docker hard overrides not applied: {e}")
"""

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
