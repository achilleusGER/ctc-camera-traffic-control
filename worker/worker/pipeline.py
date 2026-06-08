"""Verarbeitungs-Pipeline: Detection → Tracking → Zählung → Speed → Verstoß → Annotierung."""
from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

import numpy as np

if TYPE_CHECKING:
    from .alpr import BaseALPR
    from .publisher import Publisher
    from .storage import LocalStorage

log = logging.getLogger("pipeline")

# Akzent-Farbe für Annotations (BGR für cv2)
ANNOTATION_COLOR = (42, 120, 214)   # warmer Bernsteinton
TEXT_COLOR = (255, 255, 255)
SPEEDING_COLOR = (60, 60, 220)      # Rot für Verstoß (BGR)


class Pipeline:
    """Eine Pipeline-Instanz pro Kamera/Worker."""

    def __init__(
        self,
        config: dict[str, Any],
        publisher: "Publisher",
        storage: "LocalStorage",
        alpr: "BaseALPR",
    ) -> None:
        from ultralytics import YOLO
        import supervision as sv

        from .calibration import SpeedEstimator, ViewTransformer
        from .config import COCO_CLASSES
        from .violations import crop_vehicle, encode_jpeg, is_speeding

        self.publisher = publisher
        self.storage = storage
        self.alpr = alpr
        self.config = config

        cam = config["camera"]
        self.camera_id = int(cam["id"])
        self.default_limit = cam.get("default_speed_limit_kmh")
        self._is_speeding = is_speeding

        # Modell-Pfad
        from .config import settings

        model_path = settings.model_path
        log.info("Lade YOLO-Modell %s auf %s", model_path, settings.yolo_device)
        self.model = YOLO(str(model_path))

        # Klassen-Filter
        self.class_ids = list(COCO_CLASSES.keys())
        self._coco = COCO_CLASSES

        # Tracker (ByteTrack via supervision)
        fps = int(cam.get("fps_limit") or 12)
        self.tracker = sv.ByteTrack(
            frame_rate=fps,
            minimum_consecutive_frames=settings.track_min_frames,
        )

        # Zähllinien
        self.line_zones: list[tuple[dict, Any]] = []
        for line in config.get("lines", []):
            (x1, y1), (x2, y2) = line["points"]
            zone = sv.LineZone(
                start=sv.Point(x1, y1),
                end=sv.Point(x2, y2),
                triggering_anchors=(sv.Position.BOTTOM_CENTER,),
            )
            self.line_zones.append((line, zone))

        # Kalibrierung (optional)
        self.view_transformer: ViewTransformer | None = None
        cal = config.get("calibration")
        if cal:
            self.view_transformer = ViewTransformer.from_calibration(
                cal["source_points"], cal["target_width_m"], cal["target_height_m"]
            )
        self.speed = SpeedEstimator(smoothing=settings.speed_smoothing)

        # Annotators
        self.box_annotator = sv.BoxAnnotator(color=sv.Color(*ANNOTATION_COLOR), thickness=2)
        self.label_annotator = sv.LabelAnnotator(
            text_scale=0.5, text_thickness=1, text_padding=4
        )
        self.line_annotator = sv.LineZoneAnnotator(
            thickness=2, text_scale=0.5, text_thickness=1, color=sv.Color(*ANNOTATION_COLOR)
        )

        log.info(
            "Pipeline bereit: Kamera %d, %d Linien, kalibriert=%s",
            self.camera_id, len(self.line_zones), self.view_transformer is not None,
        )

    # ─── Haupt-Loop-Schritt ─────────────────────────────────────────────────
    def process(self, frame: np.ndarray, ts: float) -> tuple[np.ndarray, list[dict]]:
        from .config import settings

        # 1) Detection
        result = self.model(
            frame,
            verbose=False,
            conf=settings.yolo_conf,
            iou=settings.yolo_iou,
            classes=self.class_ids,
            device=settings.yolo_device,
        )[0]
        import supervision as sv

        detections = sv.Detections.from_ultralytics(result)
        detections = self.tracker.update_with_detections(detections)

        # 2) Speed
        speeds = self._estimate_speeds(detections, ts)

        # 3) Linienübertritte → Events
        events = self._handle_crossings(frame, detections, speeds)

        # 4) Annotation
        annotated = self._annotate(frame, detections, speeds)

        return annotated, events

    # ─── Speed pro Track ────────────────────────────────────────────────────
    def _estimate_speeds(self, det, ts: float) -> dict[int, float | None]:
        import supervision as sv

        speeds: dict[int, float | None] = {}
        if self.view_transformer is None or det.tracker_id is None or len(det) == 0:
            return speeds

        anchors = det.get_anchors_coordinates(anchor=sv.Position.BOTTOM_CENTER)
        pts_m = self.view_transformer.transform_points(anchors)
        active_ids = set()
        for i, tid in enumerate(det.tracker_id):
            tid_i = int(tid)
            speeds[tid_i] = self.speed.update(tid_i, pts_m[i], ts)
            active_ids.add(tid_i)
        self.speed.forget(active_ids)
        return speeds

    # ─── Linienübertritte → Events ───────────────────────────────────────────
    def _handle_crossings(self, frame, det, speeds) -> list[dict]:
        events: list[dict] = []
        if det.tracker_id is None or len(det) == 0:
            return events

        from .config import settings

        for line, zone in self.line_zones:
            try:
                crossed_in, crossed_out = zone.trigger(det)
            except Exception as exc:
                log.debug("LineZone.trigger-Fehler: %s", exc)
                continue

            limit = line.get("speed_limit_kmh") or self.default_limit
            for i in range(len(det)):
                if not (bool(crossed_in[i]) or bool(crossed_out[i])):
                    continue
                tid = int(det.tracker_id[i])
                cls = self._coco.get(int(det.class_id[i]), str(det.class_id[i]))
                direction = (
                    line.get("direction_in_label", "in")
                    if bool(crossed_in[i])
                    else line.get("direction_out_label", "out")
                )
                speed = speeds.get(tid)
                speeding = self._is_speeding(speed, limit, settings.speed_speeding_margin_kmh)

                evidence_refs: list[dict] = []
                plate_text: str | None = None
                plate_conf: float | None = None

                if speeding:
                    # Beweisfoto
                    from .violations import crop_vehicle, encode_jpeg, evidence_meta

                    crop = crop_vehicle(frame, det.xyxy[i])
                    if crop.size:
                        ref = self.storage.save_evidence(
                            self.camera_id, encode_jpeg(crop, quality=85),
                            kind="vehicle_crop", meta=evidence_meta(speed, limit, None),
                        )
                        evidence_refs.append(ref)
                    # ALPR
                    if self.alpr is not None:
                        try:
                            plate_text, plate_conf = self.alpr.recognize(crop)
                        except Exception as exc:
                            log.warning("ALPR-Fehler: %s", exc)

                events.append(
                    {
                        "type": "crossing",
                        "camera_id": self.camera_id,
                        "line_id": line.get("id"),
                        "ts": datetime.now(timezone.utc).isoformat(),
                        "vehicle_class": cls,
                        "direction": direction,
                        "track_id": tid,
                        "speed_kmh": round(speed, 1) if speed is not None else None,
                        "speed_limit_kmh": limit,
                        "is_speeding": speeding,
                        "plate_text": plate_text,
                        "plate_confidence": plate_conf,
                        "evidence": evidence_refs,
                    }
                )
        return events

    # ─── Annotation für die Live-View ────────────────────────────────────────
    def _annotate(self, frame, det, speeds) -> np.ndarray:
        import supervision as sv

        annotated = frame.copy()
        labels: list[str] = []
        tracker_ids = det.tracker_id if det.tracker_id is not None else [None] * len(det)

        for i in range(len(det)):
            tid = tracker_ids[i]
            cls = self._coco.get(int(det.class_id[i]), "?")
            spd = speeds.get(int(tid)) if tid is not None else None
            if spd is not None and spd > 0:
                labels.append(f"{cls} {spd:.0f}km/h")
            else:
                labels.append(cls)

        annotated = self.box_annotator.annotate(annotated, det)
        annotated = self.label_annotator.annotate(annotated, det, labels)

        for _, zone in self.line_zones:
            annotated = self.line_annotator.annotate(annotated, line_counter=zone)
        return annotated
