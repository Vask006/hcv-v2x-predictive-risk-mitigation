"""
Phase 1 edge runtime:
- reads latest GPS fix from local recording output
- generates perception/context snapshots
- computes risk and mitigation
- writes contract-aligned events to local queue
- uploads queued events to cloud when reachable
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
from typing import Any
from uuid import uuid4

import yaml

_EDGE_ROOT = Path(__file__).resolve().parent.parent
if str(_EDGE_ROOT) not in sys.path:
    sys.path.insert(0, str(_EDGE_ROOT))

from event_store.queue import EventQueue
from inference.perception_adapter import PerceptionAdapter
from risk_engine.context_provider import MockContextProvider
from risk_engine.scorer import band_rank, score_risk
from uploader.client import CloudUploader

_BAND_ORDER = ("none", "low", "medium", "high", "critical")


def _load_config(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _to_iso_z(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _resolve_output_base(cfg: dict[str, Any]) -> Path:
    rec = cfg.get("recording", {})
    out_base = Path(rec.get("output_base", str(_EDGE_ROOT / "data" / "recordings")))
    out_base = out_base.expanduser()
    if not out_base.is_absolute():
        out_base = (_EDGE_ROOT / out_base).resolve()
    out_base.mkdir(parents=True, exist_ok=True)
    return out_base


def _latest_file(pattern: str, root: Path) -> Path | None:
    files = list(root.glob(pattern))
    if not files:
        return None
    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return files[0]


def _read_last_json_line(path: Path) -> dict[str, Any] | None:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return None
    for line in reversed(lines):
        line = line.strip()
        if not line:
            continue
        try:
            return json.loads(line)
        except json.JSONDecodeError:
            continue
    return None


def _latest_gps_fix(recording_root: Path, gps_name: str) -> dict[str, Any] | None:
    gps_file = _latest_file(f"**/{gps_name}", recording_root)
    if gps_file is None:
        return None
    return _read_last_json_line(gps_file)


def _camera_health(recording_root: Path, video_name: str, healthy_age_sec: float) -> tuple[bool, float | None]:
    camera_file = _latest_file(f"**/{video_name}", recording_root)
    if camera_file is None:
        return False, None
    age = max(0.0, time.time() - camera_file.stat().st_mtime)
    return age <= healthy_age_sec, age


def _band_enabled(risk_band: str, min_band: str) -> bool:
    return band_rank(risk_band) >= band_rank(min_band)


def _build_event(
    cfg: dict[str, Any],
    gps_fix: dict[str, Any],
    risk: dict[str, Any],
    perception_summary: dict[str, Any],
    context_summary: dict[str, Any],
    mitigation: dict[str, Any],
) -> dict[str, Any]:
    wall_utc = str(gps_fix.get("wall_utc") or _to_iso_z(datetime.now(timezone.utc)))
    return {
        "schema_version": "1.0",
        "event_id": str(uuid4()),
        "device_id": str(cfg.get("device_id", "unknown")),
        "recorded_at": wall_utc,
        "gps": {
            "latitude_deg": gps_fix.get("latitude_deg"),
            "longitude_deg": gps_fix.get("longitude_deg"),
            "altitude_m": None,
            "speed_mps": None,
            "course_deg": None,
            "fix_quality": gps_fix.get("fix_quality"),
            "hdop": None,
            "satellites": None,
        },
        "risk": risk,
        "perception_summary": {
            **perception_summary,
            "context": context_summary,
            "mitigation": mitigation,
            "edge_runtime": "phase1",
        },
        "media": {"thumbnail_uri": None, "clip_uri": None},
    }


def _drain_queue(
    queue: EventQueue,
    uploader: CloudUploader,
    max_batch: int,
    log: logging.Logger,
) -> tuple[int, int]:
    uploaded = 0
    failed = 0
    for item in queue.list_pending(limit=max_batch):
        result = uploader.upload_event(item.payload)
        if result.ok:
            queue.mark_sent(item)
            uploaded += 1
        else:
            failed += 1
            log.warning(
                "upload failed event_id=%s status=%s msg=%s",
                item.payload.get("event_id"),
                result.status_code,
                result.message,
            )
            break
    return uploaded, failed


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 1 edge runtime loop.")
    parser.add_argument("--config", type=Path, default=_EDGE_ROOT / "config" / "default.yaml")
    parser.add_argument(
        "--duration-sec",
        type=float,
        default=None,
        help="Override phase1_runtime.duration_sec (0 = run forever).",
    )
    parser.add_argument("--dry-run", action="store_true", help="Compute and queue events without cloud upload.")
    args = parser.parse_args()

    cfg = _load_config(args.config)
    rec = cfg.get("recording", {})
    runtime_cfg = cfg.get("phase1_runtime", {})
    uploader_cfg = cfg.get("uploader", {})
    context_cfg = cfg.get("context_mock", {})
    risk_cfg = cfg.get("risk_engine", {})

    recording_root = _resolve_output_base(cfg)
    queue_dir = recording_root / "phase1_events"
    queue = EventQueue(queue_dir)

    interval_sec = float(runtime_cfg.get("interval_sec", 2.0))
    duration_sec = float(runtime_cfg.get("duration_sec", 0))
    if args.duration_sec is not None:
        duration_sec = float(args.duration_sec)
    min_emit_band = str(runtime_cfg.get("min_emit_band", "low"))
    camera_healthy_age_sec = float(runtime_cfg.get("camera_healthy_age_sec", 20.0))
    upload_enabled = bool(uploader_cfg.get("enabled", True)) and not args.dry_run
    max_upload_batch = int(uploader_cfg.get("max_batch", 20))
    gps_name = str(rec.get("gps_filename", "gps.jsonl"))
    video_name = str(rec.get("video_filename", "camera.mp4"))

    uploader = CloudUploader(
        base_url=str(cfg.get("cloud", {}).get("ingest_base_url", "http://127.0.0.1:8000")),
        api_key=str(cfg.get("cloud", {}).get("api_key", "")),
        path=str(uploader_cfg.get("path", "/v1/events")),
        timeout_sec=float(uploader_cfg.get("timeout_sec", 5.0)),
    )
    perception = PerceptionAdapter(runtime_cfg.get("perception_mock", {}))
    context_provider = MockContextProvider(context_cfg)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    log = logging.getLogger("edge-runtime")
    log.info("phase1 runtime start config=%s queue=%s", args.config.resolve(), queue_dir)

    stop = False

    def handle_sig(*_a: object) -> None:
        nonlocal stop
        stop = True
        log.info("stop signal")

    signal.signal(signal.SIGINT, handle_sig)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, handle_sig)

    t0 = time.monotonic()
    while not stop:
        if duration_sec > 0 and (time.monotonic() - t0) >= duration_sec:
            break

        gps_fix = _latest_gps_fix(recording_root, gps_name)
        if not gps_fix:
            log.warning("no GPS fix file found yet under %s", recording_root)
            time.sleep(interval_sec)
            continue

        lat = gps_fix.get("latitude_deg")
        lon = gps_fix.get("longitude_deg")
        if lat is None or lon is None:
            log.warning("latest GPS row missing lat/lon, skipping")
            time.sleep(interval_sec)
            continue

        camera_alive, camera_age_sec = _camera_health(recording_root, video_name, camera_healthy_age_sec)
        perception_snapshot = perception.next_snapshot(camera_alive=camera_alive, camera_age_sec=camera_age_sec)
        context_snapshot = context_provider.snapshot()
        risk = score_risk(
            gps=gps_fix,
            perception=perception_snapshot.as_dict(),
            context=context_snapshot.as_dict(),
            config=risk_cfg,
        )

        if _band_enabled(risk.band, min_emit_band):
            event = _build_event(
                cfg=cfg,
                gps_fix=gps_fix,
                risk=risk.as_event_risk(),
                perception_summary=perception_snapshot.as_dict(),
                context_summary=context_snapshot.as_dict(),
                mitigation=risk.as_mitigation(),
            )
            out = queue.enqueue(event)
            log.info(
                "event queued band=%s score=%.3f reasons=%s file=%s",
                risk.band,
                risk.score,
                ",".join(risk.reason_codes) or "none",
                out.name,
            )
        else:
            log.info("risk below emit threshold band=%s min=%s", risk.band, min_emit_band)

        if upload_enabled:
            uploaded, failed = _drain_queue(queue, uploader, max_upload_batch, log)
            if uploaded > 0 or failed > 0:
                log.info(
                    "upload cycle uploaded=%s failed=%s pending=%s",
                    uploaded,
                    failed,
                    queue.pending_count(),
                )
        time.sleep(interval_sec)

    log.info("phase1 runtime complete pending=%s", queue.pending_count())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
