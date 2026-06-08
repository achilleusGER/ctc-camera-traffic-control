"""Storage: schreibt Beweisfotos ins lokale Media-Verzeichnis.

Pfad-Schema:
    {MEDIA_DIR}/evidence/{camera_id}/{YYYY-MM-DD}/{event_id}_{kind}.jpg
    {MEDIA_DIR}/evidence/{camera_id}/{YYYY-MM-DD}/{event_id}_{kind}.json  (Sidecar)
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from .config import settings

log = logging.getLogger("storage")


class LocalStorage:
    def __init__(self) -> None:
        self.base = settings.media_dir
        self.base.mkdir(parents=True, exist_ok=True)

    def save_evidence(
        self,
        camera_id: int,
        jpeg_bytes: bytes,
        kind: str,
        event_id: int | None = None,
        meta: dict | None = None,
    ) -> dict:
        """Speichert JPEG + optional Sidecar-JSON. Returns Reference-Dict fürs Backend."""
        ts = datetime.now(timezone.utc)
        day = ts.strftime("%Y-%m-%d")
        out_dir = self.base / "evidence" / str(camera_id) / day
        out_dir.mkdir(parents=True, exist_ok=True)

        # Dateiname
        prefix = f"{event_id:012d}" if event_id is not None else ts.strftime("%H%M%S%f")
        filename = f"{prefix}_{kind}.jpg"
        full_path = out_dir / filename

        full_path.write_bytes(jpeg_bytes)
        rel_path = str(full_path.relative_to(self.base))

        if meta:
            sidecar = full_path.with_suffix(".json")
            sidecar.write_text(json.dumps(meta, default=str), encoding="utf-8")

        log.debug("Evidence: %s (%d bytes)", rel_path, len(jpeg_bytes))
        return {
            "path": rel_path,
            "kind": kind,
            "captured_at": ts.isoformat(),
            "size_bytes": len(jpeg_bytes),
        }
