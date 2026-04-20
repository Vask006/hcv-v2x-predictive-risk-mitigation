"""
Map legacy POC dict inputs → ``services/risk-engine`` typed models, then map
``RiskEventPayload`` back to ``RiskAssessment`` for ``edge_runtime``.

The legacy ``score_risk`` heuristic and the service rule engine use **different**
models; this adapter is a best-effort bridge for gradual unification. When the
service path errors, ``edge_runtime`` falls back to ``score_risk`` in ``scorer.py``.

**Import note:** the service lives in ``services/risk-engine/src/risk_engine.py``.
That file is loaded under a synthetic module name so it does not shadow the
edge package ``risk_engine`` on ``sys.path``.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

from .scorer import RiskAssessment

_SVC_ENGINE_MODULE = "_hcv_risk_engine_service_core"


def _risk_engine_src() -> Path | None:
    here = Path(__file__).resolve()
    for root in here.parents:
        cand = root / "services" / "risk-engine" / "src"
        if cand.is_dir() and (cand / "risk_engine.py").is_file():
            return cand
    return None


def _ensure_service_src_on_path() -> Path:
    src = _risk_engine_src()
    if src is None:
        raise RuntimeError(
            "services/risk-engine/src not found in parents of edge/risk_engine; "
            "clone the full monorepo on the device to use the service risk path."
        )
    s = str(src)
    if s not in sys.path:
        # Append so edge ``risk_engine`` package stays first on ``sys.path``.
        sys.path.append(s)
    return src


def _load_service_risk_engine_class() -> Any:
    src = _ensure_service_src_on_path()
    existing = sys.modules.get(_SVC_ENGINE_MODULE)
    if existing is not None:
        return existing.RiskEngine
    spec = importlib.util.spec_from_file_location(_SVC_ENGINE_MODULE, src / "risk_engine.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("importlib could not load services/risk-engine/src/risk_engine.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[_SVC_ENGINE_MODULE] = mod
    spec.loader.exec_module(mod)
    return mod.RiskEngine


def install_risk_engine_service_path() -> bool:
    """Return True if ``services/risk-engine/src`` exists (path appended for service imports)."""
    try:
        _ensure_service_src_on_path()
        return True
    except RuntimeError:
        return False


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, float(x)))


def risk_yaml_to_engine_config_kwargs(risk_cfg: dict[str, Any] | None) -> dict[str, Any]:
    """Map POC ``risk_engine.bands`` keys to ``RiskEngineConfig`` severity fields."""
    cfg = risk_cfg or {}
    out: dict[str, Any] = {}
    bands = cfg.get("bands") or {}
    mapping = (
        ("low", "severity_low"),
        ("medium", "severity_medium"),
        ("high", "severity_high"),
        ("critical", "severity_critical"),
    )
    for old_key, new_key in mapping:
        if old_key in bands:
            out[new_key] = float(bands[old_key])
    svc = cfg.get("service_engine") or {}
    if isinstance(svc, dict):
        for k, v in svc.items():
            if isinstance(v, (int, float, str, bool)) or v is None:
                out[k] = v
    return out


def legacy_dicts_to_edge_observations(
    gps: dict[str, Any],
    perception: dict[str, Any],
) -> Any:
    from risk_models import EdgeObservations

    wall = gps.get("wall_utc") or gps.get("wall_time_utc_iso")
    mono = gps.get("mono_s")
    if mono is None:
        mono = gps.get("monotonic_s")

    fq = gps.get("fix_quality")
    if fq is not None:
        try:
            fq_i = int(fq)
        except (TypeError, ValueError):
            fq_i = 0
    else:
        fq_i = 0

    lat = gps.get("latitude_deg")
    lon = gps.get("longitude_deg")
    try:
        lat_f = float(lat) if lat is not None else None
    except (TypeError, ValueError):
        lat_f = None
    try:
        lon_f = float(lon) if lon is not None else None
    except (TypeError, ValueError):
        lon_f = None

    spd = gps.get("speed_mps")
    if spd is None:
        spd = gps.get("gps_speed_mps")
    try:
        spd_f = float(spd) if spd is not None else None
    except (TypeError, ValueError):
        spd_f = None

    if spd_f is None:
        closure = float(perception.get("closure_rate_mps") or 0.0)
        if closure >= 4.0:
            spd_f = min(18.0, closure * 1.25)

    lane_dep = float(perception.get("lane_departure_prob") or 0.0)
    lane_stability_01 = _clamp01(1.0 - _clamp01(lane_dep))

    cam = perception.get("camera_alive")
    cam_ok: bool | None
    if isinstance(cam, bool):
        cam_ok = cam
    else:
        cam_ok = None

    mono_out: float | None
    try:
        mono_out = float(mono) if mono is not None else None
    except (TypeError, ValueError):
        mono_out = None

    wall_s = str(wall) if wall is not None else None

    return EdgeObservations(
        gps_speed_mps=spd_f,
        gps_fix_quality=fq_i,
        latitude_deg=lat_f,
        longitude_deg=lon_f,
        wall_time_utc_iso=wall_s,
        monotonic_s=mono_out,
        lane_stability_01=lane_stability_01,
        camera_healthy=cam_ok,
    )


def legacy_dicts_to_external_context(context: dict[str, Any]) -> Any:
    from risk_models import ExternalContext

    w = float(context.get("weather_risk") or 0.0)
    t = float(context.get("traffic_risk") or 0.0)
    r = float(context.get("road_risk") or 0.0)
    mean_ctx = (w + t + r) / 3.0 if (w or t or r) else 0.0
    mean_ctx = _clamp01(mean_ctx)

    curve_ahead = mean_ctx >= 0.48
    road_surface: Any = "wet" if w >= 0.58 else "unknown"

    return ExternalContext(
        curve_ahead=curve_ahead,
        road_surface=road_surface,
        hazard_context_01=mean_ctx,
        weather_risk_01=_clamp01(w),
        infrastructure_risk_01=_clamp01((t + r) / 2.0) if (t or r) else None,
    )


def _warnings_from_severity(severity: str) -> list[str]:
    warnings: list[str] = []
    if severity in ("medium", "high", "critical"):
        warnings.append("driver.caution")
    if severity in ("high", "critical"):
        warnings.append("driver.slow_down")
    if severity == "critical":
        warnings.append("driver.immediate_attention")
    return warnings


def risk_payload_to_assessment(payload: Any) -> RiskAssessment:
    ra = payload.risk_assessment
    sev = str(ra.severity)
    fleet = bool(payload.mitigation.fleet_notification)
    return RiskAssessment(
        score=float(ra.risk_score),
        band=sev,
        reason_codes=list(payload.reason_codes),
        warnings=_warnings_from_severity(sev),
        fleet_alert=fleet,
    )


def score_risk_via_service_engine(
    gps: dict[str, Any],
    perception: dict[str, Any],
    context: dict[str, Any],
    risk_cfg: dict[str, Any] | None = None,
    *,
    vehicle_id: str = "edge-runtime",
) -> RiskAssessment:
    """
    Run ``services/risk-engine`` on legacy-shaped dicts.

    Raises ``RuntimeError`` on missing monorepo layout or load/assess failures.
    """
    RiskEngine = _load_service_risk_engine_class()
    edge = legacy_dicts_to_edge_observations(gps, perception)
    ext = legacy_dicts_to_external_context(context)
    kwargs = risk_yaml_to_engine_config_kwargs(risk_cfg)
    engine = RiskEngine(kwargs if kwargs else None)
    payload = engine.assess(vehicle_id=vehicle_id, trip_id=None, edge=edge, context=ext)
    return risk_payload_to_assessment(payload)


def use_service_risk_engine_from_config(risk_cfg: dict[str, Any] | None) -> bool:
    """True when env ``HCV_USE_SERVICE_RISK_ENGINE`` is affirmative or YAML ``use_service_adapter: true``."""
    import os

    raw = os.environ.get("HCV_USE_SERVICE_RISK_ENGINE", "").strip().lower()
    if raw in ("1", "true", "yes", "on"):
        return True
    if raw in ("0", "false", "no", "off"):
        return False
    cfg = risk_cfg or {}
    return bool(cfg.get("use_service_adapter", False))
