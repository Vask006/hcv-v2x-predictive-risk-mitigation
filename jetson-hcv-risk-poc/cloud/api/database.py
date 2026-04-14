from __future__ import annotations

import os
from collections.abc import Generator
from pathlib import Path

from sqlalchemy import JSON, Column, DateTime, String, create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

_HERE = Path(__file__).resolve().parent


def _default_sqlite_url() -> str:
    p = _HERE / "data" / "events.db"
    p.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{p.as_posix()}"


def _database_url() -> str:
    return os.getenv("DATABASE_URL", _default_sqlite_url())


DATABASE_URL = _database_url()

connect_args: dict = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


class EventRecord(Base):
    __tablename__ = "events"

    event_id = Column(String(36), primary_key=True)
    device_id = Column(String(128), index=True, nullable=False)
    recorded_at = Column(DateTime(timezone=True), index=True, nullable=False)
    payload = Column(JSON, nullable=False)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
