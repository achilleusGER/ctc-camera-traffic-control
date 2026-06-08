"""ALPR (Kfz-Kennzeichenerkennung) — Standard: AUS.

Aktivierung pro Kamera in der Kamera-Konfiguration (alpr_enabled=True).
Backend: PaddleOCR (CPU-tauglich, gut für deutsche Kennzeichen).
"""
from __future__ import annotations

import logging
import re
from abc import ABC, abstractmethod

log = logging.getLogger("alpr")

# Sehr grobes DE-Kennzeichen-Pattern: 1-3 Buchstaben + 1-4 Ziffern + 1-2 Buchstaben
# Deckt Standard- und Saisonkennzeichen grob ab; finale Validierung im Backend.
DE_PLATE_PATTERN = re.compile(r"^[A-ZÄÖÜ]{1,3}[- ]?[A-Z]{0,2}[- ]?\d{1,4}[- ]?[A-Z]{0,2}$")


class BaseALPR(ABC):
    @abstractmethod
    def recognize(self, image) -> tuple[str | None, float | None]:
        """Returns (plate_text, confidence) oder (None, None)."""


class NoALPR(BaseALPR):
    """Default — kein ALPR aktiv."""

    def recognize(self, image) -> tuple[str | None, float | None]:
        return None, None


class PaddleALPR(BaseALPR):
    """PaddleOCR-Wrapper. Wird nur instanziiert, wenn alpr_enabled=True."""

    def __init__(self, lang: str = "german") -> None:
        try:
            from paddleocr import PaddleOCR  # type: ignore
        except ImportError as exc:
            raise RuntimeError(
                "PaddleOCR nicht installiert. Installiere via 'pip install paddleocr paddlepaddle' "
                "(nur Linux)."
            ) from exc

        log.info("Initialisiere PaddleOCR (lang=%s)", lang)
        self._ocr = PaddleOCR(use_angle_cls=True, lang=lang, show_log=False)

    def recognize(self, image) -> tuple[str | None, float | None]:
        try:
            results = self._ocr.ocr(image, cls=True)
        except Exception as exc:
            log.warning("PaddleOCR-Fehler: %s", exc)
            return None, None

        # Beste Platte (höchste Confidence + Pattern-Match) bevorzugen
        best_text: str | None = None
        best_conf: float | None = None
        for line in results or []:
            for det in line or []:
                if not det or len(det) < 2:
                    continue
                box, (text, conf) = det[0], det[1]
                if not text or not conf:
                    continue
                cleaned = re.sub(r"[^A-Z0-9 -]", "", text.upper()).strip()
                if not DE_PLATE_PATTERN.match(cleaned):
                    continue
                if best_conf is None or conf > best_conf:
                    best_text = cleaned
                    best_conf = float(conf)
        return best_text, best_conf


def build_alpr(enabled: bool) -> BaseALPR:
    if not enabled:
        return NoALPR()
    try:
        return PaddleALPR()
    except RuntimeError as exc:
        log.warning("ALPR aktiviert, aber Init fehlgeschlagen — fallback auf NoALPR: %s", exc)
        return NoALPR()
