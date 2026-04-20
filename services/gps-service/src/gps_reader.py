"""Serial NMEA GNSS reader + mock fixes (lazy ``pyserial`` import on open)."""
from __future__ import annotations

import re
import time
from datetime import datetime, timezone
from typing import Iterator, Optional

from gps_models import GpsFix

_KNOTS_TO_MPS = 0.514444


class GpsReaderError(RuntimeError):
    pass


def _parse_nmea_coord(raw: str, hemi: str) -> float | None:
    if not raw or len(raw) < 3:
        return None
    if "N" in hemi or "S" in hemi:
        deg = int(raw[0:2])
        minutes = float(raw[2:])
    else:
        deg = int(raw[0:3])
        minutes = float(raw[3:])
    val = deg + minutes / 60.0
    if hemi in ("S", "W"):
        val = -val
    return val


# Same talker flexibility as POC (GP/GN/GL/GA).
# SOG/COG captured when present (fields 7–8); empty strings → no speed/course.
_rmc = re.compile(
    r"^\$(?:GP|GN|GL|GA)RMC,"
    r"([^,]*),([AV]),"
    r"([^,]*),([NS]),"
    r"([^,]*),([EW]),"
    r"([^,]*),([^,]*)"
)


_gga = re.compile(
    r"^\$(?:GP|GN|GL|GA)GGA,"
    r"[^,]*,"
    r"([^,]*),([NS]),"
    r"([^,]*),([EW]),"
    r"([0-9]),"
)


def _optional_float(s: str) -> float | None:
    t = (s or "").strip()
    if not t:
        return None
    try:
        return float(t)
    except ValueError:
        return None


def parse_line(line: str, wall: str, mono: float) -> GpsFix | None:
    """Parse one NMEA line into ``GpsFix`` (RMC or GGA). Same contract as POC ``_parse_line``; adds optional RMC SOG/COG."""
    m = _rmc.match(line)
    if m:
        lat_s, lat_h, lon_s, lon_h = m.group(3), m.group(4), m.group(5), m.group(6)
        lat = _parse_nmea_coord(lat_s, lat_h)
        lon = _parse_nmea_coord(lon_s, lon_h)
        sog_kn = _optional_float(m.group(7))
        cog = _optional_float(m.group(8))
        speed_mps = sog_kn * _KNOTS_TO_MPS if sog_kn is not None else None
        return GpsFix(
            wall_time_utc_iso=wall,
            monotonic_s=mono,
            raw_sentence=line,
            latitude_deg=lat,
            longitude_deg=lon,
            fix_quality=1 if m.group(2) == "A" else 0,
            speed_mps=speed_mps,
            course_deg=cog,
        )
    m = _gga.match(line)
    if m:
        lat_s, lat_h, lon_s, lon_h, q = m.group(1), m.group(2), m.group(3), m.group(4), m.group(5)
        lat = _parse_nmea_coord(lat_s, lat_h)
        lon = _parse_nmea_coord(lon_s, lon_h)
        return GpsFix(
            wall_time_utc_iso=wall,
            monotonic_s=mono,
            raw_sentence=line,
            latitude_deg=lat,
            longitude_deg=lon,
            fix_quality=int(q) if q else None,
            speed_mps=None,
            course_deg=None,
        )
    return None


# Tests in ``jetson-hcv-risk-poc/tests`` import ``_parse_line`` from ``gps_service.reader``.
_parse_line = parse_line


class GpsSerialReader:
    """Non-blocking readline iterator over a serial NMEA stream (POC-compatible API)."""

    def __init__(self, port: str, baud: int = 9600, timeout_sec: float = 1.0) -> None:
        self._port = port
        self._baud = baud
        self._timeout_sec = timeout_sec
        self._ser: object | None = None

    def open(self) -> None:
        try:
            import serial  # type: ignore[import-untyped]
        except ImportError as e:
            raise GpsReaderError("Install pyserial: pip install pyserial") from e

        self._ser = serial.Serial(self._port, self._baud, timeout=self._timeout_sec)

    def close(self) -> None:
        if self._ser is not None:
            self._ser.close()
            self._ser = None

    def wait_for_fix(self, deadline_mono: float) -> GpsFix | None:
        if self._ser is None:
            raise GpsReaderError("Serial not open")
        ser = self._ser
        while time.monotonic() < deadline_mono:
            raw = ser.readline()
            if not raw:
                continue
            try:
                nmea = raw.decode("ascii", errors="replace").strip()
            except Exception:
                continue
            mono = time.monotonic()
            wall = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
            fix = parse_line(nmea, wall, mono)
            if fix:
                return fix
        return None

    def iter_lines(self, max_lines: int | None = None) -> Iterator[GpsFix]:
        if self._ser is None:
            raise GpsReaderError("Serial not open")

        count = 0
        ser = self._ser
        while max_lines is None or count < max_lines:
            raw = ser.readline()
            if not raw:
                continue
            try:
                nmea = raw.decode("ascii", errors="replace").strip()
            except Exception:
                continue
            count += 1
            mono = time.monotonic()
            wall = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
            fix = parse_line(nmea, wall, mono)
            if fix:
                yield fix

    def __enter__(self) -> GpsSerialReader:
        self.open()
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()


def mock_fixes(count: int = 5) -> Iterator[GpsFix]:
    """Synthetic fixes (non-NMEA ``raw_sentence``) — same semantics as POC ``mock_fixes``."""
    base = time.monotonic()
    for i in range(count):
        yield GpsFix(
            wall_time_utc_iso=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            monotonic_s=base + i * 0.2,
            raw_sentence=f"$HCVMOCK,BENCH_SYNTHETIC,NO_SERIAL,i={i}*",
            latitude_deg=0.0 + i * 1e-7,
            longitude_deg=0.0 + i * 1e-7,
            fix_quality=1,
            speed_mps=None,
            course_deg=None,
        )
