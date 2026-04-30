# gps-service

GNSS ingestion service that reads NMEA data and emits normalized GPS sample events.

## Run tests

```bash
cd services/gps-service
python -m pytest tests -q
```

## Optional serial dependency

```bash
cd services/gps-service
pip install -e ".[serial]"
```
