"""Redis-Pub/Sub-Wrapper: Worker → Backend (Events), Backend → Frontend (Live)."""
from __future__ import annotations

import json
import logging
from typing import Any

import redis.asyncio as redis_async

from .config import settings

log = logging.getLogger("redis_bus")

# Pub/Sub-Channels
CH_EVENTS = "traffic:events"          # Worker → Backend-Consumer (persistent in DB)
CH_FRAMES = "traffic:frames"          # Worker → MJPEG/WS (annotated JPEG bytes)
CH_LIVE = "traffic:live"              # Backend → WS-Clients (Counts, Violations)


class RedisBus:
    """Lazy-erzeugter async-Redis-Client + Helper."""

    def __init__(self) -> None:
        self._client: redis_async.Redis | None = None

    @property
    def client(self) -> redis_async.Redis:
        if self._client is None:
            self._client = redis_async.from_url(
                settings.redis_url,
                decode_responses=False,
                socket_timeout=5,
                socket_connect_timeout=5,
            )
        return self._client

    async def publish(self, channel: str, payload: bytes | str) -> int:
        if isinstance(payload, str):
            payload = payload.encode("utf-8")
        return await self.client.publish(channel, payload)

    async def publish_event(self, event: dict[str, Any]) -> int:
        return await self.publish(CH_EVENTS, json.dumps(event, default=str))

    async def publish_frame(self, camera_id: int, jpeg_bytes: bytes) -> int:
        """Annotated frame → MJPEG-Stream. Keyed by camera_id (consumer filtert)."""
        return await self.client.set(f"traffic:frame:{camera_id}", jpeg_bytes, ex=2)

    async def get_frame(self, camera_id: int) -> bytes | None:
        return await self.client.get(f"traffic:frame:{camera_id}")

    async def publish_live(self, payload: dict[str, Any]) -> int:
        return await self.publish(CH_LIVE, json.dumps(payload, default=str))

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None


# Singleton
bus = RedisBus()
