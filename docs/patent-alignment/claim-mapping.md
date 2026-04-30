# Patent Alignment Mapping

## Purpose

This document maps repository implementation components to the HCV V2X predictive risk mitigation system concept for technical traceability and demonstration review.

## System Element Mapping

| System Element | Repository Component | Implementation Status | Evidence Path | Remaining Gap |
|---|---|---|---|---|
| Onboard Vehicle Unit | `services/gps-service`, `services/camera-service` | Implemented for local/demo workflows | `services/gps-service/src`, `services/camera-service/src` | Live vehicle integration hardening |
| Camera Sensing | `services/camera-service` | Implemented | `services/camera-service/src/camera_service.py` | Advanced CV models |
| GPS / Position Sensing | `services/gps-service` | Implemented | `services/gps-service/src/gps_service.py` | Real hardware validation matrix |
| Vehicle Telemetry | `services/telemetry-service` | Implemented | `services/telemetry-service/src` | CAN/OBD-II adapter |
| Sensor Fusion / Normalization | `services/telemetry-service` + pipeline | Implemented | `services/telemetry-service/src/telemetry_normalizer.py` | Expanded sensor schema support |
| Edge Risk Assessment | `services/risk-engine` | Implemented | `services/risk-engine/src/risk_engine.py` | Model-based prediction extension |
| V2X Communication | `services/v2x-simulator` | Simulated implementation | `services/v2x-simulator/src` | Live C-V2X/DSRC integration |
| Cloud Ingestion | `services/cloud-api/server` | Implemented | `services/cloud-api/server/main.py` | Authn/authz hardening |
| Cloud Analytics / Review | `services/cloud-api/server` + dashboard | Implemented for local review | `services/dashboard/app.py` | Fleet-scale analytics |
| Driver Mitigation | `services/risk-engine` mitigation output | Implemented | `services/risk-engine/src/risk_rules.py` | HMI integration |
| Fleet Notification | `riskEvent.mitigation` + dashboard | Implemented | `services/dashboard/app.py` | Fleet workflow integration |
| Fleet Dashboard | `services/dashboard` | Implemented | `services/dashboard/app.py` | Role-based access and filtering |
| Configurable Risk Thresholds | `RiskEngineConfig` | Implemented | `services/risk-engine/src/risk_models.py` | Runtime config management |
| Demo Evidence Capture | demo scripts + outputs | Implemented | `scripts/run_demo_end_to_end.py`, `docs/demo/demo-evidence-checklist.md` | Automated report packaging |

## Demo Flow

GPS + camera + V2X event -> telemetry/context normalization -> risk engine -> mitigation output -> cloud ingest -> dashboard.

## Known Limitations

- V2X is simulated.
- CAN/OBD-II is not yet connected.
- Camera analytics are lightweight heuristics.
- Cloud API is local-demo oriented.
- No real vehicle control integration.
- No production safety certification.

## Future Production Enhancements

- Jetson live validation
- real GPS hardware validation
- CAN/OBD-II integration
- C-V2X/DSRC/MQTT adapter
- cloud deployment
- fleet analytics
- ML model training
- authentication/device identity
- observability
- cybersecurity hardening
