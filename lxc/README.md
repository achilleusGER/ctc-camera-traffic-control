# Hermes-Trafficcontrol — Proxmox-LXC Deployment

Vollständige Anleitung, um die App auf einem **frischen Debian-12-LXC** auf Proxmox
laufen zu lassen — nativ, ohne Docker im LXC.

## Architektur im LXC

| Service       | Port    | Speicherort                              |
|---------------|---------|------------------------------------------|
| postgresql    | 5432    | /var/lib/postgresql/15/main/             |
| redis         | 6379    | systemd-managed                          |
| traffic-backend (uvicorn) | 7890 (nur 127.0.0.1) | /opt/trafficcontrol/src/backend |
| traffic-worker@N (1 pro Kamera) | — | /opt/trafficcontrol/src/worker |
| nginx         | 80      | /opt/trafficcontrol/src/frontend/dist/   |
| media         | —       | /var/lib/trafficcontrol/media/           |

## 1) LXC auf Proxmox-Host erstellen

Auf dem Proxmox-Host (NICHT im LXC):

```bash
pveam update
pveam download local debian-12-standard_12.2_1.amd64.tar.zst

pct create 240 local:vztmpl/debian-12-standard_12.2_1.amd64.tar.zst \
  --hostname hermes-trafficcontrol \
  --cores 12 --memory 12288 --swap 2048 \
  --rootfs local-lvm:64 \
  --net0 name=eth0,bridge=vmbr0,ip=10.10.1.250/24,gw=10.10.1.1 \
  --features nesting=1 \
  --onboot 1 --unprivileged 1 --ostype debian

pct start 240
pct enter 240
```

> CPU/RAM bewusst großzügig, weil yolo11m auf 2-3 Streams ca. 2,5 Kerne + 1,5 GB pro Worker
> braucht. Bei 4 Kameras: 10 Kerne + 6 GB Worker + 2 GB Backend + 2 GB Postgres + 512 MB
> Redis + 1 GB nginx/system = ~16 GB. Host hat 16/14 — passt knapp.

## 2) Erstinstallation (einmalig)

Im LXC als root:

```bash
cd /tmp
# Repo clonen (einmalig, danach liegen Code + Skripte lokal)
git clone https://github.com/achilleusGER/ctc-camera-traffic-control.git /opt/trafficcontrol/src

# Praxistipp: in der Entwicklung oft rsync vom Mac (ssh-Key vorausgesetzt):
# rsync -avz --exclude='.venv' --exclude='node_modules' --exclude='.git' \
#     /Users/andreaskutter/Programmierung/Hermes-Trafficcontrol/ \
#     traffic@10.10.1.250:/opt/trafficcontrol/src/

cd /opt/trafficcontrol/src/lxc
bash setup.sh
```

`setup.sh` macht:
- apt install (PostgreSQL 15, Redis, Python 3.12, FFmpeg, nginx, UFW)
- DB-User `traffic` / DB `traffic` anlegen (Passwort: `traffic` — **vor Produktion ändern!**)
- `traffic`-App-User + Verzeichnisse
- UFW: nur SSH + HTTP offen
- Postgres + Redis nur auf 127.0.0.1 gebunden

## 3) Code deployen (App-User)

```bash
sudo -u traffic -i
cd /opt/trafficcontrol/src

# Backend venv + Migration
cd backend
python3.12 -m venv .venv
.venv/bin/pip install -e .
.venv/bin/alembic upgrade head

# Worker venv
cd ../worker
python3.12 -m venv .venv
.venv/bin/pip install -e .
# YOLO11m wird beim ersten Lauf automatisch geladen (~50 MB, dauert 1-2 Min)

# Frontend build
cd ../frontend
npm install
npm run build
```

## 4) systemd-Services installieren

```bash
# .env mit Produktions-Passwörtern anlegen
sudo cp lxc/.env.production /opt/trafficcontrol/.env
sudo nano /opt/trafficcontrol/.env   # ← Passwörter ändern

# Services kopieren
sudo cp lxc/systemd/*.service /etc/systemd/system/
sudo cp lxc/systemd/*.timer   /etc/systemd/system/
sudo systemctl daemon-reload

# nginx-Konfiguration
sudo cp lxc/nginx.conf /etc/nginx/sites-available/trafficcontrol
sudo rm -f /etc/nginx/sites-enabled/default
sudo ln -s /etc/nginx/sites-available/trafficcontrol /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx

# Backend + Worker starten
sudo systemctl enable --now postgresql redis-server nginx
sudo systemctl enable --now traffic-backend
sudo systemctl enable --now traffic-worker@1   # für Kamera 1
sudo systemctl enable --now traffic-worker@2   # für Kamera 2
sudo systemctl enable --now traffic-cleanup.timer   # Phase 6 Retention
```

## 5) App-User-Login + Kameras anlegen

Browser: `http://10.10.1.250/`

- **Kameras** → "Neue Kamera" → RTSPS-URL + Tempolimit eintragen
- **Live** → prüfen, ob Stream ankommt
- **Kalibrierung** → pro Kamera: 4 Punkte auf einer realen Rechteckfläche markieren,
  Breite/Höhe in Metern eintragen
- **Kameras** → pro Kamera: Zähllinie(n) zeichnen (kommt mit Phase 5, derzeit Backend-
  Endpoint vorhanden, UI folgt)
- **Verstöße** → sobald Daten reinkommen

## 6) Updates deployen

Wenn du Code änderst und re-deployen willst (auf deinem Mac entwickeln, im LXC testen):

```bash
# Auf dem Mac:
git add -A && git commit -m "..." && git push

# Im LXC:
sudo -u traffic -i
cd /opt/trafficcontrol/src
bash lxc/deploy-app.sh
```

`deploy-app.sh` macht:
- `git pull`
- Backend + Worker: `pip install -e .`
- Frontend: `npm run build`
- `alembic upgrade head`
- systemd restart

## 7) Backups (Q6 — via Proxmox, NICHT via App-Skript)

Proxmox erstellt LXC-Snapshots konsistent, wenn du vorher im LXC die
DB-Connections stoppst oder einen Snapshot-Mode nutzt. Einfachster Weg:

```bash
# Auf Proxmox-Host:
pct snapshot 240 pre-upgrade-$(date +%Y%m%d)  # Schnappschuss vor Update
# Oder via Web-UI: LXC 240 → Snapshot → "pre-upgrade-2026-06-08"
```

Wichtig für die Wiederherstellung: `/var/lib/trafficcontrol/media/` + Postgres-Daten
sind die einzigen persistenten Daten. Beide liegen im LXC-RootFS und werden vom
Snapshot erfasst.

Optional, falls du Postgres atomar sichern willst (außerhalb des Snapshots):

```bash
# Im LXC:
pg_dump -U traffic traffic | gzip > /tmp/traffic-$(date +%F).sql.gz
# Auf den Host kopieren:
pct pull 240 /tmp/traffic-*.sql.gz /backup/
```

## 8) Troubleshooting

| Problem | Check |
|---------|-------|
| Backend startet nicht | `sudo journalctl -u traffic-backend -n 50` |
| Worker connect nicht zum Stream | `journalctl -u traffic-worker@1 -n 30` + RTSPS-URL testen mit `ffplay rtsps://...` |
| Frontend zeigt 502 | `systemctl status traffic-backend` + `journalctl -u traffic-backend` |
| DB-Verbindung failt | `psql -U traffic -h 127.0.0.1 traffic` (Passwort = `traffic` oder neuer Wert aus .env) |
| Redis nicht erreichbar | `redis-cli ping` muss `PONG` antworten |
| Kamera wird nicht erkannt | RTSPS-URL mit `ffplay` testen, dann in `/cameras/`-API prüfen |
| YOLO-Inferenz zu langsam | `model_variant` pro Kamera auf `s` setzen (YAML im Backend, dann `alembic` migration) |

## 9) Sicherheit (Q5: HTTP-only, LAN)

- Backend lauscht nur auf 127.0.0.1:7890 (nicht öffentlich erreichbar)
- Postgres + Redis nur auf 127.0.0.1
- nginx als Reverse-Proxy
- UFW: nur SSH (22) + HTTP (80)
- Kein Login (LAN-Tool, Andreas allein — laut Hallmark-Brief)
- Beweisfotos + ALPR: ALPR standardmäßig aus, Retention via cleanup-timer (Phase 6)

Falls du das Tool irgendwann aus dem LAN exponieren willst:
- HTTPS mit Let's Encrypt (certbot)
- Reverse-Auth (z. B. Authelia) davorschalten
- Dann: `/admin/cleanup-evidence` per Auth schützen
