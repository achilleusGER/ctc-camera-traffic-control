"""Publisher: schreibt Events + annotierte Frames nach Redis.

Channel-Übersicht (kompatibel mit Backend):
  - traffic:events: JSON-Event (Worker→Backend-Consumer→DB→WS)
  - traffic:frame:{camera_id}: JPEG-Bytes (Backend-MJPEG holt sie ab)
"""
from __future__ import annotations

import json
import logging
from typing import Any

import redis

from .config import settings

log = logging.getLogger("publisher")

CH_EVENTS = "traffic:events"
FRAME_KEY_TMPL = "traffic:frame:{camera_id}"


class Publisher:
    def __init__(self) -> None:
        # Sync-Redis (Worker ist nicht async — CPU-bound, Frame-Loop synchron)
        self._client = redis.Redis.from_url(
            settings.redis_url,
            socket_timeout=5,
            socket_connect_timeout=5,
        )
        # Test-Ping
        self._client.ping()
        log.info("Redis-Publisher bereit: %s", settings.redis_url)

    def publish_event(self, event: dict[str, Any]) -> int:
        """JSON-Event auf traffic:events. Backend-Consumer persistiert."""
        return int(self._client.publish(CH_EVENTS, json.dumps(event, default=str)))

    def set_frame(self, camera_id: int, annotated_jpeg: bytes) -> None:
        """Annotierter Frame (für LiveView/MJPEG). TTL 2s."""
        self._client.set(FRAME_KEY_TMPL.format(camera_id=camera_id), annotated_jpeg, ex=2)

    def close(self) -> None:
        try:
            self._client.close()
        except Exception:
            pass
