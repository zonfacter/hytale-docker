#===============================================================================
# Hytale Server + Dashboard Docker Image
# https://github.com/zonfacter/hytale-docker
#===============================================================================

FROM debian:bookworm-slim

LABEL maintainer="zonfacter"
LABEL description="Hytale Dedicated Server with Web Dashboard"
LABEL version="1.0.0"

# Environment variables
ENV DEBIAN_FRONTEND=noninteractive \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    # Hytale Server
    HYTALE_DIR=/opt/hytale-server \
    HYTALE_PORT=5520 \
    HYTALE_MEMORY_MIN=2G \
    HYTALE_MEMORY_MAX=4G \
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

# Install dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Java for Hytale Server
    openjdk-21-jre-headless \
    # Python for Dashboard
    python3 \
    python3-venv \
    python3-pip \
    # Utilities
    curl \
    wget \
    unzip \
    git \
    procps \
    supervisor \
    gosu \
    && rm -rf /var/lib/apt/lists/*

# Create users and directories
RUN groupadd -g ${PGID} hytale && \
    useradd -u ${PUID} -g hytale -m -d ${HYTALE_DIR} -s /bin/bash hytale && \
    mkdir -p ${HYTALE_DIR}/{backups,mods,universe/worlds/default,.downloader,logs} && \
    mkdir -p ${DASHBOARD_DIR} && \
    chown -R hytale:hytale ${HYTALE_DIR}

# Clone and setup Dashboard
WORKDIR ${DASHBOARD_DIR}
RUN git clone --depth 1 https://github.com/zonfacter/hytale-dashboard.git . && \
    python3 -m venv .venv && \
    .venv/bin/pip install --no-cache-dir --upgrade pip && \
    .venv/bin/pip install --no-cache-dir -r requirements.txt && \
    chown -R hytale:hytale ${DASHBOARD_DIR}

# Copy configuration files
COPY --chown=hytale:hytale config/supervisord.conf /etc/supervisor/conf.d/supervisord.conf
COPY --chown=hytale:hytale config/server-config.json ${HYTALE_DIR}/config.json
COPY --chown=hytale:hytale config/world-config.json ${HYTALE_DIR}/universe/worlds/default/config.json
COPY --chown=hytale:hytale scripts/entrypoint.sh /entrypoint.sh
COPY --chown=hytale:hytale scripts/start-server.sh ${HYTALE_DIR}/start.sh
COPY --chown=hytale:hytale scripts/download-server.sh ${HYTALE_DIR}/.downloader/download.sh

# Make scripts executable
RUN chmod +x /entrypoint.sh ${HYTALE_DIR}/start.sh ${HYTALE_DIR}/.downloader/download.sh

# Setup wizard page (overwrites dashboard templates)
COPY --chown=hytale:hytale dashboard/templates/setup.html ${DASHBOARD_DIR}/templates/setup.html
COPY --chown=hytale:hytale dashboard/setup_routes.py ${DASHBOARD_DIR}/setup_routes.py

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
