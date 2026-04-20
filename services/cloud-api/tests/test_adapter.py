from __future__ import annotations

from uuid import UUID

from adapter import combined_pipeline_to_event_v1


def test_adapter_maps_pipeline_to_event_v1_shape() -> None:
    combined = {
        "pipelineVersion": "phase1-local-1",
        "riskEvent": {
            "eventId": "12345678-1234-5678-1234-567812345678",
            "vehicleId": "veh-a",
            "tripId": "trip-1",
            "timestamp": "2026-04-19T12:00:00.000000Z",
            "edgeObservations": {
                "latitude_deg": 48.1,
                "longitude_deg": 11.5,
                "gps_speed_mps": 12.0,
                "gps_fix_quality": 1,
            },
            "externalContext": {"curve_ahead": True},
            "riskAssessment": {"riskScore": 0.42, "severity": "medium", "hazardType": "ambient_context"},
            "mitigation": {
                "driverAlert": "Caution",
                "fleetNotification": False,
                "recommendedAction": "Log segment",
            },
            "reasonCodes": ["rule.lane_instability_hazard"],
        },
        "inputsEcho": {},
    }
    body = combined_pipeline_to_event_v1(combined)
    assert body["schema_version"] == "1.0"
    assert body["device_id"] == "veh-a"
    assert body["gps"]["latitude_deg"] == 48.1
    assert body["risk"]["band"] == "medium"
    assert body["risk"]["score"] == 0.42
    assert UUID(body["event_id"]) == UUID("12345678-1234-5678-1234-567812345678")
    assert "perception_summary" in body
    assert body["perception_summary"]["trip_id"] == "trip-1"


def test_adapter_defaults_missing_gps_position() -> None:
    combined = {
        "riskEvent": {
            "eventId": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
            "vehicleId": "v",
            "timestamp": "2026-01-01T00:00:00Z",
            "edgeObservations": {},
            "riskAssessment": {"riskScore": 0.1, "severity": "bogus_band", "hazardType": "x"},
            "reasonCodes": [],
        }
    }
    body = combined_pipeline_to_event_v1(combined)
    assert body["gps"]["latitude_deg"] == 0.0
    assert body["gps"]["longitude_deg"] == 0.0
    assert body["risk"]["band"] == "none"
    assert "adapter.gps_latitude_defaulted" in body["risk"]["reason_codes"]
