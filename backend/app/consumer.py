"""Redis-Consumer: Worker published auf traffic:events, wir persistieren in DB."""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime

from .db import AsyncSessionLocal
from .models import CrossingEvent, Plate
from .redis_bus import CH_EVENTS, bus
from .ws.hub import hub

log = logging.getLogger("consumer")


async def _handle_event(payload: dict) -> None:
    """Persistiert ein CrossingEvent + optional Plate, broadcastet via WS."""
    if payload.get("type") != "crossing":
        return

    try:
        ts = datetime.fromisoformat(payload["ts"])
    except (KeyError, ValueError):
        log.warning("Ungültiges ts in Event: %s", payload.get("ts"))
        return

    evidence_paths = [e.get("path", "") for e in payload.get("evidence", []) if e.get("path")]

    async with AsyncSessionLocal() as session:
        ev = CrossingEvent(
            camera_id=int(payload["camera_id"]),
            line_id=payload.get("line_id"),
            ts=ts,
            vehicle_class=str(payload.get("vehicle_class", "unknown")),
            direction=str(payload.get("direction", "in")),
            track_id=payload.get("track_id"),
            speed_kmh=payload.get("speed_kmh"),
            speed_limit_kmh=payload.get("speed_limit_kmh"),
            is_speeding=bool(payload.get("is_speeding", False)),
            evidence_paths=evidence_paths,
        )
        session.add(ev)
        await session.flush()

        if payload.get("plate_text"):
            session.add(
                Plate(
                    event_id=ev.id,
                    plate_text=str(payload["plate_text"])[:20],
                    confidence=payload.get("plate_confidence"),
                )
            )
        await session.commit()
        await session.refresh(ev)

        # Live-Broadcast: {type: "event", event: {...}}
        await hub.broadcast(
            {
                "type": "event",
                "event": {
                    "id": ev.id,
                    "camera_id": ev.camera_id,
                    "ts": ev.ts.isoformat(),
                    "vehicle_class": ev.vehicle_class,
                    "direction": ev.direction,
                    "speed_kmh": ev.speed_kmh,
                    "speed_limit_kmh": ev.speed_limit_kmh,
                    "is_speeding": ev.is_speeding,
                },
            }
        )


async def consume_events() -> None:
    """Endlos-Loop, läuft als Background-Task in der FastAPI-Lifespan."""
    log.info("Starte Redis-Consumer auf Channel %s", CH_EVENTS)
    while True:
        try:
            pubsub = bus.client.pubsub()
            await pubsub.subscribe(CH_EVENTS)
            async for message in pubsub.listen():
                if message.get("type") != "message":
                    continue
                raw = message.get("data")
                if not raw:
                    continue
                try:
                    payload = json.loads(raw)
                except json.JSONDecodeError:
                    log.warning("Konnte Redis-Message nicht parsen: %r", raw[:200])
                    continue
                # Persist + Broadcast — Fehler loggen, Loop nicht killen
                try:
                    await _handle_event(payload)
                except Exception as exc:
                    log.exception("Fehler bei Event-Handling: %s", exc)
        except asyncio.CancelledError:
            log.info("Redis-Consumer beendet (Cancelled)")
            return
        except Exception as exc:
            log.exception("Redis-Consumer-Fehler, restart in 3s: %s", exc)
            await asyncio.sleep(3)
