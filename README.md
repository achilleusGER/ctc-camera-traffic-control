# Hermes-Trafficcontrol

Webanwendung zur Verkehrszählung und Geschwindigkeitsmessung aus mehreren
RTSPS-Netzwerkkameras, deploybar auf einem Proxmox-LXC (nativ, ohne Docker).

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

Phase 0 — Repository-Grundgerüst. Noch keine Funktionalität.

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
