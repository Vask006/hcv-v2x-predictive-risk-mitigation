# gps-service

This service provides the local demo implementation and is designed for extension.

## Purpose

Read GNSS/NMEA input and emit normalized GPS sample events for edge risk workflows.

## Inputs

- serial NMEA stream (optional hardware path)
- deterministic mock GPS stream
- replay-friendly JSONL tail support via pipeline integration

## Outputs

- `GpsSampleEvent` payloads with fix quality, coordinates, and timing metadata

## Run/Test

```bash
cd services/gps-service
python -m pytest tests -q
```

## Example Usage

```python
from gps_service import GpsService, GpsServiceConfig
svc = GpsService(GpsServiceConfig(mock_gps=True), mock_gps=True)
event = svc.wait_for_fix(1.0)
print(event.as_dict() if event else None)
```

## Limitations

- Local defaults prioritize reproducible mock behavior over hardware-specific tuning.
