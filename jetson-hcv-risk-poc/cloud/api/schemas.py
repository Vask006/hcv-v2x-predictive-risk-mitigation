"""Pydantic models aligned with contracts/event_v1.json."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class GPSModel(BaseModel):
    latitude_deg: float = Field(ge=-90, le=90)
    longitude_deg: float = Field(ge=-180, le=180)
    altitude_m: Optional[float] = None
    speed_mps: Optional[float] = None
    course_deg: Optional[float] = Field(default=None, ge=0, le=360)
    fix_quality: Optional[int] = Field(default=None, ge=0)
    hdop: Optional[float] = None
    satellites: Optional[int] = Field(default=None, ge=0)


class RiskModel(BaseModel):
    score: float = Field(ge=0, le=1)
    band: Literal["none", "low", "medium", "high", "critical"]
    reason_codes: list[str]


class EventV1(BaseModel):
    schema_version: Literal["1.0"]
    event_id: UUID
    device_id: str = Field(min_length=1)
    recorded_at: datetime
    gps: GPSModel
    risk: RiskModel
    perception_summary: Optional[dict[str, Any]] = None
    media: Optional[dict[str, Optional[str]]] = None


class EventV1Response(BaseModel):
    ok: bool = True
    event_id: UUID
