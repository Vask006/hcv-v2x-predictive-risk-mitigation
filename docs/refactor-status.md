# Jetson POC ↔ shared services refactor status

Last reviewed: 2026-04-19

This document tracks how `jetson-hcv-risk-poc` relates to the extracted packages under `services/` after the camera, GPS, and risk-engine services were added. The priority is **in-vehicle safety**, **backward compatibility**, and **no regressions** to the proven edge workflow (record → runtime → upload).

## Summary

| Area | POC entry / facade | Uses `services/...` today? | Notes |
|------|--------------------|----------------------------|--------|
| Camera | `jetson-hcv-risk-poc/edge/camera_service/capture.py` | **Yes** (monorepo) | Adds `services/camera-service/src` to `sys.path` and wraps `OpenCVCameraReader`. Legacy inline path if repo has no `services/`. |
| GPS / NMEA | `jetson-hcv-risk-poc/edge/gps_service/reader.py` | **Yes** (monorepo) | Same pattern: `services/gps-service/src` + aliases (`GPSReader` → `GpsSerialReader`, etc.). Legacy inline if no `services/`. |
| Risk | `jetson-hcv-risk-poc/edge/risk_engine/scorer.py` | **No** | **Different contract** from `services/risk-engine` (dict-based perception scoring vs typed `RiskEngine` + `EdgeObservations`). Do not swap without an adapter and contract tests. |

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

- **POC**: `edge/risk_engine/scorer.py` — `score_risk(gps: dict, perception: dict, context: dict, ...)` returning `RiskAssessment` with bands `none`…`critical`, tuned for Phase 1 edge events and `MockContextProvider` shape (`weather_risk`, `traffic_risk`, `road_risk`).
- **Service**: `services/risk-engine/src/risk_engine.py` — `RiskEngine.assess(..., edge: EdgeObservations, context: ExternalContext, ...)` producing `RiskEventPayload` / camelCase `as_dict()` output, rule set in `risk_rules.py` (speed/curve/surface, lane+hazard, GPS/camera penalties, etc.).

These are **not API-compatible**. `edge/app/edge_runtime.py` and `tests/test_phase1_runtime_components.py` depend on the POC scorer. **Migration later** requires:

1. A **legacy adapter** mapping last GPS JSONL row + perception adapter output + context snapshot → `EdgeObservations` / `ExternalContext`, **or** evolving the edge event schema to the service payload.
2. Golden tests comparing bands / reason codes / fleet_alert behavior **before** switching production Jetson images.
3. Coordination with cloud ingestion if event JSON shape changes.

### `edge/risk_engine/context_provider.py`

- Stays POC-local (mock V2X-style context). Not duplicated in `services/risk-engine` (service expects `ExternalContext` dataclass fields, not identical to `ContextSnapshot.as_dict()` without mapping).

### Recording / JSONL shaping

- **`edge/app/recording_gps_writer.py`** — Owns JSONL row keys (`wall_utc`, `mono_s`, …). Reader/parser already shared via `gps_service.reader`; row format is a **separate contract** from `gps_models.GpsSampleEvent.as_dict()`. Consolidation is optional and touches on-disk format → **higher risk**, defer.

### Standalone clone of `jetson-hcv-risk-poc` only

- If the tree is copied **without** sibling `services/`, camera and GPS facades use **legacy inline** implementations (camera without `video_path` replay; GPS NMEA subset aligned with older POC). Behavior is preserved for that layout.

## Temporary technical debt (accepted)

1. **`sys.path` injection** from facades into `services/*/src` — Works for POC and tests; proper fix is **installable packages** (`pip install -e ./services/camera-service`, etc.) with stable module names (`hcv_camera_service` or similar) so path hacking can be removed.
2. **Dual risk implementations** — POC dict scorer vs service typed engine; until adapter + tests exist, two sources of truth for “risk” semantics.
3. **TODOs in recording modules** — Some referred to “prefer services” even where the reader/capture path already delegates; docstrings were aligned to avoid mistaken deep refactors (see git diff for `recording_video.py` / `recording_gps_writer.py`).

## What should be migrated later (ordered by benefit / risk)

1. **Packaged installs** for camera/gps (and optionally risk) on Jetson images — removes path injection; single import path.
2. **Risk**: adapter + parity tests + optional feature flag to call `RiskEngine` from edge runtime.
3. **GPS JSONL**: optional alignment with shared contracts (`services/shared/contracts`) if cloud and edge both agree on schema versioning.
4. **Centralize monorepo discovery** — small shared helper used by both facades (only if path bugs appear; otherwise low priority).

## Verification

From repo root, with `services/` present:

```bash
cd jetson-hcv-risk-poc
python -m pytest tests/test_gps_nmea.py tests/test_phase1_runtime_components.py -q
```

These exercises NMEA parsing (via facade → service) and POC `score_risk` + event queue.
