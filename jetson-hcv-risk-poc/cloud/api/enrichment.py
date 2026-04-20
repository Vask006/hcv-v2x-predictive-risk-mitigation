from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any


def _as_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc)
    if isinstance(value, str):
        txt = value.replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(txt).astimezone(timezone.utc)
        except ValueError:
            pass
    return datetime.now(timezone.utc)


def build_mock_context(recorded_at: Any, lat: float, lon: float) -> dict[str, Any]:
    dt = _as_datetime(recorded_at)
    tod = dt.hour + dt.minute / 60.0
    traffic = max(0.0, min(1.0, 0.25 + 0.35 * math.sin((tod / 24.0) * 2.0 * math.pi)))
    weather = max(0.0, min(1.0, 0.20 + 0.25 * math.cos((lat + lon) / 50.0)))
    road = max(0.0, min(1.0, 0.15 + 0.20 * math.sin((lat - lon) / 40.0)))
    return {
        "provider": "cloud_mock_context",
        "traffic_risk": round(traffic, 3),
        "weather_risk": round(weather, 3),
        "road_risk": round(road, 3),
    }
