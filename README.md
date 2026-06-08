# Hermes-Trafficcontrol

Verkehrszählung und Geschwindigkeitsmessung aus mehreren RTSPS-Netzwerkkameras,
deploybar auf einem Proxmox-LXC (nativ, ohne Docker).

- **Backend:** Python 3.12, FastAPI, SQLAlchemy 2 (async), asyncpg, Alembic
- **Worker:** Ultralytics (yolo11m/s), supervision, OpenCV, FFmpeg, PaddleOCR (optional)
- **Frontend:** React 18, Vite, TypeScript, TanStack Query, Recharts
- **Stack:** PostgreSQL 16, Redis 7, nginx, systemd (kein Docker)

## Komponenten

| Pfad | Inhalt |
|------|--------|
| `backend/` | FastAPI: REST, WebSocket, MJPEG-Stream, Redis-Consumer, DB-Modelle |
| `worker/`  | Inferenz-Worker (1 Prozess pro Kamera, systemd-Template `worker@.service`) |
| `frontend/`| React + Vite + TypeScript: Live, Dashboard, Violations, Reports, Kalibrierung, Verwaltung |
| `lxc/`     | Proxmox-LXC-Setup-Skripte und systemd-Units |

## Status

Phase 0–4 abgeschlossen (Repo-Skelett, Backend, Worker, Frontend, LXC-Setup).
Phase 5 (E2E-Test auf Proxmox) und Phase 6 (Härtung) folgen.

Implementierungsplan: [`.hermes/plans/2026-06-08_163800-proxmox-lxc-deploy.md`](.hermes/plans/2026-06-08_163800-proxmox-lxc-deploy.md)

## Voraussetzungen (geplant)

- Python ≥ 3.12
- Node ≥ 20
- FFmpeg (für RTSPS-Capture)
- PostgreSQL 16, Redis 7
- nginx

## Lizenz / DSGVO

Beweisfotos und (optionale) ALPR-Ergebnisse verarbeiten personenbezogene Daten.
Vor Produktivbetrieb Rechtsgrundlage, Aufbewahrungs- und Löschfristen klären.
ALPR ist je Kamera standardmäßig **aus**. Dieses System ist ein
Analyse- und Dokumentationswerkzeug, kein amtlicher (geeichter) Blitzer.

## Danksagung — Drittsoftware

Dieses Projekt steht auf den Schultern von Open-Source-Software. Vielen Dank an
alle Maintainer:innen und Contributer:innen der folgenden Bibliotheken und Tools.

### KI / Computer Vision

| Bibliothek | Version | Lizenz | Verwendung |
|------------|---------|--------|------------|
| [Ultralytics YOLO](https://github.com/ultralytics/ultralytics) | ≥ 8.3.0 | **AGPL-3.0** | Objekterkennung (PKW/LKW/Bus/Motorrad/Fahrrad/Person) |
| [Roboflow supervision](https://github.com/roboflow/supervision) | ≥ 0.24.0 | MIT | ByteTrack-Tracker, LineZone-Zählung, ViewTransformer (4-Punkt-Perspektive), Annotators |
| [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR) | ≥ 2.8.0 (Linux) | Apache-2.0 | Optionale Kennzeichenerkennung (ALPR), default **aus** |
| [PaddlePaddle](https://github.com/PaddlePaddle/Paddle) | ≥ 2.6.0 (Linux) | Apache-2.0 | Deep-Learning-Backend für PaddleOCR |
| [OpenCV (opencv-python-headless)](https://github.com/opencv/opencv) | ≥ 4.10.0 | Apache-2.0 | Bildverarbeitung, Resize, JPEG-Encoding |
| [PyAV](https://github.com/PyAV-Org/PyAV) | ≥ 12.0.0 | MIT | RTSPS-Frame-Reader (FFmpeg-Bindings) |

> **Wichtig zur Lizenz:** Ultralytics YOLO ist **AGPL-3.0-lizenziert**. Bei
> öffentlichem Bereitstellen eines Dienstes, der YOLO nutzt (z. B. als SaaS),
> greifen AGPL-Bestimmungen. Für ein privates LAN-Tool wie dieses (keine
> Weitergabe an Dritte) ist das unkritisch. Bei späterer Veröffentlichung
> bitte prüfen.

### Backend (Python)

| Bibliothek | Version | Lizenz | Verwendung |
|------------|---------|--------|------------|
| [FastAPI](https://github.com/fastapi/fastapi) | ≥ 0.115.0 | MIT | HTTP-Framework, REST + WebSocket |
| [SQLAlchemy](https://github.com/sqlalchemy/sqlalchemy) | ≥ 2.0.36 | MIT | ORM (async) |
| [asyncpg](https://github.com/MagicStack/asyncpg) | ≥ 0.30.0 | Apache-2.0 | PostgreSQL-Driver (async) |
| [Alembic](https://github.com/sqlalchemy/alembic) | ≥ 1.14.0 | MIT | DB-Migrationen |
| [psycopg2-binary](https://github.com/psycopg/psycopg2) | ≥ 2.9.10 | LGPL-3.0 | Alembic sync-Driver |
| [Pydantic](https://github.com/pydantic/pydantic) | ≥ 2.10.0 | MIT | Settings + Schemas |
| [redis-py](https://github.com/redis/redis-py) | ≥ 5.2.0 | MIT | Redis-Client (async) |
| [ReportLab](https://github.com/Distrotech/reportlab) | ≥ 4.2.0 | BSD-3-Clause | PDF-Reports |

### Frontend (TypeScript / React)

| Bibliothek | Version | Lizenz | Verwendung |
|------------|---------|--------|------------|
| [React](https://github.com/facebook/react) | 18.3.1 | MIT | UI-Framework |
| [Vite](https://github.com/vitejs/vite) | ≥ 5.4.11 | MIT | Build-Tool + Dev-Server |
| [TypeScript](https://github.com/microsoft/TypeScript) | ≥ 5.7.2 | Apache-2.0 | Type-System |
| [TanStack Query](https://github.com/TanStack/query) | ≥ 5.62.0 | MIT | Server-State-Management |
| [React Router](https://github.com/remix-run/react-router) | ≥ 6.28.0 | MIT | Client-Side-Routing |
| [Axios](https://github.com/axios/axios) | ≥ 1.7.9 | MIT | HTTP-Client |
| [Recharts](https://github.com/recharts/recharts) | ≥ 2.13.0 | MIT | Charts (Heatmap, Speed-Histogramm) |
| [date-fns](https://github.com/date-fns/date-fns) | ≥ 4.1.0 | MIT | Datums-Formatter (de_DE) |

### Schriften

| Schrift | Quelle | Lizenz | Verwendung |
|---------|--------|--------|------------|
| [Instrument Serif](https://fonts.google.com/specimen/Instrument+Serif) | Google Fonts | OFL-1.1 | Display-Überschriften (Tiles, Headlines) |
| [Geist](https://fonts.google.com/specimen/Geist) | Google Fonts | OFL-1.1 | Body, UI |

### System / Infra

| Komponente | Version | Lizenz | Verwendung |
|------------|---------|--------|------------|
| [PostgreSQL](https://www.postgresql.org/) | 15 (Debian-Paket) | PostgreSQL License | Datenbank |
| [Redis](https://github.com/redis/redis) | 7 (Debian-Paket) | BSD-3-Clause | Pub/Sub-Bus, MJPEG-Frame-Buffer |
| [nginx](https://github.com/nginx/nginx) | (Debian-Paket) | BSD-2-Clause | Reverse-Proxy + Static-Serving |
| [FFmpeg](https://github.com/FFmpeg/FFmpeg) | (Debian-Paket) | LGPL-2.1+ / GPL-2+ | RTSPS-Transcoding, Frame-Encoding |
| [Debian GNU/Linux](https://www.debian.org/) | 12 (Bookworm) | DFSG / variety of free licenses | Basis-OS |
| [systemd](https://github.com/systemd/systemd) | (Debian-Paket) | LGPL-2.1+ | Service-Management |
| [Proxmox VE](https://www.proxmox.com/) | — | AGPL-3.0 | Hypervisor (Host) |

### Design-Vorlage

| Tool | Lizenz | Verwendung |
|------|--------|------------|
| [Hallmark-Skill](https://github.com/hermes-agent/skills) (lokal in `~/.hermes/skills/hallmark/`) | Hermes-Agent-Skill | Lumen/Night-Foundry-Theme, Bento-Grid-Macrostructure, OKLCH-Tokens, Anti-Slop-Discipline |

### Konzeptuelle Vorlagen (Inspiration)

Diese Quellen haben das **Konzept und die Roadmap** inspiriert, wurden aber
nicht 1:1 kopiert:

- [Hallmark Anti-Slop-Design-Skill](https://github.com/hermes-agent) — Design-Discipline, Bento-Grid-Macrostructure
- [community-scripts.org](https://community-scripts.org/) — LXC-Installer-Pattern (`curl|bash`-Stil, Argumente statt ENV, farbiger Output)
- [Roboflow Supervision Repo](https://github.com/roboflow/supervision) — wurde im ursprünglichen Konzept als Quelle für die Pipeline-Logik genannt; **dieses Projekt implementiert die Pipeline-Logik eigenständig** auf Basis der supervision-API, kein Code wurde kopiert

---

Lizenz des Projekts selbst: **Noch nicht festgelegt.** Vorschlag: MIT (kompatibel
mit den meisten Dependencies, **außer** AGPL-3.0 von Ultralytics YOLO — siehe
Hinweis oben).
