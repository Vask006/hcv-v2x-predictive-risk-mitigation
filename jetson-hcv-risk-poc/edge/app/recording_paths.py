"""Shared directory layout and segment paths for camera video + GPS JSONL recording."""
from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# When `segment_duration_sec` is omitted from YAML, use chunked files (vehicle-friendly).
_DEFAULT_SEGMENT_SEC = 60.0


def resolve_segment_duration_sec(rec: dict[str, Any], cli_segment_sec: float | None) -> float:
    """
    Seconds per camera video segment and per GPS JSONL segment. Priority:
    ``--segment-sec`` > ``HCV_SEGMENT_SEC`` env > YAML.

    If the YAML key is **missing**, default is 60s.
    If YAML sets ``segment_duration_sec: 0``, one ``camera.mp4`` and one ``gps.jsonl`` per session.
    """
    if cli_segment_sec is not None:
        return float(cli_segment_sec)
    env_raw = os.environ.get("HCV_SEGMENT_SEC", "").strip()
    if env_raw:
        return float(env_raw)
    if "segment_duration_sec" in rec and rec["segment_duration_sec"] is not None:
        return float(rec["segment_duration_sec"])
    return _DEFAULT_SEGMENT_SEC


def session_dir_with_day(base: Path, folder_suffix: str = "") -> Path:
    """Create ``base/YYYY-MM-DD/YYYY-MM-DDTHH-MM-SSZ{suffix}/`` (UTC)."""
    now = datetime.now(timezone.utc)
    day = now.strftime("%Y-%m-%d")
    stamp = now.strftime("%Y-%m-%dT%H-%M-%SZ")
    name = f"{stamp}{folder_suffix}"
    d = base / day / name
    d.mkdir(parents=True, exist_ok=True)
    return d


def numbered_video_path(template: Path, index: int) -> Path:
    """``camera.mp4`` + index 1 -> ``camera_000001.mp4`` (suffix from template)."""
    return template.with_name(f"{template.stem}_{index:06d}{template.suffix}")


def initial_video_path(template: Path, segment_duration_sec: float) -> Path:
    """Single file ``camera.mp4`` when not segmenting; else ``camera_000001.mp4``."""
    if segment_duration_sec > 0:
        return numbered_video_path(template, 1)
    return template


def numbered_gps_path(template: Path, index: int) -> Path:
    """``gps.jsonl`` + index 1 -> ``gps_000001.jsonl``."""
    return template.with_name(f"{template.stem}_{index:06d}{template.suffix}")


def initial_gps_path(template: Path, segment_duration_sec: float) -> Path:
    """Single file ``gps.jsonl`` when not segmenting; else ``gps_000001.jsonl``."""
    if segment_duration_sec > 0:
        return numbered_gps_path(template, 1)
    return template


def resolve_recording_output_base(edge_root: Path, rec: dict[str, Any]) -> Path:
    """Same rules as ``record_session`` / ``edge_runtime`` for ``recording.output_base``."""
    out_base = Path(rec.get("output_base", str(edge_root / "data" / "recordings")))
    out_base = out_base.expanduser()
    if not out_base.is_absolute():
        out_base = (edge_root / out_base).resolve()
    return out_base
