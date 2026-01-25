"""
Setup Wizard Routes for Docker deployment.
These routes are added to the main app.py when running in Docker.
"""

import os
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
            log_content = DOWNLOAD_LOG.read_text()
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
