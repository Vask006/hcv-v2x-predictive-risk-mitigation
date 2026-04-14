from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterator, Optional

log = logging.getLogger(__name__)


class GPSReaderError(RuntimeError):
    pass


@dataclass
class GPSFix:
    """Parsed fix from an RMC or GGA line (partial; Phase 0)."""

    wall_time_utc_iso: str
    monotonic_s: float
    raw_sentence: str
    latitude_deg: Optional[float] = None
    longitude_deg: Optional[float] = None
    fix_quality: Optional[int] = None


def _parse_nmea_coord(raw: str, hemi: str) -> Optional[float]:
    if not raw or len(raw) < 3:
        return None
    # ddmm.mmmm for lat, dddmm.mmmm for lon (standard NMEA)
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


_rmc = re.compile(
    r"^\$(?:GP|GN)RMC,"
    r"([^,]*),([AV]),"
    r"([^,]*),([NS]),"
    r"([^,]*),([EW]),"
)


_gga = re.compile(
    r"^\$GPGGA,"
    r"[^,]*,"  # time
    r"([^,]*),([NS]),"
    r"([^,]*),([EW]),"
    r"([0-9]),"  # fix quality
)


class GPSReader:
    """Non-blocking readline iterator over a serial NMEA stream."""

    def __init__(self, port: str, baud: int = 9600, timeout_sec: float = 1.0) -> None:
        self._port = port
        self._baud = baud
        self._timeout_sec = timeout_sec
        self._ser: Optional[object] = None

    def open(self) -> None:
        try:
            import serial  # type: ignore
        except ImportError as e:
            raise GPSReaderError("Install pyserial: pip install pyserial") from e

        self._ser = serial.Serial(
            self._port, self._baud, timeout=self._timeout_sec
        )

    def close(self) -> None:
        if self._ser is not None:
            self._ser.close()
            self._ser = None

    def iter_lines(self, max_lines: Optional[int] = None) -> Iterator[GPSFix]:
        if self._ser is None:
            raise GPSReaderError("Serial not open")

        count = 0
        ser = self._ser
        while max_lines is None or count < max_lines:
            raw = ser.readline()
            if not raw:
                continue
            try:
                line = raw.decode("ascii", errors="replace").strip()
            except Exception:
                continue
            count += 1
            mono = time.monotonic()
            wall = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
            fix = _parse_line(line, wall, mono)
            if fix:
                yield fix

    def __enter__(self) -> "GPSReader":
        self.open()
        return self

    def __exit__(self, *args: object) -> None:
        self.close()


def _parse_line(line: str, wall: str, mono: float) -> Optional[GPSFix]:
    m = _rmc.match(line)
    if m:
        lat_s, lat_h, lon_s, lon_h = m.group(3), m.group(4), m.group(5), m.group(6)
        lat = _parse_nmea_coord(lat_s, lat_h)
        lon = _parse_nmea_coord(lon_s, lon_h)
        return GPSFix(
            wall_time_utc_iso=wall,
            monotonic_s=mono,
            raw_sentence=line,
            latitude_deg=lat,
            longitude_deg=lon,
            fix_quality=1 if m.group(2) == "A" else 0,
        )
    m = _gga.match(line)
    if m:
        lat_s, lat_h, lon_s, lon_h, q = m.group(1), m.group(2), m.group(3), m.group(4), m.group(5)
        lat = _parse_nmea_coord(lat_s, lat_h)
        lon = _parse_nmea_coord(lon_s, lon_h)
        return GPSFix(
            wall_time_utc_iso=wall,
            monotonic_s=mono,
            raw_sentence=line,
            latitude_deg=lat,
            longitude_deg=lon,
            fix_quality=int(q) if q else None,
        )
    return None


def mock_fixes(count: int = 5) -> Iterator[GPSFix]:
    """Deterministic fake fixes for bench test without hardware."""
    base = time.monotonic()
    for i in range(count):
        yield GPSFix(
            wall_time_utc_iso=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            monotonic_s=base + i * 0.2,
            raw_sentence=f"$GPRMC,123519,A,4717.11{i % 10},N,00833.22,E,022.4,084.4,230394,003.1,W*",
            latitude_deg=47.285 + i * 0.0001,
            longitude_deg=8.5537 + i * 0.0001,
            fix_quality=1,
        )
