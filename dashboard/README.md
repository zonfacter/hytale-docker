# Dashboard Docker Overrides

This directory contains Docker-specific modifications to make the Hytale Dashboard work with supervisord instead of systemd.

## Files

### `docker_overrides.py`
Provides supervisord-compatible implementations of functions that originally used systemd:

- **`get_service_status()`** - Queries `supervisorctl status` instead of `systemctl show`
- **`get_logs()`** - Reads log files from `/opt/hytale-server/logs` instead of using `journalctl`
- **`get_server_control_commands()`** - Returns supervisorctl commands for server control

### `apply_docker_patches.py`
Patches the cloned dashboard's `app.py` to use Docker overrides:

- Adds conditional imports to detect Docker environment
- Wraps systemd-dependent functions with Docker-aware versions
- Modifies server control actions to use supervisorctl
- Disables backup frequency management (not applicable in Docker)

### `setup_routes.py`
Custom setup wizard routes for Docker deployment (OAuth setup for server download).

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

## Testing

The patches are tested to ensure:
- Status parsing for RUNNING and STOPPED states works correctly
- Control commands (start/stop/restart) use supervisorctl
- Log files are read from the correct directory
- Integration with the dashboard works end-to-end

## Future

If the upstream dashboard adds native Docker support, these overrides can be removed.
