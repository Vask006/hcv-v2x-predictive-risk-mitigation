"""Phase 1 GPS service: YAML-friendly config, serial vs mock, ``GpsSampleEvent`` wrapper."""
from __future__ import annotations

import time
from collections.abc import Iterator, Mapping
from typing import Any

from gps_models import GpsFix, GpsSampleEvent, GpsSourceKind, GpsValidity
from gps_reader import GpsReaderError, GpsSerialReader, mock_fixes


class GpsServiceConfig:
    """``gps:`` section from POC YAML."""

    __slots__ = ("port", "baud", "timeout_sec", "mock_gps")

    def __init__(
        self,
        *,
        port: str = "/dev/ttyUSB0",
        baud: int = 9600,
        timeout_sec: float = 1.0,
        mock_gps: bool = False,
    ) -> None:
        self.port = port
        self.baud = baud
        self.timeout_sec = timeout_sec
        self.mock_gps = mock_gps

    @classmethod
    def from_gps_yaml(cls, gps: Mapping[str, Any], *, mock_gps: bool = False) -> GpsServiceConfig:
        return cls(
            port=str(gps.get("port", "/dev/ttyUSB0")),
            baud=int(gps.get("baud", 9600)),
            timeout_sec=float(gps.get("timeout_sec", 1.0)),
            mock_gps=mock_gps,
        )


def _validity_for_fix(fix: GpsFix) -> GpsValidity:
    raw = fix.raw_sentence or ""
    if "$HCVMOCK" in raw or "BENCH_SYNTHETIC" in raw:
        return "valid"
    if "RMC" in raw[:10]:
        return "valid" if (fix.fix_quality or 0) > 0 else "void"
    if "GGA" in raw[:10]:
        return "valid" if (fix.fix_quality or 0) > 0 else "unknown"
    return "unknown"


class GpsService:
    """``iter_fixes`` for streaming; ``wait_for_fix`` / ``probe_open`` for startup checks."""

    def __init__(self, config: GpsServiceConfig | Mapping[str, Any], *, mock_gps: bool | None = None) -> None:
        if isinstance(config, GpsServiceConfig):
            self._cfg = config
        else:
            self._cfg = GpsServiceConfig.from_gps_yaml(config, mock_gps=bool(mock_gps))
        if mock_gps is not None:
            self._cfg = GpsServiceConfig(
                port=self._cfg.port,
                baud=self._cfg.baud,
                timeout_sec=self._cfg.timeout_sec,
                mock_gps=bool(mock_gps),
            )

    @property
    def config(self) -> GpsServiceConfig:
        return self._cfg

    def iter_fixes(self, max_lines: int | None = None) -> Iterator[GpsSampleEvent]:
        """Serial: blocks until ``max_lines`` fixes or forever if ``max_lines`` is None.

        Mock: repeats batches of synthetic fixes (same cadence idea as ``recording_gps_writer``); caller must stop.
        """
        if self._cfg.mock_gps:
            while True:
                for fix in mock_fixes(20):
                    yield self._to_event(fix, "mock")
        reader = GpsSerialReader(self._cfg.port, self._cfg.baud, self._cfg.timeout_sec)
        reader.open()
        try:
            for fix in reader.iter_lines(max_lines=max_lines):
                yield self._to_event(fix, "serial")
        finally:
            reader.close()

    def wait_for_fix(self, wait_fix_sec: float) -> GpsSampleEvent | None:
        """First fix within ``wait_fix_sec`` (real serial) or first mock row."""
        if self._cfg.mock_gps:
            fix = next(iter(mock_fixes(1)))
            return self._to_event(fix, "mock")
        reader = GpsSerialReader(self._cfg.port, self._cfg.baud, self._cfg.timeout_sec)
        reader.open()
        try:
            deadline = time.monotonic() + max(0.5, float(wait_fix_sec))
            fix = reader.wait_for_fix(deadline)
            if fix is None:
                return None
            return self._to_event(fix, "serial")
        finally:
            reader.close()

    def probe_open(self, wait_fix_sec: float) -> tuple[bool, str]:
        """Same outcomes as ``device_connectivity.probe_gps`` for real serial; mock always ok."""
        if self._cfg.mock_gps:
            return True, "gps_ok synthetic_bench_no_serial"
        reader = GpsSerialReader(self._cfg.port, self._cfg.baud, self._cfg.timeout_sec)
        try:
            reader.open()
        except (GpsReaderError, OSError, ValueError) as e:
            return False, f"gps_open_failed {self._cfg.port}: {e}"

        deadline = time.monotonic() + max(0.5, float(wait_fix_sec))
        read_err: str | None = None
        fix: GpsFix | None = None
        try:
            try:
                fix = reader.wait_for_fix(deadline)
            except (OSError, ValueError) as e:
                read_err = str(e)
        finally:
            reader.close()

        if read_err is not None:
            return False, f"gps_read_failed: {read_err}"
        if fix is None:
            return False, f"gps_no_fix_within_{wait_fix_sec}s port={self._cfg.port}"
        return True, f"gps_ok port={self._cfg.port} baud={self._cfg.baud} fix_quality={fix.fix_quality}"

    def _to_event(self, fix: GpsFix, source: GpsSourceKind) -> GpsSampleEvent:
        return GpsSampleEvent(fix=fix, source=source, validity=_validity_for_fix(fix))
