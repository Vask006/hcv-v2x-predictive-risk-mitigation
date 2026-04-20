# models

Placeholder for **shared typed models** (Pydantic v2 or dataclasses) used by more than one service—for example:

- Normalized **GPS fix** row (post-JSONL parse) shared by `gps-service` emitters and `risk-engine` consumers.
- **Risk assessment** DTO shared if `risk-engine` and an orchestrator both import the same type.

## Phase 1 guidance

- Today, `jetson-hcv-risk-poc/cloud/api/schemas.py` defines `EventV1` **only on the server**. Edge code builds plain `dict` in `edge/app/edge_runtime.py`.
- When migrating, **either** lift `EventV1` / `GPSModel` / `RiskModel` into a small installable package here **or** generate Python from JSON Schema—pick one approach per repo convention and document it in `docs/service-migration-plan.md`.

No Python modules are required in this folder until the first extraction lands.
