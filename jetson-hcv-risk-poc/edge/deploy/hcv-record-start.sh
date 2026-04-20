#!/usr/bin/env bash
# Start camera + GPS recording after boot. Paths are derived from this script's location.
set -euo pipefail

EDGE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [ -f /etc/default/hcv-record ]; then
  # shellcheck source=/dev/null
  . /etc/default/hcv-record
fi

# Car inverter power can delay USB camera/GPS enumeration; default higher for stability.
: "${HCV_BOOT_DELAY_SEC:=30}"
: "${HCV_CONFIG:=$EDGE_ROOT/config/default.yaml}"
# Set to 1 for camera-only runs (same as --no-gps). Alternatively use config/camera_only.yaml or recording.camera_only in YAML.
: "${HCV_CAMERA_ONLY:=0}"
# Optional: force segment length in seconds (e.g. 60) — same as --segment-sec; overrides YAML if set.
: "${HCV_SEGMENT_SEC:=}"

sleep "${HCV_BOOT_DELAY_SEC}"

cd "$EDGE_ROOT"
# shellcheck source=/dev/null
source .venv/bin/activate
extra=()
if [ "${HCV_CAMERA_ONLY}" = "1" ]; then
  extra+=(--no-gps)
fi
if [ -n "${HCV_SEGMENT_SEC}" ]; then
  extra+=(--segment-sec "${HCV_SEGMENT_SEC}")
fi
exec python -m app.record_session --config "${HCV_CONFIG}" "${extra[@]}"
