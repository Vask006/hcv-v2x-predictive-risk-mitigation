from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class RiskAssessment:
    score: float
    band: str
    reason_codes: list[str]
    warnings: list[str]
    fleet_alert: bool

    def as_event_risk(self) -> dict[str, Any]:
        return {
            "score": round(self.score, 4),
            "band": self.band,
            "reason_codes": self.reason_codes,
        }

    def as_mitigation(self) -> dict[str, Any]:
        return {
            "warnings": self.warnings,
            "fleet_alert": self.fleet_alert,
        }


_BANDS = ("none", "low", "medium", "high", "critical")


def band_rank(band: str) -> int:
    return _BANDS.index(band) if band in _BANDS else 0


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _band_from_score(score: float, thresholds: dict[str, float]) -> str:
    if score >= float(thresholds.get("critical", 0.85)):
        return "critical"
    if score >= float(thresholds.get("high", 0.70)):
        return "high"
    if score >= float(thresholds.get("medium", 0.45)):
        return "medium"
    if score >= float(thresholds.get("low", 0.20)):
        return "low"
    return "none"


def score_risk(
    gps: dict[str, Any],
    perception: dict[str, Any],
    context: dict[str, Any],
    config: dict[str, Any] | None = None,
) -> RiskAssessment:
    cfg = config or {}
    reason_codes: list[str] = []

    weights = cfg.get(
        "weights",
        {
            "proximity": 0.35,
            "lane_departure": 0.20,
            "closure_rate": 0.20,
            "context": 0.20,
            "gps_penalty": 0.05,
        },
    )
    thresholds = cfg.get(
        "bands",
        {"low": 0.20, "medium": 0.45, "high": 0.70, "critical": 0.85},
    )

    nearest_object_m = float(perception.get("nearest_object_m", 999.0))
    lane_departure_prob = _clamp01(float(perception.get("lane_departure_prob", 0.0)))
    closure_rate_mps = max(0.0, float(perception.get("closure_rate_mps", 0.0)))
    context_risk = _clamp01(
        (
            float(context.get("weather_risk", 0.0))
            + float(context.get("traffic_risk", 0.0))
            + float(context.get("road_risk", 0.0))
        )
        / 3.0
    )

    proximity_score = _clamp01((30.0 - nearest_object_m) / 28.0)
    closure_score = _clamp01(closure_rate_mps / 10.0)
    gps_quality = int(gps.get("fix_quality") or 0)
    gps_penalty = 0.0 if gps_quality > 0 else 1.0

    if nearest_object_m < 15.0:
        reason_codes.append("perception.nearest_object_close")
    if lane_departure_prob >= 0.55:
        reason_codes.append("perception.lane_departure_risk")
    if closure_rate_mps >= 4.5:
        reason_codes.append("perception.closure_rate_high")
    if context_risk >= 0.45:
        reason_codes.append("context.environment_risk")
    if gps_penalty > 0.0:
        reason_codes.append("gps.no_fix_quality")

    score = (
        float(weights.get("proximity", 0.35)) * proximity_score
        + float(weights.get("lane_departure", 0.20)) * lane_departure_prob
        + float(weights.get("closure_rate", 0.20)) * closure_score
        + float(weights.get("context", 0.20)) * context_risk
        + float(weights.get("gps_penalty", 0.05)) * gps_penalty
    )
    score = _clamp01(score)
    band = _band_from_score(score, thresholds)

    warnings: list[str] = []
    if band in ("medium", "high", "critical"):
        warnings.append("driver.caution")
    if band in ("high", "critical"):
        warnings.append("driver.slow_down")
    if band == "critical":
        warnings.append("driver.immediate_attention")

    return RiskAssessment(
        score=score,
        band=band,
        reason_codes=reason_codes,
        warnings=warnings,
        fleet_alert=band in ("high", "critical"),
    )
