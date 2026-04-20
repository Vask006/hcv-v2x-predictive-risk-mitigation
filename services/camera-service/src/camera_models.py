"""Typed camera metadata for Phase 1 (no ML perception)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

CameraSourceKind = Literal["live_index", "gstreamer", "file_replay"]


@dataclass(frozen=True)
class FrameSample:
    """One captured frame timing + geometry (POC-compatible field names)."""

    wall_time_utc_iso: str
    monotonic_s: float
    width: int
    height: int
    backend: str


@dataclass(frozen=True)
class CameraHealth:
    """Open/read health for edge runtime or probes."""

    opened: bool
    last_read_ok: bool
    consecutive_failures: int
    last_error: str | None = None


@dataclass
class CameraSampleEvent:
    """Normalized sample: metadata + health + source (Phase 1 contract, not event_v1 GPS)."""

    meta: FrameSample
    source_kind: CameraSourceKind
    healthy: bool
    health: CameraHealth
    # TODO(phase2): optional numpy frame reference or shared-memory handle; keep Phase 1 dict-friendly.
    extra: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        """JSON-serializable summary (no frame array)."""
        return {
            "schema_version": "camera.sample.v1",
            "wall_time_utc_iso": self.meta.wall_time_utc_iso,
            "monotonic_s": self.meta.monotonic_s,
            "width": self.meta.width,
            "height": self.meta.height,
            "backend": self.meta.backend,
            "source_kind": self.source_kind,
            "healthy": self.healthy,
            "health": {
                "opened": self.health.opened,
                "last_read_ok": self.health.last_read_ok,
                "consecutive_failures": self.health.consecutive_failures,
                "last_error": self.health.last_error,
            },
            **self.extra,
        }
