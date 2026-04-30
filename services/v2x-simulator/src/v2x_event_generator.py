"""V2X event loading and context conversion utilities."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from v2x_models import V2XContextOutput, V2XEvent


def clamp_01(value: Any) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, parsed))


def load_v2x_event_from_file(path: Path) -> V2XEvent:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("V2X event JSON must be an object")
    return V2XEvent(
        event_id=str(raw.get("event_id") or raw.get("eventId") or ""),
        event_type=str(raw.get("event_type") or raw.get("eventType") or ""),
        source=str(raw.get("source") or "v2x-simulator"),
        timestamp=str(raw.get("timestamp") or ""),
        latitude_deg=_safe_float(raw.get("latitude_deg", raw.get("latitudeDeg"))),
        longitude_deg=_safe_float(raw.get("longitude_deg", raw.get("longitudeDeg"))),
        distance_m=_safe_float(raw.get("distance_m", raw.get("distanceM"))),
        confidence_01=clamp_01(raw.get("confidence_01", raw.get("confidence01"))),
        severity_01=clamp_01(raw.get("severity_01", raw.get("severity01"))),
        description=str(raw.get("description") or ""),
    )


def _safe_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def v2x_event_to_external_context(event: V2XEvent) -> V2XContextOutput:
    score = max(event.confidence_01, event.severity_01)
    t = event.event_type
    if t == "V2I_CURVE_WARNING":
        return V2XContextOutput(
            curve_ahead=True,
            infrastructure_risk_01=score,
            hazard_context_01=score,
            reason_codes=["v2x.v2i_curve_warning"],
        )
    if t == "V2V_HARD_BRAKE_AHEAD":
        return V2XContextOutput(hazard_context_01=score, reason_codes=["v2x.v2v_hard_brake_ahead"])
    if t == "V2N_WEATHER_ALERT":
        return V2XContextOutput(
            road_surface="wet",
            weather_risk_01=score,
            hazard_context_01=score,
            reason_codes=["v2x.v2n_weather_alert"],
        )
    if t == "V2I_WORK_ZONE":
        return V2XContextOutput(
            infrastructure_risk_01=score,
            hazard_context_01=score,
            reason_codes=["v2x.v2i_work_zone"],
        )
    if t == "V2P_VULNERABLE_USER_ZONE":
        return V2XContextOutput(hazard_context_01=score, reason_codes=["v2x.v2p_vulnerable_user_zone"])
    raise ValueError(f"Unsupported V2X event type: {t}")


def merge_contexts(base_context: dict[str, Any], v2x_context: V2XContextOutput) -> dict[str, Any]:
    merged = dict(base_context)
    vc = v2x_context.as_dict()

    for key in ("hazard_context_01", "weather_risk_01", "infrastructure_risk_01"):
        v = vc.get(key)
        if v is None:
            continue
        base = merged.get(key)
        if isinstance(base, (int, float)):
            merged[key] = max(float(base), float(v))
        else:
            merged[key] = float(v)

    if vc.get("curve_ahead") is True:
        merged["curve_ahead"] = True

    if vc.get("road_surface") is not None and not merged.get("road_surface"):
        merged["road_surface"] = vc["road_surface"]

    existing_codes = list(merged.get("reason_codes", []) or [])
    merged["reason_codes"] = existing_codes + vc.get("reason_codes", [])
    merged["v2x_reason_codes"] = vc.get("reason_codes", [])
    return merged
