# utils

Placeholder for **cross-service helpers** with no domain policy—for example:

- Resolve `recording.output_base` to an absolute `Path` (same rules as `edge/app/recording_paths.py` / `edge_runtime._resolve_output_base`).
- ISO-8601 UTC formatting helpers duplicated today in `edge_runtime._to_iso_z` and connectivity loggers.

## Phase 1 guidance

- Do **not** copy Jetson-specific `sys.path` bootstrapping here; keep that in adapters until packages are installable with `pip install -e`.
- Prefer **pure functions** with explicit inputs so `risk-engine` tests do not pull OpenCV or serial.

No modules are required until the first shared extraction needs them.
