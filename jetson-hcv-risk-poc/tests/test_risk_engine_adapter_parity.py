"""
Parity-style checks between legacy ``score_risk`` and ``service_adapter.score_risk_via_service_engine``.

The two engines use different rule sets; we assert **practical** alignment: valid outputs,
stable bands, and rough rank proximity for representative scenarios when the monorepo
``services/risk-engine`` layout is present.
"""
from __future__ import annotations

import pytest

from risk_engine.scorer import RiskAssessment, band_rank, score_risk
from risk_engine.service_adapter import score_risk_via_service_engine


def _requires_service_layout() -> None:
    from risk_engine.service_adapter import _risk_engine_src

    if _risk_engine_src() is None:
        pytest.skip("monorepo services/risk-engine/src not found from this checkout")


def _assert_valid_assessment(a: RiskAssessment) -> None:
    assert a.band in ("none", "low", "medium", "high", "critical")
    assert 0.0 <= a.score <= 1.0
    assert isinstance(a.reason_codes, list)
    assert isinstance(a.warnings, list)
    assert isinstance(a.fleet_alert, bool)


def _bands_within(a: RiskAssessment, b: RiskAssessment, max_rank_delta: int = 2) -> None:
    assert abs(band_rank(a.band) - band_rank(b.band)) <= max_rank_delta


def test_nominal_low_risk_scenario() -> None:
    _requires_service_layout()
    gps = {
        "wall_utc": "2026-04-20T10:00:00.000000Z",
        "mono_s": 1000.0,
        "latitude_deg": 48.0,
        "longitude_deg": 11.0,
        "fix_quality": 1,
    }
    perception = {
        "nearest_object_m": 40.0,
        "lane_departure_prob": 0.1,
        "closure_rate_mps": 0.5,
        "camera_alive": True,
    }
    context = {"weather_risk": 0.1, "traffic_risk": 0.1, "road_risk": 0.1, "provider": "test"}
    legacy = score_risk(gps=gps, perception=perception, context=context, config={})
    svc = score_risk_via_service_engine(gps, perception, context, {})
    _assert_valid_assessment(legacy)
    _assert_valid_assessment(svc)
    _bands_within(legacy, svc, max_rank_delta=2)
    assert band_rank(svc.band) <= band_rank("medium")


def test_elevated_speed_curve_wet_scenario() -> None:
    _requires_service_layout()
    gps = {
        "wall_utc": "2026-04-20T10:00:00.000000Z",
        "mono_s": 1000.0,
        "latitude_deg": 48.0,
        "longitude_deg": 11.0,
        "fix_quality": 1,
        "speed_mps": 28.0,
    }
    perception = {
        "nearest_object_m": 25.0,
        "lane_departure_prob": 0.2,
        "closure_rate_mps": 1.0,
        "camera_alive": True,
    }
    # Adapter maps high weather_risk → wet road_surface for service wet-curve rule.
    context = {"weather_risk": 0.65, "traffic_risk": 0.5, "road_risk": 0.5, "provider": "test"}
    legacy = score_risk(gps=gps, perception=perception, context=context, config={})
    svc = score_risk_via_service_engine(gps, perception, context, {})
    _assert_valid_assessment(legacy)
    _assert_valid_assessment(svc)
    assert "rule.speed_curve_wet" in svc.reason_codes or svc.score >= 0.12
    assert band_rank(svc.band) >= band_rank("low")


def test_degraded_lane_and_high_ambient_context() -> None:
    _requires_service_layout()
    gps = {
        "wall_utc": "2026-04-20T10:00:00.000000Z",
        "mono_s": 1000.0,
        "latitude_deg": 48.0,
        "longitude_deg": 11.0,
        "fix_quality": 1,
    }
    perception = {
        "nearest_object_m": 12.0,
        "lane_departure_prob": 0.85,
        "closure_rate_mps": 6.0,
        "camera_alive": True,
    }
    context = {"weather_risk": 0.75, "traffic_risk": 0.75, "road_risk": 0.75, "provider": "test"}
    legacy = score_risk(gps=gps, perception=perception, context=context, config={})
    svc = score_risk_via_service_engine(gps, perception, context, {})
    _assert_valid_assessment(legacy)
    _assert_valid_assessment(svc)
    assert band_rank(legacy.band) >= band_rank("low")
    assert band_rank(svc.band) >= band_rank("low")
    assert len(legacy.reason_codes) >= 1
    assert len(svc.reason_codes) >= 1


def test_missing_partial_gps_signals() -> None:
    _requires_service_layout()
    gps = {
        "wall_utc": "2026-04-20T10:00:00.000000Z",
        "mono_s": 1000.0,
        "latitude_deg": None,
        "longitude_deg": None,
        "fix_quality": 0,
    }
    perception = {
        "nearest_object_m": 30.0,
        "lane_departure_prob": 0.2,
        "closure_rate_mps": 0.0,
        "camera_alive": False,
    }
    context = {"weather_risk": 0.2, "traffic_risk": 0.2, "road_risk": 0.2, "provider": "test"}
    legacy = score_risk(gps=gps, perception=perception, context=context, config={})
    svc = score_risk_via_service_engine(gps, perception, context, {})
    _assert_valid_assessment(legacy)
    _assert_valid_assessment(svc)
    assert "gps.no_fix_quality" in legacy.reason_codes
    assert any("penalty.gps" in r or "gps" in r for r in svc.reason_codes)


def test_use_service_flag_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    from risk_engine.service_adapter import use_service_risk_engine_from_config

    monkeypatch.delenv("HCV_USE_SERVICE_RISK_ENGINE", raising=False)
    assert use_service_risk_engine_from_config({}) is False
    assert use_service_risk_engine_from_config({"use_service_adapter": True}) is True
    monkeypatch.setenv("HCV_USE_SERVICE_RISK_ENGINE", "1")
    assert use_service_risk_engine_from_config({"use_service_adapter": False}) is True
    monkeypatch.setenv("HCV_USE_SERVICE_RISK_ENGINE", "0")
    assert use_service_risk_engine_from_config({"use_service_adapter": True}) is False
