# cloud-api

## Purpose

Cloud ingress package with:

- `src/adapter.py`: maps pipeline output (`riskEvent`) into `EventV1` request shape.
- `src/client.py`: stdlib HTTP client for posting events.
- `server/`: FastAPI ingest API and persistence layer.

## Run API server

From service directory:

```bash
cd services/cloud-api/server
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

## Pipeline ingest

```bash
python services/pipeline/src/pipeline_runner.py --no-external-context --post-ingest --ingest-base-url http://127.0.0.1:8000
```

## Tests

```bash
cd services/cloud-api
python -m pytest tests -q
```
