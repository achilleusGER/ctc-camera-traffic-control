"""Kalibrierung: ViewTransformer (4-Punkt-Perspektive) + SpeedEstimator.

Das ViewTransformer rechnet Pixel-Koordinaten in eine reale Bodenebene
(target_width_m x target_height_m in Metern) um. Damit lässt sich
Geschwindigkeit in m/s → km/h ableiten.
"""
from __future__ import annotations

import logging
import math
from collections import deque

import numpy as np

log = logging.getLogger("calibration")

MIN_SPEED_KMH = 1.0      # unterhalb ignorieren (Stehbleiber, Schatten)
MAX_SPEED_KMH = 250.0    # oberhalb Ausreißer-Filter


class ViewTransformer:
    """Perspektivische Transformation: Pixel-Koordinaten → Meter-Koordinaten."""

    def __init__(self, source: np.ndarray, target: np.ndarray) -> None:
        # source: 4x2 Pixel-Punkte (TL, TR, BR, BL)
        # target: 4x2 Meter-Punkte (0,0), (W,0), (W,H), (0,H)
        self.M = cv2_get_perspective_transform(source.astype(np.float32), target.astype(np.float32))

    @classmethod
    def from_calibration(
        cls, source_points: list[list[float]], target_width_m: float, target_height_m: float
    ) -> "ViewTransformer":
        if len(source_points) != 4:
            raise ValueError("source_points muss genau 4 Punkte enthalten")
        src = np.array(source_points, dtype=np.float32)
        tgt = np.array(
            [[0, 0], [target_width_m, 0], [target_width_m, target_height_m], [0, target_height_m]],
            dtype=np.float32,
        )
        return cls(src, tgt)

    def transform_points(self, points: np.ndarray) -> np.ndarray:
        """points: (N, 2) Pixel → (N, 2) Meter."""
        if points.size == 0:
            return points
        if points.ndim == 1:
            points = points.reshape(1, 2)
        reshaped = points.reshape(-1, 1, 2).astype(np.float32)
        out = cv2_perspective_transform(reshaped, self.M)
        return out.reshape(-1, 2)


# ── cv2-Wrapper (Lazy-Import, damit das Modul auch ohne cv2 importierbar ist)


def cv2_get_perspective_transform(src: np.ndarray, dst: np.ndarray) -> np.ndarray:
    import cv2

    return cv2.getPerspectiveTransform(src, dst)


def cv2_perspective_transform(pts: np.ndarray, M: np.ndarray) -> np.ndarray:
    import cv2

    return cv2.perspectiveTransform(pts, M)


# ─── SpeedEstimator ─────────────────────────────────────────────────────────


class SpeedEstimator:
    """EMA-basierte Geschwindigkeitsschätzung pro Track.

    Annahme: ViewTransformer liefert Punkte in Metern. Aus aufeinanderfolgenden
    Positionen + Zeitdifferenz wird Geschwindigkeit berechnet.
    """

    def __init__(self, smoothing: int = 5) -> None:
        self.smoothing = smoothing
        self._history: dict[int, deque[tuple[float, float, float]]] = {}

    def update(self, track_id: int, pos_m: np.ndarray, ts: float) -> float | None:
        """Update mit aktueller (x, y) Position in Metern + Zeitstempel.

        Returns: geschätzte Geschwindigkeit in km/h oder None (noch zu wenig Daten).
        """
        h = self._history.setdefault(track_id, deque(maxlen=self.smoothing))
        h.append((float(pos_m[0]), float(pos_m[1]), ts))

        if len(h) < 2:
            return None

        # Lineare Regression auf (t → dist) — robuster als einzelne Differenz
        pts = list(h)
        x = np.array([p[2] for p in pts])
        # Distanz vom ersten Punkt (kumulative Bewegung)
        x0, y0 = pts[0][0], pts[0][1]
        d = np.array([math.hypot(p[0] - x0, p[1] - y0) for p in pts])

        # Slope m/s
        if x[-1] - x[0] < 1e-3:
            return None
        # Least-Squares-Gerade durch (t, dist)
        m, _ = np.polyfit(x, d, 1)
        speed_kmh = max(0.0, float(m) * 3.6)

        if speed_kmh < MIN_SPEED_KMH:
            return 0.0
        if speed_kmh > MAX_SPEED_KMH:
            return None
        return round(speed_kmh, 1)

    def forget(self, active_track_ids: set[int]) -> None:
        """Entfernt Tracks, die nicht mehr aktiv sind."""
        dead = set(self._history) - active_track_ids
        for tid in dead:
            self._history.pop(tid, None)
