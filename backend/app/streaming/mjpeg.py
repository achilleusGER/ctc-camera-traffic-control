"""MJPEG-Stream: holt aktuelle annotierte Frames aus Redis und streamt sie."""
from __future__ import annotations

import asyncio
import logging
from typing import AsyncIterator

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from ..redis_bus import bus

log = logging.getLogger("mjpeg")

router = APIRouter(tags=["Streaming"])

BOUNDARY = b"--frame"


async def _frame_iter(camera_id: int, target_fps: float) -> AsyncIterator[bytes]:
    interval = 1.0 / max(0.1, target_fps)
    while True:
        frame = await bus.get_frame(camera_id)
        if frame:
            yield (
                BOUNDARY + b"\r\n"
                + b"Content-Type: image/jpeg\r\n"
                + f"Content-Length: {len(frame)}\r\n\r\n".encode()
                + frame
                + b"\r\n"
            )
        else:
            # Kein Frame da → kurzer Sleep, damit der Loop nicht brennt
            await asyncio.sleep(interval)


@router.get("/cameras/{camera_id}/stream.mjpg")
async def stream(camera_id: int, fps: float = Query(default=10.0, ge=1, le=30)) -> StreamingResponse:
    """multipart/x-mixed-replace — Browser können das direkt anzeigen (<img src>)."""
    return StreamingResponse(
        _frame_iter(camera_id, fps),
        media_type=f"multipart/x-mixed-replace; boundary=frame",
    )
