"""WebSocket-Hub: verteilt Live-Events an alle verbundenen Clients."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from fastapi import WebSocket

log = logging.getLogger("ws.hub")


class Hub:
    """Sehr einfach: broadcast an alle. Später: Kamera-Filter."""

    def __init__(self) -> None:
        self._clients: set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        async with self._lock:
            self._clients.add(ws)
        log.info("WS connected, %d clients", len(self._clients))

    async def disconnect(self, ws: WebSocket) -> None:
        async with self._lock:
            self._clients.discard(ws)
        log.info("WS disconnected, %d clients", len(self._clients))

    async def broadcast(self, payload: dict[str, Any] | str) -> None:
        import json

        if isinstance(payload, dict):
            payload = json.dumps(payload, default=str)
        # Snapshot der Set, damit wir nicht während des Sendens mutieren
        async with self._lock:
            clients = list(self._clients)
        dead: list[WebSocket] = []
        for ws in clients:
            try:
                await ws.send_text(payload)
            except Exception:
                dead.append(ws)
        if dead:
            async with self._lock:
                for ws in dead:
                    self._clients.discard(ws)


hub = Hub()
