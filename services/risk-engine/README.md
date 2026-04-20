# risk-engine (Phase 1)

## Overview

Computes local risk scores and hazard classifications from normalized edge inputs and optional cooperative context. **Phase 1** implements transparent rule-based scoring (`RiskEngine`) for the **local pipeline**; the Jetson POC runtime still uses **`edge/risk_engine/scorer.py`** for `event_v1` until an adapter migration. Future work may add predictive models, adaptive thresholds, and fleet-aware correlation.

## Run locally (verify)

**Unit tests** (no `pip install`; `conftest.py` puts `src/` on `sys.path`):

```bash
cd services/risk-engine
python -m pytest tests -q
```

**One-shot assessment** (from `src/` without `pip install`, or use `pip install -e .` from the service directory and run from anywhere):

```bash
cd services/risk-engine/src
python -c "from risk_engine import RiskEngine; from risk_models import EdgeObservations, ExternalContext; p=RiskEngine().assess(vehicle_id='dev', trip_id=None, edge=EdgeObservations(gps_speed_mps=28.0, gps_fix_quality=1, latitude_deg=48.0, longitude_deg=11.0, camera_healthy=True), context=ExternalContext(curve_ahead=True, road_surface='wet')); print(p.as_dict()['riskAssessment'])"
```

For wiring with camera + GPS samples, use **`services/pipeline`** (`docs/run-local-phase1.md`).

## Reference (`jetson-hcv-risk-poc`)

| Area | POC location | Notes |
|------|----------------|------|
| Heuristic scoring (bands, weights) | `edge/risk_engine/scorer.py` | Perception + context + GPS quality |
| Mock context | `edge/risk_engine/context_provider.py` | Sine-wave risks |
| Mock perception | `edge/inference/perception_adapter.py` | Distance / lane / closure |
| Runtime + `event_v1` assembly | `edge/app/edge_runtime.py` | `_build_event`, queue, upload |
| Contract | `contracts/event_v1.json`, `services/shared/contracts/edge_event_v1.json` | Different shape from this package’s payload |

This service produces an **analytics-oriented** `RiskEventPayload` (camelCase JSON) for new edge pipelines. Adapters can map it toward `event_v1` later without changing core rules here.

## Rule summary

| ID | Condition | Effect |
|----|-----------|--------|
| **R1** | `gps_speed_mps ≥ high_speed_mps` (default **25 m/s**) AND `curve_ahead is True` AND `road_surface == "wet"` | Subscore = **1.0**, reason `rule.speed_curve_wet` |
| **R1b** | High speed + curve, surface **not** `"wet"` (dry / unknown / `None`) | Subscore = **0.55**, reason `rule.speed_curve_no_confirmed_wet` |
| **R2** | `lane_stability_01` known and **&lt;** `lane_stability_reduced_below` (default **0.55**) AND `hazard_context_01` **&gt;** `hazard_context_elevated_above` (default **0.40**) | Subscore = product of normalized gaps, reason `rule.lane_instability_hazard` |
| **R3** | Mean of **provided** `hazard_context_01`, `weather_risk_01`, `infrastructure_risk_01` (each 0..1) | Weighted by `weight_context_mean` |
| **P1** | `gps_fix_quality ≤ 0` | GPS penalty subscore (bounded) |
| **P2** | Missing `latitude_deg` or `longitude_deg` | Additional GPS penalty (bounded) |
| **P3** | `camera_healthy is False` | Camera penalty (bounded) |

**Combined score**: weighted sum of subscores (see `RiskEngineConfig` weights), clipped to **\[0, 1\]**.

**Severity**: `none` / `low` / `medium` / `high` / `critical` from configurable thresholds (defaults aligned with POC spirit: 0.2 / 0.45 / 0.70 / 0.85).

**`hazardType`**: Single label chosen by priority (`speed_curve_surface` → `speed_curve_environment` → `lane_hazard_compound` → `degraded_edge_sensing` → `ambient_context` → `nominal`).

All scoring assumptions are documented in **`src/risk_rules.py`** module docstring.

## API

```python
from risk_engine import RiskEngine
from risk_models import EdgeObservations, ExternalContext

engine = RiskEngine()
payload = engine.assess(
    vehicle_id="edge-dev-001",
    trip_id="2026-04-19T10-00-00Z",
    edge=EdgeObservations(
        wall_time_utc_iso="2026-04-19T10:00:05.000000Z",
        gps_speed_mps=26.0,
        lane_stability_01=0.85,
        gps_fix_quality=1,
        latitude_deg=48.12,
        longitude_deg=11.58,
        camera_healthy=True,
    ),
    context=ExternalContext(
        curve_ahead=True,
        road_surface="wet",
        hazard_context_01=0.35,
        weather_risk_01=0.2,
    ),
)
print(payload.as_dict())
```

## Example input / output

**Input (conceptual):** high speed on a wet curve with modest ambient hazard.

**Output (`as_dict()` excerpt):**

```json
{
  "eventId": "<uuid>",
  "vehicleId": "edge-dev-001",
  "tripId": "2026-04-19T10-00-00Z",
  "timestamp": "2026-04-19T10:00:05.000000Z",
  "edgeObservations": {
    "gps_speed_mps": 26.0,
    "gps_fix_quality": 1,
    "latitude_deg": 48.12,
    "longitude_deg": 11.58,
    "wall_time_utc_iso": "2026-04-19T10:00:05.000000Z",
    "lane_stability_01": 0.85,
    "camera_healthy": true
  },
  "externalContext": {
    "curve_ahead": true,
    "road_surface": "wet",
    "hazard_context_01": 0.35,
    "weather_risk_01": 0.2
  },
  "riskAssessment": {
    "riskScore": 0.15,
    "severity": "low",
    "hazardType": "speed_curve_surface"
  },
  "mitigation": {
    "driverAlert": null,
    "fleetNotification": false,
    "recommendedAction": "Continue monitoring; maintain normal vigilance."
  },
  "reasonCodes": ["rule.speed_curve_wet"]
}
```

*(Exact `riskScore` / `severity` depend on weights and context mean.)*

## Files

| File | Role |
|------|------|
| `src/risk_models.py` | `EdgeObservations`, `ExternalContext`, `RiskEngineConfig`, `RiskEventPayload` |
| `src/risk_rules.py` | `compute_subscores`, `combine_score`, `severity_from_score`, `hazard_type_from_subscores`, `mitigation_from_severity` |
| `src/risk_engine.py` | `RiskEngine.assess(...)` |

## Tests

From `services/risk-engine`: `python -m pytest tests -v`

## Migrate next

- Map `GpsSampleEvent.as_dict()` + camera `CameraSampleEvent.as_dict()` into `EdgeObservations` / `ExternalContext` in an orchestrator.
- Optionally bridge `RiskEventPayload` → `event_v1` for `POST /v1/events` compatibility with the existing cloud API.
