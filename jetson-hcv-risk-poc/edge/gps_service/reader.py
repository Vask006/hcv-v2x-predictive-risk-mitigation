"""
GNSS NMEA reader for the POC.

Delegates to ``services/gps-service/src`` when this repo contains
``<root>/services/gps-service/src`` (monorepo layout). Otherwise uses the legacy
inline implementation so a standalone ``jetson-hcv-risk-poc`` clone still works.

TODO: When ``hcv-gps-service`` is always installed via pip, drop the legacy branch.
"""
from __future__ import annotations

import sys
from pathlib import Path


def _shared_service_src() -> Path | None:
    here = Path(__file__).resolve()
    for root in here.parents:
        cand = root / "services" / "gps-service" / "src"
        if cand.is_dir() and (cand / "gps_reader.py").is_file():
            return cand
    return None


_SRC = _shared_service_src()
if _SRC is not None:
    p = str(_SRC)
    if p not in sys.path:
        sys.path.insert(0, p)
    from gps_reader import (  # noqa: E402
        GpsReaderError as GPSReaderError,
        GpsSerialReader as GPSReader,
        mock_fixes,
        parse_line as _parse_line,
    )
    from gps_models import GpsFix as GPSFix  # noqa: E402
else:
    import re
    import time
    from dataclasses import dataclass
    from datetime import datetime, timezone
    from typing import Iterator, Optional

    class GPSReaderError(RuntimeError):
        pass

    @dataclass
    class GPSFix:
        wall_time_utc_iso: str
        monotonic_s: float
        raw_sentence: str
        latitude_deg: Optional[float] = None
        longitude_deg: Optional[float] = None
        fix_quality: Optional[int] = None

    def _parse_nmea_coord(raw: str, hemi: str) -> Optional[float]:
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

    _rmc = re.compile(
        r"^\$(?:GP|GN|GL|GA)RMC,"
        r"([^,]*),([AV]),"
        r"([^,]*),([NS]),"
        r"([^,]*),([EW]),"
    )

    _gga = re.compile(
        r"^\$(?:GP|GN|GL|GA)GGA,"
        r"[^,]*,"
        r"([^,]*),([NS]),"
        r"([^,]*),([EW]),"
        r"([0-9]),"
    )

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

    class GPSReader:
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

            self._ser = serial.Serial(self._port, self._baud, timeout=self._timeout_sec)

        def close(self) -> None:
            if self._ser is not None:
                self._ser.close()
                self._ser = None

        def wait_for_fix(self, deadline_mono: float) -> Optional[GPSFix]:
            if self._ser is None:
                raise GPSReaderError("Serial not open")
            ser = self._ser
            while time.monotonic() < deadline_mono:
                raw = ser.readline()
                if not raw:
                    continue
                try:
                    line = raw.decode("ascii", errors="replace").strip()
                except Exception:
                    continue
                mono = time.monotonic()
                wall = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
                fix = _parse_line(line, wall, mono)
                if fix:
                    return fix
            return None

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

    def mock_fixes(count: int = 5) -> Iterator[GPSFix]:
        base = time.monotonic()
        for i in range(count):
            yield GPSFix(
                wall_time_utc_iso=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                monotonic_s=base + i * 0.2,
                raw_sentence=f"$HCVMOCK,BENCH_SYNTHETIC,NO_SERIAL,i={i}*",
                latitude_deg=0.0 + i * 1e-7,
                longitude_deg=0.0 + i * 1e-7,
                fix_quality=1,
            )
