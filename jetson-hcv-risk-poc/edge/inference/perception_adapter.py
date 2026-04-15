from __future__ import annotations

import math
import time
from dataclasses import dataclass
from typing import Any


@dataclass
class PerceptionSnapshot:
    nearest_object_m: float
    lane_departure_prob: float
    closure_rate_mps: float
    camera_alive: bool
    camera_age_sec: float | None

    def as_dict(self) -> dict[str, Any]:
        return {
            "nearest_object_m": round(self.nearest_object_m, 3),
            "lane_departure_prob": round(self.lane_departure_prob, 3),
            "closure_rate_mps": round(self.closure_rate_mps, 3),
            "camera_alive": self.camera_alive,
            "camera_age_sec": None if self.camera_age_sec is None else round(self.camera_age_sec, 3),
            "source": "mock_perception_adapter",
        }


class PerceptionAdapter:
    """Deterministic perception stub for demo scenarios.

    Produces smooth, repeatable values so the risk pipeline can be exercised
    before a full TensorRT/DeepStream perception model is integrated.
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        cfg = config or {}
        self._base_distance_m = float(cfg.get("base_distance_m", 20.0))
        self._distance_wave_m = float(cfg.get("distance_wave_m", 9.0))
        self._lane_wave = float(cfg.get("lane_wave", 0.55))
        self._closure_wave_mps = float(cfg.get("closure_wave_mps", 6.0))
        self._speedup = float(cfg.get("scenario_speed_multiplier", 1.0))
        self._t0 = time.monotonic()

    def next_snapshot(
        self,
        camera_alive: bool,
        camera_age_sec: float | None,
    ) -> PerceptionSnapshot:
        t = (time.monotonic() - self._t0) * self._speedup
        nearest = max(2.0, self._base_distance_m + self._distance_wave_m * math.sin(t / 7.0))
        lane_prob = max(0.0, min(1.0, 0.35 + self._lane_wave * (0.5 + 0.5 * math.sin(t / 5.5))))
        closure = max(0.0, self._closure_wave_mps * (0.5 + 0.5 * math.sin(t / 4.2)))
        return PerceptionSnapshot(
            nearest_object_m=nearest,
            lane_departure_prob=lane_prob,
            closure_rate_mps=closure,
            camera_alive=camera_alive,
            camera_age_sec=camera_age_sec,
        )
