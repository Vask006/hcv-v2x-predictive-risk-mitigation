"""
Phase 1 rule-based scoring — no ML.

Documented assumptions
----------------------
1. **Scale**: All internal contributing terms are clipped to ``[0, 1]`` before weights apply.
2. **Missing data**: A missing observation does **not** increase risk for rules that require it.
   Optional fields use ``None``; boolean ``curve_ahead`` only counts as true when explicitly ``True``.
3. **GPS speed**: Interpreted as **m/s** when provided (aligned with ``GpsFix.speed_mps`` from gps-service).
4. **Lane stability**: ``lane_stability_01`` is **1 = stable** (low instability). Lower values imply more instability.
5. **Road surface**: Only the literal ``\"wet\"`` triggers the wet leg of R1; ``unknown`` / ``None`` does not.
6. **Hazard / weather / infrastructure**: Each is an optional scalar in ``[0, 1]`` when present; we use the
   mean of **provided** scalars only (no penalty for omitted context).
7. **GPS fix**: ``fix_quality`` 0 or absent with absent lat/lon applies a **small** missing-signal penalty
   (bounded) so noisy receivers do not dominate the score.
8. **Camera**: ``camera_healthy is False`` adds a small bounded penalty; ``None`` means unknown (no penalty).

Rules (default)
---------------
**R1 — speed + curve + wet**: If ``gps_speed_mps >= high_speed_mps`` AND ``curve_ahead is True`` AND
``road_surface == \"wet\"``, add weighted contribution ``weight_rule_speed_curve_wet`` (full strength).

**R1b — speed + curve (no wet confirmation)**: If speed high and ``curve_ahead is True`` but surface is not
``wet`` (dry or unknown), add **half** of the R1 weight (still explainable; avoids over-penalizing unknown wet).

**R2 — lane instability + hazard context**: If ``lane_stability_01`` is known and below
``lane_stability_reduced_below`` AND ``hazard_context_01`` is known and above
``hazard_context_elevated_above``, add ``weight_rule_lane_hazard``.

**R3 — ambient context mean**: Mean of provided ``hazard_context_01``, ``weather_risk_01``,
``infrastructure_risk_01`` times ``weight_context_mean``.

Penalties are folded into subscores ``gps_signal`` and ``camera_signal`` (see ``compute_subscores``).
"""
from __future__ import annotations

from dataclasses import dataclass

from risk_models import EdgeObservations, ExternalContext, RiskEngineConfig


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


@dataclass
class SubScores:
    rule_speed_curve_surface: float
    rule_lane_hazard: float
    context_mean: float
    gps_signal: float
    camera_signal: float
    reasons: list[str]


def compute_subscores(
    edge: EdgeObservations,
    ctx: ExternalContext,
    cfg: RiskEngineConfig,
) -> SubScores:
    reasons: list[str] = []

    # --- R1 / R1b: speed + curve (+ wet) ---
    r1 = 0.0
    spd = edge.gps_speed_mps
    high_speed = spd is not None and spd >= cfg.high_speed_mps
    curve = ctx.curve_ahead is True
    wet = ctx.road_surface == "wet"
    if high_speed and curve and wet:
        r1 = 1.0
        reasons.append("rule.speed_curve_wet")
    elif high_speed and curve and ctx.road_surface != "wet":
        r1 = 0.55
        reasons.append("rule.speed_curve_no_confirmed_wet")

    # --- R2: lane stability + hazard ---
    r2 = 0.0
    if (
        edge.lane_stability_01 is not None
        and ctx.hazard_context_01 is not None
        and edge.lane_stability_01 < cfg.lane_stability_reduced_below
        and ctx.hazard_context_01 > cfg.hazard_context_elevated_above
    ):
        r2 = _clamp01(
            (cfg.lane_stability_reduced_below - edge.lane_stability_01)
            / max(cfg.lane_stability_reduced_below, 1e-6)
        ) * _clamp01((ctx.hazard_context_01 - cfg.hazard_context_elevated_above) / max(1.0 - cfg.hazard_context_elevated_above, 1e-6))
        reasons.append("rule.lane_instability_hazard")

    # --- R3: mean context risks (only keys that are not None) ---
    ctx_vals = [v for v in (ctx.hazard_context_01, ctx.weather_risk_01, ctx.infrastructure_risk_01) if v is not None]
    ctx_mean = sum(_clamp01(v) for v in ctx_vals) / len(ctx_vals) if ctx_vals else 0.0

    # --- GPS signal quality (small penalty only when clearly bad / missing position) ---
    gps_penalty = 0.0
    if edge.gps_fix_quality is not None and edge.gps_fix_quality <= 0:
        gps_penalty = 0.35
        reasons.append("penalty.gps_fix_void")
    if edge.latitude_deg is None or edge.longitude_deg is None:
        gps_penalty = max(gps_penalty, 0.25)
        reasons.append("penalty.gps_position_missing")

    # --- Camera healthy ---
    cam_penalty = 0.0
    if edge.camera_healthy is False:
        cam_penalty = 0.35
        reasons.append("penalty.camera_unhealthy")

    return SubScores(
        rule_speed_curve_surface=_clamp01(r1),
        rule_lane_hazard=_clamp01(r2),
        context_mean=_clamp01(ctx_mean),
        gps_signal=_clamp01(gps_penalty),
        camera_signal=_clamp01(cam_penalty),
        reasons=reasons,
    )


def combine_score(s: SubScores, cfg: RiskEngineConfig) -> float:
    total = (
        cfg.weight_rule_speed_curve_wet * s.rule_speed_curve_surface
        + cfg.weight_rule_lane_hazard * s.rule_lane_hazard
        + cfg.weight_context_mean * s.context_mean
        + cfg.weight_gps_signal * s.gps_signal
        + cfg.weight_camera_signal * s.camera_signal
    )
    return _clamp01(total)


def severity_from_score(score: float, cfg: RiskEngineConfig) -> str:
    if score >= cfg.severity_critical:
        return "critical"
    if score >= cfg.severity_high:
        return "high"
    if score >= cfg.severity_medium:
        return "medium"
    if score >= cfg.severity_low:
        return "low"
    return "none"


def hazard_type_from_subscores(s: SubScores) -> str:
    """Single label for dashboards; priority order is explicit."""
    if s.rule_speed_curve_surface >= 0.99:
        return "speed_curve_surface"
    if s.rule_speed_curve_surface >= 0.45:
        return "speed_curve_environment"
    if s.rule_lane_hazard >= 0.35:
        return "lane_hazard_compound"
    if s.gps_signal >= 0.3 or s.camera_signal >= 0.3:
        return "degraded_edge_sensing"
    if s.context_mean > 0.35:
        return "ambient_context"
    return "nominal"


def mitigation_from_severity(severity: str) -> tuple[str | None, bool, str]:
    if severity in ("critical", "high"):
        return (
            "Elevated risk — reduce speed and increase following distance.",
            True,
            "Fleet: review trip segment and road context within 15 minutes.",
        )
    if severity == "medium":
        return ("Caution advised — monitor road and lane position.", False, "Log segment; no immediate fleet action.")
    return (None, False, "Continue monitoring; maintain normal vigilance.")
