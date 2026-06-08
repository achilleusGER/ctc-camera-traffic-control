"""Worker-Settings: liest .env, lädt YOLO-Modell-Pfad, COCO-Klassen."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


# ─── COCO-Klassen, die wir zählen ──────────────────────────────────────────
# Aus COCO 80: 0=person, 1=bicycle, 2=car, 3=motorcycle, 5=bus, 7=truck
# Verkehrs-Labels: PKW / LKW / Bus / Motorrad / Fahrrad / Person
COCO_CLASSES: dict[int, str] = {
    0: "person",
    1: "bicycle",
    2: "car",
    3: "motorcycle",
    5: "bus",
    7: "truck",
}


class WorkerSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Backend-Anbindung
    backend_url: str = "http://127.0.0.1:7890"
    redis_url: str = "redis://127.0.0.1:6379/0"

    # Media-Storage (Spiegelpfad zum Backend)
    media_dir: Path = Path("/var/lib/trafficcontrol/media")
    media_backend: str = "local"  # aktuell nur "local"

    # YOLO
    yolo_model: str = "yolo11m.pt"
    yolo_device: str = "cpu"  # "cpu" | "cuda" | "mps"
    yolo_conf: float = Field(default=0.35, ge=0.0, le=1.0)
    yolo_iou: float = Field(default=0.45, ge=0.0, le=1.0)

    # Performance
    display_fps: int = Field(default=12, ge=1, le=60)
    # Tracker / Inferenz
    track_activation_thresh: float = 0.25
    track_min_frames: int = 3

    # ALPR
    alpr_enabled_default: bool = False  # Standard; pro Kamera überschreibbar

    # Speed
    speed_smoothing: int = 5  # EMA-Fenster für SpeedEstimator
    speed_speeding_margin_kmh: float = 1.0  # >= Limit + Margin zählt als Verstoß

    @property
    def model_path(self) -> Path:
        """Absoluter Pfad zum YOLO-Modell."""
        p = Path(self.yolo_model)
        if not p.is_absolute():
            # Suche im worker/-Verzeichnis und im MEDIA_DIR-Parent
            candidates = [
                Path.cwd() / self.yolo_model,
                Path(__file__).parent.parent / self.yolo_model,
            ]
            for c in candidates:
                if c.exists():
                    return c
        return p


@lru_cache
def get_settings() -> WorkerSettings:
    return WorkerSettings()


settings = get_settings()
