"""Worker-Einstiegspunkt: lädt Konfiguration, startet Hauptloop.

Aufruf:
    CAMERA_ID=1 python -m worker.main
    python -m worker.main --camera-id 1
    python -m worker.main --camera-id 1 --source rtsps://... (überschreibt DB-URL)
    python -m worker.main --config-file ./cam.json --source ./sample.mp4
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import time
from pathlib import Path

import requests

from .alpr import build_alpr
from .capture import FrameReader
from .config import settings
from .pipeline import Pipeline
from .publisher import Publisher
from .storage import LocalStorage
from .violations import encode_jpeg

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("worker.main")


def load_config(camera_id: int | None, config_file: str | None) -> dict:
    """Lädt Kamerakonfiguration entweder aus JSON-Datei oder vom Backend."""
    if config_file:
        with open(config_file, encoding="utf-8") as fh:
            return json.load(fh)
    if camera_id is None:
        raise SystemExit("Entweder --camera-id oder --config-file angeben.")
    url = f"{settings.backend_url}/cameras/{camera_id}/config"
    log.info("Lade Kamerakonfiguration: %s", url)
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    return resp.json()


def main() -> None:
    parser = argparse.ArgumentParser(description="Hermes-Trafficcontrol Worker")
    parser.add_argument(
        "--camera-id",
        type=int,
        default=(int(os.environ["CAMERA_ID"]) if os.environ.get("CAMERA_ID") else None),
        help="Kamera-ID (Default: $CAMERA_ID). Lädt Config vom Backend.",
    )
    parser.add_argument(
        "--source",
        default=os.getenv("SOURCE"),
        help="RTSPS-URL oder lokaler Pfad. Überschreibt camera.rtsp_url_low.",
    )
    parser.add_argument(
        "--config-file",
        default=None,
        help="Pfad zu einer JSON-Konfig (Standalone-Modus, ohne Backend).",
    )
    args = parser.parse_args()

    config = load_config(args.camera_id, args.config_file)
    cam = config["camera"]
    camera_id = int(cam["id"])
    infer_w = int(cam.get("infer_width", 1280))
    # Höhe aus Aspect Ratio ableiten
    width = int(cam.get("width", 1920))
    height = int(cam.get("height", 1080))
    infer_h = round(infer_w * height / width)

    source = args.source or cam.get("rtsp_url_low")
    if not source:
        raise SystemExit("Keine RTSP-Quelle: --source angeben oder Kamera hat rtsp_url_low")

    log.info(
        "Kamera %d | Quelle=%s | Inferenz=%dx%d | Modell=%s | Device=%s",
        camera_id, source, infer_w, infer_h, settings.yolo_model, settings.yolo_device,
    )

    publisher = Publisher()
    storage = LocalStorage()
    alpr = build_alpr(bool(cam.get("alpr_enabled")))
    pipeline = Pipeline(config, publisher, storage, alpr)
    reader = FrameReader(source, infer_w, infer_h)

    display_interval = 1.0 / max(1, settings.display_fps)
    last_display = 0.0

    try:
        for frame, ts in reader:
            annotated, events = pipeline.process(frame, ts)
            for ev in events:
                publisher.publish_event(ev)
                if ev.get("is_speeding"):
                    log.info(
                        "VERSTOSS Kamera=%d %s %s %.1f km/h (Limit %s)",
                        camera_id, ev["vehicle_class"], ev["direction"],
                        ev.get("speed_kmh") or 0.0, ev.get("speed_limit_kmh"),
                    )

            now = time.monotonic()
            if now - last_display >= display_interval:
                try:
                    jpg = encode_jpeg(annotated, quality=70)
                    publisher.set_frame(camera_id, jpg)
                except Exception as exc:
                    log.warning("Frame-Publish-Fehler: %s", exc)
                last_display = now
    except KeyboardInterrupt:
        log.info("Abbruch durch User")
    finally:
        reader.release()
        publisher.close()


if __name__ == "__main__":
    main()
