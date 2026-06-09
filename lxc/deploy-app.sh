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
LOG "Backend: pip install…"
cd "${SRC}/backend"
[[ -d .venv ]] || python3 -m venv .venv
.venv/bin/pip install --quiet --upgrade pip
.venv/bin/pip install --quiet -e .

# 3) Worker venv
LOG "Worker: pip install…"
cd "${SRC}/worker"
[[ -d .venv ]] || python3 -m venv .venv
.venv/bin/pip install --quiet --upgrade pip
.venv/bin/pip install --quiet -e .

# 4) Frontend
LOG "Frontend: npm ci + build…"
cd "${SRC}/frontend"
# package-lock.json wird im Repo nicht committed (.gitignore)
# Daher 'npm install' statt 'npm ci' — npm ci braucht eine vorhandene lockfile.
[[ -d node_modules ]] || npm install --no-audit --no-fund
npm run build

# 5) DB-Migration
LOG "DB-Migrationen…"
cd "${SRC}/backend"
.venv/bin/alembic upgrade head

# 5.1) .env aus Template uebernehmen (falls noch nicht da)
if [[ ! -f /opt/trafficcontrol/.env ]]; then
    LOG ".env aus Template uebernehmen…"
    sudo cp "${SRC}/lxc/.env.production" /opt/trafficcontrol/.env
    sudo chown traffic:traffic /opt/trafficcontrol/.env
    sudo chmod 600 /opt/trafficcontrol/.env
    LOG "WICHTIG: Default-Passwoerter vor Produktion aendern (VOR PROD AENDERN!)"
fi

# 5.2) systemd-Units + nginx-Site (idempotent, nur installieren wenn nicht da)
if [[ ! -f /etc/systemd/system/traffic-backend.service ]]; then
    LOG "systemd-Units + nginx-Site installieren…"
    sudo cp "${SRC}/lxc/systemd/"*.service "${SRC}/lxc/systemd/"*.timer /etc/systemd/system/
    sudo cp "${SRC}/lxc/nginx.conf" /etc/nginx/sites-available/trafficcontrol
    sudo rm -f /etc/nginx/sites-enabled/default
    sudo ln -sf /etc/nginx/sites-available/trafficcontrol /etc/nginx/sites-enabled/
    sudo systemctl daemon-reload
    sudo systemctl enable --now postgresql redis-server nginx
    sudo systemctl enable --now traffic-backend
    sudo systemctl enable --now traffic-worker@1
    sudo systemctl enable --now traffic-cleanup.timer
    sudo nginx -t && sudo systemctl reload nginx
else
    LOG "systemd-Units bereits installiert — ueberspringe Kopieren."
fi

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
