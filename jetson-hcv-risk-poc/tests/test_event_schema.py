"""Validate sample payload against contracts/event_v1.json."""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

_ROOT = Path(__file__).resolve().parents[1]
_SCHEMA = _ROOT / "contracts" / "event_v1.json"
_SAMPLE = _ROOT / "samples" / "event_v1_example.json"


def test_sample_validates_against_schema() -> None:
    with _SCHEMA.open(encoding="utf-8") as f:
        schema = json.load(f)
    with _SAMPLE.open(encoding="utf-8") as f:
        sample = json.load(f)
    jsonschema.validate(instance=sample, schema=schema)
