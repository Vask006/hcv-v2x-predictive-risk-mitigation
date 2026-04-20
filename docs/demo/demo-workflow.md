# Demo Workflow

## Goal

Demonstrate an end-to-end predictive risk mitigation flow for a heavy commercial vehicle using a mix of real edge inputs and simulated cooperative context.

## Demo Preconditions

- GPS input is available from device feed or replay file
- camera input is available from Jetson or represented by precomputed edge events
- risk engine is configured with baseline thresholds
- cloud API or event logging endpoint is running
- sample V2X / weather / infrastructure events are available

## End-to-End Demo Steps

### 1. Start edge input services
Start the following components:
- GPS service
- camera service or event replay
- telemetry service
- risk engine
- cloud API

### 2. Feed route and motion context
The GPS service publishes:
- latitude and longitude
- speed
- heading
- timestamp
- optional route or geofence context

### 3. Inject edge anomaly or elevated-risk condition
Examples:
- sudden speed increase before a curve
- lane instability proxy from camera analysis
- harsh braking event
- driver state or motion instability proxy

### 4. Add simulated cooperative context
Inject one or more supporting conditions:
- V2I warning for road hazard
- V2V alert from nearby vehicle
- weather alert for reduced traction
- high-risk corridor or geofenced zone flag

### 5. Compute risk score
The risk engine should:
- normalize input events
- fuse local and external context
- assign a risk score
- classify severity
- generate a mitigation output

### 6. Publish cloud event
The cloud API receives a structured event such as:
- vehicle identity or demo vehicle id
- trip context
- edge observations
- external context
- computed risk score
- mitigation recommendation

### 7. Show visible output
One or more outputs should be shown:
- JSON event output
- console log summary
- dashboard widget
- alert message

## Expected Demo Outputs

### Sample mitigation results
- "Reduce speed due to elevated rollover and weather risk"
- "High-risk zone ahead, driver advisory generated"
- "Fleet alert raised for instability event"

### Minimum evidence to capture
- screenshot of input feed
- screenshot of risk output
- JSON sample of published event
- short video of demo flow
- architecture snapshot

## Sample Data References

- `data/sample-events/gps-sample.json`
- `data/sample-events/edge-risk-event.json`

## Suggested Demo Script

1. Start services
2. Replay GPS sequence
3. Inject edge instability event
4. Inject weather or infrastructure hazard
5. Show risk score increase
6. Publish event to cloud endpoint
7. Show alert and final summary
