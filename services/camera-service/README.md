# camera-service

Camera ingestion service that captures frame metadata and health state for downstream risk processing.

## Run tests

```bash
cd services/camera-service
python -m pytest tests -q
```

## Optional OpenCV dependency

```bash
cd services/camera-service
pip install -e ".[opencv]"
```
