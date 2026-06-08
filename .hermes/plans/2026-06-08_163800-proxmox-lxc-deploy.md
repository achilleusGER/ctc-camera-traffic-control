# Hermes-Trafficcontrol — Implementierungsplan

**Repo:** `/Users/andreaskutter/Programmierung/Hermes-Trafficcontrol/` (NEU, leer zum Start)
**Stand:** 2026-06-08
**Status:** Entwurf zur Review

---

## 0. ZIEL

Webanwendung zur Verkehrszählung + Geschwindigkeitsmessung aus mehreren RTSPS-Netzwerkkameras, deploybar auf einem Proxmox-LXC, CPU-only (kein CUDA). Multikamera, mehrere Straßen, Geschwindigkeitsüberschreitung mit Beweisfoto, optionale ALPR, vollständige Auswertungen.

---

## 1. ARCHITEKTUR (ÜBERSICHT)

```
                    ┌──────────────────────────┐
   RTSPS-Kameras ──►│ Worker-Prozess (1 pro     │──► Redis Pub/Sub
   (FHD, SRTP)      │ Kamera, systemd-Template) │      ├── events (Counts, Speed, Violations)
                    │                          │      └── frames (annotiert, MJPEG-Quelle)
                    │ · FFmpeg-Capture          │
                    │ · yolo11m + supervision  │
                    │ · ByteTrack               │
                    │ · ViewTransformer (Speed) │
                    │ · PaddleOCR (ALPR) optional│
                    └──────────────────────────┘
                                │
                                ▼
                    ┌──────────────────────────┐
                    │ FastAPI Backend           │──► PostgreSQL
                    │ · REST (Streets, Cameras, │      (streets, cameras, lines, events,
                    │   Lines, Events, Reports) │       evidence, plates)
                    │ · WebSocket (Live)        │
                    │ · MJPEG-Stream (Live-View)│──► Volume /var/lib/trafficcontrol/media
                    │ · Redis-Consumer (Worker→DB)│     (Beweisfotos, Snapshots)
                    └──────────────────────────┘
                                │
                                ▼
                    ┌──────────────────────────┐
                    │ React + Vite + TS Frontend│
                    │ · LiveView (1 Kamera groß)│
                    │ · Dashboard (KPIs)        │
                    │ · Violations (Beweisbilder)│
                    │ · Reports (Heatmap, Hist) │
                    │ · CameraAdmin (CRUD)      │
                    │ · Calibration (4-Punkt)   │
                    └──────────────────────────┘
```

**Stack:**
- Backend: Python 3.12, FastAPI, SQLAlchemy 2.x async, asyncpg, Alembic
- Worker: Python 3.12, Ultralytics (yolo11m), supervision (ByteTrack, LineZone, ViewTransformer), PaddleOCR, OpenCV, FFmpeg
- Frontend: React 18, Vite, TypeScript, TanStack Query, Recharts (Charts), WS-Client
- DB: PostgreSQL 16
- Cache/Bus: Redis 7
- Reverse Proxy: nginx
- Process Mgmt: systemd (kein Docker)

---

## 2. DEPLOYMENT: PROXMOX-LXC, ALLES IN EINEM CONTAINER

### 2.1 LXC-Specs (auf Proxmox-Host)

```bash
pct create 240 local:vztmpl/debian-12-standard_12.2_1.amd64.tar.zst \
  --hostname hermes-trafficcontrol \
  --cores 12 --memory 12288 --swap 2048 \
  --rootfs local-lvm:64 \
  --net0 name=eth0,bridge=vmbr0,ip=10.10.1.250/24,gw=10.10.1.1 \
  --features nesting=1 \
  --onboot 1 --unprivileged 1 --ostype debian
pct start 240
```

**Ressourcen-Planung (Host: 16 Kerne, 14 GB RAM):**
| Service | CPU-Limit | RAM-Limit | Begründung |
|---------|-----------|-----------|------------|
| postgresql | 2 | 2 GB | DB-Cache |
| redis | 1 | 512 MB | Pub/Sub |
| backend (uvicorn) | 2 | 1 GB | FastAPI async |
| 4× worker@.service | je 2,5 (CPUQuota 250%) | je 1,5 GB | yolo11m 1280x720 ≈ 2-3 Kerne |
| nginx + ffmpeg + system | 1 | 1 GB | Rest |
| **Summe** | **~16** | **~13 GB** | knapp aber tragbar |

Hinweis: yolo11m auf 1280x720 mit 4 Streams gleichzeitig wird die CPU voll auslasten (kein Headroom). Bei Engpässen → yolo11s downgraden.

### 2.2 Was im LXC läuft (nativ, keine Container-in-Container)

```
/opt/trafficcontrol/
├── .env                            # DB-URLs, REDIS_URL, YOLO_MODEL, ...
├── backend/
│   ├── .venv/                      # Python 3.12 venv
│   ├── pyproject.toml
│   ├── alembic/                    # DB-Migrationen
│   └── app/
│       ├── main.py
│       ├── config.py
│       ├── db.py
│       ├── models.py
│       ├── schemas.py
│       ├── consumer.py             # Worker→DB
│       ├── redis_bus.py
│       ├── streaming/mjpeg.py
│       ├── ws/hub.py
│       └── api/
│           ├── streets.py
│           ├── cameras.py
│           ├── lines.py
│           ├── events.py
│           ├── stats.py
│           ├── reports.py
│           └── violations.py
├── worker/
│   ├── .venv/
│   ├── pyproject.toml
│   ├── yolo11m.pt                  # YOLO-Modell (~50 MB)
│   └── worker/
│       ├── main.py                 # CLI: --camera-id, --config-file
│       ├── pipeline.py             # YOLO → Track → Zählung → Speed
│       ├── capture.py              # RTSPS via FFmpeg
│       ├── calibration.py          # ViewTransformer + SpeedEstimator
│       ├── alpr.py                 # PaddleOCR-Wrapper
│       ├── violations.py
│       ├── storage.py              # S3- oder local-Storage für Evidence
│       └── publisher.py            # Redis-Publisher
└── frontend/
    ├── node_modules/
    ├── dist/                       # npm run build Output (nginx serviert)
    └── src/
        ├── main.tsx
        ├── App.tsx
        ├── pages/
        │   ├── LiveView.tsx
        │   ├── Dashboard.tsx
        │   ├── Violations.tsx
        │   ├── Reports.tsx
        │   ├── CameraAdmin.tsx
        │   └── Calibration.tsx
        ├── components/
        │   ├── Sidebar.tsx
        │   ├── CameraPicker.tsx
        │   ├── LineEditor.tsx
        │   ├── CalibrationEditor.tsx
        │   └── EventCard.tsx
        ├── api/
        │   ├── client.ts
        │   ├── ws.ts
        │   └── types.ts
        └── styles/
            └── tokens.css          # Hallmark-Tokens
```

### 2.3 systemd-Services

`/etc/systemd/system/traffic-backend.service`:
```ini
[Unit]
Description=Hermes-Trafficcontrol Backend
After=network.target postgresql.service redis-server.service
Wants=postgresql.service redis-server.service

[Service]
Type=simple
User=traffic
WorkingDirectory=/opt/trafficcontrol/backend
EnvironmentFile=/opt/trafficcontrol/.env
ExecStart=/opt/trafficcontrol/backend/.venv/bin/uvicorn app.main:app \
  --host 0.0.0.0 --port 7890 --workers 1
Restart=always
RestartSec=5
CPUQuota=200%
MemoryMax=2G

[Install]
WantedBy=multi-user.target
```

`/etc/systemd/system/traffic-worker@.service` (TEMPLATE — eine Instanz pro Kamera):
```ini
[Unit]
Description=Hermes-Trafficcontrol Worker (Kamera %i)
After=network.target traffic-backend.service

[Service]
Type=simple
User=traffic
WorkingDirectory=/opt/trafficcontrol/worker
Environment=CAMERA_ID=%i
EnvironmentFile=/opt/trafficcontrol/.env
ExecStart=/opt/trafficcontrol/worker/.venv/bin/python -m worker.main
Restart=always
RestartSec=5
CPUQuota=250%                    # 2,5 Kerne pro Worker
MemoryMax=2G

[Install]
WantedBy=multi-user.target
```

**Aktivierung:**
```bash
systemctl daemon-reload
systemctl enable --now postgresql redis-server nginx
systemctl enable --now traffic-backend
systemctl enable --now traffic-worker@1   # für Kamera 1
systemctl enable --now traffic-worker@2   # für Kamera 2
systemctl enable --now traffic-worker@3
systemctl enable --now traffic-worker@4
```

So skalierst du Multikamera, ohne Docker, ohne Code-Änderung.

---

## 3. DATENMODELL (POSTGRESQL)

5 Haupttabellen + 1 für ALPR-Plates:

```sql
CREATE TABLE streets (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    description VARCHAR(500),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE cameras (
    id SERIAL PRIMARY KEY,
    street_id INT REFERENCES streets(id) ON DELETE SET NULL,
    name VARCHAR(200) NOT NULL,
    rtsp_url_low VARCHAR(500) NOT NULL,    -- Substream für Inferenz
    rtsp_url_high VARCHAR(500),             -- Mainstream für Snapshots
    width INT DEFAULT 1920,
    height INT DEFAULT 1080,
    infer_width INT DEFAULT 1280,           -- YOLO-Auflösung (gewählt: 1280x720)
    fps_limit INT DEFAULT 12,
    default_speed_limit_kmh REAL,
    alpr_enabled BOOLEAN DEFAULT FALSE,
    model_variant VARCHAR(2) DEFAULT 'm',    -- 'm' (yolo11m) oder 's' (yolo11s, für CPU-Engpass-Fallback)
    enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE counting_lines (
    id SERIAL PRIMARY KEY,
    camera_id INT NOT NULL REFERENCES cameras(id) ON DELETE CASCADE,
    name VARCHAR(200) NOT NULL,
    points JSONB NOT NULL,                  -- [[x1,y1],[x2,y2]]
    direction_in_label VARCHAR(100) DEFAULT 'in',
    direction_out_label VARCHAR(100) DEFAULT 'out',
    speed_limit_kmh REAL,                   -- überschreibt camera.default
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE calibrations (
    id SERIAL PRIMARY KEY,
    camera_id INT NOT NULL UNIQUE REFERENCES cameras(id) ON DELETE CASCADE,
    source_points JSONB NOT NULL,           -- 4 Pixel-Punkte [[x,y],...]
    target_width_m REAL NOT NULL,
    target_height_m REAL NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE crossing_events (
    id BIGSERIAL PRIMARY KEY,
    camera_id INT NOT NULL REFERENCES cameras(id) ON DELETE CASCADE,
    line_id INT REFERENCES counting_lines(id) ON DELETE SET NULL,
    ts TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    vehicle_class VARCHAR(50) NOT NULL,      -- car, truck, bus, motorcycle, bicycle, person
    direction VARCHAR(100) NOT NULL,
    track_id INT,
    speed_kmh REAL,
    speed_limit_kmh REAL,                   -- am Event eingefroren
    is_speeding BOOLEAN DEFAULT FALSE,
    plate_text VARCHAR(20),
    plate_confidence REAL,
    evidence_paths JSONB DEFAULT '[]'        -- Liste von Beweisfoto-Pfaden
);
CREATE INDEX ix_events_ts ON crossing_events(ts);
CREATE INDEX ix_events_camera_ts ON crossing_events(camera_id, ts);
CREATE INDEX ix_events_speeding ON crossing_events(is_speeding) WHERE is_speeding;

CREATE TABLE plates (
    id BIGSERIAL PRIMARY KEY,
    event_id BIGINT NOT NULL REFERENCES crossing_events(id) ON DELETE CASCADE,
    plate_text VARCHAR(20) NOT NULL,
    confidence REAL,
    captured_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX ix_plates_text ON plates(plate_text);
```

### Verkehrsklassen-Mapping (yolo11m COCO)
| COCO-ID | Klasse | Verkehrs-Label |
|---------|--------|----------------|
| 0 | person | Person |
| 1 | bicycle | Fahrrad |
| 2 | car | PKW |
| 3 | motorcycle | Motorrad |
| 5 | bus | Bus |
| 7 | truck | LKW |

PKW + LKW + Bus sind getrennt zählbar (für Verkehrsstatistik wichtig).

---

## 4. PHASENPLAN

### Phase 0 — Repository-Setup (1 h, KEIN Code-Schreiben)
- [ ] `git init`
- [ ] `.gitignore` (`.venv/`, `__pycache__/`, `node_modules/`, `*.pt`, `.env`)
- [ ] `README.md` (kurz, Verweis auf `.hermes/plans/`)
- [ ] `pyproject.toml` (Backend + Worker, Python 3.12)
- [ ] `frontend/package.json` (React 18, Vite, TS, TanStack Query, Recharts)

**Review-Punkt mit Andreas vor Phase 1.**

### Phase 1 — Backend-Grundgerüst (3-4 h)
- [ ] `backend/app/db.py` — async SQLAlchemy Engine
- [ ] `backend/app/models.py` — alle 6 Tabellen
- [ ] `backend/app/schemas.py` — Pydantic
- [ ] `backend/app/config.py` — Settings (Pydantic BaseSettings, .env)
- [ ] `backend/alembic/` — initial Migration
- [ ] `backend/app/main.py` — FastAPI, lifespan (init_models + Redis-Consumer), CORS
- [ ] `backend/app/api/streets.py` — CRUD
- [ ] `backend/app/api/cameras.py` — CRUD + Config-Endpoint (`GET /cameras/{id}/config` für Worker)
- [ ] `backend/app/api/lines.py` — CRUD
- [ ] `backend/app/api/events.py` — POST /events (Worker-Push), GET /events (filter)
- [ ] `backend/app/api/violations.py` — GET /violations (mit Beweisfoto-URLs)
- [ ] `backend/app/api/stats.py` — Aggregationen (Stunde/Tag/Woche/Monat)
- [ ] `backend/app/api/reports.py` — Speed-Histogramm, Heatmap, CSV/PDF-Export
- [ ] `backend/app/streaming/mjpeg.py` — MJPEG-Stream
- [ ] `backend/app/ws/hub.py` — WebSocket-Hub

**Review mit Andreas, dann Phase 2.**

### Phase 2 — Worker (3-4 h)
- [ ] `worker/worker/config.py` — Settings
- [ ] `worker/worker/capture.py` — FFmpeg RTSPS → Frames (numpy)
- [ ] `worker/worker/pipeline.py` — YOLO → ByteTrack → Zählung → Speed → Verstoß
- [ ] `worker/worker/calibration.py` — `ViewTransformer` (4-Punkt-Perspektive), `SpeedEstimator`
- [ ] `worker/worker/alpr.py` — PaddleOCR-Wrapper, default aus
- [ ] `worker/worker/violations.py` — `is_speeding`, `crop_vehicle`, `encode_jpeg`
- [ ] `worker/worker/storage.py` — local-Storage (Pfad: `/var/lib/trafficcontrol/media/...`)
- [ ] `worker/worker/publisher.py` — Redis-Publisher (events + annotated frames)
- [ ] `worker/worker/main.py` — Einstiegspunkt, lädt Kameraconfig vom Backend

**Review mit Andreas, dann Phase 3.**

### Phase 3 — Frontend (4-5 h)

**Voraussetzung — Hallmark-Design-Context-Gate (separater Schritt):**
Bevor irgendein Frontend-Code geschrieben wird, kläre ich mit dir:
- Audience (du selbst? Mitarbeiter? LAN-Team?)
- Use case (was ist die EINE Hauptaktion, die du auf der Startseite willst?)
- Tone (editorial, modern-minimal, atmospheric, brutalist, soft, …)

Danach erst:
- [ ] Vite + React + TS Setup
- [ ] Hallmark-Theme + Macrostructure wählen (basierend auf deinen Antworten)
- [ ] `pages/LiveView.tsx` — 1 Kamera groß + Kamera-Auswahl-Sidebar
- [ ] `pages/Dashboard.tsx` — KPIs (heute, Woche, Monat, Speed-Avg)
- [ ] `pages/Violations.tsx` — Tabelle mit Beweisfoto-Vorschau
- [ ] `pages/Reports.tsx` — Heatmap (Stunde × Wochentag), Speed-Histogramm, CSV/PDF-Export
- [ ] `pages/CameraAdmin.tsx` — Straßen/Kameras/Linien verwalten
- [ ] `pages/Calibration.tsx` — 4-Punkt-Editor mit Pixel-zu-Meter-Eingabe
- [ ] TanStack Query für REST, eigener WS-Hook für Live
- [ ] Recharts für Charts

**Review mit Andreas, dann Phase 4.**

### Phase 4 — LXC-Deployment-Skripte (1-2 h)
- [ ] `lxc/setup.sh` — Debian-Pakete, Postgres+Redis, DB-User, App-User, Verzeichnisse
- [ ] `lxc/systemd/traffic-backend.service`
- [ ] `lxc/systemd/traffic-worker@.service`
- [ ] `lxc/nginx.conf`
- [ ] `lxc/.env.production` (Template)
- [ ] `lxc/README.md` — Schritt-für-Schritt-Anleitung

**Review mit Andreas, dann Phase 5.**

### Phase 5 — End-to-End-Test auf Proxmox (2-3 h)
- [ ] LXC erstellen mit den Specs aus 2.1
- [ ] `lxc/setup.sh` durchlaufen
- [ ] Alembic-Migration
- [ ] RTSPS testen mit deinen Beispiel-URLs
- [ ] Backend + Frontend starten
- [ ] Kamera anlegen (über UI), RTSPS-URL eintragen
- [ ] Linie zeichnen, kalibrieren
- [ ] 1 Worker@1 starten, Live-Stream prüfen
- [ ] Counts + Speed prüfen (ggf. Verstoß provozieren)
- [ ] Reports prüfen
- [ ] 2. Worker@2, 3. Worker@3, 4. Worker@4, Last beobachten
- [ ] ggf. Downgrade auf yolo11s wenn CPU eng

### Phase 6 — Härtung (1-2 h)
- [ ] nginx: nur 80 offen, Backend auf 127.0.0.1, HTTP-only (Q5)
- [ ] Postgres+Redis nur auf 127.0.0.1
- [ ] **Beweisfoto-Retention (Q3):**
  - [ ] Backend: `POST /admin/cleanup-evidence?older_than_days=N` Endpoint (löscht DB-Records + Files älter als N Tage)
  - [ ] Frontend: Button im CameraAdmin "Beweisfotos aufräumen" mit Tage-Eingabe
  - [ ] Optional: systemd-Timer `traffic-cleanup.timer` (täglich, cleanup_days=30)
- [ ] **Backup-Pfade dokumentieren (Q6):** README-Hinweis, dass Proxmox-Snapshot `/var/lib/trafficcontrol/media/` + Postgres-Data-Volume sichern muss
- [ ] Health-Check (`/health` Endpoint, systemd Watchdog)
- [ ] README aktualisieren (LXC-Setup, Backup-Hinweis)

---

## 5. OFFENE FRAGEN — ENTSCHIEDEN AM 2026-06-08

| # | Frage | Entscheidung |
|---|-------|--------------|
| Q1 | yolo11m vs yolo11s bei 4 Streams? | **yolo11m bleibt** als Default. Realistisch 2-3 Kameras gleichzeitig aktiv. Bei Last-Engpass Downgrade auf yolo11s pro Kamera konfigurierbar (Kamera-Verwaltung bekommt `model_variant: m / s` Feld). |
| Q2 | Hallmark-3-Fragen-Gate wann? | **Vor Phase 3** als eigener Review-Punkt. Audience/Use-case/Tone werden in einer kurzen Konversation geklärt, BEVOR irgendein Frontend-Code geschrieben wird. |
| Q3 | DSGVO-UI für Retention? | **Ja.** Phase 6 bekommt (a) Backend-Endpoint `POST /admin/cleanup-evidence?older_than_days=N`, (b) Frontend-Button "Beweisfotos aufräumen" mit Tage-Eingabe, (c) optional systemd-Timer für automatisches Cleanup. Spart auch Plattenplatz. |
| Q4 | Media-Backend local oder MinIO? | **Local.** `/var/lib/trafficcontrol/media/` als LXC-Volume, in `docker-compose`-Äquivalent als Host-Mount. Kein MinIO. |
| Q5 | nginx HTTP oder HTTPS? | **HTTP-only** (LAN-Test). nginx-Config bleibt minimal, später trivial auf HTTPS erweiterbar. |
| Q6 | Backup-Strategie? | **Kein Backup-Skript im Repo.** Andreas macht Backups via Proxmox-Snapshot. Skript-seitig nur sicherstellen, dass `pgdata` + `media`-Verzeichnis via Proxmox-Backup korrekt gesichert werden können (Pfade dokumentiert). |

---

## 6. RISIKEN

| # | Risiko | Mitigation |
|---|--------|------------|
| R1 | yolo11m auf 4 Streams gleichzeitig → CPU-Engpass | Last messen in Phase 5, ggf. yolo11s pro Kamera konfigurierbar |
| R2 | RTSPS-SRTP-Entschlüsselung kostet CPU | FFmpeg hat gute TLS-Support, messen |
| R3 | PaddleOCR-CPU-Last bei ALPR aktiv | Standardmäßig aus, nur 1 Crop pro Verstoß |
| R4 | Kein eigener Backup-Slot in Plan, Andreas muss eigenen Mechanismus anschließen | Klären in Q6 |
| R5 | Hallmark-Design-Aufwand für 6 Pages nicht trivial | 3-Fragen-Gate vor Phase 3 |

---

## 7. ZEITLEISTE

| Phase | Inhalt | Dauer |
|-------|--------|-------|
| 0 | Repo-Setup | 1 h |
| 1 | Backend | 3-4 h |
| 2 | Worker | 3-4 h |
| 3 | Frontend | 4-5 h |
| 4 | LXC-Skripte | 1-2 h |
| 5 | E2E-Test | 2-3 h |
| 6 | Härtung | 1-2 h |
| **Summe** | | **15-21 h** |

---

## 8. NICHT-ZIELE (zur Klarheit)

- Kein Docker im LXC
- Kein Cloud-Worker (lokal only)
- Kein Login/User-Management (LAN-only)
- Kein ALPR-Cloud (alles lokal, PaddleOCR)
- Kein neues Frontend-Framework
- Kein eigenes Zähl-Framework (supervision ist Industriestandard)
- Kein Mobile-First (Desktop-Tool)

---

## 9. REVIEW-PUNKTE FÜR ANDREAS

Alle offenen Fragen aus §5 sind am 2026-06-08 entschieden (siehe Tabelle dort). Verbleibende Review-Punkte:

- [ ] Plan-Umfang OK, oder etwas streichen/hinzufügen?
- [ ] Phase 0 sofort starten (git init, pyproject.toml, package.json, README-Skelett)?
- [ ] Phase-Reihenfolge sinnvoll: 0 → 1 → 2 → 3 → 4 → 5 → 6?
