from __future__ import annotations

from risk_engine import RiskEngine
from risk_models import EdgeObservations, ExternalContext, RiskEngineConfig
from risk_rules import combine_score, compute_subscores, severity_from_score


def test_r1_wet_curve_high_speed() -> None:
    edge = EdgeObservations(gps_speed_mps=28.0, lane_stability_01=0.9, gps_fix_quality=1)
    ctx = ExternalContext(curve_ahead=True, road_surface="wet")
    cfg = RiskEngineConfig()
    s = compute_subscores(edge, ctx, cfg)
    assert s.rule_speed_curve_surface == 1.0
    assert "rule.speed_curve_wet" in s.reasons
    score = combine_score(s, cfg)
    assert score >= cfg.weight_rule_speed_curve_wet * 0.99
    assert severity_from_score(score, cfg) in ("low", "medium", "high", "critical")


def test_r1b_curve_high_speed_not_wet() -> None:
    edge = EdgeObservations(gps_speed_mps=28.0, gps_fix_quality=1)
    ctx = ExternalContext(curve_ahead=True, road_surface="unknown")
    cfg = RiskEngineConfig()
    s = compute_subscores(edge, ctx, cfg)
    assert abs(s.rule_speed_curve_surface - 0.55) < 1e-6
    assert "rule.speed_curve_no_confirmed_wet" in s.reasons


def test_r2_lane_instability_and_hazard() -> None:
    edge = EdgeObservations(
        lane_stability_01=0.35,
        gps_speed_mps=10.0,
        gps_fix_quality=1,
        latitude_deg=48.0,
        longitude_deg=11.0,
    )
    ctx = ExternalContext(hazard_context_01=0.8)
    cfg = RiskEngineConfig()
    s = compute_subscores(edge, ctx, cfg)
    assert s.rule_lane_hazard > 0.18
    assert "rule.lane_instability_hazard" in s.reasons


def test_partial_inputs_neutral() -> None:
    edge = EdgeObservations()
    ctx = ExternalContext()
    cfg = RiskEngineConfig()
    s = compute_subscores(edge, ctx, cfg)
    score = combine_score(s, cfg)
    assert score < cfg.severity_low


def test_gps_penalty_no_position() -> None:
    edge = EdgeObservations(gps_speed_mps=5.0, gps_fix_quality=0)
    ctx = ExternalContext()
    cfg = RiskEngineConfig()
    s = compute_subscores(edge, ctx, cfg)
    assert s.gps_signal > 0
    assert "penalty.gps_fix_void" in s.reasons


def test_risk_engine_payload_keys() -> None:
    eng = RiskEngine()
    out = eng.assess(
        vehicle_id="veh-1",
        trip_id="trip-9",
        edge=EdgeObservations(
            wall_time_utc_iso="2026-04-19T10:00:00.000000Z",
            gps_speed_mps=26.0,
            lane_stability_01=0.5,
            gps_fix_quality=1,
            latitude_deg=1.0,
            longitude_deg=2.0,
        ),
        context=ExternalContext(curve_ahead=True, road_surface="wet", hazard_context_01=0.5),
        event_id="00000000-0000-4000-8000-000000000001",
    )
    d = out.as_dict()
    assert d["eventId"] == "00000000-0000-4000-8000-000000000001"
    assert d["vehicleId"] == "veh-1"
    assert d["tripId"] == "trip-9"
    assert "riskAssessment" in d and "mitigation" in d
    assert d["riskAssessment"]["hazardType"] in (
        "speed_curve_surface",
        "speed_curve_environment",
        "lane_hazard_compound",
        "degraded_edge_sensing",
        "ambient_context",
        "nominal",
    )
