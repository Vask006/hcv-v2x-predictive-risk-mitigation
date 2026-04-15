"""
Record GPS fixes to local JSONL file only.

Run from `edge/`:
  python -m app.record_gps --config config/default.yaml
"""
from __future__ import annotations

import argparse
import json
import logging
import signal
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import yaml

_EDGE_ROOT = Path(__file__).resolve().parent.parent
if str(_EDGE_ROOT) not in sys.path:
    sys.path.insert(0, str(_EDGE_ROOT))


def _load_config(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _session_dir(base: Path) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    d = base / f"{stamp}-gps"
    d.mkdir(parents=True, exist_ok=True)
    return d


def main() -> int:
    parser = argparse.ArgumentParser(description="Record GPS fixes to JSONL (GPS only).")
    parser.add_argument("--config", type=Path, default=_EDGE_ROOT / "config" / "default.yaml")
    parser.add_argument("--mock-gps", action="store_true", help="Use mock GPS (no serial)")
    parser.add_argument(
        "--duration-sec",
        type=float,
        default=None,
        help="Override recording.duration_sec (0 = until Ctrl+C)",
    )
    args = parser.parse_args()

    cfg = _load_config(args.config)
    rec = cfg.get("recording", {})
    out_base = Path(rec.get("output_base", str(_EDGE_ROOT / "data" / "recordings")))
    out_base = out_base.expanduser()
    if not out_base.is_absolute():
        out_base = (_EDGE_ROOT / out_base).resolve()

    duration_sec = float(rec.get("duration_sec", 0))
    if args.duration_sec is not None:
        duration_sec = float(args.duration_sec)
    gps_name = str(rec.get("gps_filename", "gps.jsonl"))
    meta_name = str(rec.get("session_meta_filename", "session.json"))

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    log = logging.getLogger("record-gps")

    session = _session_dir(out_base)
    meta_path = session / meta_name
    gps_path = session / gps_name

    device_id = cfg.get("device_id", "unknown")
    started = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    meta_path.write_text(
        json.dumps(
            {
                "device_id": device_id,
                "started_utc": started,
                "mode": "gps_only",
                "config": str(args.config.resolve()),
                "duration_sec": duration_sec,
                "mock_gps": args.mock_gps,
                "session_dir": str(session),
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    stop = False

    def handle_sig(*_a: object) -> None:
        nonlocal stop
        log.info("stop signal")
        stop = True

    signal.signal(signal.SIGINT, handle_sig)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, handle_sig)

    start_t = time.monotonic()

    def should_stop() -> bool:
        if stop:
            return True
        if duration_sec <= 0:
            return False
        return (time.monotonic() - start_t) >= duration_sec

    def write_fix(fix: object) -> None:
        row = {
            "wall_utc": fix.wall_time_utc_iso,
            "mono_s": fix.monotonic_s,
            "latitude_deg": fix.latitude_deg,
            "longitude_deg": fix.longitude_deg,
            "fix_quality": fix.fix_quality,
            "raw": (fix.raw_sentence or "")[:500],
        }
        with gps_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    try:
        if args.mock_gps:
            from gps_service.reader import mock_fixes

            log.info("GPS mock mode enabled")
            while not should_stop():
                for fix in mock_fixes(20):
                    if should_stop():
                        break
                    write_fix(fix)
                time.sleep(0.2)
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
                    write_fix(fix)
            finally:
                reader.close()
    except (RuntimeError, OSError, ValueError) as e:
        log.error("GPS recording failed: %s", e)
        return 1

    log.info("gps session complete -> %s", session)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
