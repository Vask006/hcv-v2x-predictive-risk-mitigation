"""
Record camera to a video file and GPS fixes to JSONL on local disk (Jetson / workstation).

Run from `edge/`:
  python -m app.record_session --config config/default.yaml

Stop with Ctrl+C or after duration_sec (config). Use --mock-gps if no serial GPS.
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


def _load_config(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _session_dir(base: Path) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    d = base / stamp
    d.mkdir(parents=True, exist_ok=True)
    return d


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
    video_name = str(rec.get("video_filename", "camera.mp4"))
    gps_name = str(rec.get("gps_filename", "gps.jsonl"))
    meta_name = str(rec.get("session_meta_filename", "session.json"))

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    log = logging.getLogger("record")

    session = _session_dir(out_base)
    meta_path = session / meta_name
    video_path = session / video_name
    gps_path = session / gps_name

    device_id = cfg.get("device_id", "unknown")
    started = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    meta_path.write_text(
        json.dumps(
            {
                "device_id": device_id,
                "started_utc": started,
                "config": str(args.config.resolve()),
                "fps": fps,
                "duration_sec": duration_sec,
                "mock_gps": args.mock_gps,
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
                writer, actual_video_path = _open_video_writer(video_path, fps, (w, h))
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
