# Claim-to-POC Mapping

This document maps the major patent-aligned elements to repository modules and expected proof-of-concept coverage.

| Patent / invention element | Repo module or artifact | Phase 1 status | Notes |
|---|---|---:|---|
| Onboard vehicle unit with sensing inputs | `services/camera-service`, `services/gps-service`, `services/telemetry-service` | In scope | Initial implementation can use real GPS and camera, with some simulated telemetry |
| Sensor fusion and edge risk assessment | `services/risk-engine` | In scope | Phase 1 can start rule-based before ML expansion |
| V2X communication for cooperative safety | `services/v2x-simulator` | In scope (simulated) | Real radio stack is not required for first POC |
| Vehicle-to-network / cloud integration | `services/cloud-api` | In scope | Cloud API receives normalized edge events |
| Cloud-based predictive analytics | `services/cloud-api` plus later analytics module | Partial | Phase 1 focuses on event ingestion and simple correlation |
| Forecasting of risk events | `services/risk-engine` | In scope | Initial scoring can represent predictive logic using thresholds and context fusion |
| Driver alerts and mitigation actions | `docs/demo/demo-workflow.md`, dashboard output | In scope | Alerts may be represented as logs, JSON responses, or UI messages |
| Fleet notifications and policy controls | `services/dashboard` and future settings module | Partial | Phase 1 should at least show risk event visibility |
| Infrastructure / map / weather context | sample data and simulator inputs | In scope (simulated) | Useful for demonstrating cooperative and contextual intelligence |
| Regulatory / reporting support | future analytics and reporting modules | Out of scope | Better suited for later phases |

## Interpretation for Phase 1

The purpose of Phase 1 is not to build the full product. It is to create a defensible prototype that proves the core invention path:

1. data captured at the vehicle edge
2. risk computed before an unsafe state fully develops
3. external context influences the decision
4. mitigation output is generated
5. cloud side receives the risk event for fleet visibility

## Coverage Summary

### Fully represented in Phase 1
- onboard sensing
- edge intelligence
- risk scoring
- cloud event ingestion
- mitigation recommendation output

### Partially represented in Phase 1
- V2X through simulation
- fleet policy controls
- predictive analytics depth

### Deferred to later phases
- production V2X stack
- advanced machine learning
- fleet-wide reporting and compliance workflows
