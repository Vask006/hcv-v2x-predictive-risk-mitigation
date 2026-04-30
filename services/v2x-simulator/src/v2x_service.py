"""Service wrapper around V2X simulation helpers."""

from __future__ import annotations

from pathlib import Path

from v2x_event_generator import load_v2x_event_from_file, v2x_event_to_external_context
from v2x_models import V2XContextOutput, V2XEvent


class V2XSimulatorService:
    def load_event(self, path: Path) -> V2XEvent:
        return load_v2x_event_from_file(path)

    def to_context(self, event: V2XEvent) -> V2XContextOutput:
        return v2x_event_to_external_context(event)

    def load_context_from_file(self, path: Path) -> V2XContextOutput:
        return self.to_context(self.load_event(path))
