from __future__ import annotations

import json
from pathlib import Path

from event_pipeline import EventPipeline, install_service_import_paths, write_sink


def test_pipeline_run_once_mock_writes_json(tmp_path: Path) -> None:
    install_service_import_paths()
    ext = Path(__file__).resolve().parents[1] / "examples" / "external_context_sample.json"
    pipe = EventPipeline(
        vehicle_id="test-veh",
        trip_id="test-trip",
        output_dir=tmp_path,
        external_context_path=ext if ext.is_file() else None,
        gps_jsonl_path=None,
        mock_gps=True,
        mock_camera=True,
        gps_wait_sec=1.0,
    )
    out = pipe.run_once()
    assert "riskEvent" in out and "inputsEcho" in out
    assert out["riskEvent"]["vehicleId"] == "test-veh"
    path = write_sink(out, tmp_path)
    assert path.is_file()
    loaded = json.loads(path.read_text(encoding="utf-8"))
    assert loaded["pipelineVersion"] == "phase1-local-1"


def test_gps_jsonl_tail_overrides_mock(tmp_path: Path) -> None:
    install_service_import_paths()
    gpsf = tmp_path / "gps.jsonl"
    gpsf.write_text(
        '{"wall_utc":"2026-04-19T10:00:00.000000Z","mono_s":1.0,'
        '"latitude_deg":48.0,"longitude_deg":11.0,"fix_quality":1,'
        '"raw":"$TEST*"}\n',
        encoding="utf-8",
    )
    pipe = EventPipeline(
        vehicle_id="v",
        trip_id="t",
        output_dir=tmp_path,
        external_context_path=None,
        gps_jsonl_path=gpsf,
        mock_gps=True,
        mock_camera=True,
    )
    out = pipe.run_once()
    echo = out["inputsEcho"]["gpsSample"]
    assert echo.get("source") == "jsonl_tail"
