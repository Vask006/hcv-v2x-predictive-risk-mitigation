from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class QueuedEvent:
    path: Path
    payload: dict[str, Any]


class EventQueue:
    """Filesystem-backed queue with pending/sent folders."""

    def __init__(self, root_dir: Path) -> None:
        self._root_dir = root_dir
        self._pending_dir = root_dir / "pending"
        self._sent_dir = root_dir / "sent"
        self._pending_dir.mkdir(parents=True, exist_ok=True)
        self._sent_dir.mkdir(parents=True, exist_ok=True)

    def enqueue(self, payload: dict[str, Any]) -> Path:
        event_id = str(payload.get("event_id", "unknown"))
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        out = self._pending_dir / f"{stamp}-{event_id}.json"
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return out

    def list_pending(self, limit: int = 25) -> list[QueuedEvent]:
        files = sorted(self._pending_dir.glob("*.json"))
        items: list[QueuedEvent] = []
        for p in files[: max(1, limit)]:
            try:
                payload = json.loads(p.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            items.append(QueuedEvent(path=p, payload=payload))
        return items

    def mark_sent(self, item: QueuedEvent) -> Path:
        target = self._sent_dir / item.path.name
        if target.exists():
            target.unlink()
        item.path.replace(target)
        return target

    def pending_count(self) -> int:
        return len(list(self._pending_dir.glob("*.json")))
