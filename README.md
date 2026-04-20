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

This repository is currently in early proof-of-concept setup.

### Implemented

- repository structure aligned to major invention modules
- architecture and Phase 1 documentation
- service placeholder modules
- sample event payloads for demo and design work

### In Progress

- GPS ingestion service
- camera ingestion service
- baseline risk engine
- cloud event API

### Simulated in Phase 1

- V2V and V2I cooperative context
- weather and infrastructure hazard signals
- selected fleet-side visibility flows

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
│   └── patent-mapping/
├── services/
│   ├── camera-service/
│   ├── gps-service/
│   ├── telemetry-service/
│   ├── risk-engine/
│   ├── v2x-simulator/
│   ├── cloud-api/
│   └── dashboard/
└── data/
    └── sample-events/
```

## Getting Started

1. Clone the repository.
2. Review the Phase 1 scope in [`docs/phase-1-poc-scope.md`](docs/phase-1-poc-scope.md).
3. Review the architecture in [`docs/architecture/architecture-diagram.md`](docs/architecture/architecture-diagram.md).
4. Review the claim mapping in [`docs/patent-mapping/claim-to-poc-mapping.md`](docs/patent-mapping/claim-to-poc-mapping.md).
5. Inspect the sample event payloads under `data/sample-events/`.
6. Begin implementation with the `gps-service`, `camera-service`, `risk-engine`, and `cloud-api` modules.

## Phase 1 POC Scope

Phase 1 is intentionally narrow and demoable.

### In Scope

- GPS feed ingestion
- camera feed ingestion or simulation
- normalized event model for edge inputs
- local risk scoring based on simple rules and thresholds
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

## Current Implementation Intent

This repository is being organized so each major module can evolve independently:

- `services/camera-service` handles frame capture and metadata extraction
- `services/gps-service` handles location, speed, route, and time signals
- `services/telemetry-service` normalizes edge events
- `services/risk-engine` computes risk scores and hazard classifications
- `services/v2x-simulator` injects cooperative safety messages
- `services/cloud-api` receives and stores events for downstream analytics
- `services/dashboard` visualizes trips, risk states, and alerts

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
5. the cloud API receives the event package
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

### Foundation
- finalize repo structure
- define event contracts
- add simple service stubs

### Edge Ingestion
- implement Jetson camera and GPS ingestion
- add local event normalization
- add baseline risk rules

### Cloud Integration
- expose cloud API endpoint
- add dashboard-ready summaries
- add repeatable demo scripts

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

This repo is not just a code folder. It is the implementation record for a patent-aligned predictive safety platform for heavy commercial vehicles. The structure is designed to support technical development, demonstrations, adoption conversations, and future productization.
