#!/usr/bin/env bash
# Start GPS-only recording after boot.
set -euo pipefail

EDGE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [ -f /etc/default/hcv-gps-record ]; then
  # shellcheck source=/dev/null
  . /etc/default/hcv-gps-record
fi

# Car inverter power can delay USB GPS enumeration.
: "${HCV_BOOT_DELAY_SEC:=30}"
: "${HCV_CONFIG:=$EDGE_ROOT/config/default.yaml}"

sleep "${HCV_BOOT_DELAY_SEC}"

cd "$EDGE_ROOT"
# shellcheck source=/dev/null
source .venv/bin/activate
exec python -m app.record_gps --config "${HCV_CONFIG}"
