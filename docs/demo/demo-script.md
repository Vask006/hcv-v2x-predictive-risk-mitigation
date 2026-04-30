# Demo Script

## 1) Problem

Heavy commercial vehicles require early and explainable risk detection before incidents escalate.

## 2) System Overview

This repository demonstrates a modular flow:

- onboard GPS and camera-derived signals
- telemetry normalization
- cooperative V2X context simulation
- deterministic risk scoring and mitigation output
- cloud ingestion and dashboard visibility

## 3) Run Demo

```bash
python scripts/run_demo_end_to_end.py
```

## 4) Show Risk Output

Call out:

- risk score
- severity
- hazard type
- reason codes

## 5) Explain V2X Context

Highlight the selected sample event (`v2i_curve_warning.json`) and how it increases context risk.

## 6) Show Cloud Ingestion

Open API output:

```bash
curl http://127.0.0.1:8000/v1/events
```

## 7) Show Dashboard

```bash
streamlit run services/dashboard/app.py
```

## 8) Limitations and Next Steps

- V2X is simulated in this demo.
- Camera analytics are deterministic heuristics.
- Local cloud API is ingestion-focused.
- Production hardening and fleet-scale analytics are future extensions.
