"""Phase 1 camera service: config → reader → normalized ``CameraSampleEvent``."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Optional, Tuple

from camera_models import CameraHealth, CameraSampleEvent, FrameSample
from camera_reader import CaptureError, OpenCVCameraReader


class CameraServiceConfig:
    """YAML ``camera:`` compatible knobs (+ optional file replay)."""

    __slots__ = ("index", "pipeline", "backend", "video_path")

    def __init__(
        self,
        *,
        index: int = 0,
        pipeline: Optional[str] = None,
        backend: str = "opencv",
        video_path: str | Path | None = None,
    ) -> None:
        self.index = index
        self.pipeline = pipeline
        self.backend = backend
        self.video_path = video_path

    @classmethod
    def from_camera_yaml(cls, camera: Mapping[str, Any]) -> CameraServiceConfig:
        # Optional replay path (not in default POC YAML; supported for bench / CI).
        vp = camera.get("replay_video_path") or camera.get("video_path")
        return cls(
            index=int(camera.get("index", 0)),
            pipeline=camera.get("gstream_pipeline"),
            backend=str(camera.get("backend", "opencv")),
            video_path=vp,
        )


class CameraService:
    """Owns an ``OpenCVCameraReader`` and builds ``CameraSampleEvent`` per read."""

    def __init__(self, config: CameraServiceConfig | Mapping[str, Any]) -> None:
        if isinstance(config, CameraServiceConfig):
            self._cfg = config
        else:
            self._cfg = CameraServiceConfig.from_camera_yaml(config)
        self._reader = OpenCVCameraReader(
            index=self._cfg.index,
            pipeline=self._cfg.pipeline,
            backend=self._cfg.backend,
            video_path=self._cfg.video_path,
        )

    @property
    def reader(self) -> OpenCVCameraReader:
        return self._reader

    def open(self) -> None:
        self._reader.open()

    def close(self) -> None:
        self._reader.close()

    def read_frame(self) -> Tuple[CameraSampleEvent, Any]:
        meta, frame = self._reader.read_frame()
        ev = self._build_event(meta, ok=True, err=None)
        return ev, frame

    def read_meta_only(self) -> CameraSampleEvent:
        meta = self._reader.read_meta()
        return self._build_event(meta, ok=True, err=None)

    def probe(self) -> Tuple[bool, str, CameraHealth]:
        """One-frame probe (same semantics as ``device_connectivity.probe_camera``)."""
        try:
            self.open()
            self._reader.read_frame()
            h = self._reader.health()
            return True, f"camera_ok kind={self._reader.source_kind} backend={self._cfg.backend}", h
        except CaptureError as e:
            h = self._reader.health()
            return False, str(e), h
        finally:
            self.close()

    def _build_event(self, meta: FrameSample, *, ok: bool, err: str | None) -> CameraSampleEvent:
        h = self._reader.health()
        if err:
            h = CameraHealth(
                opened=h.opened,
                last_read_ok=False,
                consecutive_failures=h.consecutive_failures,
                last_error=err,
            )
        healthy = ok and h.last_read_ok and h.consecutive_failures == 0
        return CameraSampleEvent(
            meta=meta,
            source_kind=self._reader.source_kind,
            healthy=healthy,
            health=h,
        )

    def __enter__(self) -> CameraService:
        self.open()
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()
