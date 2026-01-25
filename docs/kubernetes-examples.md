# Kubernetes Deployment Examples for Hytale Docker

This directory contains example Kubernetes configurations that address common issues with the Hytale Docker image, particularly regarding Named Pipes (FIFO) compatibility.

## Why Special Kubernetes Configuration?

The Hytale Docker image uses Named Pipes (FIFO) for console communication. However, certain Kubernetes volume types (especially network-based storage like NFS, EBS, etc.) don't support special files like FIFOs. This causes the container to fail to start.

For detailed information about FIFO issues and alternatives, see: [IPC Mechanisms Documentation](../ipc-mechanisms.md)

## Example 1: Basic Deployment with emptyDir for Pipes (Recommended)

This configuration uses `emptyDir` volume for the console pipe, which works reliably in all Kubernetes environments:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: hytale

---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: hytale-data
  namespace: hytale
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 10Gi
  # Note: Use local or block storage, not NFS/network storage

---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: hytale-server
  namespace: hytale
spec:
  replicas: 1
  strategy:
    type: Recreate  # Important: Only one instance can run at a time
  selector:
    matchLabels:
      app: hytale-server
  template:
    metadata:
      labels:
        app: hytale-server
    spec:
      securityContext:
        fsGroup: 1000
        runAsUser: 1000
        runAsNonRoot: true
      containers:
      - name: hytale
        image: zonfacter/hytale-docker:latest
        ports:
        - name: game
          containerPort: 5520
          protocol: UDP
        - name: dashboard
          containerPort: 8088
          protocol: TCP
        - name: api
          containerPort: 5523
          protocol: TCP
        env:
        - name: HYTALE_MEMORY_MIN
          value: "2G"
        - name: HYTALE_MEMORY_MAX
          value: "4G"
        - name: DASH_PASS
          valueFrom:
            secretKeyRef:
              name: hytale-secrets
              key: dashboard-password
        - name: ALLOW_CONTROL
          value: "true"
        resources:
          requests:
            memory: "4Gi"
            cpu: "1000m"
          limits:
            memory: "6Gi"
            cpu: "2000m"
        volumeMounts:
        # Persistent volumes for game data
        - name: universe
          mountPath: /opt/hytale-server/universe
        - name: mods
          mountPath: /opt/hytale-server/mods
        - name: backups
          mountPath: /opt/hytale-server/backups
        - name: downloader
          mountPath: /opt/hytale-server/.downloader
        # Important: emptyDir for pipes to avoid FIFO issues with PVC
        - name: pipes
          mountPath: /opt/hytale-server/pipes
        livenessProbe:
          httpGet:
            path: /api/status
            port: 8088
          initialDelaySeconds: 60
          periodSeconds: 30
          timeoutSeconds: 10
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /api/status
            port: 8088
          initialDelaySeconds: 30
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3
      volumes:
      - name: universe
        persistentVolumeClaim:
          claimName: hytale-data
          subPath: universe
      - name: mods
        persistentVolumeClaim:
          claimName: hytale-data
          subPath: mods
      - name: backups
        persistentVolumeClaim:
          claimName: hytale-data
          subPath: backups
      - name: downloader
        persistentVolumeClaim:
          claimName: hytale-data
          subPath: downloader
      # emptyDir for pipes - FIFO files cannot be on network storage
      - name: pipes
        emptyDir: {}

---
apiVersion: v1
kind: Secret
metadata:
  name: hytale-secrets
  namespace: hytale
type: Opaque
stringData:
  dashboard-password: "changeme-please"

---
apiVersion: v1
kind: Service
metadata:
  name: hytale-server
  namespace: hytale
spec:
  type: LoadBalancer  # Or NodePort depending on your cluster
  selector:
    app: hytale-server
  ports:
  - name: game
    port: 5520
    targetPort: 5520
    protocol: UDP
  - name: dashboard
    port: 8088
    targetPort: 8088
    protocol: TCP
  - name: api
    port: 5523
    targetPort: 5523
    protocol: TCP
```

**Important Notes:**

1. **Pipe Volume**: The `pipes` volume uses `emptyDir` which is temporary but supports FIFO files
2. **Script Update Needed**: You'll need to modify the scripts to use `/opt/hytale-server/pipes/.console_pipe` instead of `/opt/hytale-server/.console_pipe`
3. **PVC Storage**: Use local or block storage for PVCs, not NFS or network storage
4. **Security Context**: Don't use `readOnlyRootFilesystem: true` as it prevents FIFO creation

## Example 2: With ConfigMap to Override Pipe Location

Create a ConfigMap to override the pipe location:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: hytale-scripts
  namespace: hytale
data:
  entrypoint-override.sh: |
    #!/bin/bash
    # Override CONSOLE_PIPE location to use emptyDir volume
    export CONSOLE_PIPE="/opt/hytale-server/pipes/.console_pipe"
    # Call original entrypoint
    exec /entrypoint.sh "$@"
```

Then mount and use it in the Deployment:

```yaml
spec:
  containers:
  - name: hytale
    command: ["/scripts/entrypoint-override.sh"]
    args: ["supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
    volumeMounts:
    - name: scripts
      mountPath: /scripts
    # ... other mounts ...
  volumes:
  - name: scripts
    configMap:
      name: hytale-scripts
      defaultMode: 0755
```

## Example 3: StatefulSet for Stable Storage

For production use with stable hostnames:

```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: hytale
  namespace: hytale
spec:
  serviceName: hytale
  replicas: 1
  selector:
    matchLabels:
      app: hytale-server
  template:
    # ... same as Deployment template ...
  volumeClaimTemplates:
  - metadata:
      name: data
    spec:
      accessModes: ["ReadWriteOnce"]
      storageClassName: local-storage  # Use appropriate storage class
      resources:
        requests:
          storage: 10Gi
```

## Troubleshooting in Kubernetes

### Problem: Container crashes with "Operation not supported"

**Cause**: PVC uses network storage that doesn't support FIFO files

**Solution**: 
1. Use `emptyDir` volume for pipes (as shown above)
2. Use local or block storage for PVCs, not NFS

### Problem: "Permission denied" creating FIFO

**Cause**: Security context restrictions

**Solution**:
```yaml
securityContext:
  fsGroup: 1000
  runAsUser: 1000
  # Do NOT set readOnlyRootFilesystem: true
```

### Problem: Dashboard can't send commands to server

**Diagnosis**:
```bash
# Check if pipe exists and has correct type
kubectl exec -it hytale-server-xxx -- ls -l /opt/hytale-server/.console_pipe

# Should show: prw-rw---- (p = pipe)
```

**Solution**: Ensure pipe is created in `emptyDir` volume, not on PVC

## Alternative: Using TCP Sockets

For maximum Kubernetes compatibility, consider using TCP sockets instead of FIFOs. See [IPC Mechanisms Documentation](../ipc-mechanisms.md) for implementation details.

## Further Reading

- [IPC Mechanisms & FIFO Documentation](../ipc-mechanisms.md)
- [Kubernetes Volume Types](https://kubernetes.io/docs/concepts/storage/volumes/)
- [Kubernetes Security Context](https://kubernetes.io/docs/tasks/configure-pod-container/security-context/)
