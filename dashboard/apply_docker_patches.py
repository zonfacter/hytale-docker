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

    # Patch token restore to allow restore in Docker mode
    old_token_restore_guard = '''    if DOCKER_MODE:
        raise HTTPException(status_code=400, detail="Token-Restore wird im Docker-Modus aktuell nicht unterstuetzt.")
'''
    if old_token_restore_guard in content:
        content = content.replace(old_token_restore_guard, "")

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
    # string replacements above may not trigger. This fallback force-replaces
    # critical Docker routes and runtime helpers.
    hard_override_marker = "# [DockerPatch] hard_log_console_overrides"
    if hard_override_marker not in content:
        content += """

# [DockerPatch] hard_log_console_overrides
try:
    # Auto-detect container runtime without forcing developer/native systems.
    if os.environ.get("HYTALE_DOCKER_MODE", "").lower() in ("1", "true", "yes"):
        DOCKER_MODE = True

    if not DOCKER_MODE:
        _container_markers = [
            "/.dockerenv",
            "/run/.containerenv",
            "/var/run/supervisor.sock",
            "/etc/supervisor/conf.d/supervisord.conf",
            "/proc/1/cgroup",
        ]
        if any(Path(m).exists() for m in _container_markers):
            DOCKER_MODE = True

    if DOCKER_MODE:
        import contextlib
        # Prefer Hytale 2026.01+ world config path in Docker (Server/universe).
        _new_world_cfg = SERVER_DIR / "Server" / "universe" / "worlds" / "default" / "config.json"
        _old_world_cfg = SERVER_DIR / "universe" / "worlds" / "default" / "config.json"
        if _new_world_cfg.exists():
            WORLD_CONFIG_FILE = _new_world_cfg
        elif _old_world_cfg.exists():
            WORLD_CONFIG_FILE = _old_world_cfg
        else:
            WORLD_CONFIG_FILE = _new_world_cfg
        from fastapi import Depends, HTTPException, Request
        from fastapi.responses import JSONResponse
        from fastapi.routing import APIRoute
        import docker_overrides as _dov
        _docker_get_service_status = _dov.get_service_status
        _docker_get_logs = _dov.get_logs
        _docker_get_console_output = _dov.get_console_output
        _docker_get_server_control_commands = _dov.get_server_control_commands
        _docker_send_console_command = getattr(_dov, "send_console_command", None)
        _docker_run_backup = _dov.run_backup
        _docker_restore_backup = getattr(_dov, "restore_backup", lambda *args, **kwargs: {"ok": False, "error": "Restore not available"})
        _docker_check_version = getattr(_dov, "check_version", lambda: {"current_version": "unknown", "latest_version": "unknown", "update_available": False, "docker_mode": True, "error": "version check unavailable"})
        _docker_run_update = getattr(_dov, "run_update", lambda: {"docker_mode": True, "error": "update unavailable"})
        _docker_get_tailscale_summary = getattr(_dov, "get_tailscale_summary", lambda: {"enabled": False, "connected": False, "backend_state": "unknown", "ip": "", "error": "tailscale summary unavailable"})
        _docker_get_persistence_summary = getattr(_dov, "get_persistence_summary", lambda: {"ok": True, "mounted": {}, "server_files_present": False, "warnings": []})
        _docker_get_release_update_info = getattr(_dov, "get_release_update_info", lambda: {"github_dashboard_latest": "unknown", "github_docker_latest": "unknown", "dockerhub_latest": "unknown", "links": {}, "errors": []})

        def get_service_status() -> dict:
            return _docker_get_service_status()

        def get_logs() -> list[str]:
            return _docker_get_logs()

        def _get_console_output(since: str = "") -> list[str]:
            return _docker_get_console_output(since)

        _orig_get_status_data = _get_status_data
        def _get_status_data() -> dict:
            data = _orig_get_status_data()
            with contextlib.suppress(Exception):
                data["tailscale"] = _docker_get_tailscale_summary()
            with contextlib.suppress(Exception):
                data["persistence"] = _docker_get_persistence_summary()
            with contextlib.suppress(Exception):
                data["release_updates"] = _docker_get_release_update_info()
            return data

        def _replace_route(path: str, method: str, endpoint):
            method = method.upper()
            for i in range(len(app.router.routes) - 1, -1, -1):
                r = app.router.routes[i]
                if isinstance(r, APIRoute) and r.path == path and method in (r.methods or set()):
                    app.router.routes.pop(i)
            app.add_api_route(path, endpoint, methods=[method])

        async def _docker_api_server_action(action: str, user: str = Depends(verify_credentials)):
            if not ALLOW_CONTROL:
                raise HTTPException(status_code=403, detail="Control-Aktionen deaktiviert. ALLOW_CONTROL=true setzen.")
            allowed = _docker_get_server_control_commands()
            if action not in allowed:
                raise HTTPException(status_code=400, detail=f"Unbekannte Aktion: {action}")
            output, rc = run_cmd(allowed[action], timeout=60)
            if rc != 0:
                raise HTTPException(status_code=500, detail=output)
            return {"ok": True, "action": action}

        async def _docker_api_backup_run(user: str = Depends(verify_credentials)):
            if not ALLOW_CONTROL:
                raise HTTPException(status_code=403, detail="Control-Aktionen deaktiviert. ALLOW_CONTROL=true setzen.")
            output, rc = _docker_run_backup()
            if rc != 0:
                raise HTTPException(status_code=500, detail=output)
            return {"ok": True, "output": output}

        async def _docker_api_backup_create(request: Request, user: str = Depends(verify_credentials)):
            if not ALLOW_CONTROL:
                raise HTTPException(status_code=403, detail="Control-Aktionen deaktiviert. ALLOW_CONTROL=true setzen.")
            output, rc = _docker_run_backup()
            if rc != 0:
                raise HTTPException(status_code=500, detail=output)
            return {"ok": True, "output": output}

        async def _docker_api_backup_restore(request: Request, user: str = Depends(verify_credentials)):
            if not ALLOW_CONTROL:
                raise HTTPException(status_code=403, detail="Control-Aktionen deaktiviert.")
            body = await request.json()
            name = str(body.get("name", "")).strip()
            backup_type = str(body.get("backup_type", "backup")).strip()
            include_server_state = bool(body.get("include_server_state", False))
            result = _docker_restore_backup(name, backup_type, include_server_state)
            if not result.get("ok"):
                raise HTTPException(status_code=500, detail=result.get("error", "Restore fehlgeschlagen."))
            return JSONResponse(result)

        async def _docker_api_version_check(user: str = Depends(verify_credentials)):
            return JSONResponse(_docker_check_version())

        async def _docker_api_update_run(user: str = Depends(verify_credentials)):
            return JSONResponse(_docker_run_update())

        async def _docker_api_set_backup_frequency(request: Request, user: str = Depends(verify_credentials)):
            raise HTTPException(status_code=400, detail="Backup-Frequenz kann in Docker nicht geaendert werden.")

        async def _docker_api_console_send(request: Request, user: str = Depends(verify_credentials)):
            if not ALLOW_CONTROL:
                raise HTTPException(status_code=403, detail="Control-Aktionen deaktiviert.")
            body = await request.json()
            command = str(body.get("command", "")).strip()
            if not command:
                raise HTTPException(status_code=400, detail="Kein Befehl angegeben.")
            is_allowed, error_msg = should_allow_console_command(command)
            if not is_allowed:
                raise HTTPException(status_code=400, detail=error_msg)

            if _docker_send_console_command is None:
                raise HTTPException(status_code=500, detail="Docker console adapter nicht verfuegbar")
            ok, channel_or_error = _docker_send_console_command(command)
            if not ok:
                raise HTTPException(status_code=500, detail=f"Fehler beim Senden: {channel_or_error}")
            return {"ok": True, "command": command, "channel": channel_or_error}

        async def _docker_api_auth_login_start(request: Request, user: str = Depends(verify_credentials)):
            if not ALLOW_CONTROL:
                raise HTTPException(status_code=403, detail="Control-Aktionen deaktiviert.")
            body = {}
            with contextlib.suppress(Exception):
                body = await request.json()
            method = str(body.get("method", "device")).strip().lower()
            if method not in ("device", "browser"):
                method = "device"
            command_file = SERVER_DIR / ".server_command"
            try:
                with open(command_file, "a", encoding="utf-8") as f:
                    f.write(f"/auth login {method}\\n")
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
            return {"ok": True, "message": f"Auth-Login ({method}) gestartet."}

        async def _docker_api_auth_status(user: str = Depends(verify_credentials)):
            lines = _docker_get_logs()
            auth_lines = [ln for ln in lines if re.search(r"auth|token|session", ln, re.IGNORECASE)][-60:]
            lower_lines = [ln.lower() for ln in auth_lines]

            def _last_index(patterns: list[str]) -> int:
                idx = -1
                for i, ln in enumerate(lower_lines):
                    if any(p in ln for p in patterns):
                        idx = i
                return idx

            success_idx = _last_index([
                "starting authenticated flow",
                "identity token validated",
                "requesting auth grant",
                "session service client initialized",
                "server session token loaded",
            ])
            missing_idx = _last_index(["no server tokens configured"])
            error_idx = _last_index(["session token not available", "server authentication unavailable"])
            token_file_candidates = [
                SERVER_DIR / "auth.enc",
                SERVER_DIR / "Server" / "auth.enc",
                SERVER_DIR / ".downloader" / "auth.enc",
            ]
            token_file_exists = any(p.exists() for p in token_file_candidates)
            token_configured = token_file_exists or (success_idx >= 0 and success_idx > missing_idx and success_idx > error_idx)

            return JSONResponse({
                "token_file_exists": token_file_exists,
                "token_missing": (missing_idx > success_idx) and not token_file_exists,
                "token_error": (error_idx > success_idx) and not token_file_exists,
                "token_configured": token_configured,
                "session_ready": token_configured,
                "auth_lines": auth_lines,
            })

        async def _docker_api_token_restore(request: Request, user: str = Depends(verify_credentials)):
            if not ALLOW_CONTROL:
                raise HTTPException(status_code=403, detail="Control-Aktionen deaktiviert.")
            body = await request.json()
            name = str(body.get("name", "")).strip()
            if not name or Path(name).name != name or not name.endswith(".enc"):
                raise HTTPException(status_code=400, detail="Ungueltiger Token-Backup Name.")
            output, rc = run_cmd(with_optional_sudo([TOKEN_SCRIPT, "restore", name]), timeout=180)
            if rc != 0:
                raise HTTPException(status_code=500, detail=output or "Token-Restore fehlgeschlagen.")
            return {"ok": True, "message": "Token wiederhergestellt und Server neu gestartet.", "output": output}

        _replace_route("/api/server/{action}", "POST", _docker_api_server_action)
        _replace_route("/api/backup/run", "POST", _docker_api_backup_run)
        _replace_route("/api/backup/create", "POST", _docker_api_backup_create)
        _replace_route("/api/backups/create", "POST", _docker_api_backup_create)
        _replace_route("/api/backups/restore", "POST", _docker_api_backup_restore)
        _replace_route("/api/config/backup-frequency", "POST", _docker_api_set_backup_frequency)
        _replace_route("/api/console/send", "POST", _docker_api_console_send)
        _replace_route("/api/auth/login/start", "POST", _docker_api_auth_login_start)
        _replace_route("/api/auth/status", "GET", _docker_api_auth_status)
        _replace_route("/api/token/restore", "POST", _docker_api_token_restore)
        _replace_route("/api/version/check", "POST", _docker_api_version_check)
        _replace_route("/api/update/run", "POST", _docker_api_update_run)

        print("[Dashboard] Applied Docker hard overrides for status/logs/console/routes")
except Exception as e:
    print(f"[Dashboard] Warning: Docker hard overrides not applied: {e}")
"""

    # Patch static app.js to render Tailscale status on dashboard main page.
    app_js = dashboard_dir / "static" / "app.js"
    if app_js.exists():
        js = app_js.read_text()
        js_marker = "// [DockerPatch] tailscale_status_row"
        if js_marker not in js:
            old_srv_rows = '      kv(el("serverStatus"), [\n        ["ActiveState", badge],\n        ["SubState", srv.SubState || "-"],\n        ["MainPID", srv.MainPID || "-"],\n        ["Startzeit", srv.StartTime || "-"],\n      ]);'
            new_srv_rows = '      // [DockerPatch] tailscale_status_row\n      const serverRows = [\n        ["ActiveState", badge],\n        ["SubState", srv.SubState || "-"],\n        ["MainPID", srv.MainPID || "-"],\n        ["Startzeit", srv.StartTime || "-"],\n      ];\n      const tailscale = s.tailscale || null;\n      if (tailscale && tailscale.enabled) {\n        const tsState = tailscale.connected ? "verbunden" : (tailscale.backend_state || "nicht verbunden");\n        const tsValue = tailscale.ip ? `${tsState} (${tailscale.ip})` : tsState;\n        serverRows.push(["Tailscale", tsValue]);\n      }\n      const persistence = s.persistence || null;\n      if (persistence) {\n        if (persistence.ok) {\n          serverRows.push(["Persistenz", "OK"]);\n        } else {\n          const warn = (persistence.warnings && persistence.warnings[0]) ? persistence.warnings[0] : "Persistenz unvollstaendig";\n          serverRows.push(["Persistenz", `<span style=\"color: var(--yellow);\">${warn}</span>`]);\n        }\n      }\n      const rel = s.release_updates || null;\n      const hasRelRow = rel && [rel.github_docker_latest, rel.github_dashboard_latest, rel.dockerhub_latest].some(v => v && v !== "unknown");\n      if (hasRelRow) {\n        const relText = `Docker ${rel.github_docker_latest || "?"} | Dashboard ${rel.github_dashboard_latest || "?"} | Hub ${rel.dockerhub_latest || "?"}`;\n        serverRows.push(["Updates", relText]);\n      }\n\n      let banner = document.getElementById("dockerAlertBanner");\n      const main = document.querySelector("main");\n      if (!banner && main) {\n        banner = document.createElement("section");\n        banner.id = "dockerAlertBanner";\n        banner.className = "card global-banner";\n        banner.style.gridColumn = "1 / -1";\n        main.prepend(banner);\n      }\n      if (banner) {\n        const msgs = [];\n        if (persistence && !persistence.ok && persistence.warnings) msgs.push(...persistence.warnings);\n        const hasRel = rel && [rel.github_docker_latest, rel.github_dashboard_latest, rel.dockerhub_latest].some(v => v && v !== "unknown");\n        if (hasRel) msgs.push(`Latest Releases: Docker ${rel.github_docker_latest || "?"}, Dashboard ${rel.github_dashboard_latest || "?"}, Docker Hub ${rel.dockerhub_latest || "?"}`);\n\n        if (msgs.length) {\n          const warn = !!(persistence && !persistence.ok);\n          banner.style.borderLeft = `4px solid ${warn ? "var(--yellow)" : "var(--accent)"}`;\n          banner.style.background = warn ? "rgba(234,179,8,0.08)" : "rgba(59,130,246,0.08)";\n          banner.style.marginBottom = "4px";\n          banner.innerHTML = `<h2>Hinweise / Notices</h2>${msgs.map(m => `<div style=\"font-size:13px;margin:6px 0;\">${m}</div>`).join("")}`;\n          banner.hidden = false;\n        } else {\n          banner.hidden = true;\n        }\n      }\n\n      kv(el("serverStatus"), serverRows);'
            if old_srv_rows in js:
                js = js.replace(old_srv_rows, new_srv_rows, 1)
                app_js.write_text(js)
                print(f"✓ Patched {app_js} for Tailscale status row")
            else:
                print("[patch] warning: could not patch static/app.js server status rows")

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
