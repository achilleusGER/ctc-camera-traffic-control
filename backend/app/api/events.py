"""Events: Worker-Push (POST) + GET mit Filter."""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..db import get_db
from ..models import Camera, CrossingEvent, Plate
from ..schemas import CrossingEventIn, CrossingEventResponse

router = APIRouter(prefix="/events", tags=["Events"])


@router.post(
    "/", response_model=CrossingEventResponse, status_code=status.HTTP_201_CREATED
)
async def create_event(
    payload: CrossingEventIn, db: AsyncSession = Depends(get_db)
) -> CrossingEvent:
    """Worker-Push: ein Linienübertritt inkl. Speed + Beweis-Liste."""
    # Plausi
    if not await db.get(Camera, payload.camera_id):
        raise HTTPException(status_code=400, detail="camera_id not found")

    evidence_paths = [e.path for e in payload.evidence]
    event = CrossingEvent(
        camera_id=payload.camera_id,
        line_id=payload.line_id,
        ts=payload.ts,
        vehicle_class=payload.vehicle_class,
        direction=payload.direction,
        track_id=payload.track_id,
        speed_kmh=payload.speed_kmh,
        speed_limit_kmh=payload.speed_limit_kmh,
        is_speeding=payload.is_speeding,
        evidence_paths=evidence_paths,
    )
    db.add(event)
    await db.flush()  # ID vergeben

    if payload.plate_text:
        plate = Plate(
            event_id=event.id,
            plate_text=payload.plate_text,
            confidence=payload.plate_confidence,
        )
        db.add(plate)

    await db.commit()
    await db.refresh(event, attribute_names=["plates"])
    return event


@router.get("/", response_model=list[CrossingEventResponse])
async def list_events(
    camera_id: int | None = None,
    line_id: int | None = None,
    vehicle_class: str | None = None,
    is_speeding: bool | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
    limit: int = Query(default=200, ge=1, le=2000),
    db: AsyncSession = Depends(get_db),
) -> list[CrossingEvent]:
    stmt = select(CrossingEvent).options(selectinload(CrossingEvent.plates))
    if camera_id is not None:
        stmt = stmt.where(CrossingEvent.camera_id == camera_id)
    if line_id is not None:
        stmt = stmt.where(CrossingEvent.line_id == line_id)
    if vehicle_class is not None:
        stmt = stmt.where(CrossingEvent.vehicle_class == vehicle_class)
    if is_speeding is not None:
        stmt = stmt.where(CrossingEvent.is_speeding == is_speeding)
    if since is not None:
        stmt = stmt.where(CrossingEvent.ts >= since)
    if until is not None:
        stmt = stmt.where(CrossingEvent.ts <= until)
    stmt = stmt.order_by(CrossingEvent.ts.desc()).limit(limit)
    res = await db.execute(stmt)
    return list(res.scalars().all())


@router.get("/{event_id}", response_model=CrossingEventResponse)
async def get_event(event_id: int, db: AsyncSession = Depends(get_db)) -> CrossingEvent:
    stmt = (
        select(CrossingEvent)
        .options(selectinload(CrossingEvent.plates))
        .where(CrossingEvent.id == event_id)
    )
    res = await db.execute(stmt)
    ev = res.scalar_one_or_none()
    if not ev:
        raise HTTPException(status_code=404, detail="Event not found")
    return ev
