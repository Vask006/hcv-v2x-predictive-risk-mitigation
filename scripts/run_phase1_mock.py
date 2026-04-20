#!/usr/bin/env python3
"""Run the Phase 1 local pipeline once: mock GPS + synthetic camera (no OpenCV / pyserial).

Usage (repository root):

    python scripts/run_phase1_mock.py
    python scripts/run_phase1_mock.py --vehicle-id my-dev

Extra arguments are appended and passed through to ``pipeline_runner.py`` (e.g.
``--vehicle-id x``). Avoid passing a second ``--no-external-context`` unless you
intend to duplicate the flag.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    runner = root / "services" / "pipeline" / "src" / "pipeline_runner.py"
    if not runner.is_file():
        print("Expected pipeline runner at:", runner, file=sys.stderr)
        return 2
    cmd = [sys.executable, str(runner), "--no-external-context", *sys.argv[1:]]
    return subprocess.call(cmd, cwd=root)


if __name__ == "__main__":
    raise SystemExit(main())
