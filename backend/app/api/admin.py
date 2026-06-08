"""Admin: Retention / Cleanup (Q3)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..db import get_db
from ..models import CrossingEvent
from ..schemas import CleanupResult

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.post("/cleanup-evidence", response_model=CleanupResult)
async def cleanup_evidence(
    older_than_days: int = Query(..., ge=1, description="Löscht Events/Plates/Files älter als X Tage"),
    db: AsyncSession = Depends(get_db),
) -> CleanupResult:
    if older_than_days < settings.cleanup_min_age_days:
        raise HTTPException(
            status_code=400,
            detail=f"older_than_days muss >= {settings.cleanup_min_age_days} sein (Hard-Floor)",
        )

    cutoff = datetime.now(timezone.utc) - timedelta(days=older_than_days)

    # 1) Pfade einsammeln VOR dem Löschen
    stmt = select(CrossingEvent.evidence_paths, CrossingEvent.id).where(
        CrossingEvent.ts < cutoff
    )
    res = await db.execute(stmt)
    rows = res.all()
    paths: list[str] = list({p for ev_paths, _ in rows for p in (ev_paths or [])})

    # 2) Events löschen (Plates kaskadieren via FK)
    del_stmt = delete(CrossingEvent).where(CrossingEvent.ts < cutoff)
    result = await db.execute(del_stmt)
    deleted_events = int(result.rowcount or 0)

    # 3) Files löschen
    deleted_files = 0
    freed_bytes = 0
    for rel in paths:
        try:
            base = settings.media_dir.resolve()
            p = (base / rel).resolve()
            if not str(p).startswith(str(base)):
                continue
            if p.is_file():
                size = p.stat().st_size
                p.unlink()
                deleted_files += 1
                freed_bytes += size
        except Exception:
            # Cleanup-Fehler loggen wir nicht im Detail (würde Response aufblähen).
            # Fail-Safe: ein einzelner fehlgeschlagener Unlink stoppt den Cleanup nicht.
            continue

    await db.commit()

    return CleanupResult(
        deleted_events=deleted_events,
        deleted_files=deleted_files,
        freed_bytes=freed_bytes,
        older_than_days=older_than_days,
    )


@router.get("/storage-info")
async def storage_info() -> dict:
    """Übersicht: Media-Dir belegt? DB erreichbar?"""
    base = settings.media_dir
    total = 0
    n_files = 0
    if base.exists():
        for f in base.rglob("*"):
            if f.is_file():
                total += f.stat().st_size
                n_files += 1
    return {
        "media_dir": str(base),
        "exists": base.exists(),
        "file_count": n_files,
        "size_bytes": total,
    }
