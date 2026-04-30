# services/pipeline

## Purpose

Single-run local orchestration that combines:

1. GPS input (`gps-service`)
2. Camera metadata (`camera-service`)
3. Optional external context JSON
4. Risk scoring (`risk-engine`)
5. JSON sink output under `outputs/`

## Run locally

From repository root:

```bash
python scripts/run_local_pipeline.py
```

Equivalent direct command:

```bash
python services/pipeline/src/pipeline_runner.py --no-external-context
```

Run tests:

```bash
cd services/pipeline
python -m pytest tests -q
```

## Output

Each execution writes `outputs/pipeline_run_<UTCstamp>_<8hex>.json` with:

- `pipelineVersion`: `local-v1`
- `riskEvent`: risk payload from `risk-engine`
- `inputsEcho`: GPS, camera, and context trace

## Optional ingest

If cloud API is running:

```bash
python services/pipeline/src/pipeline_runner.py --no-external-context --post-ingest --ingest-base-url http://127.0.0.1:8000
```
