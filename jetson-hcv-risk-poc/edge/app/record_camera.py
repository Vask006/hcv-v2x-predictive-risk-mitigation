"""
Record camera frames to local video file only.

Run from `edge/`:
  python -m app.record_camera --config config/default.yaml
"""
from __future__ import annotations

import argparse
import json
import logging
import signal
import sys
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
    resolve_connectivity_log_path,
)


def _load_config(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _session_dir(base: Path) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    d = base / f"{stamp}-camera"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _open_video_writer(
    path: Path, fps: float, size: tuple[int, int]
) -> tuple[object, Path]:
    # OpenCV Python wheels may not expose full typing metadata for these members.
    # pylint: disable=no-member
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


def main() -> int:
    parser = argparse.ArgumentParser(description="Record camera video to disk (camera only).")
    parser.add_argument("--config", type=Path, default=_EDGE_ROOT / "config" / "default.yaml")
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
    meta_name = str(rec.get("session_meta_filename", "session.json"))

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    log = logging.getLogger("record-camera")

    connectivity_log = resolve_connectivity_log_path(_EDGE_ROOT, cfg)
    device_id = cfg.get("device_id", "unknown")
    append_connectivity_record(
        connectivity_log,
        {"event": "record_camera_attempt", "device_id": device_id},
    )
    cam_ok, cam_detail = probe_camera(cfg)
    append_connectivity_record(
        connectivity_log,
        {"event": "camera_probe", "ok": cam_ok, "detail": cam_detail, "device_id": device_id},
    )
    if not cam_ok:
        append_connectivity_record(
            connectivity_log,
            {
                "event": "session_aborted",
                "reason": "camera_probe_failed",
                "detail": cam_detail,
                "device_id": device_id,
            },
        )
        log.error("Camera not ready (%s). No session folder created.", cam_detail)
        return 1

    session = _session_dir(out_base)
    append_connectivity_record(
        connectivity_log,
        {"event": "session_folder_created", "session_dir": str(session), "device_id": device_id},
    )

    meta_path = session / meta_name
    video_path = session / video_name
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
                "session_dir": str(session),
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    stop = False

    def handle_sig(*_a: object) -> None:
        nonlocal stop
        log.info("stop signal")
        stop = True

    signal.signal(signal.SIGINT, handle_sig)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, handle_sig)

    from camera_service.capture import CameraCapture, CaptureError

    writer = None
    actual_video_path: Path | None = None
    frames = 0
    t0 = time.monotonic()

    try:
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
            log.info("Writing camera video -> %s", actual_video_path)
            writer.write(frame0)
            frames = 1

            period = 1.0 / fps if fps > 0 else 0.0
            t0 = time.monotonic()
            next_t = t0 + period

            while not stop:
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
        finally:
            cap.close()
    except CaptureError as e:
        log.error("Camera failed: %s", e)
        return 1
    finally:
        if writer is not None:
            writer.release()
            log.info("Wrote %s frames to %s", frames, actual_video_path)

    log.info("camera session complete -> %s", session)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
