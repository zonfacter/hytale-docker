# Inter-Process Communication (IPC) für Hytale Server Console / IPC Mechanisms for Hytale Server Console

[🇩🇪 Deutsche Version](#deutsche-version) | [🇬🇧 English Version](#english-version)

---

## Deutsche Version

### Übersicht

Dieses Docker-Image verwendet standardmäßig **Named Pipes (FIFOs)** für die Server-Konsolen-Kommunikation. Named Pipes ermöglichen es dem Dashboard, Befehle an den laufenden Hytale-Server zu senden.

### Aktuelle Implementierung: Named Pipes (FIFO)

#### Wie es funktioniert

1. **Pipe-Erstellung**: Beim Start erstellt `entrypoint.sh` eine Named Pipe:
   ```bash
   mkfifo /opt/hytale-server/.console_pipe
   ```

2. **Server-Start**: Der `start-server.sh` Script leitet die Pipe zur stdin des Java-Prozesses:
   ```bash
   tail -f .console_pipe | java -jar Server/HytaleServer.jar ...
   ```

3. **Befehlsausführung**: Das Dashboard oder andere Prozesse schreiben Befehle in die Pipe:
   ```bash
   echo "stop" > /opt/hytale-server/.console_pipe
   ```

#### Vorteile von Named Pipes

- ✅ **Einfach**: Einfache Implementierung mit Standard Unix-Tools
- ✅ **Keine Netzwerk-Ports**: Kommunikation über Dateisystem
- ✅ **Geringe Latenz**: Direkte Kernel-Level-Kommunikation
- ✅ **Berechtigungskontrolle**: Nutzung von Dateisystem-Permissions

#### Bekannte Probleme mit Named Pipes in Docker

##### 1. **Storage-Driver-Kompatibilität**

Verschiedene Docker Storage-Treiber haben unterschiedliche Unterstützung für spezielle Dateitypen:

| Storage Driver | FIFO-Unterstützung | Bemerkungen |
|----------------|-------------------|-------------|
| **overlay2** | ✅ Vollständig | Standard-Treiber, funktioniert gut |
| **aufs** | ⚠️ Eingeschränkt | Älterer Treiber, kann Probleme haben |
| **btrfs** | ✅ Vollständig | Funktioniert gut |
| **zfs** | ✅ Vollständig | Funktioniert gut |
| **devicemapper** | ⚠️ Variabel | Abhängig von der Konfiguration |
| **vfs** | ✅ Vollständig | Langsam, aber zuverlässig |

**Symptome bei Inkompatibilität:**
- Container startet nicht oder stürzt ab
- Fehler: "Operation not supported" oder "Invalid argument"
- Pipe kann nicht erstellt oder verwendet werden

**Lösung:**
```bash
# Storage Driver prüfen
docker info | grep "Storage Driver"

# Bei Problemen: Zu overlay2 wechseln (empfohlen)
# /etc/docker/daemon.json:
{
  "storage-driver": "overlay2"
}
```

##### 2. **Kubernetes-Probleme**

In Kubernetes-Umgebungen können Named Pipes problematisch sein:

**Problem 1: Volume-Typen**
- `emptyDir`: ✅ Funktioniert (temporär im Container)
- `hostPath`: ⚠️ Abhängig vom Host-Storage-Treiber
- `persistentVolumeClaim` (NFS): ❌ Nicht unterstützt
- `persistentVolumeClaim` (local): ✅ Funktioniert meist
- `persistentVolumeClaim` (Cloud-Storage): ❌ Oft nicht unterstützt

**Problem 2: Security Context**
- ReadOnlyRootFilesystem: ❌ Verhindert FIFO-Erstellung
- fsGroup/runAsUser: ⚠️ Kann Berechtigungsprobleme verursachen

**Beispiel-Symptome:**
```
mkfifo: cannot create fifo '/opt/hytale-server/.console_pipe': Operation not permitted
```

**Kubernetes-Workarounds:**

```yaml
# Option 1: emptyDir für Pipe (empfohlen für K8s)
apiVersion: v1
kind: Pod
spec:
  containers:
  - name: hytale
    volumeMounts:
    - name: pipe-dir
      mountPath: /opt/hytale-server/pipes
  volumes:
  - name: pipe-dir
    emptyDir: {}
```

```yaml
# Option 2: Security Context anpassen
spec:
  securityContext:
    fsGroup: 1000
    runAsUser: 1000
  containers:
  - name: hytale
    securityContext:
      allowPrivilegeEscalation: false
      # Wichtig: readOnlyRootFilesystem NICHT verwenden
```

##### 3. **Windows Docker Desktop**

Named Pipes funktionieren eingeschränkt auf Windows:

- ✅ **WSL2-Backend**: Funktioniert gut (Linux-Kernel)
- ⚠️ **Hyper-V-Backend**: Kann Probleme haben
- ❌ **Windows Container**: Nutzen Named Pipes anders (nicht kompatibel)

**Empfehlung für Windows:**
- WSL2-Backend verwenden
- Oder alternative IPC-Methode wählen (siehe unten)

##### 4. **Performance-Überlegungen**

Bei hoher Last können Named Pipes zu Problemen führen:

- **Buffer-Overflow**: Pipe-Puffer ist begrenzt (typisch 64 KB)
- **Blockierende Schreibvorgänge**: Wenn niemand liest
- **Deadlock-Risiko**: Bei falscher Implementierung

**Monitoring:**
```bash
# Pipe-Zustand überprüfen
ls -l /opt/hytale-server/.console_pipe
# Sollte anzeigen: prw-rw---- (p = pipe)

# Offene Dateideskriptoren prüfen
lsof | grep console_pipe
```

---

### Alternative IPC-Mechanismen

#### Option 1: Unix Domain Sockets (Empfohlen)

Unix Domain Sockets sind zuverlässiger als Named Pipes in Container-Umgebungen.

**Vorteile:**
- ✅ Bessere Unterstützung in allen Storage-Treibern
- ✅ Bidirektionale Kommunikation
- ✅ Verbindungsorientiert (keine verlorenen Daten)
- ✅ Bessere Fehlerbehandlung

**Implementierung:**

```bash
# server-socket.sh - Beispiel mit netcat
#!/bin/bash
SOCKET="/opt/hytale-server/.console.sock"

# Socket erstellen und Server lauschen lassen
rm -f "$SOCKET"
socat UNIX-LISTEN:"$SOCKET",fork EXEC:"java -jar Server/HytaleServer.jar ..."
```

```bash
# Befehl senden
echo "stop" | socat - UNIX-CONNECT:/opt/hytale-server/.console.sock
```

**Kubernetes-Kompatibilität:**
- ✅ Funktioniert mit allen Volume-Typen
- ✅ Keine speziellen Security-Context-Anforderungen

#### Option 2: TCP-Socket (localhost)

Für maximale Kompatibilität, auch über Netzwerk.

**Vorteile:**
- ✅ Funktioniert überall
- ✅ Kann über Netzwerk genutzt werden (optional)
- ✅ Viele Bibliotheken verfügbar

**Nachteile:**
- ⚠️ Zusätzlicher Port erforderlich
- ⚠️ Sicherheit: Authentifizierung nötig

**Implementierung:**

```bash
# server-tcp.sh
#!/bin/bash
CONSOLE_PORT=25575  # Minecraft RCON-Standard

# Server mit RCON oder eigenem TCP-Listener starten
java -jar Server/HytaleServer.jar --rcon-port "$CONSOLE_PORT" ...
```

```bash
# Befehl senden (mit mcrcon tool)
mcrcon -H 127.0.0.1 -P 25575 -p "$RCON_PASSWORD" "stop"
```

#### Option 3: Supervisord stdin/stdout

Nutzung von supervisord's eigener IPC.

**Vorteile:**
- ✅ Bereits integriert
- ✅ Keine zusätzlichen Pipes/Sockets
- ✅ Funktioniert überall

**Nachteile:**
- ⚠️ Supervisord-spezifisch
- ⚠️ Begrenzte Funktionalität

**Implementierung:**

```python
# Via supervisord XML-RPC API
import xmlrpc.client

server = xmlrpc.client.ServerProxy('http://localhost:9001/RPC2')
server.supervisor.sendProcessStdin('hytale-server', 'stop\n')
```

---

### Vergleichstabelle: IPC-Mechanismen

| Methode | Komplexität | Docker | Kubernetes | Windows | Bidirektional | Performance |
|---------|-------------|--------|------------|---------|---------------|-------------|
| **Named Pipes (FIFO)** | Niedrig | ✅ | ⚠️ | ⚠️ | ❌ | Hoch |
| **Unix Domain Sockets** | Mittel | ✅ | ✅ | ⚠️ | ✅ | Hoch |
| **TCP Sockets** | Mittel | ✅ | ✅ | ✅ | ✅ | Mittel |
| **Supervisord IPC** | Mittel | ✅ | ✅ | ✅ | ✅ | Mittel |

**Empfehlungen:**

1. **Standard Docker**: Named Pipes (aktuell) ✅
2. **Kubernetes**: Unix Domain Sockets mit `emptyDir` 🎯
3. **Windows**: TCP Sockets oder Supervisord IPC 🪟
4. **Cloud-Native**: TCP Sockets mit Authentifizierung ☁️

---

### Konfiguration & Umschalten

Aktuell nutzt das Image nur Named Pipes. In Zukunft könnte eine Umgebungsvariable implementiert werden:

```yaml
# docker-compose.yml (zukünftig)
environment:
  - CONSOLE_IPC_METHOD=fifo  # oder: socket, tcp, supervisord
```

---

### Fehlerbehebung

#### Problem: "mkfifo: Operation not supported"

**Ursache:** Storage-Driver unterstützt keine Special Files

**Lösung:**
```bash
# Storage Driver wechseln
sudo systemctl stop docker
sudo vim /etc/docker/daemon.json
# Setzen: {"storage-driver": "overlay2"}
sudo systemctl start docker
```

#### Problem: Pipe existiert, aber Befehle kommen nicht an

**Diagnose:**
```bash
# Container betreten
docker exec -it hytale-server bash

# Pipe-Status prüfen
ls -l /opt/hytale-server/.console_pipe

# Test: Befehl direkt schreiben
echo "help" > /opt/hytale-server/.console_pipe

# Prozess-Stdout überprüfen
docker logs hytale-server
```

**Lösung:**
- Sicherstellen, dass `tail -f` läuft
- Berechtigungen prüfen (660, hytale:hytale)
- Pipe neu erstellen: `rm -f .console_pipe && mkfifo .console_pipe`

#### Problem: Kubernetes "Read-only file system"

**Ursache:** `readOnlyRootFilesystem: true` in Security Context

**Lösung:**
```yaml
# Separates Volume für Pipes
volumes:
- name: pipes
  emptyDir: {}
volumeMounts:
- name: pipes
  mountPath: /opt/hytale-server/pipes
```

Dann in Scripts: `CONSOLE_PIPE="/opt/hytale-server/pipes/.console_pipe"`

---

### Weitere Informationen

- [Docker Storage Drivers](https://docs.docker.com/storage/storagedriver/)
- [Kubernetes Volume Types](https://kubernetes.io/docs/concepts/storage/volumes/)
- [Unix Named Pipes (FIFO)](https://man7.org/linux/man-pages/man7/fifo.7.html)
- [Unix Domain Sockets](https://man7.org/linux/man-pages/man7/unix.7.html)

---

## English Version

### Overview

This Docker image uses **Named Pipes (FIFOs)** by default for server console communication. Named Pipes allow the dashboard to send commands to the running Hytale server.

### Current Implementation: Named Pipes (FIFO)

#### How it Works

1. **Pipe Creation**: On startup, `entrypoint.sh` creates a Named Pipe:
   ```bash
   mkfifo /opt/hytale-server/.console_pipe
   ```

2. **Server Start**: The `start-server.sh` script pipes the FIFO to the Java process stdin:
   ```bash
   tail -f .console_pipe | java -jar Server/HytaleServer.jar ...
   ```

3. **Command Execution**: The dashboard or other processes write commands to the pipe:
   ```bash
   echo "stop" > /opt/hytale-server/.console_pipe
   ```

#### Advantages of Named Pipes

- ✅ **Simple**: Easy implementation with standard Unix tools
- ✅ **No Network Ports**: Communication via filesystem
- ✅ **Low Latency**: Direct kernel-level communication
- ✅ **Permission Control**: Uses filesystem permissions

#### Known Issues with Named Pipes in Docker

##### 1. **Storage Driver Compatibility**

Different Docker storage drivers have varying support for special file types:

| Storage Driver | FIFO Support | Notes |
|----------------|-------------|-------|
| **overlay2** | ✅ Full | Default driver, works well |
| **aufs** | ⚠️ Limited | Older driver, may have issues |
| **btrfs** | ✅ Full | Works well |
| **zfs** | ✅ Full | Works well |
| **devicemapper** | ⚠️ Variable | Depends on configuration |
| **vfs** | ✅ Full | Slow but reliable |

**Symptoms of Incompatibility:**
- Container won't start or crashes
- Error: "Operation not supported" or "Invalid argument"
- Pipe cannot be created or used

**Solution:**
```bash
# Check storage driver
docker info | grep "Storage Driver"

# If issues: Switch to overlay2 (recommended)
# /etc/docker/daemon.json:
{
  "storage-driver": "overlay2"
}
```

##### 2. **Kubernetes Issues**

Named Pipes can be problematic in Kubernetes environments:

**Problem 1: Volume Types**
- `emptyDir`: ✅ Works (temporary in container)
- `hostPath`: ⚠️ Depends on host storage driver
- `persistentVolumeClaim` (NFS): ❌ Not supported
- `persistentVolumeClaim` (local): ✅ Usually works
- `persistentVolumeClaim` (Cloud Storage): ❌ Often not supported

**Problem 2: Security Context**
- ReadOnlyRootFilesystem: ❌ Prevents FIFO creation
- fsGroup/runAsUser: ⚠️ May cause permission issues

**Example Symptoms:**
```
mkfifo: cannot create fifo '/opt/hytale-server/.console_pipe': Operation not permitted
```

**Kubernetes Workarounds:**

```yaml
# Option 1: emptyDir for pipe (recommended for K8s)
apiVersion: v1
kind: Pod
spec:
  containers:
  - name: hytale
    volumeMounts:
    - name: pipe-dir
      mountPath: /opt/hytale-server/pipes
  volumes:
  - name: pipe-dir
    emptyDir: {}
```

```yaml
# Option 2: Adjust Security Context
spec:
  securityContext:
    fsGroup: 1000
    runAsUser: 1000
  containers:
  - name: hytale
    securityContext:
      allowPrivilegeEscalation: false
      # Important: Do NOT use readOnlyRootFilesystem
```

##### 3. **Windows Docker Desktop**

Named Pipes work with limitations on Windows:

- ✅ **WSL2 Backend**: Works well (Linux kernel)
- ⚠️ **Hyper-V Backend**: May have issues
- ❌ **Windows Containers**: Use Named Pipes differently (incompatible)

**Recommendation for Windows:**
- Use WSL2 backend
- Or choose alternative IPC method (see below)

##### 4. **Performance Considerations**

Under high load, Named Pipes can cause issues:

- **Buffer Overflow**: Pipe buffer is limited (typically 64 KB)
- **Blocking Writes**: When no reader is present
- **Deadlock Risk**: With incorrect implementation

**Monitoring:**
```bash
# Check pipe state
ls -l /opt/hytale-server/.console_pipe
# Should show: prw-rw---- (p = pipe)

# Check open file descriptors
lsof | grep console_pipe
```

---

### Alternative IPC Mechanisms

#### Option 1: Unix Domain Sockets (Recommended)

Unix Domain Sockets are more reliable than Named Pipes in container environments.

**Advantages:**
- ✅ Better support across all storage drivers
- ✅ Bidirectional communication
- ✅ Connection-oriented (no lost data)
- ✅ Better error handling

**Implementation:**

```bash
# server-socket.sh - Example with netcat
#!/bin/bash
SOCKET="/opt/hytale-server/.console.sock"

# Create socket and listen
rm -f "$SOCKET"
socat UNIX-LISTEN:"$SOCKET",fork EXEC:"java -jar Server/HytaleServer.jar ..."
```

```bash
# Send command
echo "stop" | socat - UNIX-CONNECT:/opt/hytale-server/.console.sock
```

**Kubernetes Compatibility:**
- ✅ Works with all volume types
- ✅ No special security context requirements

#### Option 2: TCP Socket (localhost)

For maximum compatibility, including over network.

**Advantages:**
- ✅ Works everywhere
- ✅ Can be used over network (optional)
- ✅ Many libraries available

**Disadvantages:**
- ⚠️ Additional port required
- ⚠️ Security: Authentication needed

**Implementation:**

```bash
# server-tcp.sh
#!/bin/bash
CONSOLE_PORT=25575  # Minecraft RCON standard

# Start server with RCON or custom TCP listener
java -jar Server/HytaleServer.jar --rcon-port "$CONSOLE_PORT" ...
```

```bash
# Send command (with mcrcon tool)
mcrcon -H 127.0.0.1 -P 25575 -p "$RCON_PASSWORD" "stop"
```

#### Option 3: Supervisord stdin/stdout

Using supervisord's built-in IPC.

**Advantages:**
- ✅ Already integrated
- ✅ No additional pipes/sockets
- ✅ Works everywhere

**Disadvantages:**
- ⚠️ Supervisord-specific
- ⚠️ Limited functionality

**Implementation:**

```python
# Via supervisord XML-RPC API
import xmlrpc.client

server = xmlrpc.client.ServerProxy('http://localhost:9001/RPC2')
server.supervisor.sendProcessStdin('hytale-server', 'stop\n')
```

---

### Comparison Table: IPC Mechanisms

| Method | Complexity | Docker | Kubernetes | Windows | Bidirectional | Performance |
|--------|------------|--------|------------|---------|---------------|-------------|
| **Named Pipes (FIFO)** | Low | ✅ | ⚠️ | ⚠️ | ❌ | High |
| **Unix Domain Sockets** | Medium | ✅ | ✅ | ⚠️ | ✅ | High |
| **TCP Sockets** | Medium | ✅ | ✅ | ✅ | ✅ | Medium |
| **Supervisord IPC** | Medium | ✅ | ✅ | ✅ | ✅ | Medium |

**Recommendations:**

1. **Standard Docker**: Named Pipes (current) ✅
2. **Kubernetes**: Unix Domain Sockets with `emptyDir` 🎯
3. **Windows**: TCP Sockets or Supervisord IPC 🪟
4. **Cloud-Native**: TCP Sockets with authentication ☁️

---

### Configuration & Switching

Currently, the image only uses Named Pipes. In the future, an environment variable could be implemented:

```yaml
# docker-compose.yml (future)
environment:
  - CONSOLE_IPC_METHOD=fifo  # or: socket, tcp, supervisord
```

---

### Troubleshooting

#### Issue: "mkfifo: Operation not supported"

**Cause:** Storage driver doesn't support special files

**Solution:**
```bash
# Switch storage driver
sudo systemctl stop docker
sudo vim /etc/docker/daemon.json
# Set: {"storage-driver": "overlay2"}
sudo systemctl start docker
```

#### Issue: Pipe exists but commands don't arrive

**Diagnosis:**
```bash
# Enter container
docker exec -it hytale-server bash

# Check pipe status
ls -l /opt/hytale-server/.console_pipe

# Test: Write command directly
echo "help" > /opt/hytale-server/.console_pipe

# Check process stdout
docker logs hytale-server
```

**Solution:**
- Ensure `tail -f` is running
- Check permissions (660, hytale:hytale)
- Recreate pipe: `rm -f .console_pipe && mkfifo .console_pipe`

#### Issue: Kubernetes "Read-only file system"

**Cause:** `readOnlyRootFilesystem: true` in Security Context

**Solution:**
```yaml
# Separate volume for pipes
volumes:
- name: pipes
  emptyDir: {}
volumeMounts:
- name: pipes
  mountPath: /opt/hytale-server/pipes
```

Then in scripts: `CONSOLE_PIPE="/opt/hytale-server/pipes/.console_pipe"`

---

### Further Information

- [Docker Storage Drivers](https://docs.docker.com/storage/storagedriver/)
- [Kubernetes Volume Types](https://kubernetes.io/docs/concepts/storage/volumes/)
- [Unix Named Pipes (FIFO)](https://man7.org/linux/man-pages/man7/fifo.7.html)
- [Unix Domain Sockets](https://man7.org/linux/man-pages/man7/unix.7.html)

---

*Documentation created for hytale-docker project*
