"""CRUD: Straßen."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..models import Street
from ..schemas import StreetCreate, StreetResponse, StreetUpdate

router = APIRouter(prefix="/streets", tags=["Streets"])


@router.get("/", response_model=list[StreetResponse])
async def list_streets(db: AsyncSession = Depends(get_db)) -> list[Street]:
    res = await db.execute(select(Street).order_by(Street.name))
    return list(res.scalars().all())


@router.post("/", response_model=StreetResponse, status_code=status.HTTP_201_CREATED)
async def create_street(
    payload: StreetCreate, db: AsyncSession = Depends(get_db)
) -> Street:
    street = Street(**payload.model_dump())
    db.add(street)
    await db.commit()
    await db.refresh(street)
    return street


@router.get("/{street_id}", response_model=StreetResponse)
async def get_street(street_id: int, db: AsyncSession = Depends(get_db)) -> Street:
    street = await db.get(Street, street_id)
    if not street:
        raise HTTPException(status_code=404, detail="Street not found")
    return street


@router.patch("/{street_id}", response_model=StreetResponse)
async def update_street(
    street_id: int,
    payload: StreetUpdate,
    db: AsyncSession = Depends(get_db),
) -> Street:
    street = await db.get(Street, street_id)
    if not street:
        raise HTTPException(status_code=404, detail="Street not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(street, k, v)
    await db.commit()
    await db.refresh(street)
    return street


@router.delete("/{street_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_street(street_id: int, db: AsyncSession = Depends(get_db)) -> None:
    street = await db.get(Street, street_id)
    if not street:
        raise HTTPException(status_code=404, detail="Street not found")
    await db.delete(street)
    await db.commit()
