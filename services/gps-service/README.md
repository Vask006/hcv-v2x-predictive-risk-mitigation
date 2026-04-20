# gps-service

## Overview

Ingests live GPS or replayed route data and publishes normalized motion and route context for risk analysis. **Phase 1** reads NMEA over serial (or mock), exposes `GpsSampleEvent`, and aligns with existing POC recording paths under `jetson-hcv-risk-poc/edge/`.

## Run locally (verify)

**Unit tests** (no serial hardware, no `pip install`):

```bash
cd services/gps-service
python -m pytest tests -q
```

**Mock GNSS** (no `pyserial` needed for mock path; run from `src/` so imports resolve without `pip install`):

```bash
cd services/gps-service/src
python -c "from gps_service import GpsService, GpsServiceConfig; s=GpsService(GpsServiceConfig(), mock_gps=True); ev=s.wait_for_fix(1.0); print(ev.as_dict() if ev else None)"
```

**Real serial** (install `pyserial`, device on `port`):

```bash
cd services/gps-service
pip install -e ".[serial]"
python -c "from gps_service import GpsService; s=GpsService({'port':'COM3','baud':9600}, mock_gps=False); print(s.probe_open(10.0))"
```

Use your actual `port` (`COM3` on Windows, `/dev/ttyACM0` on Linux/Jetson). End-to-end mock pipeline: `docs/run-local-phase1.md`.

## Purpose

Phase **1** GNSS ingestion: **NMEA RMC/GGA** parsing over **pyserial** (lazy import), **mock** bench fixes, and a **normalized** `GpsSampleEvent` wrapper (timestamps, lat/lon, optional speed/course from RMC, fix quality, validity hint). This does **not** replace `event_v1` GPS blobs; it is the **sensor-side** model.

## Real paths in `jetson-hcv-risk-poc` (unchanged behavior)

| Path | Role |
|------|------|
| **Serial GPS** | `edge/app/recording_gps_writer.py` → `GPSReader.iter_lines` · `edge/app/device_connectivity.py` `probe_gps` → `GPSReader.wait_for_fix` · `edge/app/phase0_smoke.py` · `edge/app/gps_signal_test.py` |
| **Mock GPS** | `recording_gps_writer.gps_jsonl_writer_loop` with `--mock-gps` / `mock_fixes(20)` loop · `phase0_smoke` · `probe_gps` short-circuit when `mock_gps=True` |
| **Recording JSONL** | `recording_gps_writer._write_fix_row` → rows: `wall_utc`, `mono_s`, `latitude_deg`, `longitude_deg`, `fix_quality`, `raw`, optional `gps_source` |
| **Runtime** | `edge/app/edge_runtime.py` reads **last line** of `gps*.jsonl` under `recording.output_base` (does not import `gps_service` directly) |

All of the above still import **`jetson-hcv-risk-poc/edge/gps_service/reader.py`**, which **delegates** to this package when `services/gps-service/src` exists in a parent directory, else uses a **legacy inline** copy (standalone clone).

## `src/` modules

| File | Role |
|------|------|
| `gps_models.py` | `GpsFix` (POC-compatible fields + optional `speed_mps`, `course_deg`), `GpsSampleEvent.as_dict()`. |
| `gps_reader.py` | `parse_line` / `_parse_line`, `GpsSerialReader` (serial API = old `GPSReader`), `mock_fixes`, `GpsReaderError`. RMC SOG (knots) → **m/s** via 0.514444 only when the sentence contains numeric SOG/COG fields. |
| `gps_service.py` | `GpsServiceConfig`, `GpsService` (`iter_fixes`, `wait_for_fix`, `probe_open`). |

**Dependencies:** `pyserial` only when opening serial (same as POC). No hard dependency at import time.

## Instantiate from Python

```python
from gps_service import GpsService, GpsServiceConfig

# Live serial (YAML ``gps:`` dict)
svc = GpsService({"port": "/dev/ttyACM0", "baud": 9600, "timeout_sec": 1.0})
ev = svc.wait_for_fix(45.0)  # may be None if no fix
if ev:
    print(ev.as_dict())

# Mock bench stream (caller should ``break`` out of ``iter_fixes``)
mock = GpsService(GpsServiceConfig(port="/dev/ttyUSB0", mock_gps=True), mock_gps=True)
for i, ev in enumerate(mock.iter_fixes()):
    if i >= 3:
        break
    print(ev.as_dict())
```

## Example `GpsSampleEvent.as_dict()` (mock row)

```json
{
  "schema_version": "gps.sample.v1",
  "wall_time_utc_iso": "2026-04-19T12:00:00.000000Z",
  "monotonic_s": 12345.6,
  "latitude_deg": 0.0,
  "longitude_deg": 0.0,
  "fix_quality": 1,
  "validity": "valid",
  "source": "mock",
  "raw_nmea_truncated": "$HCVMOCK,BENCH_SYNTHETIC,NO_SERIAL,i=0*"
}
```

With RMC SOG/COG present, optional `speed_mps` and `course_deg` keys are added.

## POC modules still using `gps_service.reader` (not `services/` directly)

- `jetson-hcv-risk-poc/edge/app/recording_gps_writer.py`
- `jetson-hcv-risk-poc/edge/app/device_connectivity.py`
- `jetson-hcv-risk-poc/edge/app/phase0_smoke.py`
- `jetson-hcv-risk-poc/edge/app/gps_signal_test.py`
- `jetson-hcv-risk-poc/tests/test_gps_nmea.py`

**Transitive:** `record_session.py`, `record_gps.py` → `recording_gps_writer`.

## Migrate next

1. **`recording_gps_writer`**: optionally build JSONL rows from `GpsSampleEvent.as_dict()` keys mapped to existing column names (no schema break).
2. **`device_connectivity.probe_gps`**: thin call to `GpsService(...).probe_open(wait)` to dedupe logic (keep return tuple shape).
3. **`edge_runtime`**: optional use of `GpsSampleEvent` when reading JSONL is refactored to a shared parser in `services/shared`.

## Phase 1 constraints

- No new coordinate datums or magnetic variation handling.
- GGA still does not infer speed/course (fields stay `null` in `GpsFix`).
