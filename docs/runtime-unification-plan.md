# Runtime unification plan (Phase 1 — incremental)

Last updated: 2026-04-20

## Goal

Reduce parallel-system drift between **`jetson-hcv-risk-poc/edge`** (proven vehicle runtime) and **`services/*`** (extracted building blocks) **without** breaking systemd startup, queueing, upload, or `event_v1` cloud shape.

## What was unified (this step)

| Piece | Mechanism |
|-------|-----------|
| **Risk** | `edge/risk_engine/service_adapter.py` maps GPS JSONL row dict + `PerceptionSnapshot.as_dict()` + `ContextSnapshot.as_dict()` → `EdgeObservations` + `ExternalContext`, runs `RiskEngine.assess`, converts back to **`RiskAssessment`** (same type as legacy `score_risk`). |
| **`edge_runtime`** | When `risk_engine.use_service_adapter: true` **or** `HCV_USE_SERVICE_RISK_ENGINE=1`, calls the adapter; on **any** exception, logs a warning and **falls back** to `score_risk` (legacy). Default remains **off**. |

Camera and GPS were already unified via edge facades (`camera_service/capture.py`, `gps_service/reader.py`); unchanged here.

## What stays parallel (for now)

- **Legacy dict scorer** (`edge/risk_engine/scorer.py`) remains the default and the **fallback**.
- **`services/pipeline`** remains a separate local orchestration tool (not wired into systemd).
- **Cloud** remains `jetson-hcv-risk-poc/cloud/api` + optional `services/cloud-api` client adapter for pipeline-shaped JSON only.

## Feature flag behavior

| Source | Effect |
|--------|--------|
| `HCV_USE_SERVICE_RISK_ENGINE=1` / `true` / `yes` / `on` | Force service path **on** (overrides YAML). |
| `HCV_USE_SERVICE_RISK_ENGINE=0` / `false` / `no` / `off` | Force service path **off** (overrides YAML). |
| unset | Use YAML `risk_engine.use_service_adapter` (default `false` in `edge/config/default.yaml`). |

**Monorepo requirement:** `services/risk-engine/src` must exist above `edge/` in the checkout. If missing (standalone POC tree), the adapter raises; runtime catches and falls back.

## Tests that cover the new path

From `jetson-hcv-risk-poc/`:

```bash
python -m pytest tests/test_risk_engine_adapter_parity.py -q
```

Scenarios: nominal low stress, high speed + wet-curve mapping, degraded lane + high ambient context, partial GPS / camera unhealthy, env override for the flag. Tests **skip** if `services/risk-engine/src` is not discoverable (non-monorepo checkout).

## Known limitations

- **Heuristic mapping** from POC dicts to `ExternalContext` (e.g. `weather_risk` → `road_surface == "wet"`, mean context → `hazard_context_01` / `curve_ahead`) is **not** a full semantic match to real map/V2X data.
- **Scores and reason codes** differ between legacy and service engines; parity tests check **practical** alignment (valid bands, rough rank proximity, key rules like GPS penalties / wet curve where applicable), not bitwise equality.
- **Service module load** uses `importlib` under a synthetic name so `services/risk-engine/src` is **appended** to `sys.path` (not prepended), avoiding shadowing of the edge **`risk_engine`** package.

## Recommended next step

1. **Bench on Jetson** with `use_service_adapter: true` on a non-production config copy; compare queued `event_v1` risk blocks and logs against legacy.
2. **`pip install -e services/risk-engine`** on the device venv, then optionally replace `sys.path` append with import from the installed package name (separate small change).
3. **Telemetry**: optional log field `risk_engine_path: legacy|service|service_fallback` in `perception_summary` (future; not implemented to keep this diff minimal).

See also: `docs/refactor-status.md`, `docs/phase1-extraction-summary.md`.
