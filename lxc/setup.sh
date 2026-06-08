#!/usr/bin/env bash
# Hermes-Trafficcontrol — LXC Erstinstallation
# Aufruf: EINMALIG als root im frischen Debian-12-LXC
#   pct enter 240
#   curl -sSL https://raw.githubusercontent.com/.../setup.sh | bash
#   ODER lokal:  bash setup.sh
#
# Idempotent: bei erneutem Lauf werden bereits existierende User/DBs übersprungen.

set -euo pipefail
export DEBIAN_FRONTEND=noninteractive

log() { printf '\033[1;33m[setup]\033[0m %s\n' "$*"; }
die() { printf '\033[1;31m[setup:FATAL]\033[0m %s\n' "$*" >&2; exit 1; }

[[ $EUID -eq 0 ]] || die "Bitte als root ausführen."

# ─── 1) Debian-Pakete ──────────────────────────────────────────────────────
log "Installiere Debian-Pakete (PostgreSQL 15, Redis, Python, FFmpeg, nginx)…"
apt-get update
apt-get install -y --no-install-recommends \
    python3 python3-venv python3-pip python3-dev \
    build-essential libpq-dev \
    postgresql-15 postgresql-client-15 \
    redis-server \
    nginx \
    ffmpeg \
    git curl ca-certificates openssl \
    sudo ufw

# Hinweis: Auf aktuellen Debian-12 ist 'python3' = 3.11. Das ist OK — das
# Backend/Worker laufen unter 3.11+ problemlos. Falls du explizit 3.12 willst,
# kannst du nach der Installation 'pyenv' nachziehen.
PYTHON_VERSION=$(python3 --version | awk '{print $2}')
log "Python-Version: ${PYTHON_VERSION}"

# ─── 2) PostgreSQL: User + DB ─────────────────────────────────────────────
log "Konfiguriere PostgreSQL…"
PG_USER="traffic"
PG_PASS="traffic"        # ← in Produktion: ändern via .env
PG_DB="traffic"

if sudo -u postgres psql -tAc "SELECT 1 FROM pg_roles WHERE rolname='${PG_USER}'" | grep -q 1; then
    log "PostgreSQL-User '${PG_USER}' existiert bereits — überspringe."
else
    sudo -u postgres psql <<SQL
CREATE USER ${PG_USER} WITH PASSWORD '${PG_PASS}';
CREATE DATABASE ${PG_DB} OWNER ${PG_USER};
GRANT ALL PRIVILEGES ON DATABASE ${PG_DB} TO ${PG_USER};
SQL
    log "PostgreSQL-User + DB angelegt."
fi

# HBA: lokale Verbindungen mit md5 erlauben (für asyncpg)
PG_HBA=/etc/postgresql/15/main/pg_hba.conf
if ! grep -q "^host.*${PG_DB}.*md5" "${PG_HBA}"; then
    log "Erweitere pg_hba.conf (lokale md5-Auth)…"
    echo "host    ${PG_DB}    ${PG_USER}    127.0.0.1/32    md5" >> "${PG_HBA}"
    systemctl reload postgresql
fi

systemctl enable --now postgresql

# ─── 3) Redis ──────────────────────────────────────────────────────────────
log "Konfiguriere Redis (Pub/Sub-Mode, ohne Persistenz)…"
REDIS_CONF=/etc/redis/redis.conf
if ! grep -q "Hermes-Trafficcontrol" "${REDIS_CONF}"; then
    cat >> "${REDIS_CONF}" <<'EOF'

# Hermes-Trafficcontrol: Pub/Sub-Mode, keine Persistenz (Worker schreibt, Backend liest)
save ""
appendonly no
maxmemory 512mb
maxmemory-policy allkeys-lru
EOF
    log "Redis-Konfiguration ergänzt."
fi
systemctl enable --now redis-server

# ─── 4) App-User + Verzeichnisse ───────────────────────────────────────────
log "Lege App-User und Verzeichnisse an…"
APP_USER="traffic"
APP_HOME="/opt/trafficcontrol"

if ! id "${APP_USER}" &>/dev/null; then
    useradd -m -s /bin/bash -G sudo "${APP_USER}"
    log "User '${APP_USER}' angelegt."
fi

mkdir -p \
    "${APP_HOME}/backend" \
    "${APP_HOME}/worker" \
    "${APP_HOME}/frontend" \
    /var/lib/trafficcontrol/media
chown -R "${APP_USER}:${APP_USER}" "${APP_HOME}" /var/lib/trafficcontrol

# ─── 5) Firewall ───────────────────────────────────────────────────────────
log "Setze UFW-Regeln (HTTP, SSH, Rest blockiert)…"
ufw --force reset
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw allow 80/tcp comment "HTTP (nginx)"
# Optional: HTTPS, falls Let's Encrypt später dazukommt
# ufw allow 443/tcp
ufw --force enable

# ─── 6) PostgreSQL + Redis nur lokal ──────────────────────────────────────
log "Stelle sicher, dass Postgres + Redis nur auf 127.0.0.1 hören…"
PG_CONF=/etc/postgresql/15/main/postgresql.conf
sed -i "s/^#\?listen_addresses.*/listen_addresses = '127.0.0.1'/" "${PG_CONF}"
systemctl restart postgresql

# Redis bind default schon 127.0.0.1 — bestätigen
if ! grep -q "^bind 127.0.0.1" /etc/redis/redis.conf; then
    sed -i 's/^#\?bind .*/bind 127.0.0.1/' /etc/redis/redis.conf
    systemctl restart redis-server
fi

# ─── 7) Hinweise ──────────────────────────────────────────────────────────
cat <<EOF

\033[1;32m[setup:OK]\033[0m Erstinstallation abgeschlossen.

Nächste Schritte (als traffic-User):
  1. Code deployen:
        cd ${APP_HOME}
        sudo -u traffic git clone <repo>  src
        ODER:  rsync -avz <lokaler-pfad>/ src/
  2. Backend installieren + Migration:
        cd ${APP_HOME}/src/backend
        python3.12 -m venv .venv
        .venv/bin/pip install -e .
        .venv/bin/alembic upgrade head
  3. Worker installieren:
        cd ${APP_HOME}/src/worker
        python3.12 -m venv .venv
        .venv/bin/pip install -e .
        # YOLO-Modell wird beim ersten Lauf automatisch geladen (~50MB)
  4. Frontend builden:
        cd ${APP_HOME}/src/frontend
        npm install
        npm run build
  5. systemd-Services installieren:
        sudo cp ${APP_HOME}/src/lxc/systemd/*.service /etc/systemd/system/
        sudo systemctl daemon-reload
        sudo systemctl enable --now traffic-backend nginx
        sudo systemctl enable --now traffic-worker@1   # für Kamera 1
  6. Im Browser:  http://<lxc-ip>/

DB-Credentials:  ${PG_USER} / ${PG_PASS} / ${PG_DB}  (localhost only)
Backup-Hinweis (Q6):  Proxmox-LXC-Snapshot inkl. /var/lib/trafficcontrol + Postgres-Volumen.

EOF
