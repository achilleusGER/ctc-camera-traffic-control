"""SQLAlchemy-Modelle: Straßen, Kameras, Linien, Kalibrierung, Ereignisse, Plates."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


class Street(Base):
    __tablename__ = "streets"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), index=True)
    description: Mapped[str | None] = mapped_column(String(500), default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    cameras: Mapped[list[Camera]] = relationship(back_populates="street")


class Camera(Base):
    __tablename__ = "cameras"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), index=True)
    rtsp_url_low: Mapped[str] = mapped_column(String(500))
    rtsp_url_high: Mapped[str | None] = mapped_column(String(500), default=None)
    street_id: Mapped[int | None] = mapped_column(
        ForeignKey("streets.id", ondelete="SET NULL"), default=None, index=True
    )
    width: Mapped[int] = mapped_column(Integer, default=1920)
    height: Mapped[int] = mapped_column(Integer, default=1080)
    infer_width: Mapped[int] = mapped_column(Integer, default=1280)
    fps_limit: Mapped[int] = mapped_column(Integer, default=12)
    default_speed_limit_kmh: Mapped[float | None] = mapped_column(Float, default=None)
    alpr_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    model_variant: Mapped[str] = mapped_column(String(2), default="m")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    street: Mapped[Street | None] = relationship(back_populates="cameras")
    lines: Mapped[list[CountingLine]] = relationship(
        back_populates="camera", cascade="all, delete-orphan"
    )
    calibration: Mapped[Calibration | None] = relationship(
        back_populates="camera",
        cascade="all, delete-orphan",
        uselist=False,
    )


class CountingLine(Base):
    __tablename__ = "counting_lines"

    id: Mapped[int] = mapped_column(primary_key=True)
    camera_id: Mapped[int] = mapped_column(
        ForeignKey("cameras.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(200))
    points: Mapped[list[Any]] = mapped_column(JSONB)
    direction_in_label: Mapped[str] = mapped_column(String(100), default="in")
    direction_out_label: Mapped[str] = mapped_column(String(100), default="out")
    speed_limit_kmh: Mapped[float | None] = mapped_column(Float, default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    camera: Mapped[Camera] = relationship(back_populates="lines")


class Calibration(Base):
    __tablename__ = "calibrations"

    id: Mapped[int] = mapped_column(primary_key=True)
    camera_id: Mapped[int] = mapped_column(
        ForeignKey("cameras.id", ondelete="CASCADE"),
        unique=True,
        index=True,
    )
    source_points: Mapped[list[Any]] = mapped_column(JSONB)
    target_width_m: Mapped[float] = mapped_column(Float)
    target_height_m: Mapped[float] = mapped_column(Float)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    camera: Mapped[Camera] = relationship(back_populates="calibration")


class CrossingEvent(Base):
    __tablename__ = "crossing_events"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    camera_id: Mapped[int] = mapped_column(
        ForeignKey("cameras.id", ondelete="CASCADE"), index=True
    )
    line_id: Mapped[int | None] = mapped_column(
        ForeignKey("counting_lines.id", ondelete="SET NULL"),
        index=True,
        default=None,
    )
    ts: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    vehicle_class: Mapped[str] = mapped_column(String(50), index=True)
    direction: Mapped[str] = mapped_column(String(100))
    track_id: Mapped[int | None] = mapped_column(Integer, default=None)
    speed_kmh: Mapped[float | None] = mapped_column(Float, default=None)
    speed_limit_kmh: Mapped[float | None] = mapped_column(Float, default=None)
    is_speeding: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    evidence_paths: Mapped[list[str]] = mapped_column(JSONB, default=list)
    notes: Mapped[str | None] = mapped_column(Text, default=None)

    camera: Mapped[Camera] = relationship()
    line: Mapped[CountingLine | None] = relationship()
    plates: Mapped[list[Plate]] = relationship(
        back_populates="event", cascade="all, delete-orphan"
    )


class Plate(Base):
    __tablename__ = "plates"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    event_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("crossing_events.id", ondelete="CASCADE"),
        index=True,
    )
    plate_text: Mapped[str] = mapped_column(String(20), index=True)
    confidence: Mapped[float | None] = mapped_column(Float, default=None)
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    event: Mapped[CrossingEvent] = relationship(back_populates="plates")
