"""Kalibrierung: GET/PUT für die 4-Punkt-Perspektive pro Kamera."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..models import Calibration, Camera
from ..schemas import CalibrationCreate, CalibrationResponse

router = APIRouter(prefix="/cameras/{camera_id}/calibration", tags=["Calibration"])


@router.get("/", response_model=CalibrationResponse | None)
async def get_calibration(
    camera_id: int, db: AsyncSession = Depends(get_db)
) -> Calibration | None:
    cam = await db.get(Camera, camera_id)
    if not cam:
        raise HTTPException(status_code=404, detail="Camera not found")
    res = await db.execute(
        select(Calibration).where(Calibration.camera_id == camera_id)
    )
    return res.scalar_one_or_none()


@router.put("/", response_model=CalibrationResponse)
async def upsert_calibration(
    camera_id: int,
    payload: CalibrationCreate,
    db: AsyncSession = Depends(get_db),
) -> Calibration:
    cam = await db.get(Camera, camera_id)
    if not cam:
        raise HTTPException(status_code=404, detail="Camera not found")

    res = await db.execute(
        select(Calibration).where(Calibration.camera_id == camera_id)
    )
    cal = res.scalar_one_or_none()

    data = payload.model_dump()
    if cal is None:
        cal = Calibration(camera_id=camera_id, **data)
        db.add(cal)
    else:
        for k, v in data.items():
            setattr(cal, k, v)

    await db.commit()
    await db.refresh(cal)
    return cal


@router.delete("/", status_code=status.HTTP_204_NO_CONTENT)
async def delete_calibration(
    camera_id: int, db: AsyncSession = Depends(get_db)
) -> None:
    res = await db.execute(
        select(Calibration).where(Calibration.camera_id == camera_id)
    )
    cal = res.scalar_one_or_none()
    if not cal:
        raise HTTPException(status_code=404, detail="Calibration not found")
    await db.delete(cal)
    await db.commit()
