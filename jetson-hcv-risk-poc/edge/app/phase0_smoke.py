"""
Phase 0 smoke test: log camera frame metadata + GPS fixes with monotonic and UTC wall time.

Run from `edge/`:
  python -m app.phase0_smoke --config config/default.yaml

Windows (no GPS): python -m app.phase0_smoke --no-gps --mock-gps
"""
from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

import yaml

# Ensure imports resolve when run as `python -m app.phase0_smoke` from edge/
_EDGE_ROOT = Path(__file__).resolve().parent.parent
if str(_EDGE_ROOT) not in sys.path:
    sys.path.insert(0, str(_EDGE_ROOT))


def _load_config(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 0 camera + GPS timestamp smoke test.")
    parser.add_argument(
        "--config",
        type=Path,
        default=_EDGE_ROOT / "config" / "default.yaml",
        help="Path to YAML config",
    )
    parser.add_argument("--no-camera", action="store_true", help="Skip camera")
    parser.add_argument("--no-gps", action="store_true", help="Skip GPS serial")
    parser.add_argument("--mock-gps", action="store_true", help="Use mock GPS fixes (no serial)")
    args = parser.parse_args()

    cfg = _load_config(args.config)
    device_id = cfg.get("device_id", "unknown")
    p0 = cfg.get("phase0", {})
    n_frames = int(p0.get("frames_to_log", 5))
    n_gps = int(p0.get("gps_lines_to_log", 10))
    interval = float(p0.get("frame_interval_sec", 0.5))

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    log = logging.getLogger("phase0")

    log.info("device_id=%s monotonic_reference=%.6f", device_id, time.monotonic())
    log.info("config=%s", args.config.resolve())

    if not args.no_camera:
        from camera_service.capture import CameraCapture, CaptureError

        cam_cfg = cfg.get("camera", {})
        pipeline = cam_cfg.get("gstream_pipeline")
        idx = int(cam_cfg.get("index", 0))
        try:
            cap = CameraCapture(index=idx, pipeline=pipeline, backend=str(cam_cfg.get("backend", "opencv")))
            cap.open()
        except CaptureError as e:
            log.error("Camera failed: %s — use --no-camera to skip.", e)
            return 1
        try:
            for i in range(n_frames):
                meta = cap.read_meta()
                log.info(
                    "frame[%s] wall_utc=%s mono_s=%.6f size=%sx%s backend=%s",
                    i,
                    meta.wall_time_utc_iso,
                    meta.monotonic_s,
                    meta.width,
                    meta.height,
                    meta.backend,
                )
                time.sleep(interval)
        finally:
            cap.close()
    else:
        log.info("camera skipped (--no-camera)")

    if not args.no_gps:
        if args.mock_gps:
            from gps_service.reader import mock_fixes

            for i, fix in enumerate(mock_fixes(n_gps)):
                log.info(
                    "gps[%s] wall_utc=%s mono_s=%.6f lat=%s lon=%s q=%s raw=%s",
                    i,
                    fix.wall_time_utc_iso,
                    fix.monotonic_s,
                    fix.latitude_deg,
                    fix.longitude_deg,
                    fix.fix_quality,
                    fix.raw_sentence[:80],
                )
        else:
            from gps_service.reader import GPSReader, GPSReaderError

            g = cfg.get("gps", {})
            port = str(g.get("port", "/dev/ttyUSB0"))
            baud = int(g.get("baud", 9600))
            timeout = float(g.get("timeout_sec", 1.0))
            try:
                reader = GPSReader(port, baud, timeout)
                reader.open()
            except GPSReaderError as e:
                log.error("GPS open failed: %s — try --mock-gps.", e)
                return 1
            try:
                count = 0
                for fix in reader.iter_lines(max_lines=n_gps * 20):
                    log.info(
                        "gps[%s] wall_utc=%s mono_s=%.6f lat=%s lon=%s q=%s",
                        count,
                        fix.wall_time_utc_iso,
                        fix.monotonic_s,
                        fix.latitude_deg,
                        fix.longitude_deg,
                        fix.fix_quality,
                    )
                    count += 1
                    if count >= n_gps:
                        break
            finally:
                reader.close()
    else:
        log.info("gps skipped (--no-gps)")

    log.info("phase0 smoke complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
