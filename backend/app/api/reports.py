"""Reports: Heatmap (Stunde x Wochentag), Speed-Histogramm, CSV/PDF-Export."""
from __future__ import annotations

import csv
import io
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..models import CrossingEvent
from ..schemas import HeatmapCell, SpeedBin

router = APIRouter(prefix="/reports", tags=["Reports"])


# ─── Heatmap: Wochentag x Stunde ───────────────────────────────────────────


@router.get("/heatmap", response_model=list[HeatmapCell])
async def heatmap(
    since: datetime | None = None,
    until: datetime | None = None,
    camera_id: int | None = None,
    db: AsyncSession = Depends(get_db),
) -> list[HeatmapCell]:
    if since is None:
        since = datetime.now(timezone.utc) - timedelta(days=7)
    if until is None:
        until = datetime.now(timezone.utc)

    # Postgres EXTRACT: dow 0=Sunday, 1=Monday... Wir wollen 0=Monday.
    # (dow + 6) % 7 → 0=Mon, 6=Sun
    weekday_col = ((func.extract("dow", CrossingEvent.ts).cast(type_=None) + 6) % 7).label("weekday")
    hour_col = func.extract("hour", CrossingEvent.ts).label("hour")
    stmt = (
        select(weekday_col, hour_col, func.count(CrossingEvent.id))
        .where(CrossingEvent.ts >= since, CrossingEvent.ts <= until)
        .group_by(weekday_col, hour_col)
    )
    if camera_id is not None:
        stmt = stmt.where(CrossingEvent.camera_id == camera_id)
    stmt = stmt.order_by(weekday_col, hour_col)
    res = await db.execute(stmt)
    return [
        HeatmapCell(weekday=int(wd), hour=int(hr), count=cnt)
        for wd, hr, cnt in res.all()
    ]


# ─── Speed-Histogramm (5-km/h-Bins) ────────────────────────────────────────


@router.get("/speed-histogram", response_model=list[SpeedBin])
async def speed_histogram(
    since: datetime | None = None,
    until: datetime | None = None,
    camera_id: int | None = None,
    bin_kmh: float = Query(default=5.0, gt=0),
    db: AsyncSession = Depends(get_db),
) -> list[SpeedBin]:
    if since is None:
        since = datetime.now(timezone.utc) - timedelta(days=1)
    if until is None:
        until = datetime.now(timezone.utc)

    # Postgres-Funktion: width_bucket(speed, 0, 200, 40) für 5-km/h-Bins 0..200
    max_speed = 200.0
    n_bins = int(max_speed / bin_kmh)
    bucket_col = func.width_bucket(
        CrossingEvent.speed_kmh, 0, max_speed, n_bins
    ).label("bucket")
    stmt = (
        select(bucket_col, func.count(CrossingEvent.id))
        .where(
            CrossingEvent.ts >= since,
            CrossingEvent.ts <= until,
            CrossingEvent.speed_kmh.is_not(None),
        )
        .group_by(bucket_col)
        .order_by(bucket_col)
    )
    if camera_id is not None:
        stmt = stmt.where(CrossingEvent.camera_id == camera_id)

    res = await db.execute(stmt)
    out: list[SpeedBin] = []
    for bucket, cnt in res.all():
        b = int(bucket) - 1
        out.append(
            SpeedBin(
                bin_start_kmh=b * bin_kmh,
                bin_end_kmh=(b + 1) * bin_kmh,
                count=int(cnt),
            )
        )
    return out


# ─── CSV-Export ────────────────────────────────────────────────────────────


@router.get("/export.csv")
async def export_csv(
    since: datetime | None = None,
    until: datetime | None = None,
    camera_id: int | None = None,
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    if since is None:
        since = datetime.now(timezone.utc) - timedelta(days=30)
    if until is None:
        until = datetime.now(timezone.utc)

    stmt = select(CrossingEvent).where(
        CrossingEvent.ts >= since, CrossingEvent.ts <= until
    )
    if camera_id is not None:
        stmt = stmt.where(CrossingEvent.camera_id == camera_id)
    stmt = stmt.order_by(CrossingEvent.ts)
    res = await db.execute(stmt)
    events = res.scalars().all()

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        [
            "id", "ts", "camera_id", "line_id", "vehicle_class", "direction",
            "speed_kmh", "speed_limit_kmh", "is_speeding", "track_id",
            "evidence_count",
        ]
    )
    for ev in events:
        writer.writerow(
            [
                ev.id,
                ev.ts.isoformat(),
                ev.camera_id,
                ev.line_id,
                ev.vehicle_class,
                ev.direction,
                ev.speed_kmh,
                ev.speed_limit_kmh,
                ev.is_speeding,
                ev.track_id,
                len(ev.evidence_paths),
            ]
        )
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=events.csv"},
    )


# ─── PDF-Report (Verstoß-Übersicht) ────────────────────────────────────────


@router.get("/export.pdf")
async def export_pdf(
    since: datetime | None = None,
    until: datetime | None = None,
    camera_id: int | None = None,
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    if since is None:
        since = datetime.now(timezone.utc) - timedelta(days=7)
    if until is None:
        until = datetime.now(timezone.utc)

    stmt = (
        select(CrossingEvent)
        .where(
            CrossingEvent.ts >= since,
            CrossingEvent.ts <= until,
            CrossingEvent.is_speeding.is_(True),
        )
        .order_by(CrossingEvent.ts.desc())
    )
    if camera_id is not None:
        stmt = stmt.where(CrossingEvent.camera_id == camera_id)
    res = await db.execute(stmt)
    violations = res.scalars().all()

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4)
    styles = getSampleStyleSheet()
    elems: list = [
        Paragraph("Geschwindigkeitsüberschreitungen", styles["Title"]),
        Spacer(1, 12),
        Paragraph(
            f"Zeitraum: {since.isoformat()} – {until.isoformat()}<br/>"
            f"Kamera-ID: {camera_id if camera_id is not None else 'alle'}<br/>"
            f"Anzahl Verstöße: {len(violations)}",
            styles["Normal"],
        ),
        Spacer(1, 18),
    ]

    if violations:
        data = [["Zeitpunkt", "Klasse", "Richtung", "km/h", "Limit", "Δ"]]
        for ev in violations[:500]:  # Cap für PDF-Größe
            delta = (ev.speed_kmh or 0) - (ev.speed_limit_kmh or 0)
            data.append(
                [
                    ev.ts.strftime("%Y-%m-%d %H:%M:%S"),
                    ev.vehicle_class,
                    ev.direction,
                    f"{ev.speed_kmh:.1f}" if ev.speed_kmh is not None else "—",
                    f"{ev.speed_limit_kmh:.0f}" if ev.speed_limit_kmh is not None else "—",
                    f"+{delta:.1f}",
                ]
            )
        t = Table(data, repeatRows=1)
        t.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2D2D2D")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ]
            )
        )
        elems.append(t)
    else:
        elems.append(Paragraph("Keine Verstöße im Zeitraum.", styles["Italic"]))

    doc.build(elems)
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=verstoesse.pdf"},
    )
