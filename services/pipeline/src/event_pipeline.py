"""
Phase 1 local event pipeline: GPS + camera (+ optional JSON context) → risk-engine → sink.

Does not import or modify ``jetson-hcv-risk-poc``; it only mirrors ideas (JSONL tail read)
from ``edge/app/edge_runtime.py`` for optional file-based GPS.
"""
from __future__ import annotations

import json
import sys
import time
import uuid
from dataclasses import asdict, fields
from pathlib import Path
from typing import Any

_REPO_ROOT: Path | None = None


def install_service_import_paths(start: Path | None = None) -> Path:
    """Locate monorepo root and prepend ``services/*/src`` so camera, gps, risk modules import."""
    global _REPO_ROOT
    here = (start or Path(__file__).resolve()).parent
    for root in [here, *here.parents]:
        cam = root / "services" / "camera-service" / "src"
        gps = root / "services" / "gps-service" / "src"
        risk = root / "services" / "risk-engine" / "src"
        if cam.is_dir() and gps.is_dir() and risk.is_dir():
            for p in (risk, gps, cam):
                s = str(p)
                if s not in sys.path:
                    sys.path.insert(0, s)
            _REPO_ROOT = root
            return root
    raise RuntimeError(
        "Cannot find services/camera-service/src, gps-service/src, and risk-engine/src in parents of "
        f"{here}. Run from the hcv-v2x-predictive-risk-mitigation repo checkout."
    )


def repo_root() -> Path:
    if _REPO_ROOT is None:
        install_service_import_paths()
    assert _REPO_ROOT is not None
    return _REPO_ROOT


def read_last_json_object(path: Path) -> dict[str, Any] | None:
    """Last non-empty JSON line in a file (same pattern as POC ``edge_runtime`` GPS tail)."""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return None
    for line in reversed(lines):
        line = line.strip()
        if not line:
            continue
        try:
            return json.loads(line)
        except json.JSONDecodeError:
            continue
    return None


def load_external_context_file(path: Path) -> Any:
    install_service_import_paths()
    from risk_models import ExternalContext

    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("external context JSON must be an object")
    allowed = {f.name for f in fields(ExternalContext)}
    kwargs = {k: v for k, v in raw.items() if k in allowed}
    return ExternalContext(**kwargs)


def jsonl_row_to_gps_fields(row: dict[str, Any]) -> dict[str, Any]:
    """Map POC ``gps.jsonl`` row keys to ``EdgeObservations`` field names."""
    return {
        "wall_time_utc_iso": row.get("wall_utc") or row.get("wall_time_utc_iso"),
        "monotonic_s": row.get("mono_s") if row.get("mono_s") is not None else row.get("monotonic_s"),
        "latitude_deg": row.get("latitude_deg"),
        "longitude_deg": row.get("longitude_deg"),
        "gps_fix_quality": row.get("fix_quality"),
        "gps_speed_mps": row.get("speed_mps"),
    }


def synthetic_camera_sample_event() -> Any:
    """Bench camera metadata when no device (no OpenCV)."""
    install_service_import_paths()
    from camera_models import CameraHealth, CameraSampleEvent, FrameSample

    now = time.strftime("%Y-%m-%dT%H:%M:%S.000000Z", time.gmtime())
    meta = FrameSample(
        wall_time_utc_iso=now,
        monotonic_s=time.monotonic(),
        width=640,
        height=480,
        backend="mock",
    )
    h = CameraHealth(opened=True, last_read_ok=True, consecutive_failures=0, last_error=None)
    return CameraSampleEvent(meta=meta, source_kind="live_index", healthy=True, health=h)


def gps_sample_to_edge_fields(gps_ev: Any) -> dict[str, Any]:
    f = gps_ev.fix
    return {
        "gps_speed_mps": f.speed_mps,
        "gps_fix_quality": f.fix_quality,
        "latitude_deg": f.latitude_deg,
        "longitude_deg": f.longitude_deg,
        "wall_time_utc_iso": f.wall_time_utc_iso,
        "monotonic_s": f.monotonic_s,
    }


def _edge_from_gps_fields(gps_fields: dict[str, Any], lane: float | None, cam_ok: bool | None) -> Any:
    from risk_models import EdgeObservations

    return EdgeObservations(
        gps_speed_mps=gps_fields.get("gps_speed_mps"),
        gps_fix_quality=gps_fields.get("gps_fix_quality"),
        latitude_deg=gps_fields.get("latitude_deg"),
        longitude_deg=gps_fields.get("longitude_deg"),
        wall_time_utc_iso=gps_fields.get("wall_time_utc_iso"),
        monotonic_s=gps_fields.get("monotonic_s"),
        lane_stability_01=lane,
        camera_healthy=cam_ok,
    )


def camera_sample_to_lane_and_health(cam: Any) -> tuple[float | None, bool | None]:
    """Lane stability proxy: high when camera healthy; lower when unhealthy."""
    if cam is None:
        return None, None
    if cam.healthy:
        return 0.88, True
    return 0.42, False


class EventPipeline:
    """Poll-once (or callable) orchestration; no background threads."""

    def __init__(
        self,
        *,
        vehicle_id: str = "pipeline-dev",
        trip_id: str | None = None,
        output_dir: Path | None = None,
        external_context_path: Path | None = None,
        gps_jsonl_path: Path | None = None,
        mock_gps: bool = True,
        mock_camera: bool = True,
        gps_wait_sec: float | None = None,
        risk_config: dict[str, Any] | None = None,
    ) -> None:
        install_service_import_paths()
        self.vehicle_id = vehicle_id
        self.trip_id = trip_id
        self.output_dir = output_dir or (repo_root() / "outputs")
        self.external_context_path = external_context_path
        self.gps_jsonl_path = gps_jsonl_path
        self.mock_gps = mock_gps
        self.mock_camera = mock_camera
        self._gps_wait = float(gps_wait_sec if gps_wait_sec is not None else (2.0 if mock_gps else 45.0))
        self.risk_config = risk_config

    def obtain_gps_event(self) -> tuple[Any | None, dict[str, Any]]:
        """Returns (optional ``GpsSampleEvent``, fields for edge obs)."""
        from gps_service import GpsService, GpsServiceConfig

        if self.gps_jsonl_path is not None and self.gps_jsonl_path.is_file():
            row = read_last_json_object(self.gps_jsonl_path)
            if row:
                return None, jsonl_row_to_gps_fields(row)
        svc = GpsService(GpsServiceConfig(mock_gps=self.mock_gps), mock_gps=self.mock_gps)
        ev = svc.wait_for_fix(self._gps_wait)
        if ev is None:
            return None, {}
        return ev, gps_sample_to_edge_fields(ev)

    def obtain_camera_event(self) -> Any | None:
        if self.mock_camera:
            return synthetic_camera_sample_event()
        install_service_import_paths()
        from camera_service import CameraService, CameraServiceConfig

        try:
            with CameraService(CameraServiceConfig(index=0, backend="opencv")) as cam:
                ev, _frame = cam.read_frame()
                return ev
        except Exception:
            return synthetic_camera_sample_event()

    def load_external_context(self) -> Any:
        from risk_models import ExternalContext

        if self.external_context_path and self.external_context_path.is_file():
            return load_external_context_file(self.external_context_path)
        return ExternalContext()

    def run_once(self) -> dict[str, Any]:
        from risk_engine import RiskEngine

        gps_ev, gps_fields = self.obtain_gps_event()
        cam_ev = self.obtain_camera_event()
        ext = self.load_external_context()

        lane, cam_ok = camera_sample_to_lane_and_health(cam_ev)
        edge = _edge_from_gps_fields(gps_fields, lane, cam_ok)

        engine = RiskEngine(self.risk_config or {})
        payload = engine.assess(
            vehicle_id=self.vehicle_id,
            trip_id=self.trip_id,
            edge=edge,
            context=ext,
        )
        out = {
            "pipelineVersion": "phase1-local-1",
            "riskEvent": payload.as_dict(),
            "inputsEcho": {
                "gpsSample": gps_ev.as_dict() if gps_ev is not None else {"source": "jsonl_tail", "row": gps_fields},
                "cameraSample": cam_ev.as_dict() if cam_ev is not None else None,
                "externalContext": {k: v for k, v in asdict(ext).items() if v is not None},
            },
        }
        return out


def write_sink(combined: dict[str, Any], output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    path = output_dir / f"pipeline_run_{stamp}_{uuid.uuid4().hex[:8]}.json"
    path.write_text(json.dumps(combined, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
