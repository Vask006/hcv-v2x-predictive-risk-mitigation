# Jetson POC ↔ shared services refactor status

Last reviewed: 2026-04-20

This document tracks how `jetson-hcv-risk-poc` relates to the extracted packages under `services/` after the camera, GPS, and risk-engine services were added. The priority is **in-vehicle safety**, **backward compatibility**, and **no regressions** to the proven edge workflow (record → runtime → upload).

## Summary

| Area | POC entry / facade | Uses `services/...` today? | Notes |
|------|--------------------|----------------------------|--------|
| Camera | `jetson-hcv-risk-poc/edge/camera_service/capture.py` | **Yes** (monorepo) | Adds `services/camera-service/src` to `sys.path` and wraps `OpenCVCameraReader`. Legacy inline path if repo has no `services/`. |
| GPS / NMEA | `jetson-hcv-risk-poc/edge/gps_service/reader.py` | **Yes** (monorepo) | Same pattern: `services/gps-service/src` + aliases (`GPSReader` → `GpsSerialReader`, etc.). Legacy inline if no `services/`. |
| Risk | `jetson-hcv-risk-poc/edge/risk_engine/scorer.py` + optional `service_adapter.py` | **Optional** | Default: legacy `score_risk`. When `risk_engine.use_service_adapter` or `HCV_USE_SERVICE_RISK_ENGINE=1`, `edge_runtime` calls `services/risk-engine` via adapter; on failure it **falls back** to legacy. See `docs/runtime-unification-plan.md`. |

## What already reuses the new services (low coupling)

These POC modules are **not** expected to import `services/...` directly from app code. They import **edge facades**, which delegate when the monorepo layout is present (`<repo-root>/services/<name>/src` reachable by walking parents from the facade file).

- **`edge/camera_service/capture.py`** — `CameraCapture` compatibility wrapper over `camera_reader.OpenCVCameraReader` + shared `FrameSample` / `CaptureError` when `services/camera-service/src` exists.
- **`edge/gps_service/reader.py`** — Re-exports `GpsSerialReader`, `GpsFix`, `parse_line` / `_parse_line`, `mock_fixes` from `services/gps-service/src` when present.
- **Callers** (unchanged import style; safe for Jetson):
  - `edge/app/device_connectivity.py`, `phase0_smoke.py`, `recording_video.py` → `camera_service.capture`
  - `edge/app/device_connectivity.py`, `phase0_smoke.py`, `gps_signal_test.py`, `recording_gps_writer.py` → `gps_service.reader`
- **`jetson-hcv-risk-poc/tests/test_gps_nmea.py`** — Imports `_parse_line` from `gps_service.reader`; under monorepo that resolves to the shared `gps_reader` implementation.

No change to **deploy / start scripts** was required for this integration; runtime still uses `edge/` on `PYTHONPATH` as before.

## What remains independent (by design or risk)

### Risk scoring (`services/risk-engine` vs POC `risk_engine`)

- **POC (default):** `edge/risk_engine/scorer.py` — `score_risk(gps: dict, perception: dict, context: dict, ...)` returning `RiskAssessment` with bands `none`…`critical`, tuned for Phase 1 edge events and `MockContextProvider` shape (`weather_risk`, `traffic_risk`, `road_risk`).
- **Service (optional):** `services/risk-engine/src/risk_engine.py` — `RiskEngine.assess(..., edge: EdgeObservations, context: ExternalContext, ...)`; bridged by **`edge/risk_engine/service_adapter.py`** back to the same **`RiskAssessment`** type so `edge_runtime` queue/event shape is unchanged.

**Feature flag:** `risk_engine.use_service_adapter` in YAML or `HCV_USE_SERVICE_RISK_ENGINE` env (see `docs/runtime-unification-plan.md`). **Parity tests:** `jetson-hcv-risk-poc/tests/test_risk_engine_adapter_parity.py`.

Remaining **longer-term** work (not required for this step):

1. Tighter semantic mapping from mock perception/context to `ExternalContext` when real V2X/map feeds exist.
2. Bench on-vehicle comparison of queued events before defaulting the flag to **on** in production images.
3. Optional `pip install -e` for `risk-engine` to drop `sys.path` append in the adapter.

### `edge/risk_engine/context_provider.py`

- Stays POC-local (mock V2X-style context). Not duplicated in `services/risk-engine` (service expects `ExternalContext` dataclass fields, not identical to `ContextSnapshot.as_dict()` without mapping).

### Recording / JSONL shaping

- **`edge/app/recording_gps_writer.py`** — Owns JSONL row keys (`wall_utc`, `mono_s`, …). Reader/parser already shared via `gps_service.reader`; row format is a **separate contract** from `gps_models.GpsSampleEvent.as_dict()`. Consolidation is optional and touches on-disk format → **higher risk**, defer.

### Standalone clone of `jetson-hcv-risk-poc` only

- If the tree is copied **without** sibling `services/`, camera and GPS facades use **legacy inline** implementations (camera without `video_path` replay; GPS NMEA subset aligned with older POC). Behavior is preserved for that layout.

## Temporary technical debt (accepted)

1. **`sys.path` injection** from facades into `services/*/src` — Works for POC and tests; proper fix is **installable packages** (`pip install -e ./services/camera-service`, etc.) with stable module names (`hcv_camera_service` or similar) so path hacking can be removed.
2. **Dual risk implementations** — still two rule sets; runtime can choose service via flag, with legacy fallback. Default remains legacy for proven Jetson behavior.
3. **TODOs in recording modules** — Some referred to “prefer services” even where the reader/capture path already delegates; docstrings were aligned to avoid mistaken deep refactors (see git diff for `recording_video.py` / `recording_gps_writer.py`).

## What should be migrated later (ordered by benefit / risk)

1. **Packaged installs** for camera/gps (and optionally risk) on Jetson images — removes path injection; single import path.
2. **Risk**: ~~adapter + parity tests + feature flag~~ **done** for optional `RiskEngine` from `edge_runtime`; next: field trial + optional packaging.
3. **GPS JSONL**: optional alignment with shared contracts (`services/shared/contracts`) if cloud and edge both agree on schema versioning.
4. **Centralize monorepo discovery** — small shared helper used by both facades (only if path bugs appear; otherwise low priority).

## Verification

From repo root, with `services/` present:

```bash
cd jetson-hcv-risk-poc
python -m pytest tests/test_gps_nmea.py tests/test_phase1_runtime_components.py tests/test_risk_engine_adapter_parity.py -q
```

These exercise NMEA parsing (via facade → service), POC `score_risk` + event queue, and optional service risk adapter parity.
