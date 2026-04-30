"""V2X simulation event and context models."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class V2XEvent:
    event_id: str
    event_type: str
    source: str
    timestamp: str
    latitude_deg: float | None
    longitude_deg: float | None
    distance_m: float | None
    confidence_01: float
    severity_01: float
    description: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class V2XContextOutput:
    curve_ahead: bool | None = None
    road_surface: str | None = None
    hazard_context_01: float | None = None
    weather_risk_01: float | None = None
    infrastructure_risk_01: float | None = None
    reason_codes: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)
