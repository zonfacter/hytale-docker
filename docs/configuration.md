# Configuration Documentation

## Supervisord Configuration in Read-Only Containers

### Overview

The Hytale Docker container supports running in read-only mode, which is important for security-hardened deployments, Kubernetes environments, and immutable infrastructure patterns.

### How Dynamic Configuration Works

#### The Problem
Previously, the entrypoint script modified the supervisord configuration file at runtime using `sed`. This approach failed in read-only containers because the configuration file in `/etc/supervisor/conf.d/` couldn't be modified.

#### The Solution
The container now uses a **writable temporary location** for runtime configuration:

1. **At Container Start:**
   - The base supervisord configuration is copied from `/etc/supervisor/conf.d/supervisord.conf` to `/tmp/supervisor/supervisord.conf`
   - This temporary copy is modified based on the presence of the Hytale server files
   - Supervisord is started using the modified configuration from `/tmp/supervisor/`

2. **Configuration Logic:**
   - If `HytaleServer.jar` and `Assets.zip` are found in `/opt/hytale-server/Server/`, the server program's `autostart` is set to `true`
   - If the server files are not found, `autostart` remains `false` (dashboard-only mode)

3. **Read-Only Compatibility:**
   - `/tmp` is always writable, even in read-only containers
   - The original configuration in `/etc/` remains unchanged
   - No write operations occur outside of `/tmp` and mounted volumes

### Running in Read-Only Mode

To run the container in read-only mode with Docker:

```bash
docker run -d \
  --name hytale-server \
  --read-only \
  --tmpfs /tmp:rw,noexec,nosuid,size=100m \
  --tmpfs /var/log/supervisor:rw,noexec,nosuid,size=50m \
  --tmpfs /run:rw,noexec,nosuid,size=50m \
  -p 8088:8088 \
  -p 5520:5520/udp \
  -v hytale-universe:/opt/hytale-server/universe \
  -v hytale-mods:/opt/hytale-server/mods \
  -v hytale-backups:/opt/hytale-server/backups \
  -v hytale-downloader:/opt/hytale-server/.downloader \
  -v hytale-logs:/opt/hytale-server/logs \
  -e DASH_PASS=changeme \
  zonfacter/hytale-docker:latest
```

#### Docker Compose Example for Read-Only Mode

```yaml
version: '3.8'

services:
  hytale:
    image: zonfacter/hytale-docker:latest
    container_name: hytale-server
    read_only: true
    tmpfs:
      - /tmp:rw,noexec,nosuid,size=100m
      - /var/log/supervisor:rw,noexec,nosuid,size=50m
      - /run:rw,noexec,nosuid,size=50m
    ports:
      - "8088:8088"
      - "5520:5520/udp"
      - "5523:5523"
    volumes:
      - hytale-universe:/opt/hytale-server/universe
      - hytale-mods:/opt/hytale-server/mods
      - hytale-backups:/opt/hytale-server/backups
      - hytale-downloader:/opt/hytale-server/.downloader
      - hytale-logs:/opt/hytale-server/logs
    environment:
      - HYTALE_MEMORY_MIN=2G
      - HYTALE_MEMORY_MAX=4G
      - DASH_USER=admin
      - DASH_PASS=changeme
      - ALLOW_CONTROL=true
    restart: unless-stopped

volumes:
  hytale-universe:
  hytale-mods:
  hytale-backups:
  hytale-downloader:
  hytale-logs:
```

### Kubernetes Deployment

For Kubernetes deployments, the read-only configuration is particularly useful:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: hytale-server
spec:
  replicas: 1
  selector:
    matchLabels:
      app: hytale-server
  template:
    metadata:
      labels:
        app: hytale-server
    spec:
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        fsGroup: 1000
      containers:
      - name: hytale
        image: zonfacter/hytale-docker:latest
        securityContext:
          readOnlyRootFilesystem: true
          allowPrivilegeEscalation: false
          capabilities:
            drop:
              - ALL
        ports:
        - containerPort: 8088
          name: dashboard
        - containerPort: 5520
          protocol: UDP
          name: game
        - containerPort: 5523
          name: api
        volumeMounts:
        - name: universe
          mountPath: /opt/hytale-server/universe
        - name: mods
          mountPath: /opt/hytale-server/mods
        - name: backups
          mountPath: /opt/hytale-server/backups
        - name: downloader
          mountPath: /opt/hytale-server/.downloader
        - name: logs
          mountPath: /opt/hytale-server/logs
        - name: tmp
          mountPath: /tmp
        - name: supervisor-log
          mountPath: /var/log/supervisor
        - name: run
          mountPath: /run
        env:
        - name: HYTALE_MEMORY_MIN
          value: "2G"
        - name: HYTALE_MEMORY_MAX
          value: "4G"
        - name: DASH_USER
          value: "admin"
        - name: DASH_PASS
          valueFrom:
            secretKeyRef:
              name: hytale-secret
              key: dashboard-password
        resources:
          requests:
            memory: "2Gi"
            cpu: "1000m"
          limits:
            memory: "4Gi"
            cpu: "2000m"
      volumes:
      - name: universe
        persistentVolumeClaim:
          claimName: hytale-universe
      - name: mods
        persistentVolumeClaim:
          claimName: hytale-mods
      - name: backups
        persistentVolumeClaim:
          claimName: hytale-backups
      - name: downloader
        persistentVolumeClaim:
          claimName: hytale-downloader
      - name: logs
        persistentVolumeClaim:
          claimName: hytale-logs
      - name: tmp
        emptyDir:
          sizeLimit: 100Mi
      - name: supervisor-log
        emptyDir:
          sizeLimit: 50Mi
      - name: run
        emptyDir:
          sizeLimit: 50Mi
```

### Technical Details

#### Files Involved

1. **`/scripts/entrypoint.sh`**
   - Copies base configuration to `/tmp/supervisor/supervisord.conf`
   - Modifies the temporary configuration based on server presence
   - Starts supervisord with the configuration from `/tmp`

2. **`/etc/supervisor/conf.d/supervisord.conf`**
   - Static base configuration included in the image
   - Never modified at runtime
   - Serves as the template for runtime configuration

#### When Configuration Changes Occur

Configuration changes happen **once at container startup**, specifically:

1. **Before supervisord starts** - The entrypoint script determines server availability
2. **During entrypoint execution** - The configuration copy is modified in `/tmp`
3. **Never during runtime** - Once supervisord is running, no further configuration changes occur

#### Writable Locations

The following locations need to be writable (automatically handled via tmpfs in read-only mode):

- `/tmp` - For temporary supervisord configuration (≈1 MB)
- `/var/log/supervisor` - For supervisor logs (≈10-50 MB)
- `/run` - For PID files and Unix sockets (≈1 MB)

#### Volume Mounts

The following locations are always writable via volume mounts:

- `/opt/hytale-server/universe` - World data
- `/opt/hytale-server/mods` - Server mods
- `/opt/hytale-server/backups` - Backup files
- `/opt/hytale-server/.downloader` - Downloader and credentials
- `/opt/hytale-server/logs` - Server logs

### Benefits

1. **Security**: Read-only root filesystem prevents container compromise from escalating
2. **Immutability**: Aligns with immutable infrastructure principles
3. **CI/CD**: Works in strict CI environments that require read-only containers
4. **Kubernetes**: Compatible with PodSecurityPolicies and SecurityContexts requiring read-only filesystems
5. **Auditability**: Clear separation between static image content and runtime state

### Migration Notes

No changes are required for existing deployments. The container works identically in both:
- **Normal mode** (writable filesystem) - Works as before
- **Read-only mode** (`--read-only` flag) - Now supported with proper tmpfs mounts

### Troubleshooting

#### Container fails to start in read-only mode

**Symptom:** Container exits immediately when `--read-only` is set

**Solution:** Ensure tmpfs mounts are configured for required writable locations:
```bash
--tmpfs /tmp:rw,noexec,nosuid,size=100m \
--tmpfs /var/log/supervisor:rw,noexec,nosuid,size=50m \
--tmpfs /run:rw,noexec,nosuid,size=50m
```

#### Supervisord configuration not being updated

**Symptom:** Server doesn't start even though files are present

**Solution:** Check entrypoint logs for configuration copy and modification:
```bash
docker logs hytale-server 2>&1 | grep -i "entrypoint\|supervisor"
```

#### Permission denied errors in /tmp

**Symptom:** `mkdir: cannot create directory '/tmp/supervisor': Permission denied`

**Solution:** Ensure `/tmp` is mounted as writable tmpfs with appropriate size:
```bash
--tmpfs /tmp:rw,noexec,nosuid,size=100m
```

### See Also

- [IPC Mechanisms & FIFO Documentation](ipc-mechanisms.md)
- [Kubernetes Examples](kubernetes-examples.md)
- [Setup Guide (English)](setup-guide-en.md)
- [Setup Guide (Deutsch)](setup-guide-de.md)
