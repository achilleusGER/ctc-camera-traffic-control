# Hermes-Trafficcontrol — Proxmox-LXC Deployment

Verkehrszählung + Geschwindigkeitsmessung auf einem Debian-12-LXC, nativ, ohne Docker.

## Schnellstart (Proxmox-Host)

**Ein Befehl auf dem Proxmox-Host als root** — das Skript macht alles (LXC erstellen, Repo klonen, optional Setup):

```bash
bash -c "$(curl -fsSL https://raw.githubusercontent.com/achilleusGER/ctc-camera-traffic-control/main/lxc/proxmox-install.sh)"
```

Mit eigenen Werten:

```bash
bash lxc/proxmox-install.sh --id 240 --ip 10.10.1.250/24 --unattended --run-setup
```

Alle Optionen: `bash lxc/proxmox-install.sh --help`

Das Skript macht:

1. Prüft root + Proxmox-Umgebung
2. Lädt `debian-12-standard_12.2_1.amd64.tar.zst` falls nicht vorhanden
3. `pct create` + `pct start` (LXC 240, 12 Kerne, 12 GB RAM, 64 GB Disk)
4. Wartet auf Netzwerk
5. Klont `ctc-camera-traffic-control` nach `/opt/trafficcontrol/src`
6. Fragt: `setup.sh` jetzt ausführen? (bei `--run-setup` ohne Rückfrage)

## Was ist wo

| Datei | Zweck | Aufruf |
|-------|-------|--------|
| `lxc/proxmox-install.sh` | LXC anlegen + Repo klonen | **Proxmox-Host**, root |
| `lxc/setup.sh` | Debian-Pakete, Postgres+Redis, DB-User, UFW, Hardening | **im LXC**, root |
| `lxc/deploy-app.sh` | Updates deployen (git pull, pip, npm, alembic, restart) | **im LXC**, traffic-User |
| `lxc/systemd/*.service` + `*.timer` | Backend, Worker (Template), Cleanup | kopieren nach `/etc/systemd/system/` |
| `lxc/nginx.conf` | HTTP-only Reverse-Proxy + Frontend-Static | `/etc/nginx/sites-available/` |
| `lxc/.env.production` | Settings-Template (Passwörter ändern!) | `/opt/trafficcontrol/.env` |

## Volle Anleitung

### 1) Installer-Skript (Proxmox-Host)

Wie oben — ein Befehl, läuft interaktiv durch.

Wenn du ohne SSH-Key arbeitest, generiere vorher einen:

```bash
ssh-keygen -t ed25519 -N "" -f ~/.ssh/id_ed25519
# auf den Proxmox-Host kopieren (falls du remote arbeitest):
ssh-copy-id root@<proxmox-host>
```

### 2) Erstinstallation (im LXC)

Falls du beim Installer `--run-setup` nicht angegeben hast, manuell:

```bash
pct enter 240
cd /opt/trafficcontrol/src/lxc
bash setup.sh
```

`setup.sh` installiert:
- PostgreSQL 15, Redis, Python 3.12, FFmpeg, nginx, UFW
- DB-User `traffic` / DB `traffic` (Passwort: `traffic` — **vor Produktion ändern!**)
- `traffic`-App-User + Verzeichnisse
- UFW: nur SSH + 80
- Postgres + Redis nur auf 127.0.0.1

### 3) App-Code vorbereiten (im LXC, als traffic-User)

```bash
sudo -u traffic -i
cd /opt/trafficcontrol/src

# Backend
cd backend
python3.12 -m venv .venv
.venv/bin/pip install -e .
.venv/bin/alembic upgrade head

# Worker
cd ../worker
python3.12 -m venv .venv
.venv/bin/pip install -e .
# YOLO11m wird beim ersten Lauf automatisch geladen (~50 MB, 1-2 Min)

# Frontend
cd ../frontend
npm install
npm run build
```

### 4) systemd + nginx (im LXC, als root)

```bash
# .env mit Passwörtern
sudo cp lxc/.env.production /opt/trafficcontrol/.env
sudo nano /opt/trafficcontrol/.env   # Passwörter ändern!

# Services
sudo cp lxc/systemd/*.service lxc/systemd/*.timer /etc/systemd/system/
sudo systemctl daemon-reload

# nginx
sudo cp lxc/nginx.conf /etc/nginx/sites-available/trafficcontrol
sudo rm -f /etc/nginx/sites-enabled/default
sudo ln -s /etc/nginx/sites-available/trafficcontrol /etc/nginx/sites-enabled/
sudo nginx -t

# Starten
sudo systemctl enable --now postgresql redis-server nginx
sudo systemctl enable --now traffic-backend
sudo systemctl enable --now traffic-worker@1   # für Kamera 1
sudo systemctl enable --now traffic-worker@2   # für Kamera 2
sudo systemctl enable --now traffic-cleanup.timer   # Phase 6 Retention
```

### 5) App-Login (Browser)

→ `http://<lxc-ip>/` (Default: 10.10.1.250)

- **Kameras** → "Neue Kamera" → RTSPS-URL + Tempolimit eintragen
- **Live** → prüfen, ob Stream ankommt
- **Kalibrierung** → pro Kamera: 4 Punkte auf einer realen Rechteckfläche markieren, Breite/Höhe in Metern
- **Verstöße** → sobald Daten reinkommen

### 6) Updates deployen

Code auf deinem Mac ändern, committen, pushen. Dann im LXC:

```bash
sudo -u traffic -i
cd /opt/trafficcontrol/src
bash lxc/deploy-app.sh
```

`deploy-app.sh` macht:
- `git pull --rebase`
- Backend + Worker: `pip install -e .`
- Frontend: `npm run build`
- `alembic upgrade head`
- `systemctl restart` für Backend + Worker

## Backup (via Proxmox-Snapshot)

Q6-Entscheidung: **kein** Backup-Skript im Repo. Du machst Backups via Proxmox-LXC-Snapshot.

```bash
# Auf Proxmox-Host:
pct snapshot 240 pre-upgrade-$(date +%Y%m%d)
# Oder via Web-UI: LXC 240 → Snapshot → "pre-upgrade-2026-06-08"
```

Wichtig für die Wiederherstellung: `/var/lib/trafficcontrol/media/` + Postgres-Daten sind die einzigen persistenten Daten. Beide liegen im LXC-RootFS und werden vom Snapshot erfasst.

## Troubleshooting

| Problem | Check |
|---------|-------|
| LXC erstellt, aber SSH klappt nicht | `pct enter 240` direkt (kein SSH nötig im LXC) |
| Backend startet nicht | `sudo journalctl -u traffic-backend -n 50` |
| Worker connect nicht zum Stream | `journalctl -u traffic-worker@1 -n 30` + RTSPS-URL testen mit `ffplay rtsps://...` |
| Frontend zeigt 502 | `systemctl status traffic-backend` + `journalctl -u traffic-backend` |
| DB-Verbindung failt | `psql -U traffic -h 127.0.0.1 traffic` (Passwort aus .env) |
| Redis nicht erreichbar | `redis-cli ping` muss `PONG` antworten |
| Kamera wird nicht erkannt | RTSPS-URL mit `ffplay` testen, dann in `/cameras/`-API prüfen |
| YOLO-Inferenz zu langsam | `model_variant` pro Kamera auf `s` setzen |

## Sicherheit (Q5: HTTP-only, LAN)

- Backend lauscht nur auf 127.0.0.1:7890
- Postgres + Redis nur auf 127.0.0.1
- nginx als Reverse-Proxy (HTTP, nicht HTTPS — LAN-Tool)
- UFW: nur SSH (22) + HTTP (80)
- Kein Login (LAN-Tool, Andreas allein)
- Beweisfotos + ALPR: ALPR standardmäßig aus, Retention via cleanup-timer

Bei Bedarf später HTTPS: `certbot --nginx` auf der Proxmox-Host-IP.
