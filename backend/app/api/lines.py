"""CRUD: Zähllinien."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..models import Camera, CountingLine
from ..schemas import CountingLineCreate, CountingLineResponse, CountingLineUpdate

router = APIRouter(prefix="/cameras/{camera_id}/lines", tags=["CountingLines"])


@router.get("/", response_model=list[CountingLineResponse])
async def list_lines(
    camera_id: int, db: AsyncSession = Depends(get_db)
) -> list[CountingLine]:
    cam = await db.get(Camera, camera_id)
    if not cam:
        raise HTTPException(status_code=404, detail="Camera not found")
    res = await db.execute(
        select(CountingLine).where(CountingLine.camera_id == camera_id)
    )
    return list(res.scalars().all())


@router.post(
    "/", response_model=CountingLineResponse, status_code=status.HTTP_201_CREATED
)
async def create_line(
    camera_id: int,
    payload: CountingLineCreate,
    db: AsyncSession = Depends(get_db),
) -> CountingLine:
    cam = await db.get(Camera, camera_id)
    if not cam:
        raise HTTPException(status_code=404, detail="Camera not found")
    line = CountingLine(camera_id=camera_id, **payload.model_dump())
    db.add(line)
    await db.commit()
    await db.refresh(line)
    return line


@router.patch("/{line_id}", response_model=CountingLineResponse)
async def update_line(
    camera_id: int,
    line_id: int,
    payload: CountingLineUpdate,
    db: AsyncSession = Depends(get_db),
) -> CountingLine:
    line = await db.get(CountingLine, line_id)
    if not line or line.camera_id != camera_id:
        raise HTTPException(status_code=404, detail="Line not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(line, k, v)
    await db.commit()
    await db.refresh(line)
    return line


@router.delete("/{line_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_line(
    camera_id: int, line_id: int, db: AsyncSession = Depends(get_db)
) -> None:
    line = await db.get(CountingLine, line_id)
    if not line or line.camera_id != camera_id:
        raise HTTPException(status_code=404, detail="Line not found")
    await db.delete(line)
    await db.commit()
