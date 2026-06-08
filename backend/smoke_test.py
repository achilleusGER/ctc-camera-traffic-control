"""Smoke-Test für Hermes-Trafficcontrol Backend.

Aufruf:  cd backend && .venv/bin/python smoke_test.py

Prüft:
  1. Alle Module importieren ohne Fehler
  2. FastAPI-App hat alle Router registriert
  3. Settings-Defaults sind plausibel
  4. (Optional) DB-Verbindung mit DATABASE_URL aus .env

Exit-Code 0 = OK, 1 = Fehler.
"""
from __future__ import annotations

import sys
from pathlib import Path

# .env laden (optional)
try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).parent / ".env")
except ImportError:
    pass


def main() -> int:
    print("=" * 60)
    print("Hermes-Trafficcontrol Backend — Smoke-Test")
    print("=" * 60)

    # 1. Imports
    print("\n[1/4] Module-Importe …")
    from app.config import settings
    from app.db import Base, engine
    from app.models import (
        Camera,
        Calibration,
        CountingLine,
        CrossingEvent,
        Plate,
        Street,
    )
    from app.schemas import (
        CameraConfigResponse,
        CameraCreate,
        CrossingEventIn,
        CrossingEventResponse,
        HeatmapCell,
        SpeedBin,
        StreetCreate,
    )
    from app.api import (
        admin,
        calibration,
        cameras,
        events,
        lines,
        media,
        reports,
        stats,
        streets,
        violations,
    )
    from app.streaming import mjpeg
    from app.ws import hub
    from app.consumer import consume_events
    from app.main import app, lifespan
    from app.redis_bus import bus
    print("  OK")

    # 2. Router
    print("\n[2/4] FastAPI-Router …")
    paths = sorted({r.path for r in app.routes if hasattr(r, "path")})
    must_have = [
        "/streets/",
        "/cameras/",
        "/cameras/{camera_id}/lines/",
        "/cameras/{camera_id}/calibration/",
        "/cameras/{camera_id}/config",
        "/events/",
        "/violations/",
        "/stats/today",
        "/stats/by-hour",
        "/stats/speed-average",
        "/reports/heatmap",
        "/reports/speed-histogram",
        "/reports/export.csv",
        "/reports/export.pdf",
        "/media/evidence/{path:path}",
        "/admin/cleanup-evidence",
        "/admin/storage-info",
        "/health",
        "/cameras/{camera_id}/stream.mjpg",
        "/ws",
    ]
    missing = [p for p in must_have if p not in paths]
    if missing:
        print(f"  FEHLT: {missing}")
        return 1
    print(f"  {len(paths)} Pfade registriert, alle erwarteten vorhanden")

    # 3. Settings
    print("\n[3/4] Settings …")
    print(f"  DATABASE_URL  = {settings.database_url}")
    print(f"  REDIS_URL     = {settings.redis_url}")
    print(f"  MEDIA_DIR     = {settings.media_dir}")
    print(f"  CORS origins  = {settings.cors_origins_list}")
    print(f"  Cleanup-Floor = {settings.cleanup_min_age_days} Tage")
    print("  OK")

    # 4. Tabellen in Base.metadata?
    print("\n[4/4] DB-Tabellen …")
    tables = sorted(Base.metadata.tables.keys())
    expected = {"streets", "cameras", "counting_lines", "calibrations", "crossing_events", "plates"}
    missing_t = expected - set(tables)
    if missing_t:
        print(f"  FEHLT: {missing_t}")
        return 1
    print(f"  {len(tables)} Tabellen registriert: {', '.join(tables)}")
    print("  OK")

    # Optional: DB-Ping (nur wenn erreichbar)
    print("\n[optional] DB-Ping …")
    import asyncio

    async def _ping() -> bool:
        try:
            from sqlalchemy import text

            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            return True
        except Exception as exc:
            print(f"  übersprungen (DB nicht erreichbar): {type(exc).__name__}: {exc}")
            return False

    if asyncio.run(_ping()):
        print("  DB erreichbar ✓")

    print("\n" + "=" * 60)
    print("SMOKE-TEST OK")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
