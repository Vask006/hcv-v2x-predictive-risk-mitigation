"""Shared directory layout and video segment paths for local recording."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any


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


def resolve_recording_output_base(edge_root: Path, rec: dict[str, Any]) -> Path:
    """Same rules as ``record_session`` / ``edge_runtime`` for ``recording.output_base``."""
    out_base = Path(rec.get("output_base", str(edge_root / "data" / "recordings")))
    out_base = out_base.expanduser()
    if not out_base.is_absolute():
        out_base = (edge_root / out_base).resolve()
    return out_base
