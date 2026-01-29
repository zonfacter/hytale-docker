# Dashboard Docker Overrides

This directory contains Docker-specific modifications to make the Hytale Dashboard work with supervisord instead of systemd.

## Files

### `docker_overrides.py`
Provides supervisord-compatible implementations of functions that originally used systemd:

- **`get_service_status()`** - Queries `supervisorctl status` instead of `systemctl show`
- **`get_logs()`** - Reads log files from `/opt/hytale-server/logs` instead of using `journalctl`
- **`get_server_control_commands()`** - Returns supervisorctl commands for server control
- **`get_players_from_logs()`** - Parses player join/leave events from log files (supports multiple formats)
- **`get_console_output()`** - Returns recent console output from log files
- **`get_mods()`** - Lists installed mods with metadata (name, version, author from manifest)
- **`check_plugin_installed()`** - Checks if a specific plugin is installed
- **`check_dashboard_update()`** - Checks GitHub releases and Docker Hub for updates
- **`strip_ansi()`** - Removes ANSI escape codes from log output for clean display

### `apply_docker_patches.py`
Patches the cloned dashboard's `app.py` to use Docker overrides:

- Adds conditional imports to detect Docker environment
- Wraps systemd-dependent functions with Docker-aware versions
- Modifies server control actions to use supervisorctl
- Disables backup frequency management (not applicable in Docker)

### `setup_routes.py`
Custom setup wizard routes for Docker deployment:

- `/setup` - Setup wizard page
- `/api/setup/status` - Check setup status (downloader, credentials, server installed)
- `/api/setup/download` - Start server download
- `/api/setup/log` - Get download log (with ANSI code stripping)
- `/api/settings` - Runtime configuration (CF API key, downloader URL)
- `/api/ports` - Docker port mappings
- `/api/dashboard/version` - Dashboard version and update check
- `/api/mods/list` - List installed mods with metadata
- `/api/plugins/check/{plugin_id}` - Check plugin installation status

## How It Works

During the Docker build process:

1. The dashboard is cloned from the upstream repository
2. `docker_overrides.py` is copied to the dashboard directory
3. `apply_docker_patches.py` is executed to patch `app.py`
4. The patched dashboard detects it's running in Docker and uses supervisord commands

The solution is designed to:
- ✅ Work with official dashboard releases (no forking needed)
- ✅ Make minimal modifications only where needed
- ✅ Fall back to systemd for bare-metal installations
- ✅ Be maintainable and easy to understand

## Log Format Support

The player detection supports multiple log formats:

```
# Simple format (no timestamp)
[INFO] Adding player 'PlayerName' (uuid)
[INFO] Removing player 'PlayerName' (uuid)

# Detailed format with timestamp
[2026/01/26 19:00:36   INFO] Adding player 'Name' to world 'default' at location (x, y, z) (uuid)
[2026/01/26 19:00:36   INFO] Removing player 'Name' (uuid)

# ISO timestamp format
2026-01-26T19:00:36 INFO Adding player 'Name' (uuid)
```

ANSI escape codes are automatically stripped from all log output.

## Testing

The patches are tested to ensure:
- Status parsing for RUNNING and STOPPED states works correctly
- Control commands (start/stop/restart) use supervisorctl
- Log files are read from the correct directory
- Player detection works with various log formats
- ANSI escape code stripping works correctly
- Version comparison for update checks works correctly
- Integration with the dashboard works end-to-end

## Future

If the upstream dashboard adds native Docker support, these overrides can be removed.
