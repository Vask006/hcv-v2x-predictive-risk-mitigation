"""Make `edge/` importable for tests."""

from __future__ import annotations

import sys
from pathlib import Path

_EDGE = Path(__file__).resolve().parents[1] / "edge"
if str(_EDGE) not in sys.path:
    sys.path.insert(0, str(_EDGE))
