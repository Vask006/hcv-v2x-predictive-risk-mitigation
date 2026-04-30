"""Typed telemetry contracts for normalized pipeline input."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class GpsTelemetryBlock:
    latitude_deg: float | None = None
    longitude_deg: float | None = None
    speed_mps: float | None = None
    heading_deg: float | None = None
    fix_quality: int | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CameraTelemetryBlock:
    healthy: bool | None = None
    lane_stability_01: float | None = None
    object_risk_01: float | None = None
    frame_width: int | None = None
    frame_height: int | None = None
    source_kind: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class VehicleStateBlock:
    brake_applied: bool | None = None
    steering_angle_deg: float | None = None
    acceleration_mps2: float | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class NormalizedTelemetryEvent:
    vehicle_id: str
    trip_id: str | None
    timestamp: str
    gps: GpsTelemetryBlock | None
    camera: CameraTelemetryBlock | None
    vehicle_state: VehicleStateBlock | None
    source: str
    raw: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "vehicle_id": self.vehicle_id,
            "trip_id": self.trip_id,
            "timestamp": self.timestamp,
            "gps": None if self.gps is None else self.gps.as_dict(),
            "camera": None if self.camera is None else self.camera.as_dict(),
            "vehicle_state": None if self.vehicle_state is None else self.vehicle_state.as_dict(),
            "source": self.source,
            "raw": self.raw,
        }
