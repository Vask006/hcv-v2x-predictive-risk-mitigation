"""OpenCV / GStreamer camera access (lazy cv2 import)."""
from __future__ import annotations

import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from camera_models import CameraHealth, CameraSourceKind, FrameSample


class CaptureError(RuntimeError):
    pass


def _utc_wall() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


class OpenCVCameraReader:
    """Live camera (index or GStreamer pipeline) or file replay via ``video_path``.

    Behavior matches ``jetson-hcv-risk-poc/edge/camera_service/capture.py`` (Phase 0/1)
    for live paths. File replay uses ``cv2.VideoCapture(path)`` when ``video_path`` is set.
    """

    def __init__(
        self,
        index: int = 0,
        pipeline: Optional[str] = None,
        backend: str = "opencv",
        video_path: str | Path | None = None,
    ) -> None:
        self._index = index
        self._pipeline = pipeline
        self._backend = backend
        self._video_path = Path(video_path) if video_path else None
        self._cap: Any = None
        self._failures = 0
        self._last_read_ok = False
        self._last_error: str | None = None

    @property
    def source_kind(self) -> CameraSourceKind:
        if self._video_path is not None:
            return "file_replay"
        if self._pipeline:
            return "gstreamer"
        return "live_index"

    def health(self) -> CameraHealth:
        opened = self._cap is not None and bool(self._cap.isOpened())
        return CameraHealth(
            opened=opened,
            last_read_ok=self._last_read_ok,
            consecutive_failures=self._failures,
            last_error=self._last_error,
        )

    def open(self) -> None:
        import cv2  # type: ignore[import-untyped]

        if self._cap is not None:
            self.close()

        if self._video_path is not None:
            p = str(self._video_path.expanduser())
            self._cap = cv2.VideoCapture(p)
            if not self._cap.isOpened():
                raise CaptureError(f"Could not open video file for replay: {p}")
        elif self._pipeline:
            self._cap = cv2.VideoCapture(self._pipeline, cv2.CAP_GSTREAMER)
            if not self._cap.isOpened():
                raise CaptureError(
                    "Could not open GStreamer pipeline. Check string, plugins, and CAP_GSTREAMER build."
                )
        else:
            self._cap = cv2.VideoCapture(self._index)
            if not self._cap.isOpened():
                raise CaptureError(
                    "Could not open camera. Check index, permissions, or set a GStreamer pipeline in config."
                )
        self._failures = 0
        self._last_read_ok = False
        self._last_error = None

    def read_meta(self) -> FrameSample:
        """Read one frame and return metadata only (discards pixel buffer reference)."""
        meta, _frame = self.read_frame()
        return meta

    def read_frame(self) -> tuple[FrameSample, Any]:
        if self._cap is None:
            raise CaptureError("Camera not open")
        import cv2  # type: ignore[import-untyped]

        ok, frame = self._cap.read()
        if not ok or frame is None:
            self._failures += 1
            self._last_read_ok = False
            self._last_error = "Failed to read frame"
            raise CaptureError(self._last_error)

        self._failures = 0
        h, w = frame.shape[:2]
        now = time.monotonic()
        wall = _utc_wall()
        self._last_read_ok = True
        self._last_error = None
        meta = FrameSample(
            wall_time_utc_iso=wall,
            monotonic_s=now,
            width=w,
            height=h,
            backend=self._backend,
        )
        return meta, frame

    def close(self) -> None:
        if self._cap is not None:
            self._cap.release()
            self._cap = None

    def __enter__(self) -> OpenCVCameraReader:
        self.open()
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()
