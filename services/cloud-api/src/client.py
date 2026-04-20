"""Minimal HTTP client for ``POST /v1/events`` (stdlib only; mirrors POC ``edge/uploader/client.py``)."""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from urllib import error, request


@dataclass
class PostResult:
    ok: bool
    status_code: int | None
    message: str


def post_event_v1(
    base_url: str,
    body: dict[str, Any],
    *,
    path: str = "/v1/events",
    api_key: str = "",
    timeout_sec: float = 10.0,
) -> PostResult:
    """
    POST an ``EventV1``-shaped dict (e.g. from ``adapter.combined_pipeline_to_event_v1``).

    ``body`` must use **snake_case** keys matching ``jetson-hcv-risk-poc/cloud/api/schemas.EventV1``.
    """
    root = base_url.rstrip("/")
    p = path if path.startswith("/") else f"/{path}"
    payload = json.dumps(body, ensure_ascii=False, default=str).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["X-API-Key"] = api_key
    req = request.Request(url=f"{root}{p}", data=payload, headers=headers, method="POST")
    try:
        with request.urlopen(req, timeout=timeout_sec) as resp:
            code = int(getattr(resp, "status", 200))
            if 200 <= code < 300:
                return PostResult(ok=True, status_code=code, message="ok")
            return PostResult(ok=False, status_code=code, message="non-success status")
    except error.HTTPError as e:
        return PostResult(ok=False, status_code=e.code, message=f"http_error: {e.reason}")
    except error.URLError as e:
        return PostResult(ok=False, status_code=None, message=f"url_error: {e.reason!s}")
