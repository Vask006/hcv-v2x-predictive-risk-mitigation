#!/usr/bin/env bash
# Prune old video files under recording.output_base. Run from systemd timer or cron.
set -euo pipefail

EDGE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [ -f /etc/default/hcv-record ]; then
  # shellcheck source=/dev/null
  . /etc/default/hcv-record
fi

: "${HCV_CONFIG:=$EDGE_ROOT/config/default.yaml}"

cd "$EDGE_ROOT"
# shellcheck source=/dev/null
source .venv/bin/activate
exec python -m app.prune_recordings --config "${HCV_CONFIG}" "$@"
