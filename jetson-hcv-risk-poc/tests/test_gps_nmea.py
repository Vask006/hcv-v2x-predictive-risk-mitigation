"""NMEA parsing for Phase 0 GPS reader."""

from __future__ import annotations

from gps_service.reader import _parse_line


def test_gprmc_valid() -> None:
    line = "$GPRMC,123519,A,4807.038,N,01131.000,E,022.4,084.4,230394,003.1,W*"
    f = _parse_line(line, "2026-01-01T00:00:00.000000Z", 1.0)
    assert f is not None
    assert f.fix_quality == 1
    assert f.latitude_deg is not None and f.longitude_deg is not None


def test_gnrmc_valid() -> None:
    line = "$GNRMC,123519,A,4807.038,N,01131.000,E,022.4,084.4,230394,003.1,W*"
    f = _parse_line(line, "2026-01-01T00:00:00.000000Z", 1.0)
    assert f is not None
    assert f.fix_quality == 1


def test_gpgga_valid() -> None:
    line = "$GPGGA,123519,4807.038,N,01131.000,E,1,08,0.9,545.4,M,46.9,M,,*"
    f = _parse_line(line, "2026-01-01T00:00:00.000000Z", 1.0)
    assert f is not None
    assert f.fix_quality == 1


def test_gngga_valid() -> None:
    """u-blox and others often emit GNGGA instead of GPGGA."""
    line = "$GNGGA,123519,4807.038,N,01131.000,E,1,08,0.9,545.4,M,46.9,M,,*"
    f = _parse_line(line, "2026-01-01T00:00:00.000000Z", 1.0)
    assert f is not None
    assert f.fix_quality == 1


def test_rmc_void_no_fix() -> None:
    line = "$GPRMC,123519,V,4807.038,N,01131.000,E,022.4,084.4,230394,003.1,W*"
    f = _parse_line(line, "2026-01-01T00:00:00.000000Z", 1.0)
    assert f is not None
    assert f.fix_quality == 0
