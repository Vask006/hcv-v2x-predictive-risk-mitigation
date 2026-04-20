from __future__ import annotations

import sys
from pathlib import Path

_CLOUD_API = Path(__file__).resolve().parents[1] / "cloud" / "api"
if str(_CLOUD_API) not in sys.path:
    sys.path.insert(0, str(_CLOUD_API))

# pylint: disable=import-error
from enrichment import build_mock_context


def test_mock_context_output_range() -> None:
    out = build_mock_context("2026-04-14T10:00:00.000Z", lat=47.285, lon=8.5537)
    assert out["provider"] == "cloud_mock_context"
    assert 0.0 <= out["traffic_risk"] <= 1.0
    assert 0.0 <= out["weather_risk"] <= 1.0
    assert 0.0 <= out["road_risk"] <= 1.0
