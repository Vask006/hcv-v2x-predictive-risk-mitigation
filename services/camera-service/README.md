# camera-service

## Overview

Captures camera frames or accepts precomputed camera-derived events for the HCV predictive risk mitigation POC. **Phase 1** connects to a Jetson (or dev) camera or replay source, extracts frame metadata, and exposes normalized events for the local pipeline or future telemetry. Later phases may add lane drift, visibility, object cues, and driver-facing integration.

## Run locally (verify)

From the **repository root** (no `pip install` required for unit tests):

```bash
cd services/camera-service
python -m pytest tests -q
```

Optional **editable install** (then imports work from any cwd; OpenCV only when you open a device or file):

```bash
cd services/camera-service
pip install -e ".[opencv]"
python -c "from camera_service import CameraService, CameraServiceConfig; print(CameraService(CameraServiceConfig(index=0)).probe())"
```

The one-liner needs a working camera (or valid `video_path` in config); on a headless dev box, rely on `pytest` or use the **pipeline** mock path in `docs/run-local-phase1.md`.

## Purpose

Phase **1** building block for **reliable OpenCV / GStreamer frame access** and a **normalized metadata event** (`CameraSampleEvent`) with UTC + monotonic timestamps and basic **health** fields. Video segmentation / `VideoWriter` remains in `jetson-hcv-risk-poc/edge/app/recording_video.py` until a later extraction (see TODO there).

## Layout (`src/`)

| Module | Role |
|--------|------|
| `camera_models.py` | `FrameSample`, `CameraHealth`, `CameraSampleEvent` (+ `as_dict()`). |
| `camera_reader.py` | `OpenCVCameraReader`, `CaptureError` — lazy `cv2` import; live index, GStreamer pipeline, or **optional file replay** (`video_path`). |
| `camera_service.py` | `CameraServiceConfig`, `CameraService` — YAML-friendly config, `read_frame` / `read_meta_only`, `probe()`. |

**Heavy dependency:** OpenCV is imported **only** inside `open` / `read_frame` on the reader so importing `camera_models` / config types does not require `cv2`. Install with POC: `opencv-python-headless` (see `jetson-hcv-risk-poc/edge/requirements.txt`) or `pip install -e ".[opencv]"` from this directory.

## Instantiate from Python

```python
from pathlib import Path

from camera_service import CameraService, CameraServiceConfig

# From discrete knobs (live camera index 0)
svc = CameraService(CameraServiceConfig(index=0, backend="opencv"))
with svc:
    event, bgr = svc.read_frame()
    print(event.as_dict())

# From a YAML ``camera:`` dict (optional ``replay_video_path`` / ``video_path`` for file replay)
cfg = {"index": 0, "backend": "opencv", "gstream_pipeline": None}
svc2 = CameraService(cfg)

# GStreamer string (Jetson): pass pipeline in CameraServiceConfig(pipeline="nvarguscamerasrc ! ...")
```

**Lower-level (POC-compatible API):**

```python
from camera_reader import OpenCVCameraReader, CaptureError

with OpenCVCameraReader(index=0, backend="opencv") as cap:
    meta, frame = cap.read_frame()
```

## POC integration (monorepo)

`jetson-hcv-risk-poc/edge/camera_service/capture.py` walks upward for `services/camera-service/src` and, if found, **delegates** `CameraCapture` / `CaptureError` / `FrameSample` to `OpenCVCameraReader` / `camera_models`. If the tree is **standalone** (no `services/camera-service`), the same file keeps a **legacy inline** `CameraCapture` (live only; `video_path` raises).

## Old POC modules still tied to `camera_service.capture`

These import **`jetson-hcv-risk-poc/edge/camera_service/capture.py`** (not `services/` directly):

| File | Usage |
|------|--------|
| `jetson-hcv-risk-poc/edge/app/recording_video.py` | `from camera_service.capture import CameraCapture, CaptureError` |
| `jetson-hcv-risk-poc/edge/app/device_connectivity.py` | `probe_camera` uses `CameraCapture` |
| `jetson-hcv-risk-poc/edge/app/phase0_smoke.py` | smoke test uses `CameraCapture` |

**Transitive:** `record_session.py` / `record_camera.py` call `run_camera_recording_loop` in `recording_video.py`, so they still depend on the same capture entrypoint.

**Not using live capture:** `edge/app/edge_runtime.py` only checks latest recording file mtime for camera health — unchanged.

## Phase 1 scope

- Live USB/CSI (index) or GStreamer pipeline string; optional **file replay** for bench/CI when `cv2.VideoCapture(path)` is valid.
- No ML perception, no DeepStream graph beyond what you pass as a pipeline string.

## TODO (later extraction stages)

- Move `open_video_writer` + `run_camera_recording_loop` from `recording_video.py` behind this service or a sibling `recording` module.
- Replace `sys.path` / upward walk in POC `capture.py` with `pip install -e services/camera-service` once CI and Jetson venvs pin the package.
