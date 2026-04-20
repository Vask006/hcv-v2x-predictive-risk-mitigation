# Current Jetson POC status and migration map

This document maps the **existing, working** implementation under `jetson-hcv-risk-poc/` to the **planned** top-level patent-aligned layout (`services/camera-service`, `services/gps-service`, `services/risk-engine`, `services/cloud-api`). It is based on direct inspection of the files listed in [Appendix: files inspected](#appendix-files-inspected); no runtime code in the POC was modified to produce it.

**Repository:** `Vask006/hcv-v2x-predictive-risk-mitigation` (local workspace path may differ).

---

## Executive summary

| Concern | Primary locations today (`jetson-hcv-risk-poc/`) |
|--------|-----------------------------------------------------|
| Camera capture | `edge/camera_service/capture.py`, `edge/app/recording_video.py`, probes in `edge/app/device_connectivity.py`, Phase 0 in `edge/app/phase0_smoke.py` |
| GPS ingestion | `edge/gps_service/reader.py`, `edge/app/recording_gps_writer.py`, probes in `edge/app/device_connectivity.py`, CLI `edge/app/gps_connectivity.py`, Phase 0 in `edge/app/phase0_smoke.py` |
| Event normalization (edge → `event_v1`-shaped dict) | `edge/app/edge_runtime.py` (`_build_event`, GPS/camera file discovery helpers); **contract validation** is in tests (`tests/test_event_schema.py`) and cloud (`cloud/api/schemas.py`), not enforced on-device before POST |
| Risk scoring / rule logic | `edge/risk_engine/scorer.py`, config `edge/config/default.yaml` → `risk_engine:`; mock inputs from `edge/inference/perception_adapter.py`, `edge/risk_engine/context_provider.py` |
| Event storage / queueing | `edge/event_store/queue.py` (filesystem `pending/` + `sent/` under `recording.output_base/phase1_events/`) |
| Cloud upload / API posting (edge client) | `edge/uploader/client.py` (stdlib `urllib` POST to `cloud.ingest_base_url` + `uploader.path`) |
| Cloud ingest API (server) | `cloud/api/main.py`, `cloud/api/schemas.py`, `cloud/api/database.py`, optional mock enrichment `cloud/api/enrichment.py` |
| Runtime orchestration | `edge/app/record_session.py` (camera + GPS writers), `edge/app/record_camera.py`, `edge/app/record_gps.py`, `edge/app/edge_runtime.py` (Phase 1 loop), `edge/app/recording_paths.py`, `edge/app/prune_recordings.py`; systemd + shell: `edge/deploy/*.service`, `edge/deploy/*-start.sh` |

---

## What is already working (from code + docs)

- **Phase 0 smoke:** `python -m app.phase0_smoke` — real camera reads and/or serial GPS (or `--mock-gps`); documented in `jetson-hcv-risk-poc/README.md`.
- **Recording:** `python -m app.record_session` — one session folder with `session.json`, segmented or single `camera*.mp4` / `gps*.jsonl`; optional `--mock-gps`, `--no-gps`, camera-only YAML (`edge/config/camera_only.yaml`).
- **Phase 1 edge runtime:** `python -m app.edge_runtime` — polls latest GPS JSONL + camera file mtime, runs mock perception + mock context, scores risk, enqueues JSON events, uploads when `uploader.enabled` and network allows; documented in `README.md` and `PHASE1_POC_ARCHITECTURE.md`.
- **Cloud API:** FastAPI `GET /health`, `POST /v1/events`, `GET /v1/events` with optional `enrich=true` mock context (`cloud/api/main.py`).
- **Tests:** `pytest tests/` covers schema sample, GPS NMEA parsing, cloud enrichment, Phase 1 components (`tests/`).

---

## What is used in real Jetson / vehicle testing (as documented in-repo)

The **documented** on-device paths (edit `User`/`WorkingDirectory`/`ExecStart` to match the clone on the board) are:

| Artifact | Role |
|----------|------|
| `edge/deploy/hcv-record.service` + `hcv-record-start.sh` | Boots into `python -m app.record_session` after `HCV_BOOT_DELAY_SEC`; primary **combined** camera + GPS recording |
| `edge/deploy/hcv-edge-runtime.service` + `hcv-edge-runtime-start.sh` | Boots into `python -m app.edge_runtime` for Phase 1 scoring + queue + upload |
| `edge/deploy/hcv-camera-record.service` + `hcv-gps-record.service` | **Optional split** producers; README states they create **separate** session folders (not co-located with the combined unit) |
| `edge/deploy/hcv-record-validation.service` | Short validation clip with `--mock-gps`, `Restart=no` |
| `edge/deploy/hcv-prune-recordings.*` + `python -m app.prune_recordings` | Retention for old videos / session GPS JSONL |
| `edge/deploy/install-hcv-record-service.sh` | Operational helper for systemd install / CRLF / chmod |

**Config:** `edge/config/default.yaml` is the default referenced by start scripts and README (`gps.port`, `recording.output_base`, `phase1_runtime`, `cloud.ingest_base_url`, etc.).

**Operational scripts (host):** `jetson-hcv-risk-poc/scripts/Sync-GitPullOnNano.ps1`, `Copy-JetsonRecordingsToDownloads.ps1` — support workflow; not runtime logic.

*Note:* This document cannot confirm which systemd units are enabled on a specific vehicle; it reflects **what the repository ships and documents** for Jetson deployment.

---

## Mock, simulated, or optional behavior (explicit in code)

| Area | Behavior | Evidence |
|------|-----------|----------|
| GPS | `--mock-gps` / `mock_fixes()` | `edge/gps_service/reader.py` (`mock_fixes`, `$HCVMOCK` synthetic `raw_sentence`), `recording_gps_writer.py`, `phase0_smoke.py`, `record_session.py` |
| GPS optional on Linux | Missing `/dev/tty*` port can force camera-only | `record_session.py` (`gps_optional`, port existence check) |
| Perception | Deterministic stub, not TensorRT/DeepStream model | `edge/inference/perception_adapter.py` (`source: mock_perception_adapter`) |
| V2X / external context | `MockContextProvider` sine-wave risks | `edge/risk_engine/context_provider.py` |
| Cloud list enrichment | `?enrich=true` adds mock context | `cloud/api/main.py` + `cloud/api/enrichment.py` |
| Edge → cloud validation | Pydantic on server; **no** `jsonschema` on edge before upload | `grep` over `edge/` for `event_v1` / `jsonschema`: none; `edge/app/edge_runtime.py` builds dicts manually |

---

## File-to-file mapping → planned `services/*` layout

The repo root **does not yet** contain `services/`; the mapping below is the **intended** destination for a patent-aligned split. Paths are relative to repository root unless noted.

### `services/camera-service` (future)

| POC source (today) | Responsibility to carry forward |
|--------------------|----------------------------------|
| `jetson-hcv-risk-poc/edge/camera_service/capture.py` | `CameraCapture`, `FrameSample`, OpenCV / optional GStreamer pipeline |
| `jetson-hcv-risk-poc/edge/app/recording_video.py` | Segmented `VideoWriter`, fps pacing, calls into `camera_service.capture` |
| `jetson-hcv-risk-poc/edge/app/device_connectivity.py` → `probe_camera` | Pre-flight camera probe |
| `jetson-hcv-risk-poc/edge/app/record_camera.py` | Camera-only session CLI |
| `jetson-hcv-risk-poc/edge/app/record_session.py` (camera path) | Combined orchestration entry (or split later) |
| `jetson-hcv-risk-poc/edge/config/default.yaml` → `camera:` | `index`, `gstream_pipeline`, `backend` |

### `services/gps-service` (future)

| POC source (today) | Responsibility to carry forward |
|--------------------|----------------------------------|
| `jetson-hcv-risk-poc/edge/gps_service/reader.py` | `GPSReader`, NMEA parse, `mock_fixes` |
| `jetson-hcv-risk-poc/edge/app/recording_gps_writer.py` | JSONL row shape (`wall_utc`, lat/lon, `fix_quality`, `raw`, optional `gps_source`) + segmentation |
| `jetson-hcv-risk-poc/edge/app/device_connectivity.py` → `probe_gps` | Serial open + `wait_for_fix` probe |
| `jetson-hcv-risk-poc/edge/app/record_gps.py` | GPS-only session CLI |
| `jetson-hcv-risk-poc/edge/app/gps_connectivity.py` | Field diagnostic CLI |
| `jetson-hcv-risk-poc/edge/app/record_session.py` (GPS path) | Threaded `gps_writer_thread` |
| `jetson-hcv-risk-poc/edge/config/default.yaml` → `gps:` | `port`, `baud`, `timeout_sec` |

### `services/risk-engine` (future)

| POC source (today) | Responsibility to carry forward |
|--------------------|----------------------------------|
| `jetson-hcv-risk-poc/edge/risk_engine/scorer.py` | `score_risk`, `RiskAssessment`, bands/thresholds |
| `jetson-hcv-risk-poc/edge/risk_engine/context_provider.py` | `MockContextProvider` (later: real provider adapter) |
| `jetson-hcv-risk-poc/edge/inference/perception_adapter.py` | `PerceptionAdapter` stub (later: real perception) |
| `jetson-hcv-risk-poc/edge/app/edge_runtime.py` | **Orchestration loop** today: tail latest GPS file, camera health, call adapters + scorer, `_build_event`, invoke queue + uploader — on split, this becomes a smaller “runtime” or moves behind a service boundary |
| `jetson-hcv-risk-poc/edge/config/default.yaml` → `phase1_runtime:`, `risk_engine:`, `context_mock:` | Tunables for interval, emit threshold, mock waves, weights |

### `services/cloud-api` (future)

| POC source (today) | Responsibility to carry forward |
|--------------------|----------------------------------|
| `jetson-hcv-risk-poc/cloud/api/main.py` | HTTP API surface |
| `jetson-hcv-risk-poc/cloud/api/schemas.py` | `EventV1` Pydantic = ingest normalization |
| `jetson-hcv-risk-poc/cloud/api/database.py` | Persistence |
| `jetson-hcv-risk-poc/cloud/api/enrichment.py` | Mock enrichment for demos |
| `jetson-hcv-risk-poc/cloud/deploy/docker-compose.yml`, `Dockerfile`, `.env.example` | Deploy packaging |
| `jetson-hcv-risk-poc/edge/uploader/client.py` | **Edge client** counterpart (often lives with an “edge gateway” service rather than the server image; keep pairing documented) |

### Shared contract (both edge and cloud)

| POC source | Role |
|------------|------|
| `jetson-hcv-risk-poc/contracts/event_v1.json` | Canonical JSON Schema |
| `jetson-hcv-risk-poc/samples/event_v1_example.json` | Example payload |

### Event store (edge-side persistence)

| POC source | Map note |
|------------|----------|
| `jetson-hcv-risk-poc/edge/event_store/queue.py` | Becomes implementation detail of `services/risk-engine` or a dedicated `services/event-store` if you split durability from scoring; today it is filesystem-only under `phase1_events/` |

---

## What should remain in `jetson-hcv-risk-poc` temporarily

Until top-level `services/` packages exist and systemd units are repointed:

- **Entire** `jetson-hcv-risk-poc/edge/` tree (imports use `_EDGE_ROOT` + `sys.path` hacks assuming `cwd` is `edge/`).
- **All** `jetson-hcv-risk-poc/edge/deploy/*` units — they reference paths **inside** this folder (`WorkingDirectory=.../jetson-hcv-risk-poc/edge`).
- `jetson-hcv-risk-poc/cloud/` if the cloud stack is still demoed from this subtree.
- `jetson-hcv-risk-poc/README.md`, `PHASE1_POC_ARCHITECTURE.md`, `docs/patent/*` inside the POC — product and IP context for the POC boundary.

Treat this folder as the **baseline runnable prototype** until CI, imports, and install scripts are migrated.

---

## What to extract first (recommended order)

1. **`contracts/` + `samples/event_v1_example.json`** — single shared package or top-level `contracts/` already at POC; promote to repo-wide artifact first so all services depend on one path.
2. **`edge/event_store/queue.py` + `edge/uploader/client.py`** — small, few hardware deps; establishes offline-first + transport boundaries for any split runtime.
3. **`edge/risk_engine/*` + `edge/inference/perception_adapter.py`** — pure Python scoring and stubs; easiest to unit-test in isolation.
4. **`edge/gps_service/reader.py` + `edge/app/recording_gps_writer.py`** — serial + file I/O; depends on `pyserial` and path conventions from `recording_paths.py`.
5. **`edge/camera_service/capture.py` + `edge/app/recording_video.py`** — depends on OpenCV / Jetson GStreamer stack; highest platform variance — extract after shared interfaces exist.
6. **`edge/app/edge_runtime.py`** — last or parallel: it **couples** discovery of recordings, scoring, queue, and upload; extracting it early without (1)–(5) stable interfaces tends to churn.
7. **`cloud/api/*`** — can move to `services/cloud-api` largely as a unit with `docker-compose`; coordinate with edge `ingest_base_url`.

---

## Technical risks and dependency issues

| Risk | Detail |
|------|--------|
| **Import / working directory coupling** | Modules under `edge/app/` insert `edge/` on `sys.path` and assume execution from `jetson-hcv-risk-poc/edge`. Any move requires explicit packages (`pip install -e`) or `PYTHONPATH` updates and systemd `WorkingDirectory` changes. |
| **No edge-side schema validation** | Events are hand-assembled in `edge_runtime._build_event`; drift vs `contracts/event_v1.json` is caught by tests/cloud ingest, not before queue write. |
| **Split recording vs combined runtime** | `edge_runtime` glob-searches `recording.output_base` for newest `gps*.jsonl` / `camera*`; split `hcv-camera-record` + `hcv-gps-record` use **different** session dirs per README — Phase 1 alignment may degrade unless paths or a “latest session symlink” convention is added later (out of scope for this status doc). |
| **Hardware / OS variance** | OpenCV `VideoWriter` codec fallback (`mp4v` vs MJPG `.avi`), USB enumeration delays (`HCV_BOOT_DELAY_SEC`), GPS on `ttyACM*` vs `ttyUSB*`. |
| **Security** | `README.md` / `PHASE1_POC_ARCHITECTURE.md` note cloud API may be unauthenticated; `CloudUploader` sends `X-API-Key` only if configured. |
| **Recorded artifacts in git** | Workspace listing may include `edge/data/recordings*` sample files; exclude or `.gitignore` in operational clones to avoid bloating migrations. |

---

## Appendix: files inspected

### Read end-to-end for this migration map (primary)

- `jetson-hcv-risk-poc/README.md`
- `jetson-hcv-risk-poc/PHASE1_POC_ARCHITECTURE.md`
- `jetson-hcv-risk-poc/edge/app/edge_runtime.py`
- `jetson-hcv-risk-poc/edge/app/record_session.py`
- `jetson-hcv-risk-poc/edge/app/record_camera.py`
- `jetson-hcv-risk-poc/edge/app/record_gps.py`
- `jetson-hcv-risk-poc/edge/app/recording_video.py`
- `jetson-hcv-risk-poc/edge/app/recording_gps_writer.py`
- `jetson-hcv-risk-poc/edge/app/device_connectivity.py`
- `jetson-hcv-risk-poc/edge/app/recording_paths.py`
- `jetson-hcv-risk-poc/edge/app/phase0_smoke.py`
- `jetson-hcv-risk-poc/edge/app/gps_connectivity.py` (header + imports)
- `jetson-hcv-risk-poc/edge/app/prune_recordings.py` (header + imports)
- `jetson-hcv-risk-poc/edge/camera_service/capture.py`
- `jetson-hcv-risk-poc/edge/gps_service/reader.py`
- `jetson-hcv-risk-poc/edge/event_store/queue.py`
- `jetson-hcv-risk-poc/edge/uploader/client.py`
- `jetson-hcv-risk-poc/edge/risk_engine/scorer.py`
- `jetson-hcv-risk-poc/edge/risk_engine/context_provider.py`
- `jetson-hcv-risk-poc/edge/inference/perception_adapter.py`
- `jetson-hcv-risk-poc/edge/config/default.yaml`
- `jetson-hcv-risk-poc/contracts/event_v1.json` (partial)
- `jetson-hcv-risk-poc/cloud/api/main.py`
- `jetson-hcv-risk-poc/cloud/api/schemas.py`
- `jetson-hcv-risk-poc/edge/deploy/hcv-record.service`
- `jetson-hcv-risk-poc/edge/deploy/hcv-edge-runtime.service`
- `jetson-hcv-risk-poc/edge/deploy/hcv-record-start.sh`
- `jetson-hcv-risk-poc/edge/deploy/hcv-edge-runtime-start.sh`
- `jetson-hcv-risk-poc/edge/deploy/install-hcv-record-service.sh`
- `jetson-hcv-risk-poc/tests/test_event_schema.py`

### Listed / cross-checked (directory inventory; not every byte read)

- Full recursive file listing under `jetson-hcv-risk-poc/` (includes `edge/deploy/*.service`, `edge/deploy/*.sh`, `tests/*`, `cloud/*`, `scripts/*`, `docs/*` under POC, and any local `edge/data/**` or `__pycache__` present in the workspace).

### Not individually opened (exist in tree)

- `jetson-hcv-risk-poc/edge/app/gps_signal_test.py`
- `jetson-hcv-risk-poc/cloud/api/database.py`, `enrichment.py`, `Dockerfile`, `requirements.txt`
- `jetson-hcv-risk-poc/edge/deploy/hcv-camera-record*`, `hcv-gps-record*`, `hcv-record-validation*`, `hcv-prune-recordings*`, `*.default.example`
- `jetson-hcv-risk-poc/edge/config/camera_only.yaml`
- `jetson-hcv-risk-poc/tests/test_gps_nmea.py`, `test_phase1_runtime_components.py`, `test_cloud_enrichment.py`, `conftest.py`
- Patent / mapping markdown under `jetson-hcv-risk-poc/docs/**`

---

*Generated from repository inspection. Update this file when systemd entrypoints, module paths, or service boundaries change.*
