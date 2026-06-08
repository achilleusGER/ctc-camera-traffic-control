"""Pydantic-Schemas für REST + Worker-Push."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ─── Street ─────────────────────────────────────────────────────────────────


class StreetBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=500)


class StreetCreate(StreetBase):
    pass


class StreetUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=500)


class StreetResponse(StreetBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime


# ─── Camera ─────────────────────────────────────────────────────────────────


class CameraBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    rtsp_url_low: str = Field(..., min_length=1, max_length=500)
    rtsp_url_high: str | None = Field(default=None, max_length=500)
    street_id: int | None = None
    width: int = 1920
    height: int = 1080
    infer_width: int = 1280
    fps_limit: int = 12
    default_speed_limit_kmh: float | None = None
    alpr_enabled: bool = False
    model_variant: Literal["m", "s"] = "m"
    enabled: bool = True

    @field_validator("infer_width")
    @classmethod
    def _infer_width_multiple_of_32(cls, v: int) -> int:
        if v % 32 != 0:
            raise ValueError("infer_width muss Vielfaches von 32 sein (YOLO-Constraint)")
        if v < 256 or v > 1920:
            raise ValueError("infer_width muss zwischen 256 und 1920 liegen")
        return v


class CameraCreate(CameraBase):
    pass


class CameraUpdate(BaseModel):
    name: str | None = None
    rtsp_url_low: str | None = None
    rtsp_url_high: str | None = None
    street_id: int | None = None
    infer_width: int | None = None
    fps_limit: int | None = None
    default_speed_limit_kmh: float | None = None
    alpr_enabled: bool | None = None
    model_variant: Literal["m", "s"] | None = None
    enabled: bool | None = None


class CameraResponse(CameraBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime


# ─── CountingLine ───────────────────────────────────────────────────────────


class CountingLineBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    points: list[list[float]] = Field(
        ..., min_length=2, max_length=2,
        description="Genau 2 Punkte [[x1,y1],[x2,y2]] in Pixel-Koordinaten",
    )
    direction_in_label: str = "in"
    direction_out_label: str = "out"
    speed_limit_kmh: float | None = None

    @field_validator("points")
    @classmethod
    def _points_well_formed(cls, v: list[list[float]]) -> list[list[float]]:
        if len(v) != 2 or any(len(p) != 2 for p in v):
            raise ValueError("points muss genau [[x1,y1],[x2,y2]] sein")
        return [[float(x), float(y)] for x, y in v]


class CountingLineCreate(CountingLineBase):
    pass


class CountingLineUpdate(BaseModel):
    name: str | None = None
    points: list[list[float]] | None = None
    direction_in_label: str | None = None
    direction_out_label: str | None = None
    speed_limit_kmh: float | None = None


class CountingLineResponse(CountingLineBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    camera_id: int
    created_at: datetime


# ─── Calibration ────────────────────────────────────────────────────────────


class CalibrationBase(BaseModel):
    source_points: list[list[float]] = Field(
        ..., min_length=4, max_length=4,
        description="4 Punkte [[x,y],...] in Pixel-Koordinaten (Eckpunkte einer realen Rechteckfläche)",
    )
    target_width_m: float = Field(..., gt=0)
    target_height_m: float = Field(..., gt=0)

    @field_validator("source_points")
    @classmethod
    def _4_points(cls, v: list[list[float]]) -> list[list[float]]:
        if len(v) != 4 or any(len(p) != 2 for p in v):
            raise ValueError("source_points muss genau 4 Punkte [[x,y],...] sein")
        return [[float(x), float(y)] for x, y in v]


class CalibrationCreate(CalibrationBase):
    pass


class CalibrationResponse(CalibrationBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    camera_id: int
    updated_at: datetime


# ─── Worker-Push (Event erstellen) ──────────────────────────────────────────


class EvidenceRef(BaseModel):
    """Verweis auf ein gespeichertes Beweisfoto."""
    path: str
    kind: str = "vehicle_crop"


class CrossingEventIn(BaseModel):
    """Was der Worker ans Backend pusht."""
    type: Literal["crossing"] = "crossing"
    camera_id: int
    line_id: int | None = None
    ts: datetime
    vehicle_class: str
    direction: str
    track_id: int | None = None
    speed_kmh: float | None = None
    speed_limit_kmh: float | None = None
    is_speeding: bool = False
    plate_text: str | None = None
    plate_confidence: float | None = None
    evidence: list[EvidenceRef] = Field(default_factory=list)


class CrossingEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    camera_id: int
    line_id: int | None
    ts: datetime
    vehicle_class: str
    direction: str
    track_id: int | None
    speed_kmh: float | None
    speed_limit_kmh: float | None
    is_speeding: bool
    evidence_paths: list[str]
    plates: list["PlateResponse"] = Field(default_factory=list)


class PlateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    plate_text: str
    confidence: float | None
    captured_at: datetime


# ─── Worker-Config (GET /cameras/{id}/config) ───────────────────────────────


class CameraConfigResponse(BaseModel):
    """Was der Worker zum Start braucht. Plain dict, nicht ORM-gebunden."""
    camera: dict[str, Any]
    lines: list[dict[str, Any]]
    calibration: dict[str, Any] | None = None
    model_variant: Literal["m", "s"]
    infer_width: int


# ─── Stats & Reports ───────────────────────────────────────────────────────


class CountsByClass(BaseModel):
    vehicle_class: str
    count: int


class CountsByHour(BaseModel):
    hour: int  # 0..23
    count: int


class SpeedBin(BaseModel):
    bin_start_kmh: float
    bin_end_kmh: float
    count: int


class HeatmapCell(BaseModel):
    weekday: int  # 0=Montag ... 6=Sonntag
    hour: int     # 0..23
    count: int


# ─── Admin ──────────────────────────────────────────────────────────────────


class CleanupResult(BaseModel):
    deleted_events: int
    deleted_files: int
    freed_bytes: int
    older_than_days: int
