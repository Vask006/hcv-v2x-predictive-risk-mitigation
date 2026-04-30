# cloud-api

This service provides the local demo implementation and is designed for extension.

## Purpose

Provide a local cloud ingestion API and a client adapter for pipeline output delivery.

## Inputs

- `EventV1` JSON via `POST /v1/events`
- query parameters for retrieval via `GET /v1/events`

## Outputs

- persisted event records (SQLite by default)
- health and list endpoints for dashboard/demo usage

## Run

```bash
cd services/cloud-api/server
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

## Environment

- `HCV_DATABASE_URL` or `DATABASE_URL`
- `HCV_CORS_ORIGINS` or `CORS_ORIGINS`
- `HCV_ENABLE_RESET` or `ENABLE_RESET`

## Test

```bash
cd services/cloud-api
python -m pytest tests -q
```

## Example Ingest

```bash
python services/pipeline/src/pipeline_runner.py --no-external-context --post-ingest --ingest-base-url http://127.0.0.1:8000
```
