"""
Record camera frames to local video file only (see ``app.recording_video`` for capture logic).

Run from `edge/`:
  python -m app.record_camera --config config/default.yaml
"""
from __future__ import annotations

import argparse
import json
import logging
import signal
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path

import yaml

_EDGE_ROOT = Path(__file__).resolve().parent.parent
if str(_EDGE_ROOT) not in sys.path:
    sys.path.insert(0, str(_EDGE_ROOT))

from app.device_connectivity import (
    append_connectivity_record,
    probe_camera,
    resolve_connectivity_log_paths,
)
from app.recording_paths import resolve_segment_duration_sec, session_dir_with_day
from app.recording_video import run_camera_recording_loop


def _load_config(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def main() -> int:
    parser = argparse.ArgumentParser(description="Record camera video to disk (camera only).")
    parser.add_argument("--config", type=Path, default=_EDGE_ROOT / "config" / "default.yaml")
    parser.add_argument(
        "--duration-sec",
        type=float,
        default=None,
        help="Override recording.duration_sec (0 = until Ctrl+C)",
    )
    parser.add_argument(
        "--segment-sec",
        type=float,
        default=None,
        help="Override recording.segment_duration_sec (0 = single video file; >0 = rotate segments)",
    )
    args = parser.parse_args()

    cfg = _load_config(args.config)
    rec = cfg.get("recording", {})
    out_base = Path(rec.get("output_base", str(_EDGE_ROOT / "data" / "recordings")))
    out_base = out_base.expanduser()
    if not out_base.is_absolute():
        out_base = (_EDGE_ROOT / out_base).resolve()

    fps = float(rec.get("fps", 15))
    duration_sec = float(rec.get("duration_sec", 0))
    if args.duration_sec is not None:
        duration_sec = float(args.duration_sec)
    segment_duration_sec = resolve_segment_duration_sec(rec, args.segment_sec)
    video_name = str(rec.get("video_filename", "camera.mp4"))
    meta_name = str(rec.get("session_meta_filename", "session.json"))

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    log = logging.getLogger("record-camera")

    connectivity_camera, _connectivity_gps = resolve_connectivity_log_paths(_EDGE_ROOT, cfg)
    device_id = cfg.get("device_id", "unknown")
    append_connectivity_record(
        connectivity_camera,
        {"event": "record_camera_attempt", "device_id": device_id},
    )
    cam_ok, cam_detail = probe_camera(cfg)
    append_connectivity_record(
        connectivity_camera,
        {"event": "camera_probe", "ok": cam_ok, "detail": cam_detail, "device_id": device_id},
    )
    if not cam_ok:
        append_connectivity_record(
            connectivity_camera,
            {
                "event": "session_aborted",
                "reason": "camera_probe_failed",
                "detail": cam_detail,
                "device_id": device_id,
            },
        )
        log.error("Camera not ready (%s). No session folder created.", cam_detail)
        return 1

    session = session_dir_with_day(out_base, "-camera")
    append_connectivity_record(
        connectivity_camera,
        {"event": "session_folder_created", "session_dir": str(session), "device_id": device_id},
    )

    meta_path = session / meta_name
    video_template = session / video_name
    started = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    meta_path.write_text(
        json.dumps(
            {
                "device_id": device_id,
                "started_utc": started,
                "mode": "camera_only",
                "config": str(args.config.resolve()),
                "fps": fps,
                "duration_sec": duration_sec,
                "segment_duration_sec": segment_duration_sec,
                "session_dir": str(session),
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    stop = threading.Event()

    def handle_sig(*_a: object) -> None:
        log.info("stop signal")
        stop.set()

    signal.signal(signal.SIGINT, handle_sig)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, handle_sig)

    code, _frames, _path = run_camera_recording_loop(
        cfg,
        video_template,
        fps,
        segment_duration_sec,
        duration_sec,
        stop,
        log,
    )
    if code != 0:
        return code

    log.info("camera session complete -> %s", session)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
