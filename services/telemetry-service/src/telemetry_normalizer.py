"""Normalization helpers for mixed telemetry payloads."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from telemetry_models import (
    CameraTelemetryBlock,
    GpsTelemetryBlock,
    NormalizedTelemetryEvent,
    VehicleStateBlock,
)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def safe_float(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def safe_int(value: Any) -> int | None:
    try:
        if value is None or value == "":
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def clamp_01(value: Any) -> float | None:
    parsed = safe_float(value)
    if parsed is None:
        return None
    return max(0.0, min(1.0, parsed))


def _pick(data: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in data:
            return data[key]
    return None


def normalize_gps(gps: dict[str, Any] | None) -> GpsTelemetryBlock | None:
    if not gps:
        return None
    return GpsTelemetryBlock(
        latitude_deg=safe_float(_pick(gps, "latitude_deg", "latitudeDeg")),
        longitude_deg=safe_float(_pick(gps, "longitude_deg", "longitudeDeg")),
        speed_mps=safe_float(_pick(gps, "speed_mps", "speedMps")),
        heading_deg=safe_float(_pick(gps, "heading_deg", "headingDeg")),
        fix_quality=safe_int(_pick(gps, "fix_quality", "fixQuality")),
    )


def normalize_camera(camera: dict[str, Any] | None) -> CameraTelemetryBlock | None:
    if not camera:
        return None
    healthy_raw = _pick(camera, "healthy")
    healthy: bool | None = None
    if isinstance(healthy_raw, bool):
        healthy = healthy_raw
    elif healthy_raw is not None:
        healthy = str(healthy_raw).lower() in {"1", "true", "yes"}

    return CameraTelemetryBlock(
        healthy=healthy,
        lane_stability_01=clamp_01(_pick(camera, "lane_stability_01", "laneStability01")),
        object_risk_01=clamp_01(_pick(camera, "object_risk_01", "objectRisk01")),
        frame_width=safe_int(_pick(camera, "frame_width", "frameWidth")),
        frame_height=safe_int(_pick(camera, "frame_height", "frameHeight")),
        source_kind=_pick(camera, "source_kind", "sourceKind"),
    )


def normalize_vehicle_state(vehicle_state: dict[str, Any] | None) -> VehicleStateBlock | None:
    if not vehicle_state:
        return None
    brake_raw = _pick(vehicle_state, "brake_applied", "brakeApplied")
    brake_applied: bool | None = None
    if isinstance(brake_raw, bool):
        brake_applied = brake_raw
    elif brake_raw is not None:
        brake_applied = str(brake_raw).lower() in {"1", "true", "yes"}

    return VehicleStateBlock(
        brake_applied=brake_applied,
        steering_angle_deg=safe_float(_pick(vehicle_state, "steering_angle_deg", "steeringAngleDeg")),
        acceleration_mps2=safe_float(_pick(vehicle_state, "acceleration_mps2", "accelerationMps2")),
    )


def normalize_telemetry(
    *,
    vehicle_id: str,
    trip_id: str | None = None,
    gps: dict[str, Any] | None = None,
    camera: dict[str, Any] | None = None,
    vehicle_state: dict[str, Any] | None = None,
    timestamp: str | None = None,
    source: str = "telemetry-service",
) -> NormalizedTelemetryEvent:
    normalized_gps = normalize_gps(gps)
    normalized_camera = normalize_camera(camera)
    normalized_vehicle_state = normalize_vehicle_state(vehicle_state)

    resolved_timestamp = (
        timestamp
        or _pick(gps or {}, "wall_time_utc_iso", "timestamp")
        or _pick(camera or {}, "wall_time_utc_iso", "timestamp")
        or utc_now_iso()
    )

    return NormalizedTelemetryEvent(
        vehicle_id=vehicle_id,
        trip_id=trip_id,
        timestamp=resolved_timestamp,
        gps=normalized_gps,
        camera=normalized_camera,
        vehicle_state=normalized_vehicle_state,
        source=source,
        raw={"gps": gps, "camera": camera, "vehicle_state": vehicle_state},
    )
