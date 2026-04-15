from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from urllib import error, request


@dataclass
class UploadResult:
    ok: bool
    status_code: int | None
    message: str


class CloudUploader:
    def __init__(
        self,
        base_url: str,
        api_key: str = "",
        path: str = "/v1/events",
        timeout_sec: float = 5.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._path = path if path.startswith("/") else f"/{path}"
        self._api_key = api_key
        self._timeout_sec = timeout_sec

    @property
    def endpoint(self) -> str:
        return f"{self._base_url}{self._path}"

    def upload_event(self, payload: dict[str, Any]) -> UploadResult:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = request.Request(
            url=self.endpoint,
            data=body,
            headers={
                "Content-Type": "application/json",
                **({"X-API-Key": self._api_key} if self._api_key else {}),
            },
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=self._timeout_sec) as resp:
                code = int(getattr(resp, "status", 200))
                if 200 <= code < 300:
                    return UploadResult(ok=True, status_code=code, message="ok")
                return UploadResult(ok=False, status_code=code, message="non-success status")
        except error.HTTPError as e:
            return UploadResult(ok=False, status_code=e.code, message=f"http_error: {e.reason}")
        except error.URLError as e:
            return UploadResult(ok=False, status_code=None, message=f"url_error: {e.reason}")
