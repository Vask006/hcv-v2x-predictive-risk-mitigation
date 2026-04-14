from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any, Optional

log = logging.getLogger(__name__)


class CaptureError(RuntimeError):
    pass


@dataclass
class FrameSample:
    """One frame with timing metadata (Phase 0)."""

    wall_time_utc_iso: str
    monotonic_s: float
    width: int
    height: int
    backend: str


class CameraCapture:
    """Minimal OpenCV capture; optional GStreamer string if `pipeline` is set."""

    def __init__(
        self,
        index: int = 0,
        pipeline: Optional[str] = None,
        backend: str = "opencv",
    ) -> None:
        self._index = index
        self._pipeline = pipeline
        self._backend = backend
        self._cap: Any = None

    def open(self) -> None:
        import cv2  # type: ignore

        if self._pipeline:
            self._cap = cv2.VideoCapture(self._pipeline, cv2.CAP_GSTREAMER)
        else:
            self._cap = cv2.VideoCapture(self._index)

        if not self._cap.isOpened():
            raise CaptureError(
                "Could not open camera. Check index, permissions, or set a GStreamer pipeline in config."
            )

    def read_meta(self) -> FrameSample:
        if self._cap is None:
            raise CaptureError("Camera not open")
        import cv2  # type: ignore
        from datetime import datetime, timezone

        ok, frame = self._cap.read()
        if not ok or frame is None:
            raise CaptureError("Failed to read frame")

        h, w = frame.shape[:2]
        now = time.monotonic()
        wall = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        return FrameSample(
            wall_time_utc_iso=wall,
            monotonic_s=now,
            width=w,
            height=h,
            backend=self._backend,
        )

    def close(self) -> None:
        if self._cap is not None:
            self._cap.release()
            self._cap = None

    def __enter__(self) -> "CameraCapture":
        self.open()
        return self

    def __exit__(self, *args: object) -> None:
        self.close()
