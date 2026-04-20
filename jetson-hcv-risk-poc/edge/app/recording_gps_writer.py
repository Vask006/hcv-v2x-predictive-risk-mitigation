"""GPS NMEA → JSONL file (one line per fix). Used standalone or beside camera recording."""
from __future__ import annotations

import json
import logging
import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any


def _write_fix_row(out_path: Path, fix: object) -> None:
    row = {
        "wall_utc": fix.wall_time_utc_iso,
        "mono_s": fix.monotonic_s,
        "latitude_deg": fix.latitude_deg,
        "longitude_deg": fix.longitude_deg,
        "fix_quality": fix.fix_quality,
        "raw": (fix.raw_sentence or "")[:500],
    }
    with out_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def gps_jsonl_writer_loop(
    out_path: Path,
    cfg: dict[str, Any],
    mock_gps: bool,
    log: logging.Logger,
    should_stop: Callable[[], bool],
) -> bool:
    """
    Block until ``should_stop()`` is true. Writes fixes to ``out_path``.
    For mock GPS, yields between batches so CPU stays reasonable.

    Returns False if recording stopped due to an error.
    """
    try:
        if mock_gps:
            from gps_service.reader import mock_fixes

            log.info("GPS mock mode enabled")
            while not should_stop():
                for fix in mock_fixes(20):
                    if should_stop():
                        return True
                    _write_fix_row(out_path, fix)
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
                    _write_fix_row(out_path, fix)
            finally:
                reader.close()
            return True
    except Exception as e:
        log.error("GPS recording ended: %s", e)
        return False


def gps_writer_thread(
    out_path: Path,
    stop: threading.Event,
    cfg: dict[str, Any],
    mock_gps: bool,
    log: logging.Logger,
) -> None:
    """Target for ``threading.Thread`` alongside camera recording (same JSONL logic as standalone)."""

    gps_jsonl_writer_loop(out_path, cfg, mock_gps, log, stop.is_set)
