#!/usr/bin/env python3
"""Run the local pipeline once with mock GPS and synthetic camera input.

Usage (repository root):

    python scripts/run_local_pipeline.py
    python scripts/run_local_pipeline.py --vehicle-id edge-dev-1
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
