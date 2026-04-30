# HCV V2X Predictive Risk Mitigation

Production-oriented monorepo for heavy commercial vehicle safety intelligence, combining onboard sensing, local risk computation, and cloud ingestion APIs.

## Repository Goals

- Maintain clear, professional service boundaries.
- Keep runtime contracts explicit and versioned.
- Support local development and CI-friendly testing.
- Enable incremental expansion toward V2X-enhanced risk mitigation.

## Repository Structure

```text
.
├── README.md
├── docs/
│   ├── architecture/
│   └── demo/
├── services/
│   ├── camera-service/
│   ├── gps-service/
│   ├── risk-engine/
│   ├── pipeline/
│   ├── cloud-api/
│   ├── telemetry-service/
│   ├── v2x-simulator/
│   └── dashboard/
├── data/
│   └── sample-events/
├── scripts/
└── outputs/
```

## Core Services

- `services/camera-service`: frame capture and camera health metadata.
- `services/gps-service`: GNSS parsing, fix modeling, and service interface.
- `services/risk-engine`: deterministic risk scoring and mitigation output.
- `services/pipeline`: local orchestration across GPS, camera, and risk engine.
- `services/cloud-api`: ingest adapter/client plus API server module.

## Quick Start

1. Use Python 3.10+.
2. Run service tests:
   - `cd services/gps-service && python -m pytest tests -q`
   - `cd services/camera-service && python -m pytest tests -q`
   - `cd services/risk-engine && python -m pytest tests -q`
   - `cd services/cloud-api && python -m pytest tests -q`
   - `cd services/pipeline && python -m pytest tests -q`
3. Run the local pipeline from repo root:
   - `python scripts/run_local_pipeline.py`

## Documentation

- Architecture: `docs/architecture/architecture-diagram.md`
- Demo workflow: `docs/demo/demo-workflow.md`
- Service details: each `services/*/README.md`
