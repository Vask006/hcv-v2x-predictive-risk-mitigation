from __future__ import annotations

from fastapi.testclient import TestClient

from main import app


def test_health_endpoint() -> None:
    with TestClient(app) as client:
        resp = client.get("/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert body["service"] == "cloud-api"


def test_list_events_endpoint() -> None:
    with TestClient(app) as client:
        resp = client.get("/v1/events?limit=5")
        assert resp.status_code == 200
        body = resp.json()
        assert "items" in body
        assert "count" in body
