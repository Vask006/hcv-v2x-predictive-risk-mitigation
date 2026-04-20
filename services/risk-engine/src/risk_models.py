"""Phase 1 typed inputs and risk event payload (analytics-shaped, not ``event_v1``)."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

RoadSurface = Literal["dry", "wet", "unknown"]


@dataclass
class EdgeObservations:
    """Normalized edge signals (partial OK). Maps from ``GpsSampleEvent`` / camera / JSONL rows."""

    gps_speed_mps: float | None = None
    gps_fix_quality: int | None = None
    latitude_deg: float | None = None
    longitude_deg: float | None = None
    wall_time_utc_iso: str | None = None
    monotonic_s: float | None = None
    # 1.0 = stable lane / low instability proxy; None = not provided.
    lane_stability_01: float | None = None
    camera_healthy: bool | None = None


@dataclass
class ExternalContext:
    """Route / weather / infrastructure hints (all optional)."""

    curve_ahead: bool | None = None
    road_surface: RoadSurface | None = None
    # 0..1 aggregate hazard from map/V2X/mock; None = not provided.
    hazard_context_01: float | None = None
    weather_risk_01: float | None = None
    infrastructure_risk_01: float | None = None


@dataclass
class RiskEngineConfig:
    """Tunable Phase 1 thresholds (transparent defaults)."""

    # Speed above this (m/s) counts as "high" for compound environmental rule (~90 km/h).
    high_speed_mps: float = 25.0
    # Below this lane_stability is "reduced" for rule R2.
    lane_stability_reduced_below: float = 0.55
    # Above this hazard_context contributes to R2.
    hazard_context_elevated_above: float = 0.40
    # Band edges for severity (same spirit as POC ``risk_engine.bands``).
    severity_low: float = 0.20
    severity_medium: float = 0.45
    severity_high: float = 0.70
    severity_critical: float = 0.85
    # Rule weights (applied to [0,1] subscores then summed, capped at 1.0).
    weight_rule_speed_curve_wet: float = 0.28
    weight_rule_lane_hazard: float = 0.24
    weight_context_mean: float = 0.22
    weight_gps_signal: float = 0.14
    weight_camera_signal: float = 0.12


@dataclass
class RiskAssessmentBlock:
    risk_score: float
    severity: str  # none | low | medium | high | critical
    hazard_type: str


@dataclass
class MitigationBlock:
    driver_alert: str | None
    fleet_notification: bool
    recommended_action: str


@dataclass
class RiskEventPayload:
    event_id: str
    vehicle_id: str
    trip_id: str | None
    timestamp: str
    edge_observations: dict[str, Any]
    external_context: dict[str, Any]
    risk_assessment: RiskAssessmentBlock
    mitigation: MitigationBlock
    reason_codes: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "eventId": self.event_id,
            "vehicleId": self.vehicle_id,
            "tripId": self.trip_id,
            "timestamp": self.timestamp,
            "edgeObservations": self.edge_observations,
            "externalContext": self.external_context,
            "riskAssessment": {
                "riskScore": round(self.risk_assessment.risk_score, 4),
                "severity": self.risk_assessment.severity,
                "hazardType": self.risk_assessment.hazard_type,
            },
            "mitigation": {
                "driverAlert": self.mitigation.driver_alert,
                "fleetNotification": self.mitigation.fleet_notification,
                "recommendedAction": self.mitigation.recommended_action,
            },
            "reasonCodes": self.reason_codes,
        }


def edge_observations_as_dict(o: EdgeObservations) -> dict[str, Any]:
    return {k: v for k, v in asdict(o).items() if v is not None}


def external_context_as_dict(c: ExternalContext) -> dict[str, Any]:
    return {k: v for k, v in asdict(c).items() if v is not None}
