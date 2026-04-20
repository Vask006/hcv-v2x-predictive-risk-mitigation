# Phase 1 POC Scope

## Objective

Build a working proof of concept that demonstrates how onboard sensing, edge intelligence, simulated V2X context, and cloud ingestion can work together to identify and mitigate safety risks for heavy commercial vehicles.

## Phase 1 Success Criteria

The POC is successful if it can:

1. ingest GPS and camera-derived edge inputs
2. normalize those inputs into a shared event model
3. compute a risk score locally
4. enrich risk with simulated external context such as infrastructure or weather
5. publish the resulting event package to a cloud API or log pipeline
6. generate a mitigation output such as an alert or recommendation

## Scope Included

### Real or partially real inputs
- GPS feed from device or replay file
- camera frames or frame-derived event metadata
- time, speed, heading, and route context

### Simulated inputs
- V2V alerts
- roadside infrastructure messages
- weather hazard context
- digital geofence or high-risk-zone warnings

### Processing
- event normalization
- rule-based edge risk scoring
- simple hazard classification
- cloud event ingestion
- dashboard-ready summaries or logs

## Scope Excluded

- production-grade V2X radio integration
- full CAN bus integration from a real fleet vehicle
- advanced ML training and retraining workflow
- full fleet management UI
- multi-tenant cloud architecture
- compliance-grade reporting automation

## Recommended Initial Scenarios

### Scenario 1: Speed + curve + weather risk
- vehicle speed increases
- route indicates upcoming turn or risk zone
- weather context indicates poor road condition
- system raises risk score and produces a slow-down recommendation

### Scenario 2: Lane drift proxy + nearby hazard signal
- camera module detects drift or unstable lane behavior proxy
- simulated infrastructure or nearby vehicle warning is received
- edge engine escalates risk score
- cloud event is logged and alert is surfaced

### Scenario 3: Harsh braking / instability event
- GPS/telemetry indicates sudden deceleration or instability
- edge engine tags the event as abnormal
- cloud receives a high-priority risk event
- mitigation output is generated for fleet review

## Deliverables

- repo structure aligned to invention modules
- architecture diagram
- sample event payloads
- baseline risk-engine logic
- cloud ingestion endpoint or stub
- demo workflow document
- claim-to-POC mapping document

## Metrics to Capture

- time from input event to risk score
- time from risk score to alert output
- number of events processed per demo trip
- number of escalated risk events
- count of mitigation recommendations generated

## Exit Criteria for Phase 1

Phase 1 is complete when one repeatable demo can run end-to-end and produce structured outputs that clearly show:

- input capture
- risk evaluation
- external context enrichment
- mitigation recommendation
- cloud or dashboard visibility
