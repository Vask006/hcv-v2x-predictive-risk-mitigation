"""
Orchestrate a recording session: one folder, camera video + optional GPS JSONL.

Camera capture lives in ``app.recording_video``; GPS streaming in ``app.recording_gps_writer``.
Combined here so vehicle runs get time-aligned files in a single session directory.

Output layout: ``data/recordings/<YYYY-MM-DD>/<session-UTC>/``.

Run from `edge/`:
  python -m app.record_session --config config/default.yaml

For camera-only or GPS-only CLIs, use ``app.record_camera`` or ``app.record_gps`` instead.
"""
from __future__ import annotations

import argparse
import json
import logging
import signal
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

import yaml

_EDGE_ROOT = Path(__file__).resolve().parent.parent
if str(_EDGE_ROOT) not in sys.path:
    sys.path.insert(0, str(_EDGE_ROOT))

from app.device_connectivity import (
    append_connectivity_record,
    probe_camera,
    probe_gps,
    resolve_connectivity_log_paths,
)
from app.recording_gps_writer import gps_writer_thread
from app.recording_paths import resolve_segment_duration_sec, session_dir_with_day
from app.recording_video import run_camera_recording_loop


def _load_config(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def main() -> int:
    parser = argparse.ArgumentParser(description="Record camera video + GPS JSONL to disk.")
    parser.add_argument("--config", type=Path, default=_EDGE_ROOT / "config" / "default.yaml")
    parser.add_argument(
        "--mock-gps",
        action="store_true",
        help="Synthetic bench GPS in JSONL (no serial; not NMEA from hardware)",
    )
    parser.add_argument("--no-gps", action="store_true", help="Camera only, no GPS file")
    parser.add_argument("--no-camera", action="store_true", help="GPS only (no video)")
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
    if bool(rec.get("camera_only", False)):
        args.no_gps = True
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
    gps_name = str(rec.get("gps_filename", "gps.jsonl"))
    meta_name = str(rec.get("session_meta_filename", "session.json"))

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    log = logging.getLogger("record")

    if not args.no_gps and not args.mock_gps and sys.platform != "win32":
        g = cfg.get("gps", {})
        port = Path(str(g.get("port", "/dev/ttyUSB0")))
        if not port.exists() and rec.get("gps_optional", True):
            log.warning(
                "GPS port %s missing — continuing camera-only. Use --mock-gps for synthetic bench rows in JSONL.",
                port,
            )
            args.no_gps = True

    if args.no_camera and args.no_gps:
        log.error("Nothing to record: use camera and/or GPS.")
        return 2

    connectivity_camera, connectivity_gps = resolve_connectivity_log_paths(_EDGE_ROOT, cfg)
    gps_probe_timeout_sec = float(rec.get("gps_probe_timeout_sec", 45))
    device_id = cfg.get("device_id", "unknown")

    def _append_cam(rec_: dict) -> None:
        append_connectivity_record(connectivity_camera, rec_)

    def _append_gps(rec_: dict) -> None:
        append_connectivity_record(connectivity_gps, rec_)

    def _append_both(rec_: dict) -> None:
        _append_cam(rec_)
        _append_gps(rec_)

    attempt_row = {
        "event": "record_session_attempt",
        "device_id": device_id,
        "no_camera": args.no_camera,
        "no_gps": args.no_gps,
        "mock_gps": args.mock_gps,
        "camera_only_config": bool(rec.get("camera_only", False)),
    }
    _append_both(attempt_row)

    need_camera = not args.no_camera
    need_gps = not args.no_gps

    if need_camera:
        cam_ok, cam_detail = probe_camera(cfg)
        _append_cam(
            {"event": "camera_probe", "ok": cam_ok, "detail": cam_detail, "device_id": device_id},
        )
        log.info("camera probe: %s — %s", cam_ok, cam_detail)
        if not cam_ok:
            _append_cam(
                {
                    "event": "session_aborted",
                    "reason": "camera_probe_failed",
                    "detail": cam_detail,
                    "device_id": device_id,
                },
            )
            log.error("Aborting: camera not ready (%s). No session folder created.", cam_detail)
            return 1
    else:
        cam_ok, cam_detail = True, "skipped (--no-camera)"

    if need_gps:
        gps_ok, gps_detail = probe_gps(cfg, args.mock_gps, gps_probe_timeout_sec)
        _append_gps(
            {"event": "gps_probe", "ok": gps_ok, "detail": gps_detail, "device_id": device_id},
        )
        log.info("GPS probe: %s — %s", gps_ok, gps_detail)
        if not gps_ok:
            if rec.get("gps_optional", True):
                log.warning(
                    "GPS not ready (%s) — continuing camera-only (recording.gps_optional).",
                    gps_detail,
                )
                _append_gps(
                    {
                        "event": "gps_probe_fallback_camera_only",
                        "detail": gps_detail,
                        "device_id": device_id,
                    },
                )
                args.no_gps = True
            else:
                _append_gps(
                    {
                        "event": "session_aborted",
                        "reason": "gps_probe_failed",
                        "detail": gps_detail,
                        "device_id": device_id,
                    },
                )
                log.error("Aborting: GPS not ready (%s). No session folder created.", gps_detail)
                return 1
    else:
        gps_ok, gps_detail = True, "skipped (--no-gps)"

    session = session_dir_with_day(out_base)
    _append_both(
        {
            "event": "session_folder_created",
            "session_dir": str(session),
            "camera_ok": cam_ok,
            "gps_ok": gps_ok,
            "device_id": device_id,
        },
    )

    meta_path = session / meta_name
    video_template = session / video_name
    gps_template = session / gps_name
    started = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    meta_path.write_text(
        json.dumps(
            {
                "device_id": device_id,
                "started_utc": started,
                "config": str(args.config.resolve()),
                "fps": fps,
                "duration_sec": duration_sec,
                "segment_duration_sec": segment_duration_sec,
                "mock_gps": args.mock_gps,
                "camera_only": bool(rec.get("camera_only", False)),
                "session_dir": str(session),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    log.info(
        "Session %s — config=%s segment_duration_sec=%s "
        "(video: camera_*.mp4; GPS: gps_*.jsonl when segmenting)",
        session.name,
        args.config.resolve(),
        segment_duration_sec,
    )

    stop = threading.Event()
    gps_thread: threading.Thread | None = None

    def handle_sig(*_a: object) -> None:
        log.info("stop signal")
        stop.set()

    signal.signal(signal.SIGINT, handle_sig)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, handle_sig)

    if not args.no_gps:
        gps_thread = threading.Thread(
            target=gps_writer_thread,
            args=(gps_template, segment_duration_sec, stop, cfg, args.mock_gps, log),
            name="gps-writer",
            daemon=True,
        )
        gps_thread.start()

    try:
        if not args.no_camera:
            cam_code, _frames, _path = run_camera_recording_loop(
                cfg,
                video_template,
                fps,
                segment_duration_sec,
                duration_sec,
                stop,
                log,
            )
            if cam_code != 0:
                return cam_code
        else:
            log.info("camera skipped (--no-camera); GPS only until stop or duration")
            if gps_thread:
                if duration_sec > 0:
                    time.sleep(duration_sec)
                else:
                    while not stop.is_set():
                        time.sleep(0.5)
    finally:
        stop.set()
        if gps_thread is not None:
            gps_thread.join(timeout=30.0)

    log.info("session complete -> %s", session)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
