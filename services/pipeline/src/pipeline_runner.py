#!/usr/bin/env python3
"""CLI entry: one-shot Phase 1 pipeline (console + ``outputs/`` JSON)."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from event_pipeline import EventPipeline, install_service_import_paths, repo_root, write_sink  # noqa: E402


def _default_external_context() -> Path | None:
    p = _HERE.parent / "examples" / "external_context_sample.json"
    return p if p.is_file() else None


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 1 local pipeline (camera + GPS + risk → sink).")
    parser.add_argument(
        "--live-camera",
        action="store_true",
        help="Try one live OpenCV frame via camera-service; on failure uses synthetic metadata.",
    )
    parser.add_argument(
        "--real-gps",
        action="store_true",
        help="Use serial NMEA (gps-service) when not reading --gps-jsonl tail; needs pyserial + receiver.",
    )
    parser.add_argument(
        "--gps-wait-sec",
        type=float,
        default=None,
        help="Wait for first GPS fix (default: 2 mock, 45 real).",
    )
    parser.add_argument(
        "--gps-jsonl",
        type=Path,
        default=None,
        help="Use last JSON line from a POC-style gps.jsonl (overrides mock GPS position when file exists).",
    )
    parser.add_argument(
        "--external-context",
        type=Path,
        default=None,
        help="JSON file for ExternalContext fields (default: services/pipeline/examples/external_context_sample.json if present).",
    )
    parser.add_argument("--no-external-context", action="store_true", help="Skip external context file.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Directory for JSON output (default: <repo>/outputs).",
    )
    parser.add_argument("--vehicle-id", type=str, default="pipeline-dev")
    parser.add_argument("--trip-id", type=str, default=None)
    parser.add_argument(
        "--post-ingest",
        action="store_true",
        help="After run, map combined output to EventV1 and POST to existing POC FastAPI /v1/events.",
    )
    parser.add_argument(
        "--ingest-base-url",
        type=str,
        default="http://127.0.0.1:8000",
        help="Base URL for POC cloud API (uvicorn main:app).",
    )
    parser.add_argument("--ingest-api-key", type=str, default="", help="Optional X-API-Key header.")
    args = parser.parse_args()

    install_service_import_paths()
    out_dir = args.output_dir or (repo_root() / "outputs")

    mock_gps = not args.real_gps
    mock_camera = not args.live_camera
    gps_wait = args.gps_wait_sec
    if gps_wait is None:
        gps_wait = 2.0 if mock_gps else 45.0
    ext_path = None if args.no_external_context else (args.external_context or _default_external_context())

    pipe = EventPipeline(
        vehicle_id=args.vehicle_id,
        trip_id=args.trip_id,
        output_dir=out_dir,
        external_context_path=ext_path,
        gps_jsonl_path=args.gps_jsonl,
        mock_gps=mock_gps,
        mock_camera=mock_camera,
        gps_wait_sec=gps_wait,
    )
    combined = pipe.run_once()
    path = write_sink(combined, out_dir)
    print(json.dumps(combined, ensure_ascii=False, indent=2))
    print(f"\nWrote: {path}", file=sys.stderr)

    if args.post_ingest:
        cap = str(repo_root() / "services" / "cloud-api" / "src")
        if cap not in sys.path:
            sys.path.insert(0, cap)
        from adapter import combined_pipeline_to_event_v1  # noqa: E402
        from client import post_event_v1  # noqa: E402

        body = combined_pipeline_to_event_v1(combined)
        res = post_event_v1(args.ingest_base_url, body, api_key=args.ingest_api_key)
        print(
            json.dumps({"ingestPost": {"ok": res.ok, "status": res.status_code, "message": res.message}}),
            file=sys.stderr,
        )
        if not res.ok:
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
