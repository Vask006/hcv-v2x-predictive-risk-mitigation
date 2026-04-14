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

### Auto-start recording on boot (Jetson)

Each run creates a **new UTC timestamp folder** under `recording.output_base` (see `edge/config/default.yaml`). GPS rows include `wall_utc` per fix in `gps.jsonl`.

1. Clone repo once on the board, create venv, `pip install -r edge/requirements.txt`, and set `gps.port` / `recording.output_base` as needed.
2. Make the start script executable: `chmod +x edge/deploy/hcv-record-start.sh`
3. Edit `edge/deploy/hcv-record.service`: set `User`, `Group`, `WorkingDirectory`, and `ExecStart` to your **absolute** paths (example uses user `isha`).
4. Optional: copy `edge/deploy/hcv-record.default.example` to `/etc/default/hcv-record` to tune `HCV_BOOT_DELAY_SEC` (default **15** seconds so USB camera/GPS can enumerate) and `HCV_CONFIG`.
5. Install and enable:

```bash
sudo cp edge/deploy/hcv-record.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable hcv-record.service
sudo systemctl start hcv-record.service
```

Logs: `journalctl -u hcv-record.service -f` · Stop until next boot: `sudo systemctl stop hcv-record.service`

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
