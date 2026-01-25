# Dashboard Integration - Implementation Details

## Problem

Previously, the Dockerfile cloned the [hytale-dashboard](https://github.com/zonfacter/hytale-dashboard) repository from GitHub during the Docker build process:

```dockerfile
RUN git clone --depth 1 https://github.com/zonfacter/hytale-dashboard.git .
```

This approach had several issues:

1. **External Dependency**: Build fails if GitHub is unavailable
2. **Unreliable CI/CD**: Network issues can break automated builds
3. **Version Uncertainty**: Always pulls the latest version, which may be incompatible
4. **No Version Control**: Changes to the dashboard aren't tracked in this repository

## Solution: Git Submodule

The dashboard is now integrated as a Git submodule, providing:

✅ **Fixed Version**: The exact dashboard version is tracked in this repository  
✅ **Offline Builds**: No external network dependency during Docker build  
✅ **Reliable CI/CD**: Builds are deterministic and reproducible  
✅ **Version Control**: Dashboard updates are explicit Git commits  
✅ **Smaller Image**: Removed `git` package (no longer needed)

## Implementation

### 1. Submodule Setup

```bash
# Dashboard is added as a submodule
git submodule add https://github.com/zonfacter/hytale-dashboard.git dashboard-source
```

### 2. Dockerfile Changes

**Before:**
```dockerfile
# Clone and setup Dashboard
WORKDIR ${DASHBOARD_DIR}
RUN git clone --depth 1 https://github.com/zonfacter/hytale-dashboard.git . && \
    python3 -m venv .venv && \
    ...
```

**After:**
```dockerfile
# Copy Dashboard from submodule and setup
WORKDIR ${DASHBOARD_DIR}
COPY --chown=hytale:hytale dashboard-source/ .
RUN python3 -m venv .venv && \
    ...
```

### 3. CI/CD Integration

The GitHub Actions workflow now checks out submodules:

```yaml
- name: Checkout repository
  uses: actions/checkout@v4
  with:
    submodules: recursive
```

## Usage

### For Users (Pre-built Images)

No changes required! Simply pull the image as usual:

```bash
docker pull zonfacter/hytale-docker:latest
```

### For Developers (Building from Source)

When cloning the repository:

```bash
# Clone with submodules
git clone --recurse-submodules https://github.com/zonfacter/hytale-docker.git

# Or if already cloned
git submodule update --init --recursive
```

Then build normally:

```bash
docker build -t hytale-custom .
```

### Updating the Dashboard

To update to a newer version of the dashboard:

```bash
# Navigate to the submodule
cd dashboard-source

# Pull the latest changes
git pull origin master

# Return to the main repository
cd ..

# Commit the submodule update
git add dashboard-source
git commit -m "Update dashboard to version X.Y.Z"
git push
```

## Benefits

### Reliability

- **No external dependencies** during Docker build
- **Deterministic builds** - same input always produces same output
- **CI/CD stability** - no failures due to network issues

### Version Control

- Dashboard version is **explicitly tracked** in Git
- Easy to **rollback** to previous versions
- Clear **audit trail** of dashboard updates

### Maintenance

- **Intentional updates** - dashboard only changes when you want it to
- **Testing** - can test dashboard updates before committing
- **Compatibility** - ensures dashboard works with Docker customizations

## Docker-Specific Customizations

The repository contains Docker-specific files that modify the dashboard for containerized deployment:

- `dashboard/docker_overrides.py` - Replaces systemd with supervisord
- `dashboard/apply_docker_patches.py` - Applies patches to the dashboard
- `dashboard/setup_routes.py` - Custom setup wizard for Docker
- `dashboard/templates/setup.html` - Setup page template

These files are applied during the build process and remain unchanged by this solution.

## Migration Notes

### From Old Builds

If you previously built the image with the old method, there are no breaking changes:

- All functionality remains the same
- Environment variables unchanged
- Volume mounts unchanged
- Container behavior identical

### Submodule Best Practices

1. **Always use `--recurse-submodules`** when cloning
2. **Update intentionally** - don't auto-update submodules
3. **Test changes** before committing submodule updates
4. **Document versions** in commit messages

## Troubleshooting

### Submodule Not Initialized

**Symptom**: `dashboard-source` directory is empty

**Solution**:
```bash
git submodule update --init --recursive
```

### Build Fails with "dashboard-source not found"

**Symptom**: Docker build fails copying dashboard-source

**Solution**: Ensure submodules are initialized before building:
```bash
git submodule update --init --recursive
docker build -t hytale-custom .
```

### Dashboard Not Updating

**Symptom**: Changes to dashboard-source not reflected

**Solution**: Rebuild the Docker image after updating the submodule:
```bash
cd dashboard-source && git pull origin master && cd ..
git add dashboard-source && git commit -m "Update dashboard"
docker build --no-cache -t hytale-custom .
```

## Related Documentation

- [README.md](../README.md) - Main documentation
- [Dashboard Repository](https://github.com/zonfacter/hytale-dashboard) - Upstream dashboard
- [Dashboard Docker Overrides](../dashboard/README.md) - Docker-specific modifications
