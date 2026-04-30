"""Deterministic camera-derived proxy analytics for local demo use."""

from __future__ import annotations

from typing import Any


def _clamp_01(value: float) -> float:
    return max(0.0, min(1.0, value))


def brightness_score_01(frame: Any) -> float | None:
    if frame is None:
        return None
    try:
        import cv2  # type: ignore
        import numpy as np  # type: ignore

        if not hasattr(frame, "shape"):
            return None
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if len(frame.shape) == 3 else frame
        avg = float(np.mean(gray))
        return _clamp_01(avg / 255.0)
    except Exception:
        return None


def blur_risk_01(frame: Any) -> float | None:
    if frame is None:
        return None
    try:
        import cv2  # type: ignore

        if not hasattr(frame, "shape"):
            return None
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if len(frame.shape) == 3 else frame
        variance = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        # Higher variance => sharper frame => lower risk.
        risk = 1.0 - _clamp_01(variance / 500.0)
        return _clamp_01(risk)
    except Exception:
        return None


def derive_lane_stability_proxy(
    camera_healthy: bool | None,
    blur_risk_01_value: float | None,
    brightness_score_01_value: float | None,
) -> float | None:
    if camera_healthy is None:
        return None
    if camera_healthy is False:
        return 0.40
    score = 0.88
    if blur_risk_01_value is not None:
        score -= 0.25 * _clamp_01(blur_risk_01_value)
    if brightness_score_01_value is not None and brightness_score_01_value < 0.2:
        score -= 0.15
    return _clamp_01(score)


def derive_object_risk_proxy(camera_healthy: bool | None) -> float | None:
    if camera_healthy is None:
        return None
    return 0.0 if camera_healthy else 0.25
