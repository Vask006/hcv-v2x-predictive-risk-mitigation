"""
Camera capture for the POC.

Primary implementation lives under ``services/camera-service/src/`` when this repo is
laid out as ``<root>/jetson-hcv-risk-poc/edge/...`` and ``<root>/services/camera-service/src``.
If that path is not found (standalone clone), a legacy inline implementation is used.

TODO: When ``hcv-camera-service`` is always installed (``pip install -e``), remove the
legacy branch and import the package only.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Optional


def _shared_service_src() -> Path | None:
    here = Path(__file__).resolve()
    for root in here.parents:
        cand = root / "services" / "camera-service" / "src"
        if cand.is_dir() and (cand / "camera_reader.py").is_file():
            return cand
    return None


_SRC = _shared_service_src()
if _SRC is not None:
    p = str(_SRC)
    if p not in sys.path:
        sys.path.insert(0, p)
    from camera_reader import CaptureError, OpenCVCameraReader
    from camera_models import FrameSample

    class CameraCapture:
        """Compatibility wrapper over ``OpenCVCameraReader`` (same constructor as Phase 0)."""

        def __init__(
            self,
            index: int = 0,
            pipeline: Optional[str] = None,
            backend: str = "opencv",
            *,
            video_path: str | Path | None = None,
        ) -> None:
            self._inner = OpenCVCameraReader(
                index=index,
                pipeline=pipeline,
                backend=backend,
                video_path=video_path,
            )

        def open(self) -> None:
            self._inner.open()

        def read_meta(self) -> FrameSample:
            return self._inner.read_meta()

        def read_frame(self) -> tuple[FrameSample, Any]:
            return self._inner.read_frame()

        def close(self) -> None:
            self._inner.close()

        def __enter__(self) -> CameraCapture:
            self.open()
            return self

        def __exit__(self, *args: object) -> None:
            self.close()

else:
    import time
    from dataclasses import dataclass
    from datetime import datetime, timezone

    class CaptureError(RuntimeError):
        pass

    @dataclass
    class FrameSample:
        wall_time_utc_iso: str
        monotonic_s: float
        width: int
        height: int
        backend: str

    class CameraCapture:
        """Legacy inline capture (standalone ``jetson-hcv-risk-poc`` tree without monorepo ``services/``)."""

        def __init__(
            self,
            index: int = 0,
            pipeline: Optional[str] = None,
            backend: str = "opencv",
            *,
            video_path: str | Path | None = None,
        ) -> None:
            if video_path is not None:
                raise CaptureError(
                    "replay_video_path / video_path requires monorepo services/camera-service on PYTHONPATH"
                )
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

        def read_frame(self) -> tuple[FrameSample, Any]:
            if self._cap is None:
                raise CaptureError("Camera not open")
            import cv2  # type: ignore

            ok, frame = self._cap.read()
            if not ok or frame is None:
                raise CaptureError("Failed to read frame")

            h, w = frame.shape[:2]
            now = time.monotonic()
            wall = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
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

        def __enter__(self) -> CameraCapture:
            self.open()
            return self

        def __exit__(self, *args: object) -> None:
            self.close()
