"""RTSPS-Capture: liest RTSPS-Streams via PyAV (FFmpeg-Backend).

Iteration: liefert (frame: np.ndarray[BGR], ts: float) Generator.
"""
from __future__ import annotations

import logging
import time
from typing import Iterator

import numpy as np

log = logging.getLogger("capture")


class FrameReader:
    """Liest RTSPS-Stream und gibt Frames in festgelegter Auflösung zurück."""

    def __init__(self, source: str, width: int, height: int) -> None:
        self.source = source
        self.width = width
        self.height = height
        self._container = None
        self._stream = None
        self._last_frame: np.ndarray | None = None

    def __iter__(self) -> Iterator[tuple[np.ndarray, float]]:
        return self

    def _open(self) -> None:
        try:
            import av  # PyAV (FFmpeg-Bindings)
        except ImportError as exc:
            raise RuntimeError(
                "PyAV (av) nicht installiert. Installiere via 'pip install av'."
            ) from exc

        # RTSPS-Optionen:
        #   - rtsp_transport=tcp: TCP statt UDP (zuverlässiger, gerade bei TLS)
        #   - stimeout: network timeout in microseconds
        #   - fflags nobuffer: weniger Latenz
        opts = {
            "rtsp_transport": "tcp",
            "stimeout": "5000000",  # 5s
            "fflags": "nobuffer",
        }
        log.info("Öffne Stream: %s (%dx%d)", self.source, self.width, self.height)
        self._container = av.open(self.source, options=opts, mode="r")
        # Falls Datei: erstes Video-Stream
        self._stream = self._container.streams.video[0]
        # Codec-Context für Resize
        self._stream.thread_type = "AUTO"

    def __next__(self) -> tuple[np.ndarray, float]:
        if self._container is None:
            self._open()

        assert self._container is not None and self._stream is not None
        for frame in self._container.decode(self._stream):
            # Resize auf Ziel-Auflösung
            img = frame.to_ndarray(format="bgr24")
            if img.shape[1] != self.width or img.shape[0] != self.height:
                img = self._resize(img, self.width, self.height)
            ts = float(frame.pts * frame.time_base) if frame.pts else time.time()
            self._last_frame = img
            return img, ts

        # Stream zu Ende
        raise StopIteration

    @staticmethod
    def _resize(img: np.ndarray, w: int, h: int) -> np.ndarray:
        import cv2

        return cv2.resize(img, (w, h), interpolation=cv2.INTER_AREA)

    def release(self) -> None:
        if self._container is not None:
            try:
                self._container.close()
            except Exception:
                pass
            self._container = None
            self._stream = None
