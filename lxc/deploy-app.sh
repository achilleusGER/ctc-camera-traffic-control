#!/usr/bin/env bash
# Hermes-Trafficcontrol — App-Deploy / Update
# Aufruf im LXC als traffic-User:
#   cd /opt/trafficcontrol/src && bash lxc/deploy-app.sh
#
# Was passiert:
#   1. git pull (oder überspringen, wenn SOURCE != git)
#   2. Backend: venv aktualisieren (pip install -e . --quiet)
#   3. Worker: venv aktualisieren
#   4. Frontend: npm ci + npm run build
#   5. DB-Migrationen: alembic upgrade head
#   6. Services: restart

set -euo pipefail

APP_HOME="/opt/trafficcontrol"
SRC="${APP_HOME}/src"
LOG() { printf '\033[1;36m[deploy]\033[0m %s\n' "$*"; }
DIE() { printf '\033[1;31m[deploy:FATAL]\033[0m %s\n' "$*" >&2; exit 1; }

[[ -d "${SRC}" ]] || DIE "Source-Verzeichnis ${SRC} existiert nicht. Bitte erst git clone."

cd "${SRC}"

# 1) Git pull
if [[ -d .git ]]; then
    LOG "git pull…"
    git pull --rebase --autostash
else
    LOG "Kein .git — überspringe pull."
fi

# 2) Backend venv + Migration
log "Backend: pip install…"
cd "${SRC}/backend"
[[ -d .venv ]] || python3 -m venv .venv
.venv/bin/pip install --quiet --upgrade pip
.venv/bin/pip install --quiet -e .

# 3) Worker venv
log "Worker: pip install…"
cd "${SRC}/worker"
[[ -d .venv ]] || python3 -m venv .venv
.venv/bin/pip install --quiet --upgrade pip
.venv/bin/pip install --quiet -e .

# 4) Frontend
LOG "Frontend: npm ci + build…"
cd "${SRC}/frontend"
[[ -d node_modules ]] || npm ci
npm run build

# 5) DB-Migration
LOG "DB-Migrationen…"
cd "${SRC}/backend"
.venv/bin/alembic upgrade head

# 6) Services restarten
LOG "Services restarten…"
sudo systemctl restart traffic-backend
# Worker: nur restarten, wenn bereits enabled (sonsten manuell via systemctl enable)
for unit in /etc/systemd/system/traffic-worker@*.service; do
    [[ -f "${unit}" ]] || continue
    inst=$(basename "${unit}" | sed -E 's/.*traffic-worker@([0-9]+).service/\1/')
    sudo systemctl restart "traffic-worker@${inst}"
done
sudo systemctl reload nginx

LOG "OK. Backend: http://127.0.0.1:7890  ·  Frontend: http://<lxc-ip-oder-fqdn>/  (pct enter ${LXC_ID:-240}; ip a)"
