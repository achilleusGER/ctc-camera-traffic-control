"""CRUD: Kameras + Worker-Config-Endpoint."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..db import get_db
from ..models import Camera, Calibration, CountingLine, Street
from ..schemas import (
    CameraConfigResponse,
    CameraCreate,
    CameraResponse,
    CameraUpdate,
)

router = APIRouter(prefix="/cameras", tags=["Cameras"])


@router.get("/", response_model=list[CameraResponse])
async def list_cameras(
    street_id: int | None = None,
    enabled: bool | None = None,
    db: AsyncSession = Depends(get_db),
) -> list[Camera]:
    stmt = select(Camera).order_by(Camera.id)
    if street_id is not None:
        stmt = stmt.where(Camera.street_id == street_id)
    if enabled is not None:
        stmt = stmt.where(Camera.enabled == enabled)
    res = await db.execute(stmt)
    return list(res.scalars().all())


@router.post("/", response_model=CameraResponse, status_code=status.HTTP_201_CREATED)
async def create_camera(
    payload: CameraCreate, db: AsyncSession = Depends(get_db)
) -> Camera:
    if payload.street_id is not None:
        street = await db.get(Street, payload.street_id)
        if not street:
            raise HTTPException(status_code=400, detail="street_id not found")
    cam = Camera(**payload.model_dump())
    db.add(cam)
    await db.commit()
    await db.refresh(cam)
    return cam


@router.get("/{camera_id}", response_model=CameraResponse)
async def get_camera(camera_id: int, db: AsyncSession = Depends(get_db)) -> Camera:
    cam = await db.get(Camera, camera_id)
    if not cam:
        raise HTTPException(status_code=404, detail="Camera not found")
    return cam


@router.patch("/{camera_id}", response_model=CameraResponse)
async def update_camera(
    camera_id: int,
    payload: CameraUpdate,
    db: AsyncSession = Depends(get_db),
) -> Camera:
    cam = await db.get(Camera, camera_id)
    if not cam:
        raise HTTPException(status_code=404, detail="Camera not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(cam, k, v)
    await db.commit()
    await db.refresh(cam)
    return cam


@router.delete("/{camera_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_camera(camera_id: int, db: AsyncSession = Depends(get_db)) -> None:
    cam = await db.get(Camera, camera_id)
    if not cam:
        raise HTTPException(status_code=404, detail="Camera not found")
    await db.delete(cam)
    await db.commit()


@router.get("/{camera_id}/config", response_model=CameraConfigResponse)
async def get_camera_config(
    camera_id: int, db: AsyncSession = Depends(get_db)
) -> CameraConfigResponse:
    """Was der Worker zum Start braucht: Kamera + Linien + Kalibrierung."""
    stmt = (
        select(Camera)
        .options(selectinload(Camera.lines), selectinload(Camera.calibration))
        .where(Camera.id == camera_id)
    )
    res = await db.execute(stmt)
    cam = res.scalar_one_or_none()
    if not cam:
        raise HTTPException(status_code=404, detail="Camera not found")

    cam_dict = {
        "id": cam.id,
        "name": cam.name,
        "rtsp_url_low": cam.rtsp_url_low,
        "rtsp_url_high": cam.rtsp_url_high,
        "width": cam.width,
        "height": cam.height,
        "infer_width": cam.infer_width,
        "fps_limit": cam.fps_limit,
        "default_speed_limit_kmh": cam.default_speed_limit_kmh,
        "alpr_enabled": cam.alpr_enabled,
        "model_variant": cam.model_variant,
        "enabled": cam.enabled,
    }
    lines = [
        {
            "id": ln.id,
            "name": ln.name,
            "points": ln.points,
            "direction_in_label": ln.direction_in_label,
            "direction_out_label": ln.direction_out_label,
            "speed_limit_kmh": ln.speed_limit_kmh,
        }
        for ln in cam.lines
    ]
    cal = None
    if cam.calibration is not None:
        cal = {
            "source_points": cam.calibration.source_points,
            "target_width_m": cam.calibration.target_width_m,
            "target_height_m": cam.calibration.target_height_m,
        }

    return CameraConfigResponse(
        camera=cam_dict,
        lines=lines,
        calibration=cal,
        model_variant=cam.model_variant,
        infer_width=cam.infer_width,
    )
