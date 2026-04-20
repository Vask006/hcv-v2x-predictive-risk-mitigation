"""Phase 1 risk engine: normalized edge + context → ``RiskEventPayload``."""
from __future__ import annotations

from dataclasses import fields
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from risk_models import (
    EdgeObservations,
    ExternalContext,
    MitigationBlock,
    RiskAssessmentBlock,
    RiskEngineConfig,
    RiskEventPayload,
    edge_observations_as_dict,
    external_context_as_dict,
)
from risk_rules import (
    combine_score,
    compute_subscores,
    hazard_type_from_subscores,
    mitigation_from_severity,
    severity_from_score,
)


def _utc_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


class RiskEngine:
    """Rule-only assessment; thread-safe if each call uses fresh inputs (no mutable state)."""

    def __init__(self, config: RiskEngineConfig | dict[str, Any] | None = None) -> None:
        if config is None:
            self._cfg = RiskEngineConfig()
        elif isinstance(config, RiskEngineConfig):
            self._cfg = config
        else:
            allowed = {f.name for f in fields(RiskEngineConfig)}
            self._cfg = RiskEngineConfig(**{k: v for k, v in config.items() if k in allowed})

    @property
    def config(self) -> RiskEngineConfig:
        return self._cfg

    def assess(
        self,
        *,
        vehicle_id: str,
        trip_id: str | None,
        edge: EdgeObservations,
        context: ExternalContext,
        event_id: str | None = None,
        timestamp: str | None = None,
    ) -> RiskEventPayload:
        subs = compute_subscores(edge, context, self._cfg)
        score = combine_score(subs, self._cfg)
        sev = severity_from_score(score, self._cfg)
        hazard = hazard_type_from_subscores(subs)
        alert, fleet, action = mitigation_from_severity(sev)

        ts = timestamp or edge.wall_time_utc_iso or _utc_iso()
        eid = event_id or str(uuid4())

        return RiskEventPayload(
            event_id=eid,
            vehicle_id=vehicle_id,
            trip_id=trip_id,
            timestamp=ts,
            edge_observations=edge_observations_as_dict(edge),
            external_context=external_context_as_dict(context),
            risk_assessment=RiskAssessmentBlock(risk_score=score, severity=sev, hazard_type=hazard),
            mitigation=MitigationBlock(driver_alert=alert, fleet_notification=fleet, recommended_action=action),
            reason_codes=subs.reasons,
        )
