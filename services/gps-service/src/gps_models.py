"""GNSS fix and normalized sample types (Phase 1; no speculative coordinate transforms)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

GpsSourceKind = Literal["serial", "mock"]
GpsValidity = Literal["valid", "void", "unknown"]


@dataclass
class GpsFix:
    """One parsed fix (NMEA or mock). Field names match POC ``GPSFix`` for JSONL / callers."""

    wall_time_utc_iso: str
    monotonic_s: float
    raw_sentence: str
    latitude_deg: float | None = None
    longitude_deg: float | None = None
    fix_quality: int | None = None
    # Populated from RMC when sentence contains SOG/COG fields; otherwise None.
    speed_mps: float | None = None
    course_deg: float | None = None


@dataclass
class GpsSampleEvent:
    """Normalized GPS sample for edge fusion (not ``event_v1``)."""

    fix: GpsFix
    source: GpsSourceKind
    validity: GpsValidity
    extra: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        """JSON-friendly; omits null optional motion fields."""
        d: dict[str, Any] = {
            "schema_version": "gps.sample.v1",
            "wall_time_utc_iso": self.fix.wall_time_utc_iso,
            "monotonic_s": self.fix.monotonic_s,
            "latitude_deg": self.fix.latitude_deg,
            "longitude_deg": self.fix.longitude_deg,
            "fix_quality": self.fix.fix_quality,
            "validity": self.validity,
            "source": self.source,
            "raw_nmea_truncated": (self.fix.raw_sentence or "")[:500],
        }
        if self.fix.speed_mps is not None:
            d["speed_mps"] = self.fix.speed_mps
        if self.fix.course_deg is not None:
            d["course_deg"] = self.fix.course_deg
        d.update(self.extra)
        return d
