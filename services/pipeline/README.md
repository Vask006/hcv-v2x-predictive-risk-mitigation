# services/pipeline

This service provides the local demo implementation and is designed for extension.

## Purpose

Orchestrate GPS, camera, telemetry normalization, V2X context enrichment, risk scoring, and optional cloud ingestion.

## Inputs

- GPS sample (mock, serial path, or JSONL tail)
- Camera sample (mock or live capture)
- optional external context JSON
- optional V2X event JSON (`--v2x-event`)

## Outputs

- Combined JSON payload with:
  - `riskEvent`
  - `inputsEcho` including `v2xEvent` and `v2xContext` when provided
- Output artifact under `outputs/`

## Run

```bash
python services/pipeline/src/pipeline_runner.py --no-external-context
python services/pipeline/src/pipeline_runner.py --no-external-context --v2x-event services/v2x-simulator/examples/v2i_curve_warning.json
```

## Test

```bash
cd services/pipeline
python -m pytest tests -q
```

## Limitations

- Uses deterministic local orchestration, not distributed runtime scheduling.
- Sensor and V2X sources are simulation-friendly by default for laptop execution.
