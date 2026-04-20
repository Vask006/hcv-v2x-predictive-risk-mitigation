#!/usr/bin/env bash
# Fix 203/EXEC on hcv-record: ensure bash runs the script, strip CRLF, chmod +x.
# Usage (from edge/): bash deploy/install-hcv-record-service.sh
set -euo pipefail
EDGE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UNIT_SRC="$EDGE_ROOT/deploy/hcv-record.service"
UNIT_DST="/etc/systemd/system/hcv-record.service"
START="$EDGE_ROOT/deploy/hcv-record-start.sh"

echo "Installing $UNIT_SRC -> $UNIT_DST"
sudo cp "$UNIT_SRC" "$UNIT_DST"
sudo sed -i 's/\r$//' "$UNIT_DST"
chmod +x "$START"

if [ -d /etc/systemd/system/hcv-record.service.d ]; then
  echo "Warning: drop-ins override the unit. List: ls /etc/systemd/system/hcv-record.service.d/"
  echo "To remove overrides: sudo rm -rf /etc/systemd/system/hcv-record.service.d"
fi

sudo systemctl daemon-reload
echo "Done. Restart: sudo systemctl restart hcv-record.service"
echo "Verify: systemctl cat hcv-record.service | grep ExecStart"
