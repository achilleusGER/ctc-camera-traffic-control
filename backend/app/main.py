"""FastAPI-Einstiegspunkt."""
from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from .api import admin, cameras, calibration, events, lines, media, reports, stats, streets, violations
from .config import settings
from .consumer import consume_events
from .db import init_models
from .redis_bus import bus
from .streaming.mjpeg import router as mjpeg_router
from .ws.hub import hub

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_models()
    log.info("DB-Init OK, starte Redis-Consumer")
    consumer_task = asyncio.create_task(consume_events())
    try:
        yield
    finally:
        consumer_task.cancel()
        try:
            await consumer_task
        except asyncio.CancelledError:
            pass
        await bus.close()
        log.info("Shutdown complete")


app = FastAPI(
    title="Hermes-Trafficcontrol",
    description="Verkehrszählung & Geschwindigkeitsmessung",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── REST ───────────────────────────────────────────────────────────────────
app.include_router(streets.router)
app.include_router(cameras.router)
app.include_router(lines.router)
app.include_router(calibration.router)
app.include_router(events.router)
app.include_router(violations.router)
app.include_router(stats.router)
app.include_router(reports.router)
app.include_router(media.router)
app.include_router(admin.router)

# ─── Streaming ──────────────────────────────────────────────────────────────
app.include_router(mjpeg_router)

# ─── WebSocket ──────────────────────────────────────────────────────────────


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket) -> None:
    await hub.connect(ws)
    try:
        while True:
            # Eingehende Messages verwerfen (nur Push)
            await ws.receive_text()
    except WebSocketDisconnect:
        await hub.disconnect(ws)


# ─── Health ────────────────────────────────────────────────────────────────


@app.get("/health")
async def health() -> dict:
    """Schneller Health-Check (DB-Ping optional, hier leichtgewichtig)."""
    return {"status": "ok", "service": "hermes-trafficcontrol", "version": "0.1.0"}
