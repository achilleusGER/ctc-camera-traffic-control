"""Stats: Aggregationen fürs Dashboard."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..models import CrossingEvent
from ..schemas import CountsByClass, CountsByHour

router = APIRouter(prefix="/stats", tags=["Stats"])


def _day_start_utc(d: datetime | None = None) -> datetime:
    if d is None:
        d = datetime.now(timezone.utc)
    return d.replace(hour=0, minute=0, second=0, microsecond=0)


@router.get("/today", response_model=list[CountsByClass])
async def counts_today(
    camera_id: int | None = None, db: AsyncSession = Depends(get_db)
) -> list[CountsByClass]:
    since = _day_start_utc()
    stmt = (
        select(CrossingEvent.vehicle_class, func.count(CrossingEvent.id))
        .where(CrossingEvent.ts >= since)
        .group_by(CrossingEvent.vehicle_class)
    )
    if camera_id is not None:
        stmt = stmt.where(CrossingEvent.camera_id == camera_id)
    res = await db.execute(stmt)
    return [CountsByClass(vehicle_class=cls, count=cnt) for cls, cnt in res.all()]


@router.get("/by-hour", response_model=list[CountsByHour])
async def counts_by_hour(
    since: datetime | None = None,
    until: datetime | None = None,
    camera_id: int | None = None,
    db: AsyncSession = Depends(get_db),
) -> list[CountsByHour]:
    if since is None:
        since = datetime.now(timezone.utc) - timedelta(days=1)
    if until is None:
        until = datetime.now(timezone.utc)

    hour_col = func.extract("hour", CrossingEvent.ts).label("hour")
    stmt = (
        select(hour_col, func.count(CrossingEvent.id))
        .where(CrossingEvent.ts >= since, CrossingEvent.ts <= until)
        .group_by(hour_col)
    )
    if camera_id is not None:
        stmt = stmt.where(CrossingEvent.camera_id == camera_id)
    stmt = stmt.order_by(hour_col)
    res = await db.execute(stmt)
    return [CountsByHour(hour=int(h), count=c) for h, c in res.all()]


@router.get("/speed-average")
async def speed_average(
    since: datetime | None = None,
    camera_id: int | None = None,
    db: AsyncSession = Depends(get_db),
) -> dict:
    if since is None:
        since = datetime.now(timezone.utc) - timedelta(hours=24)
    stmt = select(
        func.avg(CrossingEvent.speed_kmh).label("avg"),
        func.max(CrossingEvent.speed_kmh).label("max"),
        func.count(CrossingEvent.id).label("n"),
    ).where(CrossingEvent.ts >= since, CrossingEvent.speed_kmh.is_not(None))
    if camera_id is not None:
        stmt = stmt.where(CrossingEvent.camera_id == camera_id)
    res = await db.execute(stmt)
    row = res.one()
    return {
        "avg_kmh": float(row.avg) if row.avg is not None else None,
        "max_kmh": float(row.max) if row.max is not None else None,
        "n": int(row.n),
    }
