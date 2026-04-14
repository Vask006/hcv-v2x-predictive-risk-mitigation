"""Minimal ingest + query API (Phase 0)."""

from __future__ import annotations

import os
from typing import Optional
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from database import EventRecord, get_db, init_db
from schemas import EventV1, EventV1Response

app = FastAPI(title="HCV Risk API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _startup() -> None:
    init_db()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/v1/events", response_model=EventV1Response)
def ingest_event(body: EventV1, db: Session = Depends(get_db)) -> EventV1Response:
    key = str(body.event_id)
    existing = db.get(EventRecord, key)
    if existing is not None:
        return EventV1Response(ok=True, event_id=body.event_id)

    row = EventRecord(
        event_id=key,
        device_id=body.device_id,
        recorded_at=body.recorded_at,
        payload=body.model_dump(mode="json"),
    )
    db.add(row)
    db.commit()
    return EventV1Response(ok=True, event_id=body.event_id)


@app.get("/v1/events")
def list_events(
    limit: int = 50,
    device_id: Optional[str] = None,
    db: Session = Depends(get_db),
) -> dict:
    if limit > 500:
        limit = 500
    q = db.query(EventRecord).order_by(EventRecord.recorded_at.desc())
    if device_id:
        q = q.filter(EventRecord.device_id == device_id)
    rows = q.limit(limit).all()
    return {
        "items": [
            {
                "event_id": r.event_id,
                "device_id": r.device_id,
                "recorded_at": r.recorded_at.isoformat(),
                "payload": r.payload,
            }
            for r in rows
        ]
    }


# Tests / dev: optional reset (disabled unless ENABLE_RESET=1)
@app.delete("/v1/events/{event_id}")
def delete_event(
    event_id: UUID,
    db: Session = Depends(get_db),
) -> dict[str, bool]:
    if os.getenv("ENABLE_RESET") != "1":
        raise HTTPException(status_code=404, detail="not found")
    key = str(event_id)
    row = db.get(EventRecord, key)
    if row is None:
        raise HTTPException(status_code=404, detail="unknown event_id")
    db.delete(row)
    db.commit()
    return {"ok": True}
