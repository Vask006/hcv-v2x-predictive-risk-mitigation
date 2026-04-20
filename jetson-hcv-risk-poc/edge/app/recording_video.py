"""Camera capture and segmented video file writing (OpenCV VideoWriter)."""
from __future__ import annotations

import logging
import threading
import time
from pathlib import Path
from typing import Any

from app.recording_paths import initial_video_path, numbered_video_path


def open_video_writer(path: Path, fps: float, size: tuple[int, int]) -> tuple[object, Path]:
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


def run_camera_recording_loop(
    cfg: dict[str, Any],
    video_template: Path,
    fps: float,
    segment_duration_sec: float,
    duration_sec: float,
    stop: threading.Event,
    log: logging.Logger,
) -> tuple[int, int, Path | None]:
    """
    Capture from camera and write video segment(s). ``stop`` ends the loop (SIGINT/service stop).

    Returns:
        (exit_code, frame_count, last_video_path) — exit_code 0 ok, 1 on CaptureError.
    """
    from camera_service.capture import CameraCapture, CaptureError

    segment_duration_sec = float(segment_duration_sec)
    if segment_duration_sec <= 0:
        log.warning(
            "segment_duration_sec is 0 — one file camera.mp4 for the whole session; set YAML or HCV_SEGMENT_SEC to chunk.",
        )

    cam_cfg = cfg.get("camera", {})
    pipeline = cam_cfg.get("gstream_pipeline")
    idx = int(cam_cfg.get("index", 0))
    cap = CameraCapture(
        index=idx,
        pipeline=pipeline,
        backend=str(cam_cfg.get("backend", "opencv")),
    )
    writer: object | None = None
    actual_video_path: Path | None = None
    frames = 0

    try:
        cap.open()
        try:
            _meta0, frame0 = cap.read_frame()
            h, w = frame0.shape[:2]
            first_path = initial_video_path(video_template, segment_duration_sec)
            writer, actual_video_path = open_video_writer(first_path, fps, (w, h))
            segment_start = time.monotonic()
            segment_idx = 1 if segment_duration_sec > 0 else 0
            log.info(
                "Writing video segment_length=%ss -> %s",
                segment_duration_sec,
                actual_video_path,
            )
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
                    writer, actual_video_path = open_video_writer(next_seg, fps, (w, h))
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
            return 1, frames, actual_video_path
        finally:
            cap.close()
    finally:
        if writer is not None:
            writer.release()
            log.info("Wrote %s frames to %s", frames, actual_video_path)

    return 0, frames, actual_video_path
