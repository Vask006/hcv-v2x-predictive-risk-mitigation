# Demo Workflow

## Goal

Run a repeatable local demonstration of the complete HCV V2X predictive risk flow:

Onboard inputs -> telemetry normalization -> V2X context enrichment -> risk scoring -> mitigation output -> cloud ingestion -> dashboard review.

## Commands

Install and validate:

```bash
pip install -r requirements-dev.txt
bash scripts/run_all_tests.sh
```

Run demo without ingestion:

```bash
python scripts/run_demo_end_to_end.py --skip-ingest
```

Start cloud API:

```bash
cd services/cloud-api/server
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

Run full demo:

```bash
python scripts/run_demo_end_to_end.py
```

Run dashboard:

```bash
streamlit run services/dashboard/app.py
```

## Expected Artifacts

- console summary with risk score/severity/mitigation
- JSON demo artifact under `outputs/`
- ingested event visible via `GET /v1/events`
- dashboard event table update
