"""
Test GPS serial connectivity and NMEA fix acquisition (same logic as recording probes).

Run from ``edge/`` on the device (GPS on ``gps.port``, usually ``/dev/ttyUSB0`` or ``/dev/ttyACM0``):

  python -m app.gps_connectivity --config config/default.yaml

  # Longer wait for first fix (cold start / indoors)
  python -m app.gps_connectivity --config config/default.yaml --wait-sec 120

  # Print raw NMEA lines for 8s before the fix probe (debug wiring)
  python -m app.gps_connectivity --config config/default.yaml --raw-sec 8
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import yaml

_EDGE_ROOT = Path(__file__).resolve().parent.parent
if str(_EDGE_ROOT) not in sys.path:
    sys.path.insert(0, str(_EDGE_ROOT))

from app.device_connectivity import append_connectivity_record, probe_gps, resolve_connectivity_log_paths


def _load_config(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _raw_nmea_preview(cfg: dict, seconds: float, max_lines_print: int) -> None:
    import serial  # type: ignore[import-untyped]

    g = cfg.get("gps", {})
    port = str(g.get("port", "/dev/ttyUSB0"))
    baud = int(g.get("baud", 9600))
    timeout = float(g.get("timeout_sec", 1.0))
    print(f"--- Raw NMEA preview ({seconds}s) on {port} @ {baud} ---", flush=True)
    ser = serial.Serial(port, baud, timeout=timeout)
    try:
        deadline = time.monotonic() + max(0.1, seconds)
        n = 0
        printed = 0
        while time.monotonic() < deadline:
            raw = ser.readline()
            if not raw:
                continue
            n += 1
            try:
                line = raw.decode("ascii", errors="replace").strip()
            except Exception:
                line = repr(raw)
            if line and printed < max_lines_print:
                print(line, flush=True)
                printed += 1
        print(f"--- End preview: {n} lines read (showing up to {max_lines_print}) ---", flush=True)
    finally:
        ser.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Test GPS serial + NMEA fix (connectivity probe).")
    parser.add_argument("--config", type=Path, default=_EDGE_ROOT / "config" / "default.yaml")
    parser.add_argument("--mock", action="store_true", help="Skip hardware (always report ok)")
    parser.add_argument(
        "--wait-sec",
        type=float,
        default=None,
        help="Override recording.gps_probe_timeout_sec (seconds to wait for first RMC/GGA fix)",
    )
    parser.add_argument(
        "--raw-sec",
        type=float,
        default=0.0,
        help="Before probing, read and print sample NMEA lines for this many seconds (debug)",
    )
    args = parser.parse_args()

    cfg = _load_config(args.config)
    rec = cfg.get("recording", {})
    wait = float(args.wait_sec) if args.wait_sec is not None else float(rec.get("gps_probe_timeout_sec", 45))

    _, connectivity_gps = resolve_connectivity_log_paths(_EDGE_ROOT, cfg)
    device_id = cfg.get("device_id", "unknown")

    if args.raw_sec and args.raw_sec > 0 and not args.mock:
        try:
            _raw_nmea_preview(cfg, float(args.raw_sec), max_lines_print=40)
        except Exception as e:
            print(f"Raw preview failed: {e}", flush=True)
            append_connectivity_record(
                connectivity_gps,
                {
                    "event": "gps_connectivity_raw_preview_error",
                    "device_id": device_id,
                    "detail": str(e),
                },
            )
            return 1

    ok, detail = probe_gps(cfg, args.mock, wait)
    row = {
        "event": "gps_connectivity_test",
        "device_id": device_id,
        "ok": ok,
        "detail": detail,
        "wait_sec": wait,
        "mock": args.mock,
    }
    append_connectivity_record(connectivity_gps, row)

    status = "PASS" if ok else "FAIL"
    print(f"{status}: {detail}", flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
