# Hytale Docker - Einrichtungsanleitung (Deutsch)

## Inhaltsverzeichnis

1. [Voraussetzungen](#voraussetzungen)
2. [Schnellstart](#schnellstart)
3. [Ersteinrichtung](#ersteinrichtung)
4. [Server-Download und OAuth](#server-download-und-oauth)
5. [Nach der Installation](#nach-der-installation)
6. [Konfiguration](#konfiguration)
7. [Häufige Probleme](#häufige-probleme)

---

## Voraussetzungen

- **Docker** (Version 20.10 oder neuer)
- **Docker Compose** (Version 2.0 oder neuer)
- **Hytale-Account** (für den Server-Download)
- Mindestens **4 GB RAM** für den Server
- Offene Ports: **5520/UDP** (Spiel), **8088/TCP** (Dashboard)

### Docker installieren (falls nicht vorhanden)

```bash
# Debian/Ubuntu
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# Nach der Installation: Ausloggen und wieder einloggen
```

---

## Schnellstart

```bash
# 1. Repository klonen
git clone https://github.com/zonfacter/hytale-docker.git
cd hytale-docker

# 2. Container starten
docker-compose up -d

# 3. Dashboard öffnen
# http://localhost:8088
```

---

## Ersteinrichtung

### Schritt 1: Hytale Downloader besorgen

Der Hytale Server kann nicht direkt verteilt werden - du hast zwei Optionen:

#### Option A: Manueller Download (Traditionell)

1. Besuche [hytale.com](https://hytale.com/)
2. Lade den **Server-Downloader für Linux** herunter
3. Die Datei heißt: `hytale-downloader-linux-amd64`
4. Kopiere sie in den Ordner `./data/downloader/`:

```bash
# Verzeichnis erstellen (falls nicht vorhanden)
mkdir -p ./data/downloader

# Downloader kopieren (Beispiel)
cp ~/Downloads/hytale-downloader-linux-amd64 ./data/downloader/
```

#### Option B: Automatischer Download (Empfohlen für CI/CD)

Wenn du Zugriff auf eine URL hast, die den Hytale Downloader hostet, kannst du den Download automatisieren:

1. Bearbeite `docker-compose.yml` und setze:
   ```yaml
   environment:
     - HYTALE_DOWNLOADER_URL=https://dein-server.com/hytale-downloader-linux-amd64
   ```
2. Der Downloader wird automatisch beim Container-Start heruntergeladen

⚠️ **Hinweis:** Die Downloader-URL muss von dir bereitgestellt werden. Es gibt keine offizielle öffentliche Download-URL aufgrund von Lizenzbeschränkungen.

### Schritt 2: Container starten

```bash
docker-compose up -d
```

### Schritt 3: Setup-Wizard öffnen

Öffne das Dashboard im Browser:

```
http://localhost:8088/setup
```

oder

```
http://DEINE-SERVER-IP:8088/setup
```

---

## Server-Download und OAuth

### Der OAuth-Prozess

Hytale verwendet OAuth zur Authentifizierung. Beim ersten Download musst du dich mit deinem Hytale-Account anmelden.

**So funktioniert es:**

1. Klicke im Setup-Wizard auf **"Download starten"**
2. In der Log-Ausgabe erscheint ein **OAuth-Link** (blau hervorgehoben)
3. **Kopiere den Link** und öffne ihn in deinem Browser
4. Melde dich mit deinem **Hytale-Account** an
5. Nach der Anmeldung wird der Download automatisch fortgesetzt
6. Die Credentials werden gespeichert - beim nächsten Mal ist keine Anmeldung mehr nötig

### Beispiel OAuth-Link

Der Link sieht etwa so aus:
```
https://auth.hytale.com/oauth/authorize?client_id=...&redirect_uri=...
```

### Nach dem Download

Sobald der Download abgeschlossen ist:

1. Der Setup-Wizard zeigt "Installation erfolgreich"
2. Klicke auf "Zum Dashboard"
3. Der Server startet automatisch

---

## Nach der Installation

### Dashboard-Zugangsdaten

| Einstellung | Standardwert |
|-------------|--------------|
| URL | `http://localhost:8088` |
| Benutzer | `admin` |
| Passwort | `changeme` |

**⚠️ Ändere das Passwort!** Siehe [Konfiguration](#konfiguration).

### Server-Ports

| Port | Protokoll | Verwendung |
|------|-----------|------------|
| 5520 | UDP | Hytale Spielserver |
| 5523 | TCP | Nitrado WebServer API |
| 8088 | TCP | Dashboard |

### Nützliche Befehle

```bash
# Container-Status anzeigen
docker-compose ps

# Logs anzeigen
docker-compose logs -f

# Container stoppen
docker-compose down

# Container neu starten
docker-compose restart

# Updates holen
docker-compose pull
docker-compose up -d
```

---

## Konfiguration

### Passwort ändern

Bearbeite `docker-compose.yml`:

```yaml
environment:
  - DASH_PASS=DEIN_SICHERES_PASSWORT
```

Dann Container neu starten:

```bash
docker-compose up -d
```

### CurseForge Integration

Um Mods direkt aus CurseForge zu installieren:

1. Erstelle einen kostenlosen API-Key: [console.curseforge.com](https://console.curseforge.com/)
2. Füge den Key in `docker-compose.yml` ein:

```yaml
environment:
  - CF_API_KEY=dein-api-key-hier
```

### Server-Speicher anpassen

```yaml
environment:
  - HYTALE_MEMORY_MIN=2G
  - HYTALE_MEMORY_MAX=4G
```

### Alle Umgebungsvariablen

| Variable | Standard | Beschreibung |
|----------|----------|--------------|
| `HYTALE_MEMORY_MIN` | `2G` | Minimaler Java-Heap |
| `HYTALE_MEMORY_MAX` | `4G` | Maximaler Java-Heap |
| `HYTALE_PORT` | `5520` | Spielserver-Port |
| `DASHBOARD_PORT` | `8088` | Dashboard-Port |
| `DASH_USER` | `admin` | Dashboard-Benutzer |
| `DASH_PASS` | `changeme` | Dashboard-Passwort |
| `ALLOW_CONTROL` | `true` | Server-Steuerung erlauben |
| `CF_API_KEY` | *(leer)* | CurseForge API-Key |
| `TZ` | `Europe/Berlin` | Zeitzone |

---

## Häufige Probleme

### "Downloader nicht gefunden"

**Problem:** Der Setup-Wizard zeigt "Downloader nicht gefunden"

**Lösung:**
1. Stelle sicher, dass die Datei existiert:
   ```bash
   ls -la ./data/downloader/
   ```
2. Der Dateiname muss exakt `hytale-downloader-linux-amd64` sein
3. Die Datei muss ausführbar sein (wird automatisch gesetzt)

### OAuth-Link erscheint nicht

**Problem:** Nach "Download starten" erscheint kein Link

**Lösung:**
1. Klicke auf "Log aktualisieren"
2. Warte einige Sekunden
3. Scrolle im Log nach unten
4. Prüfe, ob ein Fehler angezeigt wird

### "Connection refused" beim Dashboard

**Problem:** Browser zeigt "Connection refused"

**Lösung:**
1. Prüfe, ob der Container läuft:
   ```bash
   docker-compose ps
   ```
2. Prüfe die Logs:
   ```bash
   docker-compose logs dashboard
   ```
3. Firewall prüfen:
   ```bash
   sudo ufw allow 8088/tcp
   ```

### Server startet nicht

**Problem:** Server erscheint als "Stopped" im Dashboard

**Lösung:**
1. Prüfe die Server-Logs im Dashboard unter "Logs"
2. Oder via Docker:
   ```bash
   docker-compose logs hytale
   ```
3. Häufige Ursachen:
   - Zu wenig RAM (`HYTALE_MEMORY_MAX` erhöhen)
   - Port bereits belegt
   - Fehlende Server-Dateien

### Mods funktionieren nicht

**Problem:** Installierte Mods werden nicht geladen

**Lösung:**
1. Mods müssen als `.jar`-Dateien direkt im `mods/`-Ordner liegen
2. Nach Mod-Installation: Server neu starten
3. Prüfe die Server-Logs auf Fehler

---

## Support

- **GitHub Issues:** [github.com/zonfacter/hytale-docker/issues](https://github.com/zonfacter/hytale-docker/issues)
- **Dashboard Repository:** [github.com/zonfacter/hytale-dashboard](https://github.com/zonfacter/hytale-dashboard)

---

*Erstellt mit ❤️ von Claude Opus 4.5*
