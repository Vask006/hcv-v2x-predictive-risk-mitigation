# cloud-api (Phase 1 adapters + client)

## Overview

Receives edge risk events and supports cloud-side analytics, dashboarding, and fleet visibility. **Today** the FastAPI ingest server lives in **`jetson-hcv-risk-poc/cloud/api`**. This folder holds a **client-side adapter** and **stdlib HTTP client** so `services/pipeline` output can POST to that API without changing the server.

## Safest integration path

**Keep** the existing FastAPI app in **`jetson-hcv-risk-poc/cloud/api`** (`POST /v1/events`, `schemas.EventV1`, SQLite/Postgres). It already validates and stores payloads unchanged.

The **`services/pipeline`** output is a **different analytics shape** (`riskEvent` camelCase, nested `riskAssessment` / `mitigation`). It **cannot** be ingested with **no change**.

**Minimal Phase 1 approach:** add a **client-side adapter** here (`src/adapter.py`) that maps `combined` pipeline JSON → **`EventV1`-compatible snake_case dict**, then POST with **`src/client.py`** (stdlib `urllib`, same pattern as `jetson-hcv-risk-poc/edge/uploader/client.py`). **No server edits** required → backward compatible for all existing POC edge uploads and tests.

## Schema mismatches (pipeline `riskEvent` vs `EventV1`)

| Pipeline / risk-engine | `EventV1` (POC API) | Adapter behavior |
|------------------------|---------------------|------------------|
| `vehicleId` | `device_id` | Renamed |
| `timestamp` | `recorded_at` | Parsed to ISO datetime string |
| `edgeObservations` (flat) | `gps` object (`latitude_deg`, `longitude_deg`, …) | Subset mapped; missing lat/lon → **0.0** + `adapter.gps_*_defaulted` reason codes |
| `riskAssessment.riskScore` | `risk.score` | Copied, clamped [0,1] |
| `riskAssessment.severity` | `risk.band` | Same vocabulary; unknown → `none` |
| `reasonCodes` (top-level) | `risk.reason_codes` | Merged with adapter diagnostics |
| `tripId`, `externalContext`, `mitigation`, `hazardType` | *(no top-level fields)* | Folded into **`perception_summary`** for audit/trace |
| `eventId` (camelCase) | `event_id` (UUID) | String UUID; invalid/missing → regenerate + reason |

`schema_version`, `media`, and optional `perception_summary` / `gps` optional fields follow the same shape as **`jetson-hcv-risk-poc/contracts/event_v1.json`** (FastAPI `schemas.EventV1`). A documentation mirror lives at **`services/shared/contracts/edge_event_v1.json`** — keep them in sync when the ingest contract changes.

## Files (this folder)

| Path | Role |
|------|------|
| `src/adapter.py` | `combined_pipeline_to_event_v1(combined)` → `dict` for JSON POST |
| `src/client.py` | `post_event_v1(base_url, body, ...)` → `PostResult` |

The **authoritative** FastAPI implementation remains under **`jetson-hcv-risk-poc/cloud/api/`** (`main.py`, `schemas.py`, `database.py`). This repo folder is the **adapter + thin HTTP client** until the server is relocated under `services/` in a later phase.

## POST from the pipeline (one command)

1. Start the POC API (from repo):

```powershell
cd jetson-hcv-risk-poc/cloud/api
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

2. Run the pipeline with ingest (from repo root):

```powershell
python services/pipeline/src/pipeline_runner.py --no-external-context --post-ingest --ingest-base-url http://127.0.0.1:8000
```

## POST manually (Python)

```python
import sys
from pathlib import Path

root = Path(".../hcv-v2x-predictive-risk-mitigation").resolve()
sys.path.insert(0, str(root / "services/pipeline/src"))
sys.path.insert(0, str(root / "services/cloud-api/src"))

from event_pipeline import EventPipeline, install_service_import_paths
from adapter import combined_pipeline_to_event_v1
from client import post_event_v1

install_service_import_paths()
combined = EventPipeline(mock_gps=True, mock_camera=True).run_once()
body = combined_pipeline_to_event_v1(combined)
print(post_event_v1("http://127.0.0.1:8000", body))
```

## Tests

```powershell
cd services/cloud-api
python -m pytest tests -v
```

## Phase 1 scope

- No new FastAPI routes required for ingest.
- Optional API key header supported (`X-API-Key`) same as POC uploader.
- Future: move `jetson-hcv-risk-poc/cloud/api` into `services/cloud-api/server/` and keep adapters for compatibility — out of scope here.
