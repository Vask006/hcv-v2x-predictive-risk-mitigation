"""
Delete recorded video (mp4/avi) and segmented GPS JSONL older than
``recording.retention_days_video`` under ``recording.output_base``.

Run from ``edge/``:
  python -m app.prune_recordings --config config/default.yaml
  python -m app.prune_recordings --config config/default.yaml --dry-run
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

from app.recording_paths import resolve_recording_output_base

_VIDEO_SUFFIXES = frozenset({".mp4", ".avi"})


def _is_session_gps_jsonl(path: Path) -> bool:
    """Session ``gps.jsonl`` / ``gps_000001.jsonl`` — not connectivity logs."""
    if path.suffix.lower() != ".jsonl":
        return False
    n = path.name
    return n == "gps.jsonl" or (n.startswith("gps_") and n.endswith(".jsonl"))


def _load_config(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def main() -> int:
    parser = argparse.ArgumentParser(description="Remove old recording videos and GPS JSONL session files.")
    parser.add_argument("--config", type=Path, default=_EDGE_ROOT / "config" / "default.yaml")
    parser.add_argument(
        "--days",
        type=float,
        default=None,
        help="Override recording.retention_days_video (0 = disable pruning)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Log files that would be deleted without removing them",
    )
    args = parser.parse_args()

    cfg = _load_config(args.config)
    rec = cfg.get("recording", {})
    retention = args.days
    if retention is None:
        retention = float(rec.get("retention_days_video", 3))
    else:
        retention = float(retention)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    log = logging.getLogger("prune_recordings")

    if retention <= 0:
        log.info("retention_days_video is %s — nothing to do (disabled).", retention)
        return 0

    root = resolve_recording_output_base(_EDGE_ROOT, rec)
    if not root.is_dir():
        log.warning("Recording root does not exist or is not a directory: %s", root)
        return 0

    cutoff = time.time() - retention * 86400.0
    removed = 0
    bytes_freed = 0

    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        suf = path.suffix.lower()
        if suf not in _VIDEO_SUFFIXES and not _is_session_gps_jsonl(path):
            continue
        try:
            st = path.stat()
        except OSError as e:
            log.warning("stat failed %s: %s", path, e)
            continue
        if st.st_mtime >= cutoff:
            continue
        size = st.st_size
        if args.dry_run:
            log.info("would delete (age) %s", path)
            removed += 1
            bytes_freed += size
            continue
        try:
            path.unlink()
            removed += 1
            bytes_freed += size
            log.info("deleted %s", path)
        except OSError as e:
            log.error("failed to delete %s: %s", path, e)

    log.info(
        "done: %s file(s)%s, ~%.1f MiB",
        removed,
        " (dry-run)" if args.dry_run else "",
        bytes_freed / (1024 * 1024),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
