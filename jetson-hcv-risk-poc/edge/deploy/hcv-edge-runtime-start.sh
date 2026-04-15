#!/usr/bin/env bash
# Start Phase 1 edge runtime after boot.
set -euo pipefail

EDGE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [ -f /etc/default/hcv-edge-runtime ]; then
  # shellcheck source=/dev/null
  . /etc/default/hcv-edge-runtime
fi

: "${HCV_BOOT_DELAY_SEC:=35}"
: "${HCV_CONFIG:=$EDGE_ROOT/config/default.yaml}"

sleep "${HCV_BOOT_DELAY_SEC}"

cd "$EDGE_ROOT"
# shellcheck source=/dev/null
source .venv/bin/activate
exec python -m app.edge_runtime --config "${HCV_CONFIG}"
