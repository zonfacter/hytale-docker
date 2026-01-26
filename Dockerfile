#===============================================================================
# Hytale Server + Dashboard Docker Image
# https://github.com/zonfacter/hytale-docker
#===============================================================================

# Build arguments for customization
ARG DEBIAN_BASE_IMAGE=debian:trixie-slim
ARG DEBIAN_CODENAME=trixie
ARG JAVA_VERSION=24

FROM ${DEBIAN_BASE_IMAGE}

LABEL maintainer="zonfacter"
LABEL description="Hytale Dedicated Server with Web Dashboard"
LABEL version="1.6.0"

# Environment variables
ENV DEBIAN_FRONTEND=noninteractive \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    # Hytale Server
    HYTALE_DIR=/opt/hytale-server \
    HYTALE_PORT=5520 \
    HYTALE_MEMORY_MIN=2G \
    HYTALE_MEMORY_MAX=4G \
    # Downloader (optional: set URL to auto-download)
    HYTALE_DOWNLOADER_URL="" \
    # Dashboard
    DASHBOARD_DIR=/opt/hytale-dashboard \
    DASHBOARD_PORT=8088 \
    DASH_USER=admin \
    DASH_PASS=changeme \
    ALLOW_CONTROL=true \
    CF_API_KEY="" \
    # Internal
    PUID=1000 \
    PGID=1000

# Install dependencies and Eclipse Temurin Java 21
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Utilities first (needed for adding repo)
    curl \
    wget \
    gnupg \
    ca-certificates \
    # Python for Dashboard
    python3 \
    python3-venv \
    python3-pip \
    # Other utilities
    unzip \
    procps \
    supervisor \
    gosu \
    screen \
    && rm -rf /var/lib/apt/lists/*

# Install Eclipse Temurin Java (Adoptium)
# Re-declare ARGs after FROM to make them available in this build stage
# (ARGs before FROM are only available for the FROM instruction)
ARG DEBIAN_CODENAME
ARG JAVA_VERSION
RUN curl -fsSL https://packages.adoptium.net/artifactory/api/gpg/key/public | gpg --dearmor -o /usr/share/keyrings/adoptium.gpg \
    && echo "deb [signed-by=/usr/share/keyrings/adoptium.gpg] https://packages.adoptium.net/artifactory/deb ${DEBIAN_CODENAME} main" > /etc/apt/sources.list.d/adoptium.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends temurin-${JAVA_VERSION}-jre \
    && rm -rf /var/lib/apt/lists/*

# Create users and directories
RUN groupadd -g ${PGID} hytale && \
    useradd -u ${PUID} -g hytale -m -d ${HYTALE_DIR} -s /bin/bash hytale && \
    mkdir -p ${HYTALE_DIR}/{backups,mods,universe/worlds/default,.downloader,logs} && \
    mkdir -p ${DASHBOARD_DIR} && \
    chown -R hytale:hytale ${HYTALE_DIR}

# Copy Dashboard from submodule and setup
WORKDIR ${DASHBOARD_DIR}
COPY --chown=hytale:hytale dashboard-source/ .
RUN python3 -m venv .venv && \
    .venv/bin/pip install --no-cache-dir --upgrade pip && \
    .venv/bin/pip install --no-cache-dir -r requirements.txt && \
    chown -R hytale:hytale ${DASHBOARD_DIR}

# Copy configuration files
COPY --chown=hytale:hytale config/supervisord.conf /etc/supervisor/conf.d/supervisord.conf
COPY --chown=hytale:hytale config/server-config.json ${HYTALE_DIR}/config.json
COPY --chown=hytale:hytale config/world-config.json ${HYTALE_DIR}/universe/worlds/default/config.json
COPY --chown=hytale:hytale scripts/entrypoint.sh /entrypoint.sh
COPY --chown=hytale:hytale scripts/start-server.sh ${HYTALE_DIR}/start.sh
# Scripts that need to persist in volumes are copied at runtime by entrypoint
# Scripts outside volumes (won't be overwritten by mounts)
COPY --chown=root:root scripts/download-server.sh /usr/local/bin/hytale-download.sh
COPY --chown=root:root scripts/fetch-downloader.sh /usr/local/bin/hytale-fetch-downloader.sh
COPY --chown=root:root scripts/server-wrapper.sh /usr/local/bin/hytale-server-wrapper.sh

# Make scripts executable
RUN chmod +x /entrypoint.sh ${HYTALE_DIR}/start.sh /usr/local/bin/hytale-download.sh /usr/local/bin/hytale-fetch-downloader.sh /usr/local/bin/hytale-server-wrapper.sh

# Setup wizard page (overwrites dashboard templates)
COPY --chown=hytale:hytale dashboard/templates/setup.html ${DASHBOARD_DIR}/templates/setup.html
COPY --chown=hytale:hytale dashboard/setup_routes.py ${DASHBOARD_DIR}/setup_routes.py
COPY --chown=root:root scripts/patch-dashboard-setup.sh /usr/local/bin/patch-dashboard-setup.sh

# Integrate setup routes into dashboard app
RUN chmod +x /usr/local/bin/patch-dashboard-setup.sh && \
    /usr/local/bin/patch-dashboard-setup.sh

# Apply Docker-specific patches to make dashboard work with supervisord
COPY --chown=hytale:hytale dashboard/docker_overrides.py ${DASHBOARD_DIR}/docker_overrides.py
COPY --chown=hytale:hytale dashboard/apply_docker_patches.py ${DASHBOARD_DIR}/apply_docker_patches.py
RUN python3 ${DASHBOARD_DIR}/apply_docker_patches.py ${DASHBOARD_DIR} && \
    chown -R hytale:hytale ${DASHBOARD_DIR}

# Expose ports
# 5520/udp - Hytale Game Server
# 5523/tcp - Nitrado WebServer API (plugins)
# 8088/tcp - Dashboard
EXPOSE 5520/udp 5523/tcp 8088/tcp

# Volumes for persistent data
VOLUME ["${HYTALE_DIR}/universe", "${HYTALE_DIR}/mods", "${HYTALE_DIR}/backups", "${HYTALE_DIR}/.downloader"]

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:${DASHBOARD_PORT}/api/status || exit 1

WORKDIR ${HYTALE_DIR}
ENTRYPOINT ["/entrypoint.sh"]
CMD ["supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
