from __future__ import annotations

from telemetry_normalizer import clamp_01, normalize_telemetry


def test_full_input_normalization() -> None:
    out = normalize_telemetry(
        vehicle_id="veh-1",
        trip_id="trip-1",
        gps={"latitude_deg": "48.1", "longitude_deg": "11.5", "speed_mps": "12.3", "heading_deg": "90", "fix_quality": "1"},
        camera={"healthy": True, "lane_stability_01": 0.7, "object_risk_01": 0.2, "frame_width": 640, "frame_height": 480, "source_kind": "live"},
        vehicle_state={"brake_applied": False, "steering_angle_deg": 4.5, "acceleration_mps2": 1.2},
        timestamp="2026-01-01T00:00:00.000000Z",
    )
    assert out.vehicle_id == "veh-1"
    assert out.gps is not None and out.gps.latitude_deg == 48.1
    assert out.camera is not None and out.camera.frame_width == 640
    assert out.vehicle_state is not None and out.vehicle_state.acceleration_mps2 == 1.2


def test_missing_blocks() -> None:
    out = normalize_telemetry(vehicle_id="veh-1", gps=None, camera=None, vehicle_state=None)
    assert out.gps is None
    assert out.camera is None
    assert out.vehicle_state is None


def test_camel_case_support() -> None:
    out = normalize_telemetry(
        vehicle_id="veh-1",
        gps={"latitudeDeg": 1, "longitudeDeg": 2, "speedMps": 3, "headingDeg": 4, "fixQuality": 1},
        camera={"laneStability01": 0.9, "objectRisk01": 0.1, "frameWidth": 10, "frameHeight": 20, "sourceKind": "mock"},
        vehicle_state={"brakeApplied": True, "steeringAngleDeg": 1.2, "accelerationMps2": 0.5},
    )
    assert out.gps is not None and out.gps.longitude_deg == 2.0
    assert out.camera is not None and out.camera.source_kind == "mock"
    assert out.vehicle_state is not None and out.vehicle_state.brake_applied is True


def test_invalid_numeric_input_and_clamp() -> None:
    out = normalize_telemetry(
        vehicle_id="veh-1",
        gps={"latitude_deg": "abc"},
        camera={"lane_stability_01": 5, "object_risk_01": -2},
    )
    assert out.gps is not None and out.gps.latitude_deg is None
    assert out.camera is not None and out.camera.lane_stability_01 == 1.0
    assert out.camera.object_risk_01 == 0.0
    assert clamp_01("bad") is None


def test_timestamp_fallback_and_raw_preserved() -> None:
    out = normalize_telemetry(
        vehicle_id="veh-1",
        gps={"wall_time_utc_iso": "2026-01-02T00:00:00.000000Z"},
        camera={"healthy": True},
    )
    assert out.timestamp == "2026-01-02T00:00:00.000000Z"
    assert out.raw["gps"] == {"wall_time_utc_iso": "2026-01-02T00:00:00.000000Z"}
