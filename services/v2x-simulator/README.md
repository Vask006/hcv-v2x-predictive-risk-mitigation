# v2x-simulator

This service provides the local demo implementation and is designed for extension.

## Purpose

Simulate cooperative V2X events and map them into risk-engine-compatible external context.

## Supported Event Types

- `V2V_HARD_BRAKE_AHEAD`
- `V2I_CURVE_WARNING`
- `V2I_WORK_ZONE`
- `V2N_WEATHER_ALERT`
- `V2P_VULNERABLE_USER_ZONE`

## Inputs

- V2X event JSON from `examples/`.

## Outputs

- `V2XEvent` typed representation.
- `V2XContextOutput` mapped context fields.
- merged context dictionary for pipeline use.

## Example Usage

```python
from pathlib import Path
from v2x_service import V2XSimulatorService

svc = V2XSimulatorService()
event = svc.load_event(Path("services/v2x-simulator/examples/v2i_curve_warning.json"))
context = svc.to_context(event)
print(context.as_dict())
```

## Test

```bash
cd services/v2x-simulator
python -m pytest tests -q
```
