from __future__ import annotations

import math
import time
from dataclasses import dataclass
from typing import Any


@dataclass
class ContextSnapshot:
    weather_risk: float
    traffic_risk: float
    road_risk: float
    provider: str = "mock_v2x_context"

    def as_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "weather_risk": round(self.weather_risk, 3),
            "traffic_risk": round(self.traffic_risk, 3),
            "road_risk": round(self.road_risk, 3),
        }


class MockContextProvider:
    """Synthetic context feed for Phase 1 demos."""

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        cfg = config or {}
        self._base_weather = float(cfg.get("base_weather_risk", 0.22))
        self._base_traffic = float(cfg.get("base_traffic_risk", 0.30))
        self._base_road = float(cfg.get("base_road_risk", 0.18))
        self._wave = float(cfg.get("risk_wave_amplitude", 0.20))
        self._speedup = float(cfg.get("scenario_speed_multiplier", 1.0))
        self._t0 = time.monotonic()

    @staticmethod
    def _clamp01(v: float) -> float:
        return max(0.0, min(1.0, v))

    def snapshot(self) -> ContextSnapshot:
        t = (time.monotonic() - self._t0) * self._speedup
        weather = self._clamp01(self._base_weather + self._wave * math.sin(t / 11.0))
        traffic = self._clamp01(self._base_traffic + self._wave * math.sin(t / 7.0 + 1.7))
        road = self._clamp01(self._base_road + self._wave * math.sin(t / 13.0 + 0.9))
        return ContextSnapshot(weather_risk=weather, traffic_risk=traffic, road_risk=road)
