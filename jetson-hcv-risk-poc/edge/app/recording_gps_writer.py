"""GPS NMEA → JSONL file(s); segmented like video when ``segment_duration_sec`` > 0.

NMEA parsing and serial iteration already go through ``gps_service.reader`` (which
delegates to ``services/gps-service/src`` when the monorepo is present). A later
step would be optional alignment of JSONL rows with shared event contracts, not
re-wiring the reader import here (on-disk format is a separate risk).
"""
from __future__ import annotations

import json
import logging
import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from app.recording_paths import initial_gps_path, numbered_gps_path


def _write_fix_row(out_path: Path, fix: object, *, gps_source: str | None = None) -> None:
    row = {
        "wall_utc": fix.wall_time_utc_iso,
        "mono_s": fix.monotonic_s,
        "latitude_deg": fix.latitude_deg,
        "longitude_deg": fix.longitude_deg,
        "fix_quality": fix.fix_quality,
        "raw": (fix.raw_sentence or "")[:500],
    }
    if gps_source:
        row["gps_source"] = gps_source
    with out_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _rotate_gps_segment_if_needed(
    gps_template: Path,
    segment_duration_sec: float,
    segment_start: float,
    segment_idx: int,
    out_path: Path,
    log: logging.Logger,
) -> tuple[Path, float, int]:
    if segment_duration_sec <= 0:
        return out_path, segment_start, segment_idx
    if (time.monotonic() - segment_start) < segment_duration_sec:
        return out_path, segment_start, segment_idx
    next_idx = segment_idx + 1
    new_path = numbered_gps_path(gps_template, next_idx)
    log.info("Rotated GPS JSONL segment -> %s", new_path)
    return new_path, time.monotonic(), next_idx


def gps_jsonl_writer_loop(
    gps_template: Path,
    segment_duration_sec: float,
    cfg: dict[str, Any],
    mock_gps: bool,
    log: logging.Logger,
    should_stop: Callable[[], bool],
) -> bool:
    """
    Block until ``should_stop()`` is true. Writes fixes under ``gps_template`` naming:
    one ``gps.jsonl`` if ``segment_duration_sec == 0``, else ``gps_000001.jsonl``, …
    rotating on the same schedule as camera segments.

    Returns False if recording stopped due to an error.
    """
    seg = float(segment_duration_sec)
    out_path = initial_gps_path(gps_template, seg)
    segment_start = time.monotonic()
    segment_idx = 1 if seg > 0 else 0
    log.info("GPS JSONL -> %s (segment_duration_sec=%s)", out_path, seg)

    try:
        if mock_gps:
            from gps_service.reader import mock_fixes

            log.info(
                "GPS synthetic bench mode (--mock-gps): JSONL rows are tagged gps_source=hcv_synthetic_mock"
            )
            while not should_stop():
                for fix in mock_fixes(20):
                    if should_stop():
                        return True
                    out_path, segment_start, segment_idx = _rotate_gps_segment_if_needed(
                        gps_template, seg, segment_start, segment_idx, out_path, log
                    )
                    _write_fix_row(out_path, fix, gps_source="hcv_synthetic_mock")
                time.sleep(0.2)
            return True
        else:
            from gps_service.reader import GPSReader

            g = cfg.get("gps", {})
            port = str(g.get("port", "/dev/ttyUSB0"))
            baud = int(g.get("baud", 9600))
            timeout = float(g.get("timeout_sec", 1.0))
            reader = GPSReader(port, baud, timeout)
            reader.open()
            log.info("GPS serial open %s baud=%s", port, baud)
            try:
                for fix in reader.iter_lines(max_lines=None):
                    if should_stop():
                        break
                    out_path, segment_start, segment_idx = _rotate_gps_segment_if_needed(
                        gps_template, seg, segment_start, segment_idx, out_path, log
                    )
                    _write_fix_row(out_path, fix)
            finally:
                reader.close()
            return True
    except Exception as e:
        log.error("GPS recording ended: %s", e)
        return False


def gps_writer_thread(
    gps_template: Path,
    segment_duration_sec: float,
    stop: threading.Event,
    cfg: dict[str, Any],
    mock_gps: bool,
    log: logging.Logger,
) -> None:
    """Target for ``threading.Thread`` alongside camera recording."""

    gps_jsonl_writer_loop(gps_template, segment_duration_sec, cfg, mock_gps, log, stop.is_set)
