#!/usr/bin/env bash
# Start camera + GPS recording after boot. Paths are derived from this script's location.
set -euo pipefail

EDGE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [ -f /etc/default/hcv-record ]; then
  # shellcheck source=/dev/null
  . /etc/default/hcv-record
fi

: "${HCV_BOOT_DELAY_SEC:=15}"
: "${HCV_CONFIG:=$EDGE_ROOT/config/default.yaml}"

sleep "${HCV_BOOT_DELAY_SEC}"

cd "$EDGE_ROOT"
# shellcheck source=/dev/null
source .venv/bin/activate
exec python -m app.record_session --config "${HCV_CONFIG}"
