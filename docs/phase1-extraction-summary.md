# Phase 1 service extraction — final validation summary

Date: 2026-04-20  
Audience: engineers validating the Phase 1 baseline against the **Jetson POC** (`jetson-hcv-risk-poc`).

## What was created (monorepo `services/`)

| Area | Location | Role |
|------|-----------|------|
| Camera | `services/camera-service/` | `OpenCVCameraReader`, `CameraSampleEvent` (`camera.sample.v1`), `CameraService` / config |
| GNSS | `services/gps-service/` | NMEA parse, serial + mock, `GpsSampleEvent` (`gps.sample.v1`), `GpsService` |
| Risk (analytics) | `services/risk-engine/` | Typed `EdgeObservations` + `ExternalContext` → `RiskEngine.assess` → `RiskEventPayload.as_dict()` (camelCase analytics, **not** `event_v1`) |
| Local orchestration | `services/pipeline/` | `event_pipeline.EventPipeline` wires GPS + camera + optional JSON context → risk-engine → `outputs/pipeline_run_*.json`; CLI `src/pipeline_runner.py` |
| Cloud bridge | `services/cloud-api/` | `adapter.combined_pipeline_to_event_v1` + `client.post_event_v1` for **existing** POC FastAPI |
| Shared | `services/shared/` | JSON Schema mirror `contracts/edge_event_v1.json`, README scaffolds for `models/`, `utils/` |
| Docs / scripts | `docs/`, `scripts/` | e.g. `run-local-phase1.md`, `refactor-status.md`, `run_phase1_mock.py` |

Flat **`src/`** modules + `pyproject.toml` per service (no shared Python package root); the pipeline calls `install_service_import_paths()` to prepend each `services/*/src` to `sys.path`.

## What was reused from `jetson-hcv-risk-poc`

| POC asset | Reuse |
|-----------|--------|
| `edge/camera_service/capture.py` | Facade: when monorepo `services/camera-service/src` exists, delegates to `OpenCVCameraReader` / models; else legacy inline capture |
| `edge/gps_service/reader.py` | Same pattern for `services/gps-service/src` |
| `edge/app/recording_*.py`, `device_connectivity.py`, `phase0_smoke.py` | Still import **edge** `camera_service` / `gps_service` (transitively hit shared `src/` on device with full repo) |
| `edge/app/edge_runtime.py` | Continuous loop: default **legacy** `risk_engine/scorer.py`; optional **`services/risk-engine`** via `risk_engine/service_adapter.py` + feature flag (fallback to legacy on error). Same `event_v1`, queue, upload. |
| `jetson-hcv-risk-poc/cloud/api/` | **Authoritative** `POST /v1/events`, `schemas.EventV1`, DB — adapter targets this API only |

## What remains in the old folder (by design)

- **Full edge runtime**: recording, connectivity probes, `edge_runtime`, perception adapter, **POC** `risk_engine/scorer.py` + `context_provider.py`, uploader, deploy scripts under `jetson-hcv-risk-poc/edge/`.
- **Contracts**: canonical **`jetson-hcv-risk-poc/contracts/event_v1.json`** for ingest.
- **Cloud**: FastAPI app stays under `jetson-hcv-risk-poc/cloud/api/` until a later relocation.

## What is now runnable (verified paths)

| Command / entry | Validates |
|-----------------|-----------|
| `python scripts/run_phase1_mock.py` (repo root) | Pipeline mock end-to-end → `outputs/` |
| `python services/pipeline/src/pipeline_runner.py --help` | CLI and `install_service_import_paths()` |
| `cd services/camera-service && python -m pytest tests -q` | Camera models / reader (where tests cover) |
| `cd services/gps-service && python -m pytest tests -q` | GPS models / parse |
| `cd services/risk-engine && python -m pytest tests -q` | Rules + `RiskEngine` |
| `cd services/pipeline && python -m pytest tests -q` | JSONL tail + sink |
| `cd services/cloud-api && python -m pytest tests -q` | Adapter → `EventV1` dict shape |
| `cd jetson-hcv-risk-poc/cloud/api && python -m uvicorn main:app --host 127.0.0.1 --port 8000` | POC API for optional `--post-ingest` |

**Imports / paths:** `event_pipeline.install_service_import_paths()` requires a checkout whose parents include `services/camera-service/src`, `services/gps-service/src`, and `services/risk-engine/src` together (standard monorepo layout). Pipeline does **not** import `jetson-hcv-risk-poc`; optional `--post-ingest` adds `services/cloud-api/src` only.

## Event model consistency (explicit layering)

There are **three** distinct shapes; naming overlap is intentional but easy to confuse:

1. **Sensor samples (service-native)**  
   - `camera.sample.v1` — `CameraSampleEvent.as_dict()`  
   - `gps.sample.v1` — `GpsSampleEvent.as_dict()`  
   Used in pipeline `inputsEcho` and for future fusion; **not** POST bodies to the POC API.

2. **Analytics risk event (services/risk-engine)**  
   - `RiskEventPayload.as_dict()` — camelCase (`vehicleId`, `edgeObservations`, `riskAssessment`, …)  
   - `edgeObservations` keys are **snake_case** Python field names from `EdgeObservations` (e.g. `gps_speed_mps`, `latitude_deg`).

3. **Ingest contract (POC cloud)**  
   - `EventV1` — snake_case top-level (`device_id`, `recorded_at`, `gps`, `risk`, …)  
   - **`services/cloud-api/src/adapter.py`** maps (2) → (3); defaults missing lat/lon to `0.0` and appends `adapter.*` reason codes.

**Duplicate schema files:** `jetson-hcv-risk-poc/contracts/event_v1.json` and `services/shared/contracts/edge_event_v1.json` describe the **same ingest shape** (minor metadata / line-ending differences). **Canonical for the running server + Pydantic models:** the Jetson repo copy. Update both when the contract changes.

## Dead files / confusion (audit)

- **No orphaned service modules** required for the pipeline; `cloud-api/src/.gitkeep` is an empty placeholder only.
- **`.pytest_cache/`** under services: local test artifacts — not part of the deliverable baseline (prefer `.gitignore` in CI, not deleted here).
- **“Two risk engines”:** POC `edge/risk_engine/scorer.py` vs `services/risk-engine` — different rule semantics; runtime can select service path via flag with legacy fallback. See `docs/runtime-unification-plan.md`.

## Current limitations (Phase 1 baseline)

- **`sys.path` injection** instead of pinned `pip install -e` on Jetson for every service.
- **Pipeline** does not emit `event_v1` directly; requires adapter for POC cloud.
- **`edge_runtime`** defaults to dict-based `score_risk`; optional `RiskEngine.assess` behind flag + adapter (`docs/runtime-unification-plan.md`).
- **`--live-camera` / `--real-gps`** depend on environment (OpenCV build, serial port, permissions).
- **JSONL → edge fields:** `jsonl_row_to_gps_fields` maps POC keys (`wall_utc`, `mono_s`, `fix_quality`, optional `speed_mps`); rows missing optional fields are fine.

## Recommended next implementation step

1. **Field trial** optional service risk path on Jetson (`use_service_adapter: true` on a staging config); review logs and queued `risk` blocks vs legacy.  
2. **Pin services on the Jetson venv** with `pip install -e` for `camera-service`, `gps-service`, `risk-engine` (and optionally `pipeline`), then simplify POC facades / adapter imports.  
3. Keep **one** contract workflow: change **`jetson-hcv-risk-poc/contracts/event_v1.json`** first, then copy/sync to **`services/shared/contracts/edge_event_v1.json`**.

---

## Blockers and assumptions

**Assumptions**

- Developers run commands from the **monorepo root** (or `services/<name>/` for pytest) with the full `services/` tree present.
- Jetson production path continues to use **`python -m app.edge_runtime`** from `jetson-hcv-risk-poc/edge` per existing deploy scripts; no requirement to run `services/pipeline` on-vehicle for Phase 1.

**Non-blockers (known gaps)**

- `services/shared/models/` and `utils/` are README scaffolds only — not required for runnable Phase 1.
- Optional `--post-ingest` requires the POC API running and reachable; failure modes are HTTP errors only.

**If something fails**

- `RuntimeError` from `install_service_import_paths`: not in monorepo layout or missing a service `src/` directory.  
- Adapter / API 422: compare POST body to `schemas.EventV1` in `jetson-hcv-risk-poc/cloud/api/schemas.py`.
