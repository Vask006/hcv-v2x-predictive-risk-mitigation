#!/usr/bin/env python3
"""Run an end-to-end local demo with optional cloud ingest."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path


def _install_paths(repo_root: Path) -> None:
    for rel in (
        "services/pipeline/src",
        "services/cloud-api/src",
    ):
        p = str(repo_root / rel)
        if p not in sys.path:
            sys.path.insert(0, p)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run local HCV V2X demo workflow.")
    parser.add_argument("--vehicle-id", default="hcv-demo-001")
    parser.add_argument("--trip-id", default="demo-trip-001")
    parser.add_argument(
        "--v2x-event",
        default="services/v2x-simulator/examples/v2i_curve_warning.json",
    )
    parser.add_argument("--ingest-base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--skip-ingest", action="store_true")
    parser.add_argument("--output-dir", default="outputs")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    _install_paths(root)

    from event_pipeline import EventPipeline, write_sink
    from adapter import combined_pipeline_to_event_v1
    from client import post_event_v1

    pipeline = EventPipeline(
        vehicle_id=args.vehicle_id,
        trip_id=args.trip_id,
        output_dir=root / args.output_dir,
        external_context_path=None,
        v2x_event_path=root / args.v2x_event,
        mock_gps=True,
        mock_camera=True,
        gps_wait_sec=1.0,
    )
    try:
        combined = pipeline.run_once()
    except ValueError as exc:
        print(f"Demo input error: {exc}")
        return 2

    output_path = root / args.output_dir
    output_path.mkdir(parents=True, exist_ok=True)
    stamped = output_path / f"demo_run_{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}.json"
    stamped.write_text(json.dumps(combined, ensure_ascii=False, indent=2), encoding="utf-8")
    write_sink(combined, output_path)

    cloud_status = "skipped"
    if not args.skip_ingest:
        try:
            body = combined_pipeline_to_event_v1(combined)
            result = post_event_v1(args.ingest_base_url, body)
            cloud_status = "success" if result.ok else "unavailable"
        except Exception:
            cloud_status = "unavailable"

    risk = combined.get("riskEvent", {}).get("riskAssessment", {})
    mitigation = combined.get("riskEvent", {}).get("mitigation", {})
    reason_codes = combined.get("riskEvent", {}).get("reasonCodes", [])

    print("HCV V2X Predictive Risk Mitigation Demo")
    print("---------------------------------------")
    print(f"Vehicle ID: {args.vehicle_id}")
    print(f"Trip ID: {args.trip_id}")
    print(f"Risk Score: {risk.get('riskScore')}")
    print(f"Severity: {risk.get('severity')}")
    print(f"Hazard Type: {risk.get('hazardType')}")
    print(f"Driver Alert: {mitigation.get('driverAlert')}")
    print(f"Fleet Notification: {str(mitigation.get('fleetNotification')).lower()}")
    print(f"Reason Codes: {', '.join(reason_codes)}")
    print(f"Cloud Ingest: {cloud_status}")
    print(f"Output File: {stamped.relative_to(root)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
