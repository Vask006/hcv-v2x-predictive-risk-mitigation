# Run local Phase 1 (developer guide)

Short path to **prove** `camera-service`, `gps-service`, `risk-engine`, and `pipeline` on a dev machine or Jetson. Commands assume the **monorepo root** `hcv-v2x-predictive-risk-mitigation` (sibling `services/` + optional `jetson-hcv-risk-poc/`).

## Prerequisites

- **Python 3.10+**
- **`pytest`** for unit checks: `python -m pip install pytest`
- **Repo layout**: `services/camera-service/src`, `services/gps-service/src`, `services/risk-engine/src`, `services/pipeline/src` present
- **Mock pipeline**: no extra wheels
- **`--live-camera`**: `opencv-python-headless` (see `services/camera-service` README, optional extra `[opencv]`)
- **`--real-gps`**: `pyserial` + GNSS on the configured serial port

## First end-to-end flow (mock — do this first)

This is the **single** command sequence that exercises all four pieces through the pipeline (mock GNSS + synthetic camera metadata + `risk-engine` rules + JSON sink).

```bash
# 1) Repository root
cd /path/to/hcv-v2x-predictive-risk-mitigation

# 2) (Optional) 30s — unit-test each service in isolation
cd services/camera-service && python -m pytest tests -q && cd ../..
cd services/gps-service && python -m pytest tests -q && cd ../..
cd services/risk-engine && python -m pytest tests -q && cd ../..
cd services/pipeline && python -m pytest tests -q && cd ../..

# 3) One-shot pipeline (mock)
python scripts/run_phase1_mock.py
```

Equivalent without the helper:

```bash
python services/pipeline/src/pipeline_runner.py --no-external-context
```

### What you should see

- **Stdout**: JSON with `pipelineVersion` (`phase1-local-1`), `riskEvent` (camelCase `RiskEventPayload`), and `inputsEcho` (GPS + camera samples used).
- **Stderr**: a line like `Wrote: .../outputs/pipeline_run_<UTC>_<8hex>.json`
- **Disk**: new file under `outputs/` at repo root (directory is tracked with `.gitkeep`; JSON files are local artifacts).

### With optional external context

If `services/pipeline/examples/external_context_sample.json` exists, the default CLI **loads** it. To match the mock helper exactly, keep `--no-external-context`. To exercise that file:

```bash
python services/pipeline/src/pipeline_runner.py
```

## Jetson-connected paths

### A) Full sensors on the Jetson (monorepo on device)

From repo root on the Jetson (same layout as Git):

```bash
python services/pipeline/src/pipeline_runner.py --live-camera --real-gps --no-external-context
```

Uses defaults inside the pipeline for camera index and GPS port; tune later via code/config as you wire YAML. Requires **video** group / **dialout** (or equivalent) and working OpenCV + serial.

### B) Record on Jetson, replay JSONL on a dev PC (common)

1. On the Jetson, under `jetson-hcv-risk-poc/edge`, use your existing venv and workflow, e.g. mock GPS to a file:

   ```bash
   cd jetson-hcv-risk-poc/edge
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   python -m app.record_gps --mock-gps --duration-sec 8
   ```

2. GPS lines are written under `jetson-hcv-risk-poc/edge/data/recordings/<date>/<session>/gps.jsonl` (see `recording.output_base` in `edge/config/default.yaml`).

3. Copy `gps.jsonl` to your PC, then from **monorepo root**:

   ```bash
   python services/pipeline/src/pipeline_runner.py --gps-jsonl /path/to/gps.jsonl
   ```

The pipeline reads the **last JSON line** from that file (same idea as `edge/app/edge_runtime.py`).

## Troubleshooting

| Symptom | Check |
|--------|--------|
| `ModuleNotFoundError` in service tests | Run `pytest` from `services/<name>/` (not from `src/`); `conftest.py` adds `src/` to `sys.path`. |
| `python scripts/run_phase1_mock.py` says missing runner | Run from repo root; path must be `services/pipeline/src/pipeline_runner.py`. |
| Camera probe / `--live-camera` fails | Device index, permissions, or missing OpenCV GStreamer build; pipeline falls back to **synthetic** camera metadata when live read fails. |
| `--real-gps` never returns | Wrong `port` / baud; antenna; `pyserial` not installed; increase `--gps-wait-sec`. |
| `--gps-jsonl` ignored | Path must exist; file must contain at least one valid JSON line. |
| Empty `externalContext` in output | You passed `--no-external-context` (expected) or the optional JSON file is missing / skipped. |

## Related docs

- Per-service detail: `services/camera-service/README.md`, `services/gps-service/README.md`, `services/risk-engine/README.md`, `services/pipeline/README.md`
- POC runtime (continuous loop, `event_v1`): `jetson-hcv-risk-poc/edge/deploy/hcv-edge-runtime-start.sh` → `python -m app.edge_runtime`
- Refactor boundaries: `docs/refactor-status.md`
