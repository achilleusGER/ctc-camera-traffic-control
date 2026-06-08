"""Smoke-Test für Hermes-Trafficcontrol Worker (statisch — keine Imports nötig).

Aufruf:  cd worker && python3 smoke_test.py

Prüft:
  1. Syntax aller Module (compileall)
  2. Pipeline-Constructor-Argumente passen
  3. COCO-Klassen-Mapping plausibel
  4. Beispiel-Konfig (example-config.json) ist valides JSON mit erwarteten Keys

Exit 0 = OK, 1 = Fehler.
"""
from __future__ import annotations

import json
import sys
import unittest.mock
from pathlib import Path

WORKER_DIR = Path(__file__).parent
WORKER_PKG = WORKER_DIR / "worker"


def check_syntax() -> None:
    import py_compile

    print("[1/4] Syntax-Check …")
    for py in sorted(WORKER_PKG.glob("*.py")):
        py_compile.compile(str(py), doraise=True, quiet=1)
    print("  OK")


def check_pipeline_signature() -> None:
    """Prüft, dass Pipeline.__init__ die richtigen Args erwartet."""
    import inspect

    print("[2/4] Pipeline-Signatur …")
    # Mock-Imports, damit wir die Datei laden können
    sys.modules.setdefault("ultralytics", unittest.mock.MagicMock())
    sys.modules.setdefault("supervision", unittest.mock.MagicMock())
    sys.modules.setdefault("cv2", unittest.mock.MagicMock())

    from worker import pipeline

    sig = inspect.signature(pipeline.Pipeline.__init__)
    expected = {"self", "config", "publisher", "storage", "alpr"}
    actual = set(sig.parameters.keys())
    missing = expected - actual
    extra = actual - expected
    if missing:
        raise SystemExit(f"  Pipeline.__init__ fehlt: {missing}")
    print(f"  OK ({len(actual) - 1} Parameter: {sorted(actual - {'self'})})")


def check_coco_classes() -> None:
    print("[3/4] COCO-Klassen …")
    from worker.config import COCO_CLASSES

    expected = {0: "person", 1: "bicycle", 2: "car", 3: "motorcycle", 5: "bus", 7: "truck"}
    if COCO_CLASSES != expected:
        raise SystemExit(f"  COCO_CLASSES weicht ab: {COCO_CLASSES} != {expected}")
    print(f"  OK ({len(COCO_CLASSES)} Klassen)")


def check_example_config() -> None:
    print("[4/4] example-config.json …")
    cfg_path = WORKER_DIR / "example-config.json"
    with cfg_path.open(encoding="utf-8") as fh:
        cfg = json.load(fh)
    if "camera" not in cfg or "lines" not in cfg:
        raise SystemExit("  camera und lines fehlen")
    cam = cfg["camera"]
    required_cam = {"id", "name", "rtsp_url_low", "infer_width", "default_speed_limit_kmh"}
    missing = required_cam - set(cam.keys())
    if missing:
        raise SystemExit(f"  camera fehlt: {missing}")
    for ln in cfg["lines"]:
        if len(ln.get("points", [])) != 2:
            raise SystemExit(f"  line.points muss 2 Punkte haben: {ln}")
    cal = cfg.get("calibration")
    if cal and len(cal.get("source_points", [])) != 4:
        raise SystemExit("  calibration.source_points muss 4 Punkte haben")
    print(f"  OK (camera={cam['id']}, lines={len(cfg['lines'])}, calibrated={cal is not None})")


def main() -> int:
    print("=" * 60)
    print("Hermes-Trafficcontrol Worker — Smoke-Test (statisch)")
    print("=" * 60)
    check_syntax()
    check_pipeline_signature()
    check_coco_classes()
    check_example_config()
    print("\n" + "=" * 60)
    print("SMOKE-TEST OK")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
