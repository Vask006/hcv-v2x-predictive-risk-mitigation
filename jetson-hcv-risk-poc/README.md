# jetson-hcv-risk-poc

Predictive risk mitigation proof of concept for heavy commercial vehicles: Jetson Orin Nano edge stack plus cloud API and dashboard.

## Layout

| Path | Purpose |
|------|---------|
| `contracts/` | Shared JSON Schema (e.g. `event_v1.json`) |
| `docs/architecture/` | System and deployment diagrams, ADRs |
| `docs/eb1a-evidence/` | Extraordinary ability evidence artifacts (summaries, exhibits index) |
| `docs/patent-mapping/` | Claims ↔ implementation mapping notes |
| `docs/scenarios/` | Test and demo scenarios |
| `docs/demo-script/` | Step-by-step demo narration |
| `edge/camera_service/` | Camera capture / GStreamer or DeepStream adapters |
| `edge/gps_service/` | GPS / GNSS ingestion and quality metrics |
| `edge/inference/` | TensorRT (or similar) perception pipeline |
| `edge/risk_engine/` | Fusion, scoring, triggers |
| `edge/event_store/` | Local persistence and upload queue |
| `edge/uploader/` | HTTPS client to cloud ingest API |
| `edge/app/` | Composition, config, main entry |
| `cloud/api/` | Ingest and query backend |
| `cloud/dashboard/` | Demonstration UI |
| `tests/` | Unit and integration tests |
| `scripts/` | Jetson setup, packaging, CI helpers |
| `samples/` | Sample configs, schemas, non-production data |

## Phase 0 — what is implemented

- **`contracts/event_v1.json`** — JSON Schema for geo-tagged risk events.
- **`edge/config/default.yaml`** — defaults for device id, camera, GPS, Phase 0 smoke limits.
- **`edge/app/phase0_smoke.py`** — logs UTC wall time + monotonic time for camera frames and/or GPS (or `--mock-gps`).
- **`cloud/api`** — FastAPI: `GET /health`, `POST /v1/events`, `GET /v1/events`; SQLite by default, Postgres via `DATABASE_URL`.
- **`cloud/deploy/docker-compose.yml`** — Postgres + API on port **8000**.

### Edge smoke test (workstation or Jetson)

```bash
cd jetson-hcv-risk-poc/edge
python -m venv .venv
.venv\Scripts\activate   # Windows
# source .venv/bin/activate  # Linux / Jetson
pip install -r requirements.txt
```

Camera + serial GPS (set `gps.port` in `config/default.yaml`, e.g. `COM3` on Windows):

```bash
python -m app.phase0_smoke --config config/default.yaml
```

No hardware (camera optional, mock GPS):

```bash
python -m app.phase0_smoke --no-camera --mock-gps
```

### Edge recording (camera file + GPS JSONL on disk)

Writes under `edge/data/recordings/<UTC-timestamp>/` by default (`camera.mp4` or `camera.avi`, `gps.jsonl`, `session.json`).  
Set `recording.output_base` in `config/default.yaml` to an absolute path (for example an SSD mount on Jetson).

```bash
cd jetson-hcv-risk-poc/edge
source .venv/bin/activate
python -m app.record_session --config config/default.yaml --mock-gps
```

Use real USB GPS (set `gps.port` in config): omit `--mock-gps`. Stop with Ctrl+C or set `recording.duration_sec` in YAML.
For production/vehicle runs, set `recording.gps_optional: false` to fail fast if GPS serial is missing.

### Auto-start recording on boot (Jetson)

Each run creates a **new UTC timestamp folder** under `recording.output_base` (see `edge/config/default.yaml`). GPS rows include `wall_utc` per fix in `gps.jsonl`.

1. Clone repo once on the board, create venv, `pip install -r edge/requirements.txt`, and set `gps.port` / `recording.output_base` as needed.
2. Make the start script executable: `chmod +x edge/deploy/hcv-record-start.sh`
3. Edit `edge/deploy/hcv-record.service`: set `User`, `Group`, `WorkingDirectory`, and `ExecStart` to your **absolute** paths (example uses user `isha`).
4. Optional: copy `edge/deploy/hcv-record.default.example` to `/etc/default/hcv-record` to tune `HCV_BOOT_DELAY_SEC` (default **30** seconds; use **45** on unstable inverter power so USB camera/GPS can enumerate) and `HCV_CONFIG`.
5. Install and enable:

```bash
sudo cp edge/deploy/hcv-record.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable hcv-record.service
sudo systemctl start hcv-record.service
```

Logs: `journalctl -u hcv-record.service -f` · Stop until next boot: `sudo systemctl stop hcv-record.service`

### Auto-start with separate camera and GPS services (recommended)

If you want failures isolated (camera failure does not stop GPS, GPS failure does not stop camera), use two systemd services.

1. Make start scripts executable:

```bash
chmod +x edge/deploy/hcv-camera-record-start.sh
chmod +x edge/deploy/hcv-gps-record-start.sh
```

2. Edit both service files for your absolute paths:
   - `edge/deploy/hcv-camera-record.service`
   - `edge/deploy/hcv-gps-record.service`

3. Optional: copy defaults and tune `HCV_BOOT_DELAY_SEC` (30-45 on vehicle inverter power):

```bash
sudo cp edge/deploy/hcv-camera-record.default.example /etc/default/hcv-camera-record
sudo cp edge/deploy/hcv-gps-record.default.example /etc/default/hcv-gps-record
```

4. Install and enable both units:

```bash
sudo cp edge/deploy/hcv-camera-record.service /etc/systemd/system/
sudo cp edge/deploy/hcv-gps-record.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable hcv-camera-record.service
sudo systemctl enable hcv-gps-record.service
sudo systemctl start hcv-camera-record.service
sudo systemctl start hcv-gps-record.service
```

5. Operate and inspect independently:

```bash
journalctl -u hcv-camera-record.service -f
journalctl -u hcv-gps-record.service -f
sudo systemctl restart hcv-camera-record.service
sudo systemctl restart hcv-gps-record.service
```

### Phase 1 runtime (risk scoring + queue + cloud upload)

Phase 1 architecture details live in `PHASE1_POC_ARCHITECTURE.md`.
The runtime consumes latest sensor outputs, generates `event_v1` records, stores them in a durable queue, and uploads to cloud when reachable.

Run manually:

```bash
cd jetson-hcv-risk-poc/edge
source .venv/bin/activate
python -m app.edge_runtime --config config/default.yaml
```

Install as service:

```bash
chmod +x edge/deploy/hcv-edge-runtime-start.sh
sudo cp edge/deploy/hcv-edge-runtime.service /etc/systemd/system/
sudo cp edge/deploy/hcv-edge-runtime.default.example /etc/default/hcv-edge-runtime
sudo systemctl daemon-reload
sudo systemctl enable hcv-edge-runtime.service
sudo systemctl start hcv-edge-runtime.service
```

Inspect runtime health:

```bash
journalctl -u hcv-edge-runtime.service -f
ls edge/data/recordings/phase1_events/pending
ls edge/data/recordings/phase1_events/sent
```

**Validation clip (~30s, one-shot):** use `edge/deploy/hcv-record-validation.service` so recording **stops cleanly** (MP4 `moov` written). It uses `--mock-gps` and `Restart=no` (does not loop like the main service).

```bash
chmod +x edge/deploy/hcv-record-validation-start.sh
sudo cp edge/deploy/hcv-record-validation.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl stop hcv-record.service    # free the camera if the main service is running
sudo systemctl start hcv-record-validation.service
journalctl -u hcv-record-validation.service -f
```

Optional: `/etc/default/hcv-record-validation` from `edge/deploy/hcv-record-validation.default.example` to change `HCV_DURATION_SEC` or `HCV_CONFIG`.

On Jetson, prefer system OpenCV with GStreamer support where needed; `opencv-python-headless` is for convenience on dev PCs.

### Cloud API — local (SQLite)

```bash
cd jetson-hcv-risk-poc/cloud/api
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

- Health: `GET http://127.0.0.1:8000/health`
- Ingest: `POST http://127.0.0.1:8000/v1/events` with body matching `samples/event_v1_example.json`
- List with mock context enrichment: `GET http://127.0.0.1:8000/v1/events?enrich=true`

### Cloud API — Docker (Postgres)

From `jetson-hcv-risk-poc/cloud/deploy`:

```bash
docker compose up --build
```

API: `http://127.0.0.1:8000` · Postgres: `localhost:5432` (user/password/db: `hcv` / `hcv` / `hcv`).

### Tests

```bash
cd jetson-hcv-risk-poc
pip install -r tests/requirements.txt
pytest tests -v
```

Validates `samples/event_v1_example.json` against `contracts/event_v1.json`.
