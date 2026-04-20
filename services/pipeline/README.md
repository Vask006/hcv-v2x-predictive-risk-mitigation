# services/pipeline (Phase 1)

## Run locally (verify)

**Fastest mock run** (from repository root; writes under `outputs/`):

```bash
python services/pipeline/src/pipeline_runner.py --no-external-context
```

Or use the thin helper (same default; forwards extra CLI args):

```bash
python scripts/run_phase1_mock.py
```

**Tests:**

```bash
cd services/pipeline
python -m pytest tests -q
```

Step-by-step Phase 1 flow (mock vs Jetson, troubleshooting): **`docs/run-local-phase1.md`**.

## Purpose

Single-shot **local** orchestration that wires:

1. **gps-service** — mock tail or serial `wait_for_fix`, or last line of a POC-style `gps.jsonl`
2. **camera-service** — one live frame (optional) or **synthetic** `CameraSampleEvent` (no hardware)
3. **Optional JSON** — `ExternalContext` fields (curve, wet road, hazard scores)
4. **risk-engine** — `RiskEngine.assess` → `RiskEventPayload`
5. **Sink** — print JSON to stdout and write under **`<repo>/outputs/`** (configurable)

No message bus, no Kubernetes. This package **does not import** `jetson-hcv-risk-poc`; it only **reuses the same JSONL field names** when you point `--gps-jsonl` at a recording file (same idea as `edge/app/edge_runtime.py` tail-read). The POC **systemd / `edge_runtime` loop is unchanged**.

## Dependencies

- Python **3.10+**
- Repo checkout containing `services/camera-service/src`, `services/gps-service/src`, `services/risk-engine/src`
- **Mock default:** no `opencv` / `pyserial` required
- **`--live-camera`:** requires `opencv` (same as camera-service)
- **`--real-gps`:** requires `pyserial` + GNSS on `gps.port` (defaults in `GpsServiceConfig`; extend runner later for YAML)

## How to run (CLI reference)

From **repository root** unless noted. See **`docs/run-local-phase1.md`** for prerequisites, Jetson flows, and troubleshooting.

| Goal | Command |
|------|---------|
| Mock + default external JSON if `examples/external_context_sample.json` exists | `python services/pipeline/src/pipeline_runner.py` |
| Mock, no external JSON | `python services/pipeline/src/pipeline_runner.py --no-external-context` or `python scripts/run_phase1_mock.py` |
| Custom sink directory | `python services/pipeline/src/pipeline_runner.py --no-external-context --output-dir ./outputs --vehicle-id edge-001 --trip-id demo-1` |
| One live camera frame (falls back to synthetic on error) | `python services/pipeline/src/pipeline_runner.py --live-camera --no-external-context` |
| Serial GPS (default wait ~45s) | `python services/pipeline/src/pipeline_runner.py --real-gps --gps-wait-sec 60 --no-external-context` |
| Last line of POC `gps.jsonl` | `python services/pipeline/src/pipeline_runner.py --gps-jsonl path/to/gps.jsonl` (path must exist) |

**Tests:** `cd services/pipeline && python -m pytest tests -q`

## Expected output shape

Each run writes `outputs/pipeline_run_<UTCstamp>_<8hex>.json` and prints the same object. Top-level keys:

| Key | Meaning |
|-----|---------|
| `pipelineVersion` | `phase1-local-1` |
| `riskEvent` | `RiskEventPayload.as_dict()` (camelCase) |
| `inputsEcho` | GPS/camera/context echoes for audit |

### Example (mock GPS, synthetic camera, no external context)

```json
{
  "pipelineVersion": "phase1-local-1",
  "riskEvent": {
    "eventId": "<uuid>",
    "vehicleId": "pipeline-dev",
    "tripId": null,
    "timestamp": "<iso>",
    "edgeObservations": {
      "gps_fix_quality": 1,
      "latitude_deg": 0.0,
      "longitude_deg": 0.0,
      "wall_time_utc_iso": "<iso>",
      "monotonic_s": 30176.14,
      "lane_stability_01": 0.88,
      "camera_healthy": true
    },
    "externalContext": {},
    "riskAssessment": {
      "riskScore": 0.0,
      "severity": "none",
      "hazardType": "nominal"
    },
    "mitigation": {
      "driverAlert": null,
      "fleetNotification": false,
      "recommendedAction": "Continue monitoring; maintain normal vigilance."
    },
    "reasonCodes": []
  },
  "inputsEcho": { "gpsSample": { "schema_version": "gps.sample.v1", "source": "mock", "..." : "..." }, "cameraSample": { "schema_version": "camera.sample.v1", "..." : "..." }, "externalContext": {} }
}
```

With `examples/external_context_sample.json` (wet + curve + hazards), scores rise when **GPS speed** is present (e.g. add `"speed_mps": 28` to the JSONL tail or use a receiver that emits RMC SOG).

## POST to existing POC cloud API (optional)

After a successful run, map the combined JSON to **`EventV1`** and `POST` to the **unchanged** FastAPI app in `jetson-hcv-risk-poc/cloud/api` using `services/cloud-api/src/adapter.py` + `client.py`:

```powershell
# Terminal 1: start API (from jetson-hcv-risk-poc/cloud/api)
python -m uvicorn main:app --host 127.0.0.1 --port 8000

# Terminal 2: from repo root
python services/pipeline/src/pipeline_runner.py --no-external-context --post-ingest --ingest-base-url http://127.0.0.1:8000
```

See **`services/cloud-api/README.md`** for schema mapping details.

## Relation to `jetson-hcv-risk-poc`

| POC | Pipeline |
|-----|----------|
| `edge/app/edge_runtime.py` | Continuous loop, queue, `event_v1`, upload |
| `edge/app/record_session.py` + JSONL | This pipeline can **read** the same `gps.jsonl` layout via `--gps-jsonl` |
| `edge/risk_engine/scorer.py` | Separate heuristics; pipeline uses **`services/risk-engine`** rules |

**Cloud path later:** map `riskEvent` into `services/shared/contracts/edge_event_v1.json` and POST to `services/cloud-api` — not implemented here by design.

## Files

| Path | Role |
|------|------|
| `src/event_pipeline.py` | Path install, `EventPipeline`, JSONL tail, sinks |
| `src/pipeline_runner.py` | CLI |
| `examples/external_context_sample.json` | Sample `ExternalContext` |
| `tests/test_pipeline_runner.py` | Mock + JSONL tests |
