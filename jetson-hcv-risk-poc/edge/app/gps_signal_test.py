"""
Quick GPS check on the Jetson (or Linux): raw NMEA from the serial port and/or parsed fixes.

Run from edge/:
  python -m app.gps_signal_test
  python -m app.gps_signal_test --raw-sec 15
  python -m app.gps_signal_test --parse-only --fixes 30
"""
from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

import yaml

_EDGE_ROOT = Path(__file__).resolve().parent.parent
if str(_EDGE_ROOT) not in sys.path:
    sys.path.insert(0, str(_EDGE_ROOT))


def _load_config(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _list_serial_hints() -> str:
    import glob

    parts = sorted(glob.glob("/dev/ttyUSB*") + glob.glob("/dev/ttyACM*"))
    return "  " + "\n  ".join(parts) if parts else "  (none — plug in USB GPS / check cable)"


def _raw_dump(port: str, baud: int, timeout_sec: float, duration_sec: float) -> None:
    import serial  # type: ignore

    ser = serial.Serial(port, baud, timeout=timeout_sec)
    t_end = time.monotonic() + duration_sec
    print(f"# Reading raw NMEA from {port} @ {baud} baud for {duration_sec}s (Ctrl+C to stop)\n")
    try:
        while time.monotonic() < t_end:
            raw = ser.readline()
            if not raw:
                continue
            line = raw.decode("ascii", errors="replace").strip()
            if line:
                print(line)
    finally:
        ser.close()


def main() -> int:
    p = argparse.ArgumentParser(description="Test GPS serial: raw NMEA and/or parsed RMC/GGA fixes.")
    p.add_argument("--config", type=Path, default=_EDGE_ROOT / "config" / "default.yaml")
    p.add_argument(
        "--port",
        type=str,
        default=None,
        help="Serial device (overrides gps.port in config), e.g. /dev/ttyACM0",
    )
    p.add_argument("--raw-sec", type=float, default=10.0, help="Seconds to print raw NMEA lines (0 = skip raw)")
    p.add_argument("--parse-only", action="store_true", help="Only print parsed fixes, no raw dump")
    p.add_argument("--fixes", type=int, default=15, help="Max parsed fixes to print when not parse-only")
    args = p.parse_args()

    cfg = _load_config(args.config)
    g = cfg.get("gps", {})
    port = str(args.port or g.get("port", "/dev/ttyUSB0"))
    baud = int(g.get("baud", 9600))
    timeout = float(g.get("timeout_sec", 1.0))

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    log = logging.getLogger("gps_test")

    if not Path(port).exists():
        log.error("Serial device not found: %s", port)
        log.error("Candidates on this system:\n%s", _list_serial_hints())
        log.error("Fix: plug USB GPS, set gps.port in config/default.yaml, or run with --port /dev/ttyACM0")
        return 2

    if not args.parse_only and args.raw_sec > 0:
        try:
            _raw_dump(port, baud, timeout, args.raw_sec)
        except OSError as e:
            log.error("Raw read failed: %s", e)
            return 1
        print()

    from gps_service.reader import GPSReader

    log.info("# Parsed fixes (RMC/GGA with lat/lon) from %s @ %s", port, baud)
    try:
        reader = GPSReader(port, baud, timeout)
        reader.open()
    except Exception as e:  # GPSReaderError, SerialException, permission, etc.
        log.error("Open failed: %s", e)
        return 1
    try:
        n = 0
        for fix in reader.iter_lines(max_lines=None):
            log.info(
                "fix[%s] lat=%s lon=%s q=%s | %s",
                n,
                fix.latitude_deg,
                fix.longitude_deg,
                fix.fix_quality,
                (fix.raw_sentence or "")[:100],
            )
            n += 1
            if n >= args.fixes:
                break
        if n == 0:
            log.warning(
                "No RMC/GGA lines parsed. If raw lines above show $G... sentences, check baud or talker IDs."
            )
    finally:
        reader.close()

    log.info("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
