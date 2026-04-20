# Camera Service

## Purpose

Captures camera frames or accepts precomputed camera-derived events for the HCV predictive risk mitigation POC.

## Phase 1 Role

- connect to Jetson camera or replay source
- extract or forward frame metadata
- publish normalized camera events to the telemetry service or risk engine

## Future Scope

- lane drift detection
- visibility quality estimation
- object and hazard cues
- driver-facing camera integration
