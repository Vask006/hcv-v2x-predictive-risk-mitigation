# telemetry-service

This service provides the local demo implementation and is designed for extension.

## Purpose

Normalize GPS, camera, and vehicle-state payloads into a stable telemetry contract for downstream services.

## Event Contract

`NormalizedTelemetryEvent` contains:

- vehicle identity (`vehicle_id`, `trip_id`)
- timestamp
- normalized `gps`, `camera`, `vehicle_state` blocks
- source metadata
- raw input payload traceability

## Example Usage

```python
from telemetry_service import TelemetryService

svc = TelemetryService()
event = svc.normalize(
    vehicle_id="hcv-demo-001",
    gps={"latitudeDeg": 48.1, "longitudeDeg": 11.5, "speedMps": 20.0},
    camera={"healthy": True, "laneStability01": 0.82},
)
print(event.as_dict())
```

## Test

```bash
cd services/telemetry-service
python -m pytest tests -q
```
