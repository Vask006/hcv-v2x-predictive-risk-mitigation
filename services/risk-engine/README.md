# risk-engine

This service provides the local demo implementation and is designed for extension.

## Purpose

Compute deterministic, explainable risk assessment and mitigation output from normalized edge signals and context.

## Inputs

- `EdgeObservations` (speed, fix quality, camera-related signals)
- `ExternalContext` (curve, weather, infrastructure risk)

## Outputs

- `RiskEventPayload` containing risk score, severity, hazard type, mitigation, and reason codes

## Run/Test

```bash
cd services/risk-engine
python -m pytest tests -q
```

## Example Usage

```python
from risk_engine import RiskEngine
from risk_models import EdgeObservations, ExternalContext

out = RiskEngine().assess(
    vehicle_id="hcv-demo-001",
    trip_id="demo-trip-001",
    edge=EdgeObservations(gps_speed_mps=28.0, gps_fix_quality=1, latitude_deg=48.1, longitude_deg=11.5, camera_healthy=True),
    context=ExternalContext(curve_ahead=True, road_surface="wet"),
)
print(out.as_dict())
```
