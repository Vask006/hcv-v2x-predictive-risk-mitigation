"""Connectivity logging and hardware probes before creating recording session folders."""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _resolve_under_edge(edge_root: Path, rel: str) -> Path:
    p = Path(rel).expanduser()
    if not p.is_absolute():
        p = (edge_root / p).resolve()
    return p


def resolve_connectivity_log_paths(edge_root: Path, cfg: dict[str, Any]) -> tuple[Path, Path]:
    """Return (camera connectivity jsonl path, gps connectivity jsonl path)."""
    rec = cfg.get("recording", {})
    cam_rel = rec.get("connectivity_log_camera")
    gps_rel = rec.get("connectivity_log_gps")
    legacy = rec.get("connectivity_log")

    if cam_rel and gps_rel:
        return _resolve_under_edge(edge_root, str(cam_rel)), _resolve_under_edge(edge_root, str(gps_rel))
    if legacy and not cam_rel and not gps_rel:
        leg = _resolve_under_edge(edge_root, str(legacy))
        parent = leg.parent
        stem = leg.stem
        suf = leg.suffix or ".jsonl"
        return parent / f"{stem}_camera{suf}", parent / f"{stem}_gps{suf}"
    default_cam = str(cam_rel or "data/recordings/device_connectivity_camera.jsonl")
    default_gps = str(gps_rel or "data/recordings/device_connectivity_gps.jsonl")
    return _resolve_under_edge(edge_root, default_cam), _resolve_under_edge(edge_root, default_gps)


def resolve_connectivity_log_path(edge_root: Path, cfg: dict[str, Any]) -> Path:
    """Backward compatible: camera-side connectivity log (prefer resolve_connectivity_log_paths)."""
    return resolve_connectivity_log_paths(edge_root, cfg)[0]


def append_connectivity_record(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    row = {"utc": utc_now_iso(), **record}
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def probe_camera(cfg: dict[str, Any]) -> tuple[bool, str]:
    from camera_service.capture import CameraCapture, CaptureError

    cam_cfg = cfg.get("camera", {})
    pipeline = cam_cfg.get("gstream_pipeline")
    idx = int(cam_cfg.get("index", 0))
    cap = CameraCapture(
        index=idx,
        pipeline=pipeline,
        backend=str(cam_cfg.get("backend", "opencv")),
    )
    try:
        cap.open()
        _meta, _frame = cap.read_frame()
        return True, f"camera_ok index={idx} backend={cam_cfg.get('backend', 'opencv')}"
    except CaptureError as e:
        return False, str(e)
    finally:
        cap.close()


def probe_gps(cfg: dict[str, Any], mock_gps: bool, wait_fix_sec: float) -> tuple[bool, str]:
    if mock_gps:
        return True, "gps_ok synthetic_bench_no_serial"

    from gps_service.reader import GPSReader, GPSReaderError

    g = cfg.get("gps", {})
    port = str(g.get("port", "/dev/ttyUSB0"))
    baud = int(g.get("baud", 9600))
    timeout = float(g.get("timeout_sec", 1.0))
    reader = GPSReader(port, baud, timeout)
    try:
        reader.open()
    except (GPSReaderError, OSError, ValueError) as e:
        return False, f"gps_open_failed {port}: {e}"

    deadline = time.monotonic() + max(0.5, wait_fix_sec)
    fix = None
    read_err: str | None = None
    try:
        fix = reader.wait_for_fix(deadline)
    except (OSError, ValueError) as e:
        read_err = str(e)
    finally:
        reader.close()

    if read_err is not None:
        return False, f"gps_read_failed: {read_err}"
    if fix is None:
        return False, f"gps_no_fix_within_{wait_fix_sec}s port={port}"

    return True, f"gps_ok port={port} baud={baud} fix_quality={fix.fix_quality}"
