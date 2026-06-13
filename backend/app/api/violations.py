"""Violations: komfortabler GET für die UI (nur is_speeding=True)."""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..db import get_db
from ..models import CrossingEvent
from ..schemas import CrossingEventResponse

router = APIRouter(prefix="/violations", tags=["Violations"])


@router.get("/", response_model=list[CrossingEventResponse])
async def list_violations(
    camera_id: int | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
    min_overrun_kmh: float | None = None,
    limit: int = Query(default=200, ge=1, le=2000),
    db: AsyncSession = Depends(get_db),
) -> list[CrossingEvent]:
    stmt = (
        select(CrossingEvent)
        .options(selectinload(CrossingEvent.plates))
        .where(CrossingEvent.is_speeding.is_(True))
    )
    if camera_id is not None:
        stmt = stmt.where(CrossingEvent.camera_id == camera_id)
    if since is not None:
        stmt = stmt.where(CrossingEvent.ts >= since)
    if until is not None:
        stmt = stmt.where(CrossingEvent.ts <= until)
    if min_overrun_kmh is not None:
        stmt = stmt.where(
            (CrossingEvent.speed_kmh - CrossingEvent.speed_limit_kmh) >= min_overrun_kmh
        )
    stmt = stmt.order_by(CrossingEvent.ts.desc()).limit(limit)
    res = await db.execute(stmt)
    return list(res.scalars().all())


@router.get("/{event_id}", response_model=CrossingEventResponse)
async def get_violation(
    event_id: int,
    db: AsyncSession = Depends(get_db),
) -> CrossingEvent:
    stmt = (
        select(CrossingEvent)
        .options(selectinload(CrossingEvent.plates))
        .where(CrossingEvent.id == event_id)
        .where(CrossingEvent.is_speeding.is_(True))
    )
    res = await db.execute(stmt)
    event = res.scalar_one_or_none()
    if event is None:
        raise HTTPException(status_code=404, detail="Violation not found")
    return event
