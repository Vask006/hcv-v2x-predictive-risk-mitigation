# camera-service

This service provides the local demo implementation and is designed for extension.

## Purpose

Capture camera metadata and provide deterministic analytics proxies for downstream risk scoring.

## Inputs

- Live camera frame (optional)
- replay frame input (optional)
- mock fallback path for no-hardware environments

## Outputs

- camera sample metadata
- camera health status
- optional analytics proxies (`camera_analytics.py`)

## Run/Test

```bash
cd services/camera-service
python -m pytest tests -q
```

## Example Usage

```python
from camera_service import CameraService, CameraServiceConfig
with CameraService(CameraServiceConfig(index=0, backend="opencv")) as svc:
    sample, _frame = svc.read_frame()
    print(sample.as_dict())
```

## Limitations

- Local demo path uses lightweight heuristics and metadata, not full perception models.
