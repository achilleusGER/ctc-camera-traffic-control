"""Verstoß-Logik: Speed-Check + JPEG-Encoding + Vehicle-Crop."""
from __future__ import annotations

import logging
from typing import Any

import numpy as np

log = logging.getLogger("violations")


def is_speeding(speed_kmh: float | None, limit_kmh: float | None, margin_kmh: float = 1.0) -> bool:
    """True, wenn speed_kmh das Limit um >= margin_kmh überschreitet."""
    if speed_kmh is None or limit_kmh is None:
        return False
    return speed_kmh >= (limit_kmh + margin_kmh)


def crop_vehicle(frame: np.ndarray, xyxy: np.ndarray, pad: float = 0.1) -> np.ndarray:
    """Croppt das Fahrzeug aus dem Frame mit kleinem Padding (relativ)."""
    h, w = frame.shape[:2]
    x1, y1, x2, y2 = (float(v) for v in xyxy)
    bw, bh = x2 - x1, y2 - y1
    x1 = max(0, int(x1 - bw * pad))
    y1 = max(0, int(y1 - bh * pad))
    x2 = min(w, int(x2 + bw * pad))
    y2 = min(h, int(y2 + bh * pad))
    return frame[y1:y2, x1:x2]


def encode_jpeg(img: np.ndarray, quality: int = 80) -> bytes:
    """JPEG-Encode (cv2 → bytes)."""
    import cv2

    ok, buf = cv2.imencode(".jpg", img, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
    if not ok:
        raise RuntimeError("JPEG-Encoding fehlgeschlagen")
    return bytes(buf)


def evidence_meta(speed_kmh: float | None, limit_kmh: float | None, plate: str | None) -> dict[str, Any]:
    """Metadaten für die Beweisfoto-Datei (Sidecar-JSON)."""
    return {
        "speed_kmh": speed_kmh,
        "speed_limit_kmh": limit_kmh,
        "plate_text": plate,
    }
