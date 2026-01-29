"""
Setup Wizard Routes for Docker deployment.
These routes are added to the main app.py when running in Docker.
"""

import os
import re
import subprocess
import asyncio
from pathlib import Path
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

# Configuration
HYTALE_DIR = Path(os.environ.get("HYTALE_DIR", "/opt/hytale-server"))
DOWNLOADER_DIR = HYTALE_DIR / ".downloader"
DOWNLOADER_BIN = DOWNLOADER_DIR / "hytale-downloader-linux-amd64"
CREDENTIALS_FILE = DOWNLOADER_DIR / ".hytale-downloader-credentials.json"
DOWNLOAD_LOG = HYTALE_DIR / "logs" / "download.log"
SERVER_JAR = HYTALE_DIR / "Server" / "HytaleServer.jar"
ASSETS_ZIP = HYTALE_DIR / "Assets.zip"

# ANSI escape code pattern for stripping terminal colors
ANSI_PATTERN = re.compile(r'\x1b\[[0-9;]*m|\[(?:[0-9;]*)?m')


def strip_ansi(text: str) -> str:
    """Remove ANSI escape codes from text."""
    return ANSI_PATTERN.sub('', text)


router = APIRouter()
templates = Jinja2Templates(directory=Path(__file__).parent / "templates")

# Track download process
download_process = None


@router.get("/setup", response_class=HTMLResponse)
async def setup_page(request: Request):
    """Render the setup wizard page."""
    return templates.TemplateResponse("setup.html", {"request": request})


@router.get("/api/setup/status")
async def setup_status():
    """Check the current setup status."""
    return JSONResponse({
        "downloader_exists": DOWNLOADER_BIN.exists(),
        "credentials_exist": CREDENTIALS_FILE.exists(),
        "server_installed": SERVER_JAR.exists() and ASSETS_ZIP.exists(),
        "download_running": download_process is not None and download_process.poll() is None,
    })


@router.post("/api/setup/download")
async def start_download():
    """Start the server download process."""
    global download_process

    if not DOWNLOADER_BIN.exists():
        return JSONResponse({
            "error": "Downloader nicht gefunden / Downloader not found",
            "path": str(DOWNLOADER_BIN),
        }, status_code=400)

    # Check if already running
    if download_process is not None and download_process.poll() is None:
        return JSONResponse({
            "error": "Download läuft bereits / Download already running",
        }, status_code=400)

    # Ensure log directory exists
    DOWNLOAD_LOG.parent.mkdir(parents=True, exist_ok=True)

    # Clear old log
    if DOWNLOAD_LOG.exists():
        DOWNLOAD_LOG.unlink()

    # Start download script
    download_script = DOWNLOADER_DIR / "download.sh"

    if download_script.exists():
        try:
            download_process = subprocess.Popen(
                ["/bin/bash", str(download_script)],
                cwd=str(DOWNLOADER_DIR),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            return JSONResponse({"ok": True, "pid": download_process.pid})
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=500)
    else:
        return JSONResponse({
            "error": "Download-Script nicht gefunden / Download script not found",
        }, status_code=500)


@router.get("/api/setup/log")
async def get_download_log():
    """Get the current download log content."""
    global download_process

    log_content = ""
    if DOWNLOAD_LOG.exists():
        try:
            raw_content = DOWNLOAD_LOG.read_text()
            # Strip ANSI escape codes for clean display
            log_content = strip_ansi(raw_content)
        except Exception:
            pass

    running = download_process is not None and download_process.poll() is None

    return JSONResponse({
        "log": log_content,
        "running": running,
    })


@router.post("/api/setup/cancel")
async def cancel_download():
    """Cancel the running download process."""
    global download_process

    if download_process is not None and download_process.poll() is None:
        download_process.terminate()
        download_process = None
        return JSONResponse({"ok": True, "message": "Download abgebrochen / Download cancelled"})

    return JSONResponse({"ok": False, "message": "Kein Download aktiv / No download active"})


# ============================================================================
# Settings API (Runtime Configuration)
# ============================================================================

@router.get("/api/settings")
async def get_settings():
    """Get current runtime settings."""
    try:
        from docker_overrides import load_config, get_cf_api_key, get_downloader_url
        config = load_config()
        return JSONResponse({
            "cf_api_key": "***" if config.get("cf_api_key") else "",  # Mask the key
            "cf_api_key_set": bool(config.get("cf_api_key")),
            "downloader_url": config.get("downloader_url", ""),
        })
    except ImportError:
        # Not in Docker mode
        return JSONResponse({
            "error": "Settings nur im Docker-Modus verfügbar / Settings only available in Docker mode"
        }, status_code=400)


@router.post("/api/settings")
async def update_settings(request: Request):
    """Update runtime settings."""
    try:
        from docker_overrides import load_config, save_config
    except ImportError:
        return JSONResponse({
            "error": "Settings nur im Docker-Modus verfügbar / Settings only available in Docker mode"
        }, status_code=400)

    body = await request.json()
    config = load_config()

    # Update only provided values
    if "cf_api_key" in body and body["cf_api_key"] != "***":
        config["cf_api_key"] = body["cf_api_key"]

    if "downloader_url" in body:
        config["downloader_url"] = body["downloader_url"]

    if save_config(config):
        return JSONResponse({"ok": True, "message": "Einstellungen gespeichert / Settings saved"})
    else:
        return JSONResponse({
            "error": "Speichern fehlgeschlagen / Save failed"
        }, status_code=500)


@router.post("/api/console/command")
async def send_console_command(request: Request):
    """Send a command to the server console."""
    body = await request.json()
    command = body.get("command", "").strip()

    if not command:
        return JSONResponse({"error": "No command provided"}, status_code=400)

    command_file = HYTALE_DIR / ".server_command"

    try:
        # Write command to file (server-wrapper.sh reads this)
        with open(command_file, "a") as f:
            f.write(command + "\n")
        return JSONResponse({"ok": True, "message": f"Command sent: {command}"})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/api/ports")
async def get_port_mappings():
    """Get Docker port mappings for this container."""
    try:
        from docker_overrides import get_port_mappings
        return JSONResponse(get_port_mappings())
    except ImportError:
        return JSONResponse({
            "available": False,
            "error": "Not in Docker mode",
            "internal_ports": {
                "game": "5520/udp",
                "api": "5523/tcp",
                "dashboard": "8088/tcp"
            }
        })


@router.get("/api/settings/cf-status")
async def check_cf_status():
    """Check if CurseForge API key is valid."""
    try:
        from docker_overrides import get_cf_api_key
        api_key = get_cf_api_key()
    except ImportError:
        api_key = os.environ.get("CF_API_KEY", "")

    if not api_key:
        return JSONResponse({
            "valid": False,
            "message": "Kein API-Key konfiguriert / No API key configured"
        })

    # Test the API key
    import urllib.request
    try:
        req = urllib.request.Request(
            "https://api.curseforge.com/v1/games",
            headers={"Accept": "application/json", "x-api-key": api_key}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status == 200:
                return JSONResponse({"valid": True, "message": "API-Key gültig / API key valid"})
    except Exception as e:
        return JSONResponse({
            "valid": False,
            "message": f"API-Key ungültig / API key invalid: {str(e)}"
        })

    return JSONResponse({"valid": False, "message": "Unbekannter Fehler / Unknown error"})


@router.get("/api/dashboard/version")
async def get_dashboard_version():
    """Get current dashboard version and check for updates."""
    try:
        from docker_overrides import check_dashboard_update
        return JSONResponse(check_dashboard_update())
    except ImportError:
        return JSONResponse({
            "error": "Version check nur im Docker-Modus verfügbar / Version check only available in Docker mode"
        }, status_code=400)


@router.get("/api/mods/list")
async def get_mods_list():
    """Get list of installed mods with metadata."""
    try:
        from docker_overrides import get_mods
        return JSONResponse({"mods": get_mods()})
    except ImportError:
        return JSONResponse({
            "error": "Mod-Liste nur im Docker-Modus verfügbar / Mod list only available in Docker mode"
        }, status_code=400)


@router.get("/api/plugins/check/{plugin_id}")
async def check_plugin_status(plugin_id: str):
    """Check if a specific plugin is installed."""
    try:
        from docker_overrides import check_plugin_installed
        return JSONResponse(check_plugin_installed(plugin_id))
    except ImportError:
        return JSONResponse({
            "error": "Plugin-Status nur im Docker-Modus verfügbar / Plugin status only available in Docker mode"
        }, status_code=400)


# Auto-redirect to setup if server not installed
async def check_setup_required(request: Request):
    """Middleware to redirect to setup if server is not installed."""
    # Skip for static files and API endpoints
    path = request.url.path
    if path.startswith("/static") or path.startswith("/api") or path == "/setup":
        return None

    # Check if server is installed
    if not SERVER_JAR.exists() or not ASSETS_ZIP.exists():
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url="/setup", status_code=302)

    return None
