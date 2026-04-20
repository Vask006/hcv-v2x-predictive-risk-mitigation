# shared

Cross-cutting artifacts for edge and cloud services in this repository: **JSON contracts**, **shared data models** (Pydantic/dataclasses when introduced), and **utilities** (config loading, paths, time helpers) that should not be duplicated per service.

## Phase 1 rule

Anything placed here must remain **compatible with the running POC** in `jetson-hcv-risk-poc/` until callers are switched: prefer **copy-then-align** for schemas (`edge_event_v1.json` tracks the edge emission shape aligned with POC `contracts/event_v1.json`).

## Layout

| Path | Role |
|------|------|
| `contracts/` | JSON Schema and future OpenAPI fragments shared by edge emitters and cloud ingest |
| `models/` | Typed models shared between services (empty scaffold—see `models/README.md`) |
| `utils/` | Shared non-domain helpers (empty scaffold—see `utils/README.md`) |
