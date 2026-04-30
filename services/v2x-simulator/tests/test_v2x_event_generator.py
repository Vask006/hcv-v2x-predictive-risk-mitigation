from __future__ import annotations

from pathlib import Path

import pytest

from v2x_event_generator import clamp_01, load_v2x_event_from_file, merge_contexts, v2x_event_to_external_context
from v2x_models import V2XEvent


def _example(name: str) -> Path:
    return Path(__file__).resolve().parents[1] / "examples" / name


def test_load_json_event() -> None:
    ev = load_v2x_event_from_file(_example("v2i_curve_warning.json"))
    assert ev.event_type == "V2I_CURVE_WARNING"
    assert ev.confidence_01 > 0


def test_event_mappings() -> None:
    cases = [
        ("V2I_CURVE_WARNING", "v2x.v2i_curve_warning"),
        ("V2V_HARD_BRAKE_AHEAD", "v2x.v2v_hard_brake_ahead"),
        ("V2N_WEATHER_ALERT", "v2x.v2n_weather_alert"),
        ("V2I_WORK_ZONE", "v2x.v2i_work_zone"),
        ("V2P_VULNERABLE_USER_ZONE", "v2x.v2p_vulnerable_user_zone"),
    ]
    for event_type, code in cases:
        ctx = v2x_event_to_external_context(
            V2XEvent("e1", event_type, "sim", "2026-01-01T00:00:00Z", None, None, None, 0.6, 0.7, "")
        )
        assert code in ctx.reason_codes


def test_merge_contexts_uses_max() -> None:
    base = {"hazard_context_01": 0.2, "reason_codes": ["base"]}
    v2x_ctx = v2x_event_to_external_context(
        V2XEvent("e1", "V2V_HARD_BRAKE_AHEAD", "sim", "2026-01-01T00:00:00Z", None, None, None, 0.9, 0.8, "")
    )
    merged = merge_contexts(base, v2x_ctx)
    assert merged["hazard_context_01"] == 0.9
    assert "base" in merged["reason_codes"]
    assert "v2x.v2v_hard_brake_ahead" in merged["reason_codes"]


def test_clamp_behavior() -> None:
    assert clamp_01(5) == 1.0
    assert clamp_01(-2) == 0.0
    assert clamp_01("bad") == 0.0


def test_unknown_event_type_raises() -> None:
    with pytest.raises(ValueError):
        v2x_event_to_external_context(
            V2XEvent("e1", "UNKNOWN", "sim", "2026-01-01T00:00:00Z", None, None, None, 0.1, 0.2, "")
        )
