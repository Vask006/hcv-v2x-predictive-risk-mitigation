#!/usr/bin/env bash
# One 30s camera recording for validation (finalize MP4 moov atom). No boot delay.
set -euo pipefail

EDGE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [ -f /etc/default/hcv-record-validation ]; then
  # shellcheck source=/dev/null
  . /etc/default/hcv-record-validation
fi

: "${HCV_CONFIG:=$EDGE_ROOT/config/default.yaml}"
: "${HCV_DURATION_SEC:=30}"

cd "$EDGE_ROOT"
# shellcheck source=/dev/null
source .venv/bin/activate
exec python -m app.record_session \
  --config "${HCV_CONFIG}" \
  --duration-sec "${HCV_DURATION_SEC}" \
  --mock-gps
