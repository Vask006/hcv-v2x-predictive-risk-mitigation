from __future__ import annotations

from camera_models import CameraHealth, CameraSampleEvent, FrameSample


def test_frame_sample_fields() -> None:
    fs = FrameSample(
        wall_time_utc_iso="2026-01-01T00:00:00.000000Z",
        monotonic_s=1.5,
        width=640,
        height=480,
        backend="opencv",
    )
    assert fs.width == 640 and fs.height == 480
    assert fs.backend == "opencv"


def test_camera_sample_event_as_dict_shape() -> None:
    fs = FrameSample(
        wall_time_utc_iso="2026-01-01T00:00:00.000000Z",
        monotonic_s=2.0,
        width=1280,
        height=720,
        backend="opencv",
    )
    h = CameraHealth(opened=True, last_read_ok=True, consecutive_failures=0, last_error=None)
    ev = CameraSampleEvent(
        meta=fs,
        source_kind="live_index",
        healthy=True,
        health=h,
        extra={"device_id": "test"},
    )
    d = ev.as_dict()
    assert d["schema_version"] == "camera.sample.v1"
    assert d["source_kind"] == "live_index"
    assert d["healthy"] is True
    assert d["health"]["opened"] is True
    assert d["device_id"] == "test"
