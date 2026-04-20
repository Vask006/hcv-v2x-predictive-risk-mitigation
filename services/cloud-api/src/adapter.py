"""
Map ``services/pipeline`` combined output (camelCase ``riskEvent``) → POC ``EventV1`` JSON (snake_case).

The FastAPI app in ``jetson-hcv-risk-poc/cloud/api`` validates bodies with ``schemas.EventV1``;
it does **not** accept the pipeline's analytics shape unchanged — use this adapter on the client
before ``POST /v1/events``.

See ``services/cloud-api/README.md`` for field-level mismatches.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

_RISK_BANDS = frozenset({"none", "low", "medium", "high", "critical"})


def _band(severity: str | None) -> str:
    s = (severity or "none").strip().lower()
    return s if s in _RISK_BANDS else "none"


def _parse_event_id(raw: str | None, reasons: list[str]) -> UUID:
    if not raw:
        reasons.append("adapter.missing_event_id")
        return uuid4()
    try:
        return UUID(str(raw))
    except ValueError:
        reasons.append("adapter.invalid_event_id_regenerated")
        return uuid4()


def _recorded_at(ts: str | None) -> datetime:
    if not ts:
        return datetime.now(timezone.utc)
    t = ts.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(t)
    except ValueError:
        return datetime.now(timezone.utc)


def combined_pipeline_to_event_v1(combined: dict[str, Any]) -> dict[str, Any]:
    """
    Build a dict suitable as JSON body for ``POST .../v1/events`` on the existing POC API.

    Expects ``combined`` like ``EventPipeline.run_once()`` output (``riskEvent`` + optional ``inputsEcho``).
    """
    risk = combined.get("riskEvent") or combined
    if not isinstance(risk, dict):
        raise TypeError("combined['riskEvent'] must be a dict")

    reasons_out: list[str] = list(risk.get("reasonCodes") or [])
    eid = _parse_event_id(risk.get("eventId"), reasons_out)

    edge = risk.get("edgeObservations") or {}
    if not isinstance(edge, dict):
        edge = {}

    lat = edge.get("latitude_deg")
    lon = edge.get("longitude_deg")
    if lat is None:
        reasons_out.append("adapter.gps_latitude_defaulted")
        lat = 0.0
    if lon is None:
        reasons_out.append("adapter.gps_longitude_defaulted")
        lon = 0.0

    ra = risk.get("riskAssessment") or {}
    score = float(ra.get("riskScore") or 0.0)
    score = max(0.0, min(1.0, score))

    mit = risk.get("mitigation") or {}
    ext = risk.get("externalContext") or {}

    perception_summary: dict[str, Any] = {
        "pipeline_version": combined.get("pipelineVersion"),
        "trip_id": risk.get("tripId"),
        "hazard_type": ra.get("hazardType"),
        "mitigation": mit,
        "external_context": ext,
        "edge_observations": edge,
        "adapter": "services/cloud-api/src/adapter.py",
    }
    if "inputsEcho" in combined:
        perception_summary["inputs_echo"] = combined["inputsEcho"]

    return {
        "schema_version": "1.0",
        "event_id": str(eid),
        "device_id": str(risk.get("vehicleId") or "unknown"),
        "recorded_at": _recorded_at(risk.get("timestamp")).isoformat(),
        "gps": {
            "latitude_deg": float(lat),
            "longitude_deg": float(lon),
            "altitude_m": None,
            "speed_mps": edge.get("gps_speed_mps"),
            "course_deg": None,
            "fix_quality": edge.get("gps_fix_quality"),
            "hdop": None,
            "satellites": None,
        },
        "risk": {
            "score": round(score, 4),
            "band": _band(ra.get("severity")),
            "reason_codes": reasons_out,
        },
        "perception_summary": perception_summary,
        "media": {"thumbnail_uri": None, "clip_uri": None},
    }
