# HCV V2X Predictive Risk Mitigation

Integrated V2X-based, cloud-enhanced predictive risk mitigation system for heavy commercial vehicles (HCVs).

## Overview

This repository is the product and proof-of-concept workspace for an intelligent safety platform that combines:

- onboard sensing
- edge intelligence
- V2X communication
- cloud analytics
- predictive risk mitigation workflows

The goal is to move from reactive vehicle safety to proactive and cooperative risk mitigation for trucks, buses, and fleet-operated heavy vehicles.

## Current Status

This repository is no longer just a concept scaffold. It now contains:

- a **working Jetson-based POC baseline** under `jetson-hcv-risk-poc/`
- **real camera and GPS capture paths** used for on-device and in-vehicle testing
- **extracted shared services** under `services/` for camera, GPS, risk, pipeline, and cloud bridging
- **migration and refactor documentation** describing how the old runtime and new service-oriented structure are being unified

### Working Baseline

The current operational baseline remains:

- `jetson-hcv-risk-poc/edge/...`
- queue and upload flow
- deployment scripts and systemd units
- cloud ingest API under `jetson-hcv-risk-poc/cloud/api`

### Shared / Extracted Services

The repo now also includes:

- `services/camera-service`
- `services/gps-service`
- `services/risk-engine`
- `services/pipeline`
- `services/cloud-api`
- `services/shared`

### Current Unification State

- camera path is already bridged into shared service code where safe
- GPS path is already bridged into shared service code where safe
- risk-engine extraction is implemented, but full runtime unification is still in progress
- the old Jetson runtime remains the safest operational path while service reuse expands incrementally

## Problem Statement

Heavy commercial vehicles operate under higher safety risk because of:

- large vehicle mass and longer braking distances
- blind spots and limited maneuverability
- long driving hours and fatigue risk
- changing traffic, road, and weather conditions
- fragmented data across vehicle, edge, and fleet platforms

Traditional systems such as ABS, ESC, and standard ADAS are valuable, but they often remain local and reactive. This project focuses on predicting unsafe situations earlier and coordinating mitigation across the vehicle, surrounding environment, and cloud services.

## Patent-Aligned System Vision

The system is organized around the major invention modules:

1. **Onboard Vehicle Unit (OBU)**
   - camera, GPS, IMU, CAN/vehicle telemetry, driver-state, braking/steering inputs
2. **Edge Intelligence Layer**
   - sensor fusion, local preprocessing, event detection, risk scoring
3. **V2X Communication Layer**
   - V2V, V2I, V2N, and optional V2P message exchange or simulation
4. **Cloud Predictive Analytics Platform**
   - event ingestion, correlation, forecasting, fleet-level risk analysis
5. **Mitigation and Fleet Interface**
   - alerts, recommendations, dashboards, policy controls, reporting

See:

- [`docs/phase-1-poc-scope.md`](docs/phase-1-poc-scope.md)
- [`docs/architecture/architecture-diagram.md`](docs/architecture/architecture-diagram.md)
- [`docs/patent-mapping/claim-to-poc-mapping.md`](docs/patent-mapping/claim-to-poc-mapping.md)
- [`docs/demo/demo-workflow.md`](docs/demo/demo-workflow.md)

## Target POC Environment

The initial edge proof of concept is intended to run on NVIDIA Jetson hardware with:

- camera input
- GPS input
- local edge event processing
- cloud event publishing

This repository represents a patent-aligned proof-of-concept workspace and does not yet implement every production-scale component of the full system.

## Repository Structure

```text
.
├── README.md
├── docs/
│   ├── architecture/
│   ├── demo/
│   ├── patent-mapping/
│   ├── current-jetson-poc-status.md
│   ├── service-migration-plan.md
│   ├── refactor-status.md
│   └── phase1-extraction-summary.md
├── data/
│   └── sample-events/
├── outputs/
├── services/
│   ├── camera-service/
│   ├── gps-service/
│   ├── risk-engine/
│   ├── pipeline/
│   ├── cloud-api/
│   └── shared/
└── jetson-hcv-risk-poc/
    ├── edge/
    ├── cloud/
    ├── contracts/
    ├── samples/
    ├── tests/
    └── docs/
```

## Architecture State Today

The repo currently has two intentionally overlapping layers:

### 1. Proven Jetson Runtime Layer
This is the currently trusted operational path.

- recording and capture
- queue and upload
- systemd deployment units
- cloud ingest API contract

### 2. Extracted Service Layer
This is the modularization and unification path.

- reusable camera and GPS services
- reusable rule-based risk engine
- local event pipeline
- cloud adapter for current API contract

This transition state is temporary by design. The strategy is to unify the old runtime with the new services incrementally, without breaking the proven Jetson workflow.

## Getting Started

Choose one of these paths depending on what you want to do.

### Path A — Understand the current architecture
1. Review the Phase 1 scope in [`docs/phase-1-poc-scope.md`](docs/phase-1-poc-scope.md).
2. Review the architecture in [`docs/architecture/architecture-diagram.md`](docs/architecture/architecture-diagram.md).
3. Review the current migration state in:
   - [`docs/current-jetson-poc-status.md`](docs/current-jetson-poc-status.md)
   - [`docs/service-migration-plan.md`](docs/service-migration-plan.md)
   - [`docs/refactor-status.md`](docs/refactor-status.md)
   - [`docs/phase1-extraction-summary.md`](docs/phase1-extraction-summary.md)

### Path B — Run the extracted Phase 1 service pipeline locally
1. Inspect `services/pipeline/`
2. Review `docs/run-local-phase1.md`
3. Run the mock/local verification path described there

### Path C — Work with the existing Jetson baseline
1. Go to `jetson-hcv-risk-poc/`
2. Review `jetson-hcv-risk-poc/README.md`
3. Use the documented Jetson runtime, recording, and cloud API steps from that subtree

## Phase 1 POC Scope

Phase 1 is intentionally narrow and demoable.

### In Scope

- GPS feed ingestion
- camera feed ingestion or simulation
- normalized event model for edge inputs
- local risk scoring based on simple rules and thresholds
- queueable/uploadable edge risk events
- cloud/event API ingestion
- simulated V2X and environmental signals
- dashboard-ready output or structured logs
- one end-to-end demo workflow

### Out of Scope for Phase 1

- production-grade V2X hardware stack
- full CAN integration across real vehicles
- advanced ML model training pipeline
- large-scale fleet orchestration
- regulatory-grade audit workflows

## Current Implementation Layout

### Jetson Baseline

`jetson-hcv-risk-poc` currently contains the working baseline for:

- camera capture
- GPS ingestion
- session recording
- edge runtime
- event queueing
- cloud upload
- cloud API
- deployment and operational scripts

### Shared Services

The extracted services are being positioned as the long-term reusable modules:

- `services/camera-service` handles frame capture and camera metadata
- `services/gps-service` handles serial/mock GNSS and normalized GPS sample events
- `services/risk-engine` computes rule-based risk payloads from normalized inputs
- `services/pipeline` provides a simple local event pipeline for Phase 1 validation
- `services/cloud-api` adapts service-side outputs to the current POC cloud ingest contract
- `services/shared` contains shared contracts and supporting scaffolding

## Example Phase 1 Demo Scenario

A heavy commercial vehicle is approaching a curved wet road segment.

- GPS indicates vehicle speed and upcoming curve distance
- camera or edge logic detects reduced lane stability
- simulated infrastructure or weather context signals slippery conditions
- the risk engine raises the risk score
- the cloud API receives the event
- the system recommends speed reduction and surfaces a fleet alert

## Demo Workflow

A simple first demonstration should show:

1. GPS and camera or edge data are ingested
2. a local risk event is detected
3. a simulated V2X or weather/infrastructure event increases risk context
4. the risk engine computes a higher score
5. the event is queued, written locally, or posted to the cloud API
6. a mitigation recommendation is produced

Example outputs include:

- driver alert
- reduced-speed recommendation
- high-risk zone warning
- fleet alert entry

## Sample Data

Sample event payloads are included under:

- [`data/sample-events/gps-sample.json`](data/sample-events/gps-sample.json)
- [`data/sample-events/edge-risk-event-v1.json`](data/sample-events/edge-risk-event-v1.json)

## Near-Term Roadmap

### Baseline Preservation
- keep the Jetson runtime stable and runnable
- preserve queue, upload, and deployment behavior
- avoid regressions in proven camera/GPS flows

### Runtime Unification
- increase reuse of extracted services from the old runtime
- unify risk-engine behavior through adapters and parity tests
- reduce duplicated logic between old and new paths

### Packaging and Installation
- move toward installable service packages
- reduce `sys.path`-based import handling
- make Jetson and development setup more consistent

### Cooperative Intelligence Expansion
- expand with simulated or real V2X inputs
- improve predictive models
- add measurable evaluation metrics

## Product Outcomes to Measure

- risk events detected per trip
- alert generation latency
- edge-to-cloud delivery time
- high-risk zone prediction count
- harsh braking / lane drift / rollover proxy detections
- percentage of trips with mitigation recommendations

## Why This Repository Matters

This repo is not just a code folder. It is the implementation record for a patent-aligned predictive safety platform for heavy commercial vehicles. It now contains both:

- a working Jetson-based baseline used for real capture/testing
- a modular service-oriented extraction path for long-term productization

That combination makes the repository useful for technical development, demonstrations, adoption conversations, and future productization.