# Tailscale VPN Integration

## Overview

Tailscale VPN integration allows you to securely access your Hytale server from anywhere without port-forwarding. This is ideal for:
- 🔒 **Secure Remote Access**: Access your server dashboard from anywhere
- 🌍 **Easy Multiplayer**: Friends can join your server without NAT traversal issues
- 🔐 **Encrypted Connections**: All connections are end-to-end encrypted
- 🚫 **No Port Forwarding**: No need to expose ports to the public internet

## Prerequisites

1. A [Tailscale account](https://login.tailscale.com/start) (free for personal use)
2. Docker with support for:
   - `NET_ADMIN` and `SYS_MODULE` capabilities
   - `/dev/net/tun` device access

## Quick Start

### 1. Update docker-compose.yml

The docker-compose.yml file already includes the necessary Tailscale configuration. Simply set the environment variables:

```yaml
services:
  hytale:
    environment:
      - TAILSCALE_ENABLED=true
      - TAILSCALE_AUTHKEY=tskey-auth-xxxxx  # Optional but recommended
      - TAILSCALE_HOSTNAME=hytale-server
```

### 2. Get an Auth Key (Recommended)

1. Go to [Tailscale Admin Console → Settings → Keys](https://login.tailscale.com/admin/settings/keys)
2. Click **Generate auth key**
3. Configure the key:
   - ✅ **Reusable**: Enable if you plan to recreate the container
   - ✅ **Ephemeral**: Enable to automatically remove the device when it goes offline
   - ⏰ **Expiration**: Set to 90 days or more
4. Copy the key (starts with `tskey-auth-`)

### 3. Start the Container

```bash
docker-compose up -d
```

### 4. Verify Connection

Check the container logs:

```bash
docker-compose logs hytale | grep -i tailscale
```

You should see output like:
```
║  Tailscale Connected                                           ║
║  IP: 100.64.0.15
║  Hostname: hytale-server
║  Players can connect via: 100.64.0.15:5520
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `TAILSCALE_ENABLED` | `false` | Enable/disable Tailscale integration |
| `TAILSCALE_AUTHKEY` | *(empty)* | Auth key from Tailscale Admin Console |
| `TAILSCALE_HOSTNAME` | `hytale-server` | Hostname in your Tailscale network |
| `TAILSCALE_ADVERTISE_ROUTES` | *(empty)* | Optional: Subnet routing (e.g., `10.0.0.0/24`) |

### Docker Compose Configuration

The following configuration is already included in the provided `docker-compose.yml`:

```yaml
services:
  hytale:
    # Required capabilities for Tailscale
    cap_add:
      - NET_ADMIN
      - SYS_MODULE
    
    # Required device for Tailscale
    devices:
      - /dev/net/tun:/dev/net/tun
    
    # Environment variables
    environment:
      - TAILSCALE_ENABLED=false  # Set to true to enable
      - TAILSCALE_AUTHKEY=       # Optional auth key
      - TAILSCALE_HOSTNAME=hytale-server
      - TAILSCALE_ADVERTISE_ROUTES=
    
    # Persistent Tailscale state
    volumes:
      - hytale-tailscale:/var/lib/tailscale

volumes:
  hytale-tailscale:
    driver: local
```

## Usage

### Dashboard Access

Once Tailscale is connected, you can access the dashboard using the Tailscale IP:

```
http://100.64.0.15:8088
```

Replace `100.64.0.15` with your actual Tailscale IP (shown in container logs or dashboard).

### Player Connection

Players who are also on your Tailscale network can connect using:

```
100.64.0.15:5520
```

### Dashboard UI

The setup wizard includes a Tailscale section that shows:
- ✅ Connection status (Connected/Not connected)
- 📍 Tailscale IP address
- 🎮 Connection string for players
- 🔄 Refresh button to update status

Access it at: `http://localhost:8088/setup` (or via your Tailscale IP)

### API Endpoints

The dashboard exposes authenticated REST API endpoints:

#### Get Status
```bash
curl -u admin:changeme http://localhost:8088/api/tailscale/status
```

Response:
```json
{
  "enabled": true,
  "connected": true,
  "backend_state": "Running",
  "hostname": "hytale-server",
  "tailscale_ips": ["100.64.0.15"],
  "online": true,
  "peers": 3
}
```

#### Get IP Address
```bash
curl -u admin:changeme http://localhost:8088/api/tailscale/ip
```

Response:
```json
{
  "enabled": true,
  "ip": "100.64.0.15",
  "ipv4": "100.64.0.15",
  "hytale_port": "5520"
}
```

#### Start Connection
```bash
curl -u admin:changeme -X POST http://localhost:8088/api/tailscale/up \
  -H "Content-Type: application/json" \
  -d '{"hostname": "my-hytale-server"}'
```

#### Stop Connection
```bash
curl -u admin:changeme -X POST http://localhost:8088/api/tailscale/down
```

## Manual Authentication

If you didn't provide an auth key, you'll need to manually authenticate:

### Option 1: Using the Browser

```bash
docker exec -it hytale-server tailscale up
```

This will output a URL. Open it in your browser and log in to Tailscale.

### Option 2: Using Device Authorization

```bash
docker exec -it hytale-server tailscale up --qr
```

This displays a QR code you can scan with the Tailscale mobile app.

## Troubleshooting

### Tailscale not starting

**Symptom**: Container starts but Tailscale doesn't connect

**Solutions**:
1. Check if Tailscale is enabled:
   ```bash
   docker exec hytale-server env | grep TAILSCALE
   ```
   
2. Check capabilities:
   ```bash
   docker inspect hytale-server | grep -A 10 "CapAdd"
   ```
   Should show `NET_ADMIN` and `SYS_MODULE`

3. Check device access:
   ```bash
   docker exec hytale-server ls -l /dev/net/tun
   ```
   Should exist and be accessible

4. Check tailscaled logs:
   ```bash
   docker exec hytale-server cat /var/log/supervisor/tailscaled.log
   ```

### Connection refused

**Symptom**: Can't access dashboard via Tailscale IP

**Solutions**:
1. Verify Tailscale is connected:
   ```bash
   docker exec hytale-server tailscale status
   ```

2. Check if dashboard is running:
   ```bash
   docker exec hytale-server supervisorctl status dashboard
   ```

3. Verify port is correct (default 8088):
   ```bash
   docker exec hytale-server env | grep DASHBOARD_PORT
   ```

### Auth key not working

**Symptom**: Container starts but requires manual authentication

**Solutions**:
1. Verify auth key is set correctly:
   ```bash
   docker exec hytale-server env | grep TAILSCALE_AUTHKEY
   ```

2. Check if auth key is expired:
   - Go to [Tailscale Admin Console → Settings → Keys](https://login.tailscale.com/admin/settings/keys)
   - Generate a new key if expired

3. Check connection script logs:
   ```bash
   docker exec hytale-server cat /var/log/supervisor/tailscale-connect.log
   ```

### State persistence issues

**Symptom**: Need to re-authenticate after container restart

**Solutions**:
1. Verify volume is mounted:
   ```bash
   docker volume inspect hytale-tailscale
   ```

2. Check volume contents:
   ```bash
   docker exec hytale-server ls -la /var/lib/tailscale/
   ```

3. Ensure volume persists between restarts (don't use `docker-compose down -v`)

## Security Considerations

### Auth Keys

- **Treat auth keys as secrets**: Never commit them to version control
- **Use ephemeral keys** for testing/development
- **Use reusable keys** for production with long expiration
- **Rotate keys regularly**: Generate new keys every 90 days

### Access Control

- **Use ACLs**: Configure [Tailscale ACLs](https://tailscale.com/kb/1018/acls) to restrict access
- **Principle of least privilege**: Only allow necessary connections
- **Monitor connected devices**: Regularly review devices in Tailscale Admin Console

### Network Exposure

- **Tailscale is encrypted**: All traffic is end-to-end encrypted via WireGuard
- **No port forwarding needed**: Ports don't need to be exposed to the internet
- **Private network**: Only devices on your Tailscale network can connect

## Advanced Configuration

### Subnet Routing

To make your entire local network accessible via Tailscale:

1. Enable IP forwarding on the host:
   ```bash
   sysctl -w net.ipv4.ip_forward=1
   ```

2. Set the advertise routes environment variable:
   ```yaml
   environment:
     - TAILSCALE_ADVERTISE_ROUTES=192.168.1.0/24
   ```

3. Approve the routes in [Tailscale Admin Console](https://login.tailscale.com/admin/machines)

### Using with Kubernetes

For Kubernetes deployments, see [kubernetes-examples.md](kubernetes-examples.md) and add:

```yaml
spec:
  template:
    spec:
      containers:
      - name: hytale
        env:
        - name: TAILSCALE_ENABLED
          value: "true"
        - name: TAILSCALE_AUTHKEY
          valueFrom:
            secretKeyRef:
              name: tailscale-auth
              key: authkey
        securityContext:
          capabilities:
            add:
            - NET_ADMIN
            - SYS_MODULE
```

## References

- [Tailscale Documentation](https://tailscale.com/kb/)
- [Tailscale in Docker](https://tailscale.com/kb/1282/docker)
- [Tailscale Auth Keys](https://tailscale.com/kb/1085/auth-keys)
- [Tailscale ACLs](https://tailscale.com/kb/1018/acls)
