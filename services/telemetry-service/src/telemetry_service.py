"""Service wrapper for telemetry normalization."""

from __future__ import annotations

from typing import Any

from telemetry_models import NormalizedTelemetryEvent
from telemetry_normalizer import normalize_telemetry


class TelemetryService:
    """Normalize mixed sensor payloads into a stable telemetry event contract."""

    def normalize(
        self,
        vehicle_id: str,
        trip_id: str | None = None,
        gps: dict[str, Any] | None = None,
        camera: dict[str, Any] | None = None,
        vehicle_state: dict[str, Any] | None = None,
        timestamp: str | None = None,
    ) -> NormalizedTelemetryEvent:
        return normalize_telemetry(
            vehicle_id=vehicle_id,
            trip_id=trip_id,
            gps=gps,
            camera=camera,
            vehicle_state=vehicle_state,
            timestamp=timestamp,
        )
