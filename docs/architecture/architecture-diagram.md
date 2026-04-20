# Architecture Diagram

## High-Level Architecture

```mermaid
flowchart LR
    A[Onboard Vehicle Unit] --> B[Edge Intelligence Layer]
    C[V2X Inputs / Simulation] --> B
    D[Maps / Weather / Infrastructure Context] --> E[Cloud Predictive Platform]
    B --> E
    E --> F[Fleet Dashboard]
    E --> G[Mitigation Engine]
    G --> H[Driver Alert / Recommendation]
    G --> I[Fleet Alert / Policy Response]

    subgraph OBU[Onboard Vehicle Unit]
        A1[Camera]
        A2[GPS]
        A3[Vehicle Telemetry]
        A4[Driver / Motion Signals]
    end

    subgraph EDGE[Edge Intelligence]
        B1[Event Normalization]
        B2[Sensor Fusion]
        B3[Local Risk Scoring]
        B4[Hazard Detection]
    end

    subgraph V2X[V2X Communication]
        C1[V2V]
        C2[V2I]
        C3[V2N]
        C4[V2P Optional]
    end

    subgraph CLOUD[Cloud Platform]
        E1[Event Ingestion API]
        E2[Risk Correlation]
        E3[Trip / Fleet Analytics]
        E4[Policy Evaluation]
    end

    A1 --> B1
    A2 --> B1
    A3 --> B1
    A4 --> B1
    B1 --> B2 --> B3 --> B4
    C1 --> B2
    C2 --> B2
    C3 --> E1
    C4 --> B2
    B4 --> E1
    D --> E2
    E1 --> E2 --> E3 --> E4
```

## Phase 1 Implementation View

```mermaid
flowchart LR
    G[GPS Service] --> T[Telemetry Service]
    C[Camera Service] --> T
    V[V2X Simulator] --> R[Risk Engine]
    T --> R
    R --> A[Cloud API]
    R --> D[Dashboard / Logs]
    A --> D
```

## Planned Service Boundaries

- `camera-service`: frame capture and derived event metadata
- `gps-service`: route, speed, heading, and timestamp ingestion
- `telemetry-service`: normalized event contracts
- `risk-engine`: local scoring and hazard classification
- `v2x-simulator`: cooperative safety event injection for POC use
- `cloud-api`: ingestion endpoint and fleet-side aggregation
- `dashboard`: visualization of trips, alerts, and mitigation outputs
