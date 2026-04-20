from __future__ import annotations

from gps_models import GpsFix, GpsSampleEvent
from gps_reader import parse_line


def test_gps_sample_event_mock_dict() -> None:
    fix = GpsFix(
        wall_time_utc_iso="2026-01-01T00:00:00.000000Z",
        monotonic_s=1.0,
        raw_sentence="$HCVMOCK,BENCH_SYNTHETIC,NO_SERIAL,i=0*",
        latitude_deg=0.0,
        longitude_deg=0.0,
        fix_quality=1,
        speed_mps=None,
        course_deg=None,
    )
    ev = GpsSampleEvent(fix=fix, source="mock", validity="valid")
    d = ev.as_dict()
    assert d["schema_version"] == "gps.sample.v1"
    assert d["source"] == "mock"
    assert d["validity"] == "valid"
    assert "speed_mps" not in d
    assert "course_deg" not in d


def test_rmc_speed_course_parsed() -> None:
    line = "$GPRMC,123519,A,4807.038,N,01131.000,E,022.4,084.4,230394,003.1,W*"
    f = parse_line(line, "2026-01-01T00:00:00.000000Z", 1.0)
    assert f is not None
    assert f.speed_mps is not None and f.speed_mps > 10.0
    assert f.course_deg is not None and abs(f.course_deg - 84.4) < 0.01


def test_gga_no_speed() -> None:
    line = "$GPGGA,123519,4807.038,N,01131.000,E,1,08,0.9,545.4,M,46.9,M,,*"
    f = parse_line(line, "2026-01-01T00:00:00.000000Z", 1.0)
    assert f is not None
    assert f.speed_mps is None and f.course_deg is None
