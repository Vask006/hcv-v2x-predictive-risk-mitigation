from __future__ import annotations

import numpy as np

from camera_analytics import (
    brightness_score_01,
    derive_lane_stability_proxy,
    derive_object_risk_proxy,
)


def test_brightness_high_frame() -> None:
    frame = np.full((10, 10, 3), 250, dtype=np.uint8)
    val = brightness_score_01(frame)
    assert val is not None and val > 0.9


def test_brightness_low_frame() -> None:
    frame = np.zeros((10, 10, 3), dtype=np.uint8)
    val = brightness_score_01(frame)
    assert val is not None and val < 0.1


def test_brightness_invalid_frame() -> None:
    assert brightness_score_01(None) is None
    assert brightness_score_01("bad") is None


def test_lane_stability_healthy() -> None:
    score = derive_lane_stability_proxy(True, 0.1, 0.9)
    assert score is not None and score > 0.7


def test_lane_stability_unhealthy() -> None:
    assert derive_lane_stability_proxy(False, 0.1, 0.9) == 0.40


def test_object_risk_proxy() -> None:
    assert derive_object_risk_proxy(True) == 0.0
    assert derive_object_risk_proxy(False) == 0.25
