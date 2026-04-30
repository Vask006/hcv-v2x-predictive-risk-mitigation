# dashboard

This service provides the local demo implementation and is designed for extension.

## Purpose

Provide a lightweight event review dashboard for ingested HCV risk events.

## Setup

```bash
pip install -r requirements-dev.txt
```

## Run

```bash
streamlit run services/dashboard/app.py
```

Expected API URL: `http://127.0.0.1:8000`

## Notes

- The dashboard handles missing fields defensively.
- If the API is unavailable, the UI remains usable with clear status messaging.
- Add a captured dashboard image under `docs/demo/` when available.
