"""
Record camera to video file(s) and GPS fixes to JSONL on local disk (Jetson / workstation).

Output layout: ``data/recordings/<YYYY-MM-DD>/<session-UTC>/`` (one calendar-day folder).
Optional ``recording.segment_duration_sec`` splits video into ``camera_000001.mp4``, … so an
abrupt stop only risks truncating the current segment.

Run from `edge/`:
  python -m app.record_session --config config/default.yaml

Stop with Ctrl+C or after duration_sec (config). Use --mock-gps if no serial GPS.
Set recording.camera_only: true in YAML (or HCV_CAMERA_ONLY=1 via
deploy/hcv-record-start.sh) to skip GPS probe and recording — same as --no-gps.
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
from app.recording_paths import initial_video_path, numbered_video_path, session_dir_with_day


def _load_config(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _open_video_writer(
    path: Path, fps: float, size: tuple[int, int]
) -> tuple[object, Path]:
    import cv2  # type: ignore

    w, h = size
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(path), fourcc, fps, (w, h))
    if writer.isOpened():
        return writer, path
    path_avi = path.with_suffix(".avi")
    fourcc = cv2.VideoWriter_fourcc(*"MJPG")
    writer = cv2.VideoWriter(str(path_avi), fourcc, fps, (w, h))
    if not writer.isOpened():
        raise RuntimeError("Could not open VideoWriter (tried mp4v and MJPG/avi)")
    return writer, path_avi


def _gps_thread(
    out_path: Path,
    stop: threading.Event,
    cfg: dict,
    mock_gps: bool,
    log: logging.Logger,
) -> None:
    def write_fix(fix: object) -> None:
        row = {
            "wall_utc": fix.wall_time_utc_iso,
            "mono_s": fix.monotonic_s,
            "latitude_deg": fix.latitude_deg,
            "longitude_deg": fix.longitude_deg,
            "fix_quality": fix.fix_quality,
            "raw": (fix.raw_sentence or "")[:500],
        }
        with out_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    try:
        if mock_gps:
            from gps_service.reader import mock_fixes

            while not stop.is_set():
                for fix in mock_fixes(20):
                    if stop.is_set():
                        return
                    write_fix(fix)
        else:
            from gps_service.reader import GPSReader

            g = cfg.get("gps", {})
            port = str(g.get("port", "/dev/ttyUSB0"))
            baud = int(g.get("baud", 9600))
            timeout = float(g.get("timeout_sec", 1.0))
            reader = GPSReader(port, baud, timeout)
            reader.open()
            log.info("GPS serial open %s baud=%s", port, baud)
            try:
                for fix in reader.iter_lines(max_lines=None):
                    if stop.is_set():
                        break
                    write_fix(fix)
            finally:
                reader.close()
    except Exception as e:
        log.error("GPS recording thread ended: %s", e)


def main() -> int:
    parser = argparse.ArgumentParser(description="Record camera video + GPS JSONL to disk.")
    parser.add_argument("--config", type=Path, default=_EDGE_ROOT / "config" / "default.yaml")
    parser.add_argument("--mock-gps", action="store_true", help="Use mock GPS (no serial)")
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
    segment_duration_sec = float(rec.get("segment_duration_sec", 0))
    if args.segment_sec is not None:
        segment_duration_sec = float(args.segment_sec)
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
                "GPS port %s missing — continuing camera-only. Use --mock-gps to log fake GPS.",
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
    gps_path = session / gps_name
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
            target=_gps_thread,
            args=(gps_path, stop, cfg, args.mock_gps, log),
            name="gps-writer",
            daemon=True,
        )
        gps_thread.start()

    writer = None
    actual_video_path: Path | None = None
    frames = 0
    t0 = time.monotonic()

    try:
        if not args.no_camera:
            from camera_service.capture import CameraCapture, CaptureError

            cam_cfg = cfg.get("camera", {})
            pipeline = cam_cfg.get("gstream_pipeline")
            idx = int(cam_cfg.get("index", 0))
            cap = CameraCapture(
                index=idx,
                pipeline=pipeline,
                backend=str(cam_cfg.get("backend", "opencv")),
            )
            cap.open()
            try:
                _meta0, frame0 = cap.read_frame()
                h, w = frame0.shape[:2]
                first_path = initial_video_path(video_template, segment_duration_sec)
                writer, actual_video_path = _open_video_writer(first_path, fps, (w, h))
                segment_start = time.monotonic()
                segment_idx = 1 if segment_duration_sec > 0 else 0
                log.info("Writing video -> %s", actual_video_path)
                writer.write(frame0)
                frames = 1

                period = 1.0 / fps if fps > 0 else 0.0
                t0 = time.monotonic()
                next_t = t0 + period

                while not stop.is_set():
                    if duration_sec > 0 and (time.monotonic() - t0) >= duration_sec:
                        break
                    _meta, frame = cap.read_frame()
                    if segment_duration_sec > 0 and (time.monotonic() - segment_start) >= segment_duration_sec:
                        writer.release()
                        segment_idx += 1
                        next_seg = numbered_video_path(video_template, segment_idx)
                        writer, actual_video_path = _open_video_writer(next_seg, fps, (w, h))
                        log.info("Rotated video segment -> %s", actual_video_path)
                        segment_start = time.monotonic()
                    writer.write(frame)
                    frames += 1
                    now = time.monotonic()
                    if period > 0:
                        sleep = next_t - now
                        if sleep > 0:
                            time.sleep(sleep)
                        next_t += period
                    else:
                        next_t = now
            except CaptureError as e:
                log.error("Camera failed: %s", e)
                return 1
            finally:
                cap.close()
        else:
            log.info("camera skipped (--no-camera); GPS only until stop or duration")
            t0 = time.monotonic()
            if gps_thread:
                if duration_sec > 0:
                    time.sleep(duration_sec)
                else:
                    while not stop.is_set():
                        time.sleep(0.5)
    finally:
        stop.set()
        if writer is not None:
            writer.release()
            log.info("Wrote %s frames to %s", frames, actual_video_path)
        if gps_thread is not None:
            gps_thread.join(timeout=30.0)

    log.info("session complete -> %s", session)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
