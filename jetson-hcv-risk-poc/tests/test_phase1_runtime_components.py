from __future__ import annotations

from pathlib import Path

# pylint: disable=import-error
from event_store.queue import EventQueue
from risk_engine.scorer import score_risk


def test_score_risk_outputs_band_and_reasons() -> None:
    gps = {"latitude_deg": 47.2, "longitude_deg": 8.5, "fix_quality": 1}
    perception = {
        "nearest_object_m": 8.0,
        "lane_departure_prob": 0.7,
        "closure_rate_mps": 5.5,
    }
    context = {"weather_risk": 0.6, "traffic_risk": 0.5, "road_risk": 0.4}
    out = score_risk(gps=gps, perception=perception, context=context, config={})
    assert 0.0 <= out.score <= 1.0
    assert out.band in {"none", "low", "medium", "high", "critical"}
    assert "perception.nearest_object_close" in out.reason_codes
    assert out.warnings


def test_event_queue_roundtrip(tmp_path: Path) -> None:
    q = EventQueue(tmp_path / "events")
    payload = {"event_id": "abc-123", "schema_version": "1.0"}
    q.enqueue(payload)
    pending = q.list_pending(limit=10)
    assert len(pending) == 1
    assert pending[0].payload["event_id"] == "abc-123"
    q.mark_sent(pending[0])
    assert q.pending_count() == 0
